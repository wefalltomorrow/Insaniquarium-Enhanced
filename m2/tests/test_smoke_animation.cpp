#include "../SmokeAnimation.hpp"
#include "../SmokePixels.hpp"
#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
using namespace EnhancedM2;
void check(bool value, const char* message) {
    if (!value) { std::cerr << "FAIL " << message << "\n"; std::exit(1); }
}
struct Color { int mRed = 12, mGreen = 34, mBlue = 56, mAlpha = 199; };
struct Image {
    int mWidth=0, mHeight=0, mNumCols=1, mNumRows=1, updates=0;
    bool noBits=false, fail=false;
    std::vector<std::uint32_t> bits;
    void Create(int w, int h) { mWidth=w; mHeight=h; bits.resize(w*h); }
    std::uint32_t* GetBits() {
        if (fail) throw std::bad_alloc();
        return noBits ? nullptr : bits.data();
    }
    void BitsChanged() { ++updates; }
};
struct Graphics {
    Color color; bool colorize = true; int mode = 0; double x = 2.5;
    bool fail = false;
    std::vector<std::pair<int,int>> calls;
    const Color& GetColor() { return color; }
    void SetColor(const Color& c) { color = c; }
    void DrawImageCel(Image*, int, int, int cel) {
        calls.emplace_back(cel, color.mAlpha);
        if (fail) throw std::runtime_error("draw failed");
    }
    void DrawImage(Image* im, int x, int y) { DrawImageCel(im,x,y,-99); }
};
void pixels() {
    // Independent floating-point reference over every coverage and mix weight.
    // Equal source pixels must never get the old alpha-over opacity dip.
    for (unsigned a=0;a<256;++a) for (unsigned w=0;w<=256;++w) {
        const std::uint32_t pixel=(a<<24)|0x6381bd;
        auto same=BlendSmokePixel(pixel,pixel,w);
        check((same>>24)==a,"identical coverage is invariant");
        if (a) check(same==pixel,"identical visible pixel is invariant");
        unsigned b=255-a;
        auto out=BlendSmokePixel((a<<24)|0xff0000,(b<<24)|0x0000ff,w);
        double t=w/256.0, alpha=a*(1-t)+b*t;
        check(std::abs(int(out>>24)-alpha)<=0.500001,"linear coverage reference");
        if (alpha>0) {
            check(std::abs(int((out>>16)&255)-255*a*(1-t)/alpha)<=0.500001,"premultiplied red reference");
            check(std::abs(int(out&255)-255*b*t/alpha)<=0.500001,"premultiplied blue reference");
        }
    }
    check(BlendSmokePixel(0x00ff0000,0xff0000ff,128)==0x800000ff,"transparent RGB cannot create fringe");
    check(BlendSmokePixel(0x00abcdef,0x00123456,128)==0,"transparent pair");
    Image source; source.Create(4,2); source.mNumCols=2;
    source.bits={0xffff0000,0x00ff0000,0xff0000ff,0xff0000ff,
                 0x80112233,0x00123456,0x80112233,0x00abcdef};
    const auto original=source.bits;
    SmokePixelBuffer<Image> buffer;
    SmokeFramePlan p{0,1,0.5,true};
    Image* composed=buffer.Prepare(&source,p);
    check(composed && composed->mWidth==2 && composed->mHeight==2,"cel dimensions");
    check(composed->bits==std::vector<std::uint32_t>({0xff800080,0x800000ff,0x80112233,0}),"row stride and adjacent cels");
    check(source.bits==original && source.updates==0,"source untouched");
    check(buffer.Prepare(&source,p)==composed && composed->updates==2,"buffer reused");
    source.bits[2]=0xff00ff00;
    buffer.Prepare(&source,p);
    check(composed->bits[0]==0xff808000,"fresh source data after replacement");
    source.Create(2,1); source.bits={0xff000000,0xffffffff};
    check(buffer.Prepare(&source,p)==composed && composed->mWidth==1 && composed->mHeight==1,"resize without stale cel");
    for (int mode=0; mode<9; ++mode) {
        Image bad; bad.Create(4,1); bad.mNumCols=2;
        SmokeFramePlan q{0,1,0.5,true};
        if(mode==0) bad.mNumRows=2;
        if(mode==1) bad.mWidth=3;
        if(mode==2) bad.mHeight=129;
        if(mode==3) bad.mWidth=258;
        if(mode==4) bad.noBits=true;
        if(mode==5) bad.fail=true;
        if(mode==6) q.from=-1;
        if(mode==7) q.mix=std::numeric_limits<double>::quiet_NaN();
        check(!buffer.Prepare(mode==8 ? nullptr : &bad,q) && !q.transition && q.from==q.to,"fallback updates reported plan");
    }
    for (double phase : {0.0,1.0}) {
        SmokeFramePlan q{0,1,phase,true};
        check(!buffer.Prepare(&source,q) && q.transition,"endpoint uses original asset");
    }
}
int main() {
    pixels();
    SmokeAnimationHistory h;
    auto plan = [&](int age=4, int cel=1, double blend=0.5, bool enabled=true,
                    bool paused=false, int type=6, int delay=0, int cols=20, int rows=1) {
        return h.Plan(enabled,paused,type,age,cel,delay,cols,rows,blend);
    };
    check(!plan().transition,"new object has no history");
    h.Capture(true,6,3,0,0);
    auto p=plan();
    check(p.transition && p.from==0 && p.to==1 && p.mix==0.5,"adjacent simulation cels blend");
    check(!plan(4,1,0.5,false).transition,"disabled");
    check(!plan(4,1,0.5,true,true).transition,"paused");
    for (int type=0;type<10;++type)
        if (type!=6) check(!plan(4,1,0.5,true,false,type).transition,"other type or changed type");
    check(!plan(4,1,0.5,true,false,6,1).transition,"delayed");
    check(!plan(4,1,0.5,true,false,6,0,1).transition,"sheet bounds");
    check(!plan(4,1,0.5,true,false,6,0,20,2).transition,"unexpected rows");
    for (double blend : {-0.1,1.1,std::numeric_limits<double>::infinity(),
                         std::numeric_limits<double>::quiet_NaN()})
        check(!plan(4,1,blend).transition,"invalid blend");
    check(!plan(5,1).transition,"nonadjacent tick");
    check(!plan(4,2).transition,"wrong animation cel");
    check(!plan(1,-1).transition,"hidden startup");
    h.valid=false;
    check(!plan().transition,"pause/load invalidation");
    // Entire original smoke lifetime at arbitrary render counts per tick.
    // All original cells stay in place; no future cell or lifetime extension.
    for (int type : {6,7}) {
        for (int age=0;age<=40;++age) {
            h.Capture(true,type,age-1,(age-1)/2-1,0);
            for (int i=0;i<=20;++i) {
                const int originalCel=age/2-1;
                auto q=h.Plan(true,false,type,age,originalCel,0,20,1,i/20.0);
                check(q.to==originalCel,"current simulation cel preserved");
                if (q.transition) {
                    check(age>=4 && age<=38 && age%2==0,"only valid cel-change ticks");
                    check(q.from==q.to-1 && q.from>=0,"bounded neighbor, no extrapolation");
                }
                check(h.age==age-1,"redraw never advances animation history");
            }
        }
    }
    h.Capture(true,6,3,0,1); check(!h.valid,"delay history rejected");
    h.Capture(true,6,3,5,0); check(!h.valid,"corrupt history rejected");
    h.Capture(false,6,3,0,0); check(!h.valid,"non M2 history rejected");
    h.Capture(true,6,3,0,0);
    Graphics g; Image image, composed;
    DrawSmokeFrames(&g,&image,plan(),&composed);
    check(g.calls.size()==1 && g.calls[0]==std::make_pair(-99,199),"one composed draw with original alpha");
    check(g.color.mAlpha==199 && g.color.mRed==12 && g.color.mGreen==34 &&
          g.color.mBlue==56 && g.colorize && g.mode==0 && g.x==2.5,"graphics restored");
    for (int endpoint : {0,1}) {
        g.calls.clear(); DrawSmokeFrames(&g,&image,plan(4,1,endpoint),static_cast<Image*>(nullptr));
        check(g.calls.size()==1 && g.calls[0]==std::make_pair(endpoint,199),"endpoint draws once");
    }
    g.calls.clear(); DrawSmokeFrames(&g,&image,plan(4,1,0.5,false),static_cast<Image*>(nullptr));
    check(g.calls.size()==1 && g.calls[0]==std::make_pair(1,199),"fallback exact original draw");
    g.fail=true;
    try { DrawSmokeFrames(&g,&image,plan(),&composed); } catch (const std::runtime_error&) {}
    check(g.color.mAlpha==199,"exception restores color");
    std::cout << "PASS smoke lifetime, pixel coverage/color reference, buffers, guards and drawing\n";
}

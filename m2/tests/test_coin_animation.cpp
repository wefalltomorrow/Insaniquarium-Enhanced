#include "../CoinAnimation.hpp"
#include "../ImageIdentity.hpp"
#include "../DebugTrace.hpp"
#include <fstream>
#include <iostream>
#include <limits>
using namespace EnhancedM2;
void Check(bool ok, const char* message) {
    if (!ok) { std::cerr << "FAIL " << message << '\n'; std::exit(1); }
}
struct Image {
    ImageIdentity mM2ImageIdentity;
    int mWidth=0, mHeight=0, mNumCols=10, mNumRows=5, mImageFlags=0, updates=0;
    std::uint32_t* mBits=nullptr;
    std::vector<std::uint32_t> bits;
    static inline bool fail=false, empty=false;
    int reads=0;
    void Create(int w, int h) { mWidth=w; mHeight=h; bits.resize(w*h); mBits=bits.data(); }
    auto* GetBits() {
        ++reads;
        if (fail) throw std::bad_alloc();
        return empty ? nullptr : mBits;
    }
    void BitsChanged() { ++updates; mM2ImageIdentity.BitsChanged(); }
};
struct Graphics {
    int draws=0, cel=-1, row=-1, x=-1, y=-1;
    void DrawImage(Image*, int a, int b) { ++draws; cel=-2; x=a; y=b; }
    void DrawImageCel(Image*, int a, int b, int c, int r) { ++draws; cel=c; row=r; x=a; y=b; }
};
int main() {
    Image source; source.Create(20,10); source.mImageFlags=7;
    for (int i=0; i<200; ++i) source.bits[i]=0xff000000 | (i * 7919);
    const auto original=source.bits;
    CoinAnimationState prev{2,3,1,2}, now{2,4,2,2};
    CoinAnimation<Image> h; CoinBlendResult result{0,0};
    auto capture=[&] { h.Capture(true,prev,&source); };
    auto draw=[&](double mix=0.5) { return h.Prepare(true,false,true,now,&source,mix,result); };
    Check(!draw() && std::string(result.reason)=="history","new owner");
    capture(); auto* out=draw();
    Check(out && out->mWidth==2 && out->mHeight==2 && out->mImageFlags==7,"bounded output and filter flags");
    for (int y=0;y<2;++y) for(int x=0;x<2;++x)
        Check(out->bits[y*2+x]==BlendSmokePixel(source.bits[40+y*20+2+x], source.bits[40+y*20+4+x],128),
              "gold row, source stride and adjacent cels");
    Check(source.bits==original && source.reads==0 && source.updates==0,"source bytes and methods untouched");
    Check(draw(0.25)==out && draw(0.75)==out,"multiple presentation draws reuse output");
    Graphics g; DrawCoinFrame(&g,&source,out,3,4,1,result);
    Check(g.draws==1 && g.cel==-2 && g.x==3 && g.y==4,"one composed draw at original coordinates");
    Check(!draw(0.0) && result.from==1 && result.mix==0.0,"exact earlier endpoint");
    DrawCoinFrame(&g,&source,static_cast<Image*>(nullptr),3,4,1,result);
    Check(g.draws==2 && g.cel==1 && g.row==1,"endpoint uses original row");
    Check(!draw(1.0) && result.to==2,"exact current endpoint");
    // Raw writes anywhere in the selected row revoke this interval, even if restored.
    capture(); source.bits[79]^=1;
    Check(!draw() && std::string(result.reason)=="pixels","unreported write caught");
    source.bits=original; source.mBits=source.bits.data();
    Check(!draw(),"revoked history cannot revive before next update");
    capture(); source.BitsChanged(); Check(!draw(),"reported mutation");
    capture(); source.mM2ImageIdentity=ImageIdentity(); Check(!draw(),"same-address replacement");
    capture(); source.mBits=nullptr; Check(!draw() && source.reads==0,"purge never recovers source");
    source.mBits=source.bits.data();
    for (int issue=0; issue<15; ++issue) {
        capture(); auto bad=now; bool enabled=true,paused=false,normal=true; double mix=0.5;
        if(issue==0) enabled=false;
        if(issue==1) paused=true;
        if(issue==2) normal=false;
        if(issue==3) bad.type=1;
        if(issue==4) bad.mode=1;
        if(issue==5) bad.divisor=4;
        if(issue==6) bad.shell=true;
        if(issue==7) bad.collected=true;
        if(issue==8) bad.fade=1;
        if(issue==9) bad.timer=6;
        if(issue==10) bad.cel=3;
        if(issue==11) mix=-0.1;
        if(issue==12) mix=1.1;
        if(issue==13) mix=std::numeric_limits<double>::quiet_NaN();
        if(issue==14) mix=std::numeric_limits<double>::infinity();
        Check(!h.Prepare(enabled,paused,normal,bad,&source,mix,result) && result.to==bad.cel && result.mix==1.0,
              "ineligible state always draws current cel");
    }
    for (int issue=0;issue<7;++issue) {
        Image bad; bad.Create(20,10);
        if(issue==0) bad.mNumCols=9;
        if(issue==1) bad.mNumRows=4;
        if(issue==2) bad.mWidth=19;
        if(issue==3) bad.mHeight=9;
        if(issue==4) bad.mWidth=730;
        if(issue==5) bad.mHeight=365;
        if(issue==6) bad.mBits=nullptr;
        h.Capture(true,prev,&bad);
        Check(!h.Prepare(true,false,true,now,&bad,0.5,result) && bad.reads==0,"layout/residency before pixel access");
    }
    capture(); source.mWidth=10; Check(!draw(),"changed layout"); source.mWidth=20;
    capture(); Image::fail=true; Check(!draw(),"allocation failure falls back"); Image::fail=false;
    capture(); Image::empty=true; Check(!draw(),"missing destination falls back"); Image::empty=false;
    capture(); h.Reset(); Check(!draw(),"serialization reset");
    // Complete original 80-tick cycles for both speeds and rows, including wrap.
    int transitions=0;
    for (int type : {1,2}) for (int divisor : {2,4}) for (int timer=0;timer<80;++timer) {
        CoinAnimationState a{type,timer,(timer/divisor)%10,divisor};
        const int next=(timer+1)%80;
        CoinAnimationState b{type,next,(next/divisor)%10,divisor};
        h.Capture(true,a,&source);
        const bool expected=next==timer+1 && b.cel==a.cel+1;
        for(double phase : {0.2,0.6,0.9}) {
            auto* p=h.Prepare(true,false,true,b,&source,phase,result);
            Check(bool(p)==expected,"entire cycle and skipped wraps");
            if(p) ++transitions;
        }
    }
    Check(transitions==324,"both rows and speed cycles exercised");
#ifdef _WIN32
    _putenv_s("INSANIQUARIUM_M2_DEBUG","1");
#else
    setenv("INSANIQUARIUM_M2_DEBUG","1",1);
#endif
    {
        M2Debug::Recorder r; r.Begin(16,0.5,1); r.SimTick();
        for(int i=0;i<65;++i) r.CoinBlend(&source,1,4,2,1,2,0.5,"composed");
        r.End(1,true,true,16,1,0); r.Begin(16,0.5,0);
        r.CoinBlend(&source,1,4,2,2,2,1.0,"pixels"); r.End(0,true,true,16,1,0);
    }
    std::ifstream log("M2DebugCoinBlend.csv"); std::string line; int lines=0;
    while(std::getline(log,line)) ++lines;
    Check(lines==66,"coin blend recorder bounded independently to 64 rows/frame");
    std::cout << "PASS coin composition, full cycles, boundaries, raw mutation, lifetime, residency, failures and telemetry\n";
}

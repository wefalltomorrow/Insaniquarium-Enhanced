#include "../SmokeAnimation.hpp"
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
struct Image {};
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
};
int main() {
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
    Graphics g; Image image;
    DrawSmokeFrames(&g,&image,plan());
    check(g.calls.size()==2 && g.calls[0]==std::make_pair(0,99) &&
          g.calls[1]==std::make_pair(1,100),"two valid cells with rounded complementary alpha");
    check(g.color.mAlpha==199 && g.color.mRed==12 && g.color.mGreen==34 &&
          g.color.mBlue==56 && g.colorize && g.mode==0 && g.x==2.5,"graphics restored");
    for (int endpoint : {0,1}) {
        g.calls.clear(); DrawSmokeFrames(&g,&image,plan(4,1,endpoint));
        check(g.calls.size()==1 && g.calls[0]==std::make_pair(endpoint,199),"endpoint draws once");
    }
    g.calls.clear(); DrawSmokeFrames(&g,&image,plan(4,1,0.5,false));
    check(g.calls.size()==1 && g.calls[0]==std::make_pair(1,199),"fallback exact original draw");
    g.fail=true;
    try { DrawSmokeFrames(&g,&image,plan()); } catch (const std::runtime_error&) {}
    check(g.color.mAlpha==199,"exception restores color");
    std::cout << "PASS smoke lifetime, guards, render-only transitions and color restoration\n";
}

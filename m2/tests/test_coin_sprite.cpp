#include "../CoinSpriteTrace.hpp"
#include <fstream>
#include <sstream>
#include <vector>
#include <string>

static void Check(bool ok) { if (!ok) { std::fputs("Coin sprite test failed\n", stderr); std::exit(1); } }
static void Enable(bool enabled) {
#ifdef _WIN32
    _putenv_s("INSANIQUARIUM_M2_DEBUG", enabled ? "1" : "0");
#else
    setenv("INSANIQUARIUM_M2_DEBUG", enabled ? "1" : "0", 1);
#endif
}
struct Image { int mWidth=720, mHeight=360, mNumCols=10, mNumRows=5; };
struct Rect { int mX=1, mY=2, mWidth=640, mHeight=480; };
struct Color { int mRed=17, mGreen=34, mBlue=51, mAlpha=102; };
struct Graphics {
    float mTransX=120.5f, mTransY=-0.25f, mScaleX=1.5f, mScaleY=2;
    float mScaleOrigX=320, mScaleOrigY=240;
    Rect mClipRect; Color color;
    bool colorized=false;
    bool GetColorizeImages() { return colorized; }
    const Color& GetColor() { return color; }
    int GetDrawMode() { return 0; }
};
static std::vector<std::string> Fields(const std::string& s) {
    std::vector<std::string> v; std::istringstream in(s); std::string part;
    while (std::getline(in, part, ',')) v.push_back(part);
    return v;
}
int main() {
    std::remove("M2DebugCoinSprites.csv");
    Enable(false);
    {
        M2Debug::Recorder r;
        Check(r.NewCoinLifetime()==0);
        r.Begin(16,0,0);
        // Disabled helper must not dereference even a missing graphics context.
        Image im;
        M2Debug::RecordCoinSprite(r, static_cast<Graphics*>(nullptr), &im,
                                &im,0,1,false,2,0,0,0,false,false,0);
    }
    Check(!std::ifstream("M2DebugCoinSprites.csv").good());
    Enable(true);
    {
        M2Debug::Recorder r; Graphics g; Image im;
        auto first=r.NewCoinLifetime(), second=r.NewCoinLifetime();
        Check(first>0 && second>first);
        r.Begin(16,0,1); r.SimTick();
        for (int i=0;i<65;++i)
            M2Debug::RecordCoinSprite(r,&g,&im,&im,first,1,false,2,0,0,0,false,false,0);
        // Recorder owns an independent budget from the smoke and object files.
        r.SmokeAnimation(&im,6,4,1,0,1,0.5,true,false);
        r.End(1,true,true,16,1,0);
        r.Begin(16,0,0);
        g.colorized=true;
        M2Debug::RecordCoinSprite(r,&g,&im,&im,second,9,true,3,1,20,20,true,true,2);
        Check(g.color.mAlpha==102 && g.mTransX==120.5f && g.colorized);
        r.End(0,true,true,16,1,0);
    }
    std::ifstream in("M2DebugCoinSprites.csv"); std::string line;
    Check(bool(std::getline(in,line))); auto header=Fields(line); Check(header.size()==37);
    int rows=0;
    while (std::getline(in,line)) {
        auto f=Fields(line); Check(f.size()==header.size()); ++rows;
        Check(f[8]=="0" && f[27]=="0");
        Check(f[17]=="120.5" && f[18]=="-0.25" && f[19]=="1.5");
        if (rows==1) Check(f[3]=="1" && f[7]=="IMAGE_MONEY" && f[29]=="255" && f[32]=="255");
        if (rows==65) Check(f[0]=="1" && f[1]=="1" && f[3]=="2" &&
                           f[7]=="IMAGE_SHELLS" && f[29]=="17" && f[32]=="102" &&
                           f[34]=="1" && f[35]=="1" && f[36]=="2");
    }
    Check(rows==65);
    std::ifstream events("M2DebugEvents.csv"); int drops=0;
    while (std::getline(events,line)) if(line.find("coin_sprite_frame_budget_exceeded")!=std::string::npos) ++drops;
    Check(drops==1);
    std::puts("PASS coin sprite identities, disabled path, resolved state, independent budget and read-only capture");
}

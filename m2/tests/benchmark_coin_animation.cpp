#include "CoinAnimation.hpp"
#include "ImageIdentity.hpp"
#include <chrono>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
using namespace EnhancedM2;
using Clock = std::chrono::steady_clock;
// CPU-only stand-in: no texture upload, renderer, disk IO or game callbacks.
struct Image {
    ImageIdentity mM2ImageIdentity;
    int mWidth=0, mHeight=0, mNumCols=10, mNumRows=6, mImageFlags=0;
    std::uint32_t* mBits=nullptr;
    std::vector<std::uint32_t> bits;
    void Create(int w,int h) { mWidth=w; mHeight=h; bits.resize(w*h); mBits=bits.data(); }
    auto* GetBits() { return mBits; }
    void BitsChanged() { mM2ImageIdentity.BitsChanged(); }
};
void Require(bool ok) { if (!ok) { std::cerr << "Benchmark correctness check failed\n"; std::exit(1); } }
std::uint32_t Random(std::uint32_t& s) { s^=s<<13; s^=s>>17; s^=s<<5; return s; }
int main(int argc,char** argv) {
    int samples=31;
    if(argc==2 && std::string(argv[1])=="--quick") samples=5;
    else if(argc!=1) { std::cerr << "Usage: M2CoinBenchmark [--quick]\n"; return 2; }
    std::cout << "profile,owners,operation,samples,median_us,p95_us,payload_bytes,checksum\n";
    std::uint64_t checksum=0;
    for(const std::string profile : {"opaque","equal_partial","mixed_alpha","masked"}) {
        Image source; source.Create(720,432);
        std::uint32_t seed=0x12345678;
        for(int y=0;y<432;++y) for(int x=0;x<720;++x) {
            const auto r=Random(seed);
            const unsigned alpha=profile=="opaque" ? 255 : profile=="equal_partial" ? 127 :
                profile=="mixed_alpha" ? r>>24 : ((x%72-36)*(x%72-36)+(y%72-36)*(y%72-36)<900 ? 255 : 0);
            source.bits[y*720+x]=(r&0xffffffu)|(alpha<<24);
        }
        const auto original=source.bits;
        for(int count : {1,32,128}) {
            std::vector<CoinAnimation<Image>> history(count);
            std::vector<Image*> outputs(count,nullptr);
            std::vector<CoinBlendResult> results(count, CoinBlendResult{0,0});
            auto previous=[](int i) { return CoinAnimationState{1+i%2,3,1,2}; };
            auto current=[](int i) { return CoinAnimationState{1+i%2,4,2,2}; };
            for(const std::string operation : {"capture","transition","endpoint","held","disabled"}) {
                const bool capture=operation=="capture", held=operation=="held", enabled=operation!="disabled";
                std::vector<double> times;
                for(int sample=-3;sample<samples;++sample) {
                    for(int i=0;i<count;++i) {
                        auto before=previous(i);
                        if(held) before.timer=2;
                        history[i].Capture(true,before,&source);
                    }
                    const double phase=operation=="endpoint" ? 1.0 : 0.1+0.8*(sample+3)/(samples+3);
                    const auto start=Clock::now();
                    for(int i=0;i<count;++i) {
                        if(capture) history[i].Capture(true,previous(i),&source);
                        else {
                            auto now=current(i);
                            // A held interval uses divisor 2, timer 2 -> 3.
                            if(held) now={1+i%2,3,1,2};
                            outputs[i]=history[i].Prepare(enabled,false,true,now,&source,phase,results[i]);
                        }
                    }
                    const double us=std::chrono::duration<double,std::micro>(Clock::now()-start).count();
                    if(sample>=0) times.push_back(us);
                    for(int i=0;i<count;++i) {
                        if(capture) {
                            outputs[i]=history[i].Prepare(true,false,true,current(i),&source,phase,results[i]);
                        }
                        if(capture || operation=="transition") {
                            Require(outputs[i]!=nullptr);
                            Require(std::string(results[i].reason)=="composed");
                            for(auto pixel:outputs[i]->bits) checksum+=pixel;
                        } else {
                            Require(outputs[i]==nullptr);
                            Require(std::string(results[i].reason)==(held ? "held" : enabled ? "endpoint" : "disabled"));
                        }
                    }
                }
                std::sort(times.begin(),times.end());
                std::cout << profile << "," << count << "," << operation << "," << samples << ","
                    << std::fixed << std::setprecision(3) << times[times.size()/2] << ","
                    << times[(times.size()*95+99)/100-1] << "," << count*72*72*11*4 << "," << checksum << "\n";
            }
        }
        Require(source.bits==original);
    }
}

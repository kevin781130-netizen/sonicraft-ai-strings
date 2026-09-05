#include "portable_rng_v27.h"
#include <cmath>
#include <sstream>
namespace Sonicraft::ParityV27 {
static constexpr double PI=3.1415926535897932384626433832795;
uint64_t fnv1a64(const std::string& s){uint64_t h=1469598103934665603ull;for(unsigned char c:s){h^=c;h*=1099511628211ull;}return h;}
static uint64_t splitmix64(uint64_t x){x+=0x9E3779B97F4A7C15ull;uint64_t z=x;z=(z^(z>>30))*0xBF58476D1CE4E5B9ull;z=(z^(z>>27))*0x94D049BB133111EBull;return z^(z>>31);}
static double uniform01(uint64_t& state){state=splitmix64(state);return (double(state>>11)+0.5)/double(1ull<<53);}
std::vector<float> normalArray(const std::string& key,size_t n){uint64_t st=fnv1a64(key);std::vector<float> out(n);size_t i=0;while(i<n){double u1=uniform01(st),u2=uniform01(st);if(u1<1e-15)u1=1e-15;double r=std::sqrt(-2.0*std::log(u1)),th=2.0*PI*u2;out[i++]=float(r*std::cos(th));if(i<n)out[i++]=float(r*std::sin(th));}return out;}
std::string eventSeedKey(int64_t s,int64_t e,uint32_t sr,int part,int voice,const std::vector<ProductShell::TimelineEvent>& events){std::ostringstream o;o<<"v27|s="<<s<<"|e="<<e<<"|sr="<<sr<<"|p="<<part<<"|v="<<voice;for(auto&x:events){o<<'|'<<x.sample<<','<<int(x.type)<<','<<int(x.part)<<','<<int(x.note)<<','<<int(x.articulation)<<','<<std::llround(double(x.velocity)*1000000.0);}return o.str();}
}

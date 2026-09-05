#include "realtime_shell_core.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <limits>
#include <numeric>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
using socket_t=SOCKET; static constexpr socket_t bad_socket=INVALID_SOCKET;
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
using socket_t=int; static constexpr socket_t bad_socket=-1;
#define closesocket close
#endif

namespace Sonicraft::ProductShell {
namespace {
#pragma pack(push,1)
struct RequestHeader { char magic[4]; uint16_t version,msgType; uint64_t requestId; int64_t startSample,endSample; uint32_t sampleRate,eventCount; uint16_t partCount,mode; float tempo,lookahead; uint32_t flags; };
struct WireEvent { int64_t projectSample; uint8_t type,part,note,articulation; float velocity,tempo; float controls[14]; };
struct ResponseHeader { char magic[4]; uint16_t version,status; uint64_t requestId; int64_t startSample; uint32_t frames,sampleRate; uint16_t channels,flags; uint64_t payloadBytes; };
#pragma pack(pop)
static_assert(sizeof(RequestHeader)==56); static_assert(sizeof(WireEvent)==76); static_assert(sizeof(ResponseHeader)==44);
constexpr uint8_t kNoteOn=1,kNoteOff=2,kKeyswitch=3,kControl=4;
constexpr uint16_t kRender=1,kPing=2,kOK=0,kCacheHit=4;

bool sendAll(socket_t s,const void* p,size_t n){auto*b=(const char*)p;while(n){int k=::send(s,b,(int)std::min<size_t>(n,1u<<20),0);if(k<=0)return false;b+=k;n-=size_t(k);}return true;}
bool recvAll(socket_t s,void* p,size_t n){auto*b=(char*)p;while(n){int k=::recv(s,b,(int)std::min<size_t>(n,1u<<20),0);if(k<=0)return false;b+=k;n-=size_t(k);}return true;}
void fill(float* d,const Controls& c){d[0]=c.dyn;d[1]=c.vib;d[2]=c.exp;d[3]=c.vol;d[4]=c.pan;d[5]=c.sus;d[6]=c.leg;d[7]=c.room;d[8]=c.bend;d[9]=c.art;d[10]=c.transition;d[11]=c.tightness;d[12]=c.attack;d[13]=c.speedProfile;}
uint32_t flagsFor(const Policy&p){return uint32_t(std::clamp(p.assist,0,2)) | (uint32_t(std::clamp(p.style,0,5))<<2) | (uint32_t(p.smartDynamics?1:0)<<5) | (uint32_t(p.smartArticulation?1:0)<<6) | (uint32_t(p.polyphony?1:0)<<7) | (uint32_t(std::clamp(p.retakeTarget,0,7))<<8) | (uint32_t(std::clamp(p.retakeNonce,0,255))<<11) | (uint32_t(std::clamp(p.stagePerspective,0,3))<<19) | (uint32_t(std::clamp(int(p.retakeAmount*15.f+.5f),0,15))<<21) | (uint32_t(p.multiOut?1:0)<<25) | (uint32_t(p.midiAuthorityLock?1:0)<<26) | (uint32_t(p.phraseDirector?1:0)<<27) | (uint32_t(std::clamp(int(p.ensembleLooseness*15.f+.5f),0,15))<<28);}
void applyCc(Controls& c,int cc,int v){float x=std::clamp(v/127.f,0.f,1.f);switch(cc){case 1:c.dyn=x;break;case 3:c.vib=x;break;case 11:c.exp=x;break;case 7:c.vol=x;break;case 10:c.pan=x;break;case 64:c.sus=x>=.5f?1.f:0.f;break;case 68:c.leg=x>=.5f?1.f:0.f;break;case 91:c.room=x;break;case 20:c.speedProfile=(v<32?0.f:(v<64?1.f/3.f:(v<96?2.f/3.f:1.f)));break;default:break;}}
void u16(std::ofstream& f,uint16_t v){f.put(char(v&255));f.put(char((v>>8)&255));}
void u32(std::ofstream& f,uint32_t v){for(int i=0;i<4;++i)f.put(char((v>>(8*i))&255));}
struct SocketInit { SocketInit(){
#ifdef _WIN32
WSADATA w{};WSAStartup(MAKEWORD(2,2),&w);
#endif
} ~SocketInit(){
#ifdef _WIN32
WSACleanup();
#endif
}};
}

void Timeline::reset(){std::lock_guard<std::mutex> g(mu);events.clear();for(auto& p:active)p.fill(false);for(auto& p:deferredOff)p.fill(false);sustainDown.fill(false);for(auto& a:arts)a=0;ctrl={};}
void Timeline::setSelectedPart(int p){std::lock_guard<std::mutex> g(mu);selected=std::clamp(p,0,3);}
int Timeline::selectedPart()const{std::lock_guard<std::mutex> g(mu);return selected;}
void Timeline::setArticulation(int part,int art){std::lock_guard<std::mutex> g(mu);part=std::clamp(part,0,3);arts[part]=std::clamp(art,0,11);ctrl[part].art=arts[part]/11.f;}
int Timeline::articulation(int part)const{std::lock_guard<std::mutex> g(mu);return arts[std::clamp(part,0,3)];}
void Timeline::pushNote(bool on,int part,int note,int velocity,int64_t sample,float tempo){std::lock_guard<std::mutex> g(mu);part=std::clamp(part,0,3);note=std::clamp(note,0,127);active[part][note]=on;TimelineEvent e{};e.sample=sample;e.type=on?kNoteOn:kNoteOff;e.part=uint8_t(part);e.note=uint8_t(note);e.articulation=uint8_t(arts[part]);e.velocity=on?std::clamp(velocity/127.f,0.f,1.f):0.f;e.tempo=tempo;e.controls=ctrl[part];events.push_back(e);}
void Timeline::pushMidiShort(uint8_t st,uint8_t d1,uint8_t d2,int64_t sample,float tempo){
    const int kind=st&0xF0, ch=st&0x0F;std::lock_guard<std::mutex> g(mu);int part=(ch<4)?ch:selected;
    if(kind==0x90 && d2>0){if(d1>=24&&d1<36){arts[part]=int(d1-24);ctrl[part].art=arts[part]/11.f;TimelineEvent e{};e.sample=sample;e.type=kKeyswitch;e.part=uint8_t(part);e.note=d1;e.articulation=uint8_t(arts[part]);e.tempo=tempo;e.controls=ctrl[part];events.push_back(e);}else{deferredOff[part][d1]=false;active[part][d1]=true;TimelineEvent e{};e.sample=sample;e.type=kNoteOn;e.part=uint8_t(part);e.note=d1;e.articulation=uint8_t(arts[part]);e.velocity=d2/127.f;e.tempo=tempo;e.controls=ctrl[part];events.push_back(e);}return;}
    if(kind==0x80 || (kind==0x90&&d2==0)){if(sustainDown[part]){deferredOff[part][d1]=true;active[part][d1]=true;return;}active[part][d1]=false;deferredOff[part][d1]=false;TimelineEvent e{};e.sample=sample;e.type=kNoteOff;e.part=uint8_t(part);e.note=d1;e.articulation=uint8_t(arts[part]);e.tempo=tempo;e.controls=ctrl[part];events.push_back(e);return;}
    if(kind==0xB0){bool wasSus=sustainDown[part];applyCc(ctrl[part],d1,d2);if(d1==64)sustainDown[part]=(d2>=64);TimelineEvent e{};e.sample=sample;e.type=kControl;e.part=uint8_t(part);e.articulation=uint8_t(arts[part]);e.tempo=tempo;e.controls=ctrl[part];events.push_back(e);if(d1==64&&wasSus&&!sustainDown[part]){for(int n=0;n<128;++n)if(deferredOff[part][n]){deferredOff[part][n]=false;active[part][n]=false;TimelineEvent off{};off.sample=sample;off.type=kNoteOff;off.part=uint8_t(part);off.note=uint8_t(n);off.articulation=uint8_t(arts[part]);off.tempo=tempo;off.controls=ctrl[part];events.push_back(off);}}return;}
    if(kind==0xE0){int v=int(d1)|(int(d2)<<7);ctrl[part].bend=std::clamp(v/16383.f,0.f,1.f);TimelineEvent e{};e.sample=sample;e.type=kControl;e.part=uint8_t(part);e.articulation=uint8_t(arts[part]);e.tempo=tempo;e.controls=ctrl[part];events.push_back(e);}
}
std::vector<TimelineEvent> Timeline::contextFor(int64_t start,int64_t end,int64_t lookback)const{std::lock_guard<std::mutex> g(mu);const int64_t lo=start-std::max<int64_t>(0,lookback);std::vector<TimelineEvent> out;out.reserve(events.size());for(const auto&e:events)if(e.sample>=lo&&e.sample<=end)out.push_back(e);return out;}
bool Timeline::anyActiveNotes()const{std::lock_guard<std::mutex> g(mu);for(const auto&p:active)for(bool b:p)if(b)return true;return false;}
std::array<Controls,4> Timeline::controlsSnapshot()const{std::lock_guard<std::mutex> g(mu);return ctrl;}

bool RendererClient::ping(uint32_t sr)const{SocketInit init;socket_t s=::socket(AF_INET,SOCK_STREAM,0);if(s==bad_socket)return false;sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(uint16_t(std::clamp(port_,1,65535)));if(inet_pton(AF_INET,host_.c_str(),&a.sin_addr)!=1||::connect(s,(sockaddr*)&a,sizeof(a))!=0){closesocket(s);return false;}RequestHeader h{{'S','A','I','R'},1,kPing,1,0,1,sr,0,4,1,72.f,.1f,0};bool ok=sendAll(s,&h,sizeof(h));ResponseHeader r{};ok=ok&&recvAll(s,&r,sizeof(r))&&std::memcmp(r.magic,"SAOR",4)==0&&r.version==1;closesocket(s);return ok;}

bool RendererClient::render(const std::vector<TimelineEvent>& events,int64_t start,int64_t end,uint32_t sr,const Policy&p,uint64_t req,RenderAudio& out)const{
    if(events.empty()||end<=start)return false;SocketInit init;socket_t s=::socket(AF_INET,SOCK_STREAM,0);if(s==bad_socket)return false;sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(uint16_t(std::clamp(port_,1,65535)));if(inet_pton(AF_INET,host_.c_str(),&a.sin_addr)!=1||::connect(s,(sockaddr*)&a,sizeof(a))!=0){closesocket(s);return false;}
    RequestHeader h{{'S','A','I','R'},1,kRender,req,start,end,sr,uint32_t(events.size()),4,uint16_t(std::clamp(p.mode,1,2)),p.tempo,p.lookahead,flagsFor(p)};std::vector<WireEvent>w(events.size());for(size_t i=0;i<events.size();++i){const auto&e=events[i];auto&z=w[i];z.projectSample=e.sample;z.type=e.type;z.part=e.part;z.note=e.note;z.articulation=e.articulation;z.velocity=e.velocity;z.tempo=e.tempo;fill(z.controls,e.controls);}bool ok=sendAll(s,&h,sizeof(h))&&sendAll(s,w.data(),w.size()*sizeof(WireEvent));ResponseHeader r{};ok=ok&&recvAll(s,&r,sizeof(r));if(!ok||std::memcmp(r.magic,"SAOR",4)||r.version!=1||(r.status!=kOK&&r.status!=kCacheHit)||(r.channels!=2&&r.channels!=24&&r.channels!=34)||r.payloadBytes!=uint64_t(r.frames)*r.channels*sizeof(float)){closesocket(s);return false;}out.sampleRate=r.sampleRate;out.frames=r.frames;out.channels=r.channels;out.status=r.status;out.interleaved.resize(size_t(r.frames)*r.channels);ok=recvAll(s,out.interleaved.data(),size_t(r.payloadBytes));closesocket(s);return ok;
}

std::vector<float> mixToStereo(const RenderAudio&a,const MixerState&m){std::vector<float> y(size_t(a.frames)*2,0.f);if(a.channels!=2&&a.channels!=24&&a.channels!=34)return y;for(uint32_t i=0;i<a.frames;++i){const size_t b=size_t(i)*a.channels;float l=a.interleaved[b]*m.master,r=a.interleaved[b+1]*m.master;if(a.channels==24||a.channels==34){const int pairs=std::min(16,(int(a.channels)-2)/2);for(int k=0;k<pairs;++k){float g=std::max(0.f,m.feed[k]);l+=a.interleaved[b+2+2*k]*g;r+=a.interleaved[b+3+2*k]*g;}}const float norm=std::max(1.f,m.master+.65f*std::accumulate(m.feed.begin(),m.feed.end(),0.f));l=(l/norm)*m.output;r=(r/norm)*m.output;y[2*i]=std::tanh(l);y[2*i+1]=std::tanh(r);}return y;}
bool writePcm16Wav(const std::string&path,const std::vector<float>&x,uint32_t sr){if(x.size()%2)return false;uint32_t bytes=uint32_t(x.size()*2);std::ofstream f(path,std::ios::binary);if(!f)return false;f.write("RIFF",4);u32(f,36+bytes);f.write("WAVEfmt ",8);u32(f,16);u16(f,1);u16(f,2);u32(f,sr);u32(f,sr*4);u16(f,4);u16(f,16);f.write("data",4);u32(f,bytes);for(float v:x){int s=int(std::lround(std::clamp(v,-1.f,1.f)*32767.f));u16(f,uint16_t(int16_t(s)));}return bool(f);}
const char* feedName(int i){static const char* n[]={"Spot L","Spot C","Spot R","Tree L","Tree C","Tree R","Wide L","Wide R","Room L","Room R","Rear","Mid L","Mid R","Far L","Far R","Gallery"};return(i>=0&&i<16)?n[i]:"?";}

} // namespace Sonicraft::ProductShell

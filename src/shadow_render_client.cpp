#include "shadow_render_client.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <deque>
#include <limits>
#include <vector>
#include <thread>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib,"Ws2_32.lib")
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
using SOCKET=int;
static constexpr int INVALID_SOCKET=-1,SOCKET_ERROR=-1;
static int closesocket(int s){return ::close(s);}
#endif

namespace Sonicraft::AIStrings {
namespace {
#pragma pack(push,1)
struct RequestHeader {
    char magic[4]; uint16_t version,type; uint64_t requestId; int64_t startSample,endSample;
    uint32_t sampleRate,eventCount; uint16_t partCount,mode; float tempoBpm,lookahead; uint32_t flags;
};
struct WireEvent {
    int64_t projectSample; uint8_t type,part,note,articulation; float velocity,tempoBpm; float controls[14];
};
struct ResponseHeader {
    char magic[4]; uint16_t version,status; uint64_t requestId; int64_t startSample; uint32_t frames,sampleRate; uint16_t channels,flags; uint64_t payloadBytes;
};
struct JudgeConfigV37 { float baseNonce; uint8_t favoriteMask,rejectMask; uint16_t reserved; };
struct JudgePayloadV37 { uint16_t version; uint8_t winner,validMask; float values[24]; };
struct JudgePayloadV38 { uint16_t version; uint8_t winner,validMask; float values[34]; uint32_t profileHash32; };
#pragma pack(pop)
static_assert(sizeof(RequestHeader)==56); static_assert(sizeof(WireEvent)==76); static_assert(sizeof(ResponseHeader)==44);
static_assert(sizeof(JudgeConfigV37)==8); static_assert(sizeof(JudgePayloadV37)==100); static_assert(sizeof(JudgePayloadV38)==144);

enum : uint16_t { kRender=1,kJudge=3,kStatusOK=0,kStatusModelNotReady=1,kStatusCacheHit=4 };

bool sendAll(SOCKET s,const void* p,size_t n){const char* c=(const char*)p;while(n){int k=::send(s,c,(int)std::min(n,size_t(1<<20)),0);if(k<=0)return false;c+=k;n-=k;}return true;}
bool recvAll(SOCKET s,void* p,size_t n){char* c=(char*)p;while(n){int k=::recv(s,c,(int)std::min(n,size_t(1<<20)),0);if(k<=0)return false;c+=k;n-=k;}return true;}
void fillControls(float* d,const ShadowControls& c){d[0]=c.dyn;d[1]=c.vib;d[2]=c.exp;d[3]=c.vol;d[4]=c.pan;d[5]=c.sus;d[6]=c.leg;d[7]=c.room;d[8]=c.bend;d[9]=c.art;d[10]=c.transition;d[11]=c.tightness;d[12]=c.attack;d[13]=c.speedProfile;}
}

bool ShadowAudioCache::install(int64_t start,uint32_t sampleRate,uint32_t frames,uint16_t channels,std::vector<float>&& audio){
    if((channels!=2&&channels!=24&&channels!=34)||audio.size()!=size_t(frames)*size_t(channels)||frames==0)return false;
    const int a=active.load(std::memory_order_acquire); int target=-1;
    for(int pass=0;pass<2&&target<0;++pass){
        for(int i=0;i<kSlots;++i){
            if(pass==0&&i==a)continue;
            bool expected=false;
            if(!slots[i].writing.compare_exchange_strong(expected,true,std::memory_order_acq_rel))continue;
            if(slots[i].readers.load(std::memory_order_acquire)==0){target=i;break;}
            slots[i].writing.store(false,std::memory_order_release);
        }
    }
    if(target<0)return false;
    auto& s=slots[target];
    s.startSample=start;s.sampleRate=sampleRate;s.frames=frames;s.channels=channels;s.interleaved=std::move(audio);s.generation=generation.fetch_add(1,std::memory_order_acq_rel)+1;
    active.store(target,std::memory_order_release);
    s.writing.store(false,std::memory_order_release);
    return true;
}

void ShadowAudioCache::mix(float* left,float* right,float* const* auxLeft,float* const* auxRight,int auxPairs,int32_t n,int64_t projectStart,float wet,float crossfadeMs) noexcept{
    if(!left||!right||n<=0||wet<=0.f)return;
    wet=std::clamp(wet,0.f,1.f);auxPairs=std::clamp(auxPairs,0,16);
    int chosen=-1; uint64_t bestGen=0;
    for(int i=0;i<kSlots;++i){
        auto& s=slots[i];
        if(s.writing.load(std::memory_order_acquire))continue;
        s.readers.fetch_add(1,std::memory_order_acq_rel);
        if(s.writing.load(std::memory_order_acquire)){s.readers.fetch_sub(1,std::memory_order_release);continue;}
        const int64_t clipEnd=s.startSample+(int64_t)s.frames;
        const bool overlap=s.frames>0&&s.sampleRate>0&&!s.interleaved.empty()&&projectStart<clipEnd&&projectStart+n>s.startSample;
        if(overlap&&s.generation>=bestGen){
            if(chosen>=0)slots[chosen].readers.fetch_sub(1,std::memory_order_release);
            chosen=i;bestGen=s.generation;
        }else s.readers.fetch_sub(1,std::memory_order_release);
    }
    if(chosen<0)return;
    auto& q=slots[chosen]; const int64_t clipEnd=q.startSample+(int64_t)q.frames;const size_t channels=q.channels;
    const int fade=std::max(1,int(q.sampleRate*crossfadeMs*.001f));
    for(int32_t i=0;i<n;++i){
        const int64_t ps=projectStart+i;if(ps<q.startSample||ps>=clipEnd)continue;
        const size_t k=size_t(ps-q.startSample);float edge=1.f;
        if((int64_t)k<fade)edge=float(k)/float(fade);
        const int64_t rem=clipEnd-ps-1;if(rem<fade)edge=std::min(edge,float(std::max<int64_t>(0,rem))/float(fade));
        const float w=wet*std::clamp(edge,0.f,1.f);const size_t base=k*channels;
        left[i]=left[i]*(1.f-w)+q.interleaved[base]*w;right[i]=right[i]*(1.f-w)+q.interleaved[base+1]*w;
        if(channels==24 || channels==34){
            const int availablePairs = std::max(0, (int(channels)-2)/2);
            for(int a=0;a<std::min(auxPairs,availablePairs);++a){
                if(!auxLeft||!auxRight||!auxLeft[a]||!auxRight[a])continue;
                const size_t off=base+2u+size_t(a)*2u;
                auxLeft[a][i]=auxLeft[a][i]*(1.f-w)+q.interleaved[off]*w;
                auxRight[a][i]=auxRight[a][i]*(1.f-w)+q.interleaved[off+1]*w;
            }
        }
    }
    q.readers.fetch_sub(1,std::memory_order_release);
}

ShadowRenderClient::ShadowRenderClient(){
#ifdef _WIN32
    WSADATA w{};WSAStartup(MAKEWORD(2,2),&w);
#endif
    worker=std::thread([this]{workerMain();});
}
ShadowRenderClient::~ShadowRenderClient(){stop.store(true,std::memory_order_release);const intptr_t raw=activeSocket.exchange(-1,std::memory_order_acq_rel);if(raw>=0){
#ifdef _WIN32
    ::shutdown((SOCKET)raw,SD_BOTH);
#else
    ::shutdown((SOCKET)raw,SHUT_RDWR);
#endif
}if(worker.joinable())worker.join();
#ifdef _WIN32
    WSACleanup();
#endif
}
void ShadowRenderClient::setRuntimeState(int m,float mix,float look,float assist,float style,float smartDyn,float smartArt,float target,float amount,float nonce,float stage,float poly,float authority,float phrase,float looseness,bool wantMultiOut,bool isPlaying,int64_t projectStart,int32_t blockSamples,float tempo) noexcept{
    mode.store(std::clamp(m,0,2));aiMix.store(std::clamp(mix,0.f,1.f));lookAhead.store(std::clamp(look,0.f,1.f));assistProfile.store(std::clamp(int(std::round(assist*2.f)),0,2));performanceStyle.store(std::clamp(int(std::round(style*5.f)),0,5));smartDynamics.store(smartDyn>=.5f);smartArticulation.store(smartArt>=.5f);retakeTarget.store(std::clamp(int(std::round(target*7.f)),0,7));retakeAmount.store(std::clamp(amount,0.f,1.f));retakeNonce.store(std::clamp(int(std::round(nonce*255.f)),0,255));stagePerspective.store(std::clamp(int(std::round(stage*3.f)),0,3));polyphony.store(poly>=.5f);midiAuthorityLock.store(authority>=.5f);phraseDirector.store(phrase>=.5f);ensembleLooseness.store(std::clamp(looseness,0.f,1.f));multiOut.store(wantMultiOut);playing.store(isPlaying);latestProjectStart.store(projectStart);latestProjectEnd.store(projectStart+blockSamples);tempoBpm.store(std::max(24.f,tempo));
}
void ShadowRenderClient::pushMidi(EventType type,int64_t projectSample,int part,int note,int articulation,float velocity,float tempo,const ShadowControls& c) noexcept{ShadowEvent e{};e.projectSample=projectSample;e.type=uint8_t(type);e.part=uint8_t(std::clamp(part,0,3));e.note=uint8_t(std::clamp(note,0,127));e.articulation=uint8_t(std::clamp(articulation,0,11));e.velocity=velocity;e.tempoBpm=tempo;e.controls=c;eventRing.push(e);}
void ShadowRenderClient::pushControl(int64_t projectSample,int part,float tempo,const ShadowControls& c) noexcept{pushMidi(Control,projectSample,part,0,int(std::round(c.art*11.f)),0.f,tempo,c);}
void ShadowRenderClient::resetTimeline(int64_t projectSample) noexcept{ShadowControls c{};pushMidi(Reset,projectSample,0,0,0,0.f,tempoBpm.load(),c);}
void ShadowRenderClient::requestTakeJudge(int64_t startSample,int64_t endSample,float baseNonce,uint8_t favoriteMask,uint8_t rejectMask,uint64_t configToken,uint32_t policyFlags,int judgeMode,float judgeTempo,float judgeLookAhead,bool personalEnabled,float personalStrength) noexcept{
    if(endSample<=startSample)return;
    judgeStart.store(startSample,std::memory_order_relaxed);judgeEnd.store(endSample,std::memory_order_relaxed);
    judgeBaseNonce.store(std::clamp(baseNonce,0.f,1.f),std::memory_order_relaxed);
    judgeReviewMasks.store(uint32_t(favoriteMask&0x0F)| (uint32_t(rejectMask&0x0F)<<8),std::memory_order_relaxed);
    judgePendingToken.store(configToken,std::memory_order_relaxed);
    judgePendingFlags.store(policyFlags,std::memory_order_relaxed);judgePendingMode.store(std::clamp(judgeMode,1,2),std::memory_order_relaxed);
    judgePendingTempo.store(std::max(24.f,judgeTempo),std::memory_order_relaxed);judgePendingLook.store(std::clamp(judgeLookAhead,0.f,1.f),std::memory_order_relaxed);judgePendingPersonalEnabled.store(personalEnabled,std::memory_order_relaxed);judgePendingPersonalStrength.store(std::clamp(personalStrength,0.f,1.f),std::memory_order_relaxed);
    judgePending.store(true,std::memory_order_release);
}
TakeJudgeSnapshotV37 ShadowRenderClient::takeJudgeSnapshot() const noexcept{
    TakeJudgeSnapshotV37 out{};
    for(int tries=0;tries<3;++tries){
        const uint32_t g0=judgeGeneration.load(std::memory_order_acquire);
        out.generation=g0;out.startSample=judgeResultStart.load(std::memory_order_relaxed);out.configToken=judgeResultToken.load(std::memory_order_relaxed);out.winner=judgeWinner.load(std::memory_order_relaxed);
        out.validMask=uint8_t(judgeValidMask.load(std::memory_order_relaxed)&0x0F);
        for(int i=0;i<4;++i){
            out.overall[i]=judgeOverall[i].load(std::memory_order_relaxed);
            out.dynamics[i]=judgeDynamics[i].load(std::memory_order_relaxed);
            out.attack[i]=judgeAttack[i].load(std::memory_order_relaxed);
            out.transition[i]=judgeTransition[i].load(std::memory_order_relaxed);
            out.stability[i]=judgeStability[i].load(std::memory_order_relaxed);
            out.safety[i]=judgeSafety[i].load(std::memory_order_relaxed);out.personal[i]=judgePersonal[i].load(std::memory_order_relaxed);
        }
        out.profileHash32=judgeProfileHash32.load(std::memory_order_relaxed);out.profileConfidence=judgeProfileConfidence.load(std::memory_order_relaxed);for(int i=0;i<5;++i)out.profileWeights[i]=judgeProfileWeights[i].load(std::memory_order_relaxed);
        if(g0==judgeGeneration.load(std::memory_order_acquire))break;
    }
    return out;
}
void ShadowRenderClient::mix(float* l,float* r,float* const* auxLeft,float* const* auxRight,int auxPairs,int32_t n,int64_t ps) noexcept{const int m=mode.load(std::memory_order_relaxed);if(m<=0)return;float wet=(m>=2)?1.f:std::max(.15f,aiMix.load(std::memory_order_relaxed));cache.mix(l,r,auxLeft,auxRight,auxPairs,n,ps,wet,22.f);}

bool ShadowRenderClient::requestRender(const std::vector<ShadowEvent>& events,int64_t start,int64_t end,uint64_t reqId,int m,float tempo,float look){
    if(events.empty()||end<=start)return false;
    SOCKET s=::socket(AF_INET,SOCK_STREAM,0);if(s==INVALID_SOCKET){ready.store(false);return false;}activeSocket.store((intptr_t)s,std::memory_order_release);
#ifdef _WIN32
    DWORD timeout=120000;setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,(const char*)&timeout,sizeof(timeout));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,(const char*)&timeout,sizeof(timeout));
#else
    timeval tv{120,0};setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof(tv));
#endif
    sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(49337);inet_pton(AF_INET,"127.0.0.1",&a.sin_addr);if(::connect(s,(sockaddr*)&a,sizeof(a))==SOCKET_ERROR){activeSocket.store(-1,std::memory_order_release);closesocket(s);ready.store(false);return false;}
    const uint32_t flags=(uint32_t)(assistProfile.load(std::memory_order_relaxed)&0x3) | ((uint32_t)(performanceStyle.load(std::memory_order_relaxed)&0x7)<<2) | ((uint32_t)(smartDynamics.load(std::memory_order_relaxed)?1:0)<<5) | ((uint32_t)(smartArticulation.load(std::memory_order_relaxed)?1:0)<<6) | ((uint32_t)(polyphony.load(std::memory_order_relaxed)?1:0)<<7) | ((uint32_t)(retakeTarget.load(std::memory_order_relaxed)&0x7)<<8) | ((uint32_t)(retakeNonce.load(std::memory_order_relaxed)&0xFF)<<11) | ((uint32_t)(stagePerspective.load(std::memory_order_relaxed)&0x3)<<19) | ((uint32_t)std::clamp(int(retakeAmount.load(std::memory_order_relaxed)*15.f+.5f),0,15)<<21) | ((uint32_t)(multiOut.load(std::memory_order_relaxed)?1:0)<<25) | ((uint32_t)(midiAuthorityLock.load(std::memory_order_relaxed)?1:0)<<26) | ((uint32_t)(phraseDirector.load(std::memory_order_relaxed)?1:0)<<27) | ((uint32_t)std::clamp(int(ensembleLooseness.load(std::memory_order_relaxed)*15.f+.5f),0,15)<<28);
    RequestHeader h{{'S','A','I','R'},1,kRender,reqId,start,end,(uint32_t)std::max(8000.0,sr.load()),(uint32_t)events.size(),4,(uint16_t)m,tempo,look,flags};
    std::vector<WireEvent> wire(events.size());for(size_t i=0;i<events.size();++i){const auto&e=events[i];auto&w=wire[i];w.projectSample=e.projectSample;w.type=e.type;w.part=e.part;w.note=e.note;w.articulation=e.articulation;w.velocity=e.velocity;w.tempoBpm=e.tempoBpm;fillControls(w.controls,e.controls);}
    if(!sendAll(s,&h,sizeof(h))||!sendAll(s,wire.data(),wire.size()*sizeof(WireEvent))){activeSocket.store(-1,std::memory_order_release);closesocket(s);ready.store(false);return false;}
    ResponseHeader rh{};if(!recvAll(s,&rh,sizeof(rh))||std::memcmp(rh.magic,"SAOR",4)!=0||rh.version!=1){activeSocket.store(-1,std::memory_order_release);closesocket(s);ready.store(false);return false;}
    if(rh.status==kStatusModelNotReady){ready.store(false);activeSocket.store(-1,std::memory_order_release);closesocket(s);return false;}
    if((rh.status!=kStatusOK&&rh.status!=kStatusCacheHit)||(rh.channels!=2&&rh.channels!=24&&rh.channels!=34)||rh.payloadBytes!=uint64_t(rh.frames)*uint64_t(rh.channels)*sizeof(float)||rh.frames>uint32_t(sr.load()*46.0)){activeSocket.store(-1,std::memory_order_release);closesocket(s);return false;}
    std::vector<float> audio(size_t(rh.frames)*size_t(rh.channels));if(!recvAll(s,audio.data(),rh.payloadBytes)){activeSocket.store(-1,std::memory_order_release);closesocket(s);return false;}activeSocket.store(-1,std::memory_order_release);closesocket(s);ready.store(true);renderCount.fetch_add(1);if(rh.status==kStatusCacheHit)hitCount.fetch_add(1);return cache.install(rh.startSample,rh.sampleRate,rh.frames,rh.channels,std::move(audio));
}

bool ShadowRenderClient::requestJudgeRender(const std::vector<ShadowEvent>& events,int64_t start,int64_t end,uint64_t reqId,int m,float tempo,float look,float baseNonce,uint8_t favoriteMask,uint8_t rejectMask,uint64_t configToken,uint32_t policyFlags,bool personalEnabled,float personalStrength){
    if(events.empty()||end<=start)return false;
    SOCKET s=::socket(AF_INET,SOCK_STREAM,0);if(s==INVALID_SOCKET){ready.store(false);return false;}activeSocket.store((intptr_t)s,std::memory_order_release);
#ifdef _WIN32
    DWORD timeout=120000;setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,(const char*)&timeout,sizeof(timeout));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,(const char*)&timeout,sizeof(timeout));
#else
    timeval tv{120,0};setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,&tv,sizeof(tv));
#endif
    sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(49337);inet_pton(AF_INET,"127.0.0.1",&a.sin_addr);
    if(::connect(s,(sockaddr*)&a,sizeof(a))==SOCKET_ERROR){activeSocket.store(-1,std::memory_order_release);closesocket(s);ready.store(false);return false;}
    const uint32_t flags=policyFlags;
    RequestHeader h{{'S','A','I','R'},1,kJudge,reqId,start,end,(uint32_t)std::max(8000.0,sr.load()),(uint32_t)events.size(),4,(uint16_t)m,tempo,look,flags};
    const uint16_t personalBits=uint16_t(0x8000u|(personalEnabled?0x4000u:0u)|uint16_t(std::clamp(int(personalStrength*255.f+.5f),0,255)));
    JudgeConfigV37 cfg{std::clamp(baseNonce,0.f,1.f),uint8_t(favoriteMask&0x0F),uint8_t(rejectMask&0x0F),personalBits};
    std::vector<WireEvent> wire(events.size());for(size_t i=0;i<events.size();++i){const auto&e=events[i];auto&w=wire[i];w.projectSample=e.projectSample;w.type=e.type;w.part=e.part;w.note=e.note;w.articulation=e.articulation;w.velocity=e.velocity;w.tempoBpm=e.tempoBpm;fillControls(w.controls,e.controls);}
    if(!sendAll(s,&h,sizeof(h))||!sendAll(s,&cfg,sizeof(cfg))||!sendAll(s,wire.data(),wire.size()*sizeof(WireEvent))){activeSocket.store(-1,std::memory_order_release);closesocket(s);return false;}
    ResponseHeader rh{};if(!recvAll(s,&rh,sizeof(rh))||std::memcmp(rh.magic,"SAOR",4)!=0||rh.version!=1||rh.status!=kStatusOK||(rh.payloadBytes!=sizeof(JudgePayloadV37)&&rh.payloadBytes!=sizeof(JudgePayloadV38))){activeSocket.store(-1,std::memory_order_release);closesocket(s);return false;}
    JudgePayloadV37 p37{};JudgePayloadV38 p38{};const float* values=nullptr;uint8_t winner=255,validMask=0;const bool personalPayload=rh.payloadBytes==sizeof(JudgePayloadV38);
    if(personalPayload){if(!recvAll(s,&p38,sizeof(p38))||p38.version!=2){activeSocket.store(-1);closesocket(s);return false;}values=p38.values;winner=p38.winner;validMask=p38.validMask;}else{if(!recvAll(s,&p37,sizeof(p37))||p37.version!=1){activeSocket.store(-1);closesocket(s);return false;}values=p37.values;winner=p37.winner;validMask=p37.validMask;}
    activeSocket.store(-1,std::memory_order_release);closesocket(s);ready.store(true);judgeResultStart.store(rh.startSample,std::memory_order_relaxed);judgeResultToken.store(configToken,std::memory_order_relaxed);judgeWinner.store(winner==255?-1:int(winner),std::memory_order_relaxed);judgeValidMask.store(validMask&0x0F,std::memory_order_relaxed);
    for(int take=0;take<4;++take){const int base=take*6;judgeOverall[take].store(values[base]);judgeDynamics[take].store(values[base+1]);judgeAttack[take].store(values[base+2]);judgeTransition[take].store(values[base+3]);judgeStability[take].store(values[base+4]);judgeSafety[take].store(values[base+5]);judgePersonal[take].store(personalPayload?p38.values[24+take]:values[base]);}
    if(personalPayload){judgeProfileConfidence.store(p38.values[28]);for(int i=0;i<5;++i)judgeProfileWeights[i].store(p38.values[29+i]);judgeProfileHash32.store(p38.profileHash32);}else{judgeProfileConfidence.store(0);for(int i=0;i<5;++i)judgeProfileWeights[i].store(0);judgeProfileHash32.store(0);}
    judgeGeneration.fetch_add(1,std::memory_order_release);
    return true;
}

void ShadowRenderClient::workerMain(){
    std::deque<ShadowEvent> history;uint64_t req=1;auto last=std::chrono::steady_clock::now()-std::chrono::seconds(2);
    while(!stop.load(std::memory_order_acquire)){
        ShadowEvent e;bool got=false;while(eventRing.pop(e)){got=true;if(e.type==Reset){history.clear();continue;}history.push_back(e);}
        const double sampleRate=std::max(8000.0,sr.load());const int64_t nowEnd=latestProjectEnd.load();const int64_t keepFrom=nowEnd-int64_t(sampleRate*90.0);while(!history.empty()&&history.front().projectSample<keepFrom)history.pop_front();
        const int m=mode.load();const bool play=playing.load();const auto now=std::chrono::steady_clock::now();const bool due=(now-last)>std::chrono::milliseconds(m>=2?180:350);
        if(judgePending.exchange(false,std::memory_order_acq_rel)&&!history.empty()){
            const int64_t js=judgeStart.load(std::memory_order_relaxed),je=judgeEnd.load(std::memory_order_relaxed);
            const double beatSec=60.0/std::max(24.f,tempoBpm.load());
            const int64_t contextStart=js-int64_t(sampleRate*std::clamp(4.0*beatSec,1.0,4.0));
            std::vector<ShadowEvent> jv;jv.reserve(history.size());
            for(const auto&x:history)if(x.projectSample>=contextStart&&x.projectSample<=je)jv.push_back(x);
            const uint32_t masks=judgeReviewMasks.load(std::memory_order_relaxed);
            const uint64_t judgeToken=judgePendingToken.load(std::memory_order_relaxed);
            const uint32_t judgeFlags=judgePendingFlags.load(std::memory_order_relaxed);
            const int judgeMode=judgePendingMode.load(std::memory_order_relaxed);
            const float judgeTempo=judgePendingTempo.load(std::memory_order_relaxed),judgeLook=judgePendingLook.load(std::memory_order_relaxed);
            if(!jv.empty())requestJudgeRender(jv,js,je,req++,judgeMode,judgeTempo,judgeLook,
                                             judgeBaseNonce.load(std::memory_order_relaxed),uint8_t(masks&0x0F),uint8_t((masks>>8)&0x0F),judgeToken,judgeFlags,judgePendingPersonalEnabled.load(std::memory_order_relaxed),judgePendingPersonalStrength.load(std::memory_order_relaxed));
        }
        if(m>0&&play&&due&&!history.empty()){
            int64_t start=history.front().projectSample;for(const auto&x:history){if(x.type==NoteOn){start=x.projectSample;break;}}
            start=std::max(start,nowEnd-int64_t(sampleRate*6.0));const float look=lookAhead.load();const int64_t tail=int64_t(sampleRate*(.25+.75*std::clamp(look,0.f,1.f)));const int64_t end=nowEnd+tail;
            // v1.8 phrase memory: send up to eight beats of score/control look-back while
            // keeping the requested audio start unchanged. No protocol/version expansion.
            const double beatSec=60.0/std::max(24.f,tempoBpm.load());
            const double ctxSec=std::clamp(8.0*beatSec,2.0,8.0);
            const int64_t contextStart=start-int64_t(sampleRate*ctxSec);
            std::vector<ShadowEvent> v;v.reserve(history.size());for(const auto&x:history)if(x.projectSample>=contextStart&&x.projectSample<=end)v.push_back(x);
            if(!v.empty())requestRender(v,start,end,req++,m,tempoBpm.load(),look);
            last=now;
        }
        if(!got)std::this_thread::sleep_for(std::chrono::milliseconds(8));
    }
}

} // namespace

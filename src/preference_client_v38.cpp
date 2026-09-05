#include "preference_client_v38.h"
#include <algorithm>
#include <chrono>
#include <cstring>
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
using SOCKET=int; static constexpr int INVALID_SOCKET=-1,SOCKET_ERROR=-1; static int closesocket(int s){return ::close(s);}
#endif
namespace Sonicraft::AIStrings { namespace {
#pragma pack(push,1)
struct Req{char magic[4];uint16_t ver,type;uint64_t id;int64_t a,b;uint32_t sr,ne;uint16_t pc,mode;float tempo,look;uint32_t flags;};
struct Resp{char magic[4];uint16_t ver,status;uint64_t id;int64_t start;uint32_t frames,sr;uint16_t ch,flags;uint64_t bytes;};
struct Pref{uint8_t kind,take;uint16_t reserved;float metrics[24];};
struct Prof{uint16_t ver,reserved;uint64_t hash;float confidence,evidence,weights[5];};
#pragma pack(pop)
static_assert(sizeof(Req)==56&&sizeof(Resp)==44&&sizeof(Pref)==100&&sizeof(Prof)==40);
bool sendAll(SOCKET s,const void*p,size_t n){auto*c=(const char*)p;while(n){int k=::send(s,c,(int)n,0);if(k<=0)return false;c+=k;n-=k;}return true;}
bool recvAll(SOCKET s,void*p,size_t n){auto*c=(char*)p;while(n){int k=::recv(s,c,(int)n,0);if(k<=0)return false;c+=k;n-=k;}return true;}
bool connectLocal(SOCKET&s){s=::socket(AF_INET,SOCK_STREAM,0);if(s==INVALID_SOCKET)return false;sockaddr_in x{};x.sin_family=AF_INET;x.sin_port=htons(49337);inet_pton(AF_INET,"127.0.0.1",&x.sin_addr);if(::connect(s,(sockaddr*)&x,sizeof(x))==SOCKET_ERROR){closesocket(s);return false;}return true;}
}
PreferenceClientV38::PreferenceClientV38(){
#ifdef _WIN32
WSADATA w{};WSAStartup(MAKEWORD(2,2),&w);
#endif
worker=std::thread([this]{workerMain();});}
PreferenceClientV38::~PreferenceClientV38(){stop.store(true);if(worker.joinable())worker.join();
#ifdef _WIN32
WSACleanup();
#endif
}
void PreferenceClientV38::record(int kind,int take,const TakeJudgeSnapshotV37&s) noexcept{if(kind<1||kind>3||take<0||take>3||s.generation==0)return;PreferenceEventWireV38 e{};e.kind=(uint8_t)kind;e.take=(uint8_t)take;for(int i=0;i<4;++i){int b=i*6;e.metrics[b]=s.overall[i];e.metrics[b+1]=s.dynamics[i];e.metrics[b+2]=s.attack[i];e.metrics[b+3]=s.transition[i];e.metrics[b+4]=s.stability[i];e.metrics[b+5]=s.safety[i];}ring.push(e);}
void PreferenceClientV38::clear() noexcept{clearPending.store(true);}
PreferenceProfileV38 PreferenceClientV38::snapshot() const noexcept{PreferenceProfileV38 p{};p.hash=hash.load();p.confidence=confidence.load();p.evidence=evidence.load();for(int i=0;i<5;++i)p.weights[i]=weights[i].load();return p;}
bool PreferenceClientV38::sendEvent(const PreferenceEventWireV38&e,uint64_t id){SOCKET s;if(!connectLocal(s))return false;Req h{{'S','A','I','R'},1,4,id,0,0,48000,0,0,0,68.f,0.f,0};Pref p{};p.kind=e.kind;p.take=e.take;for(int i=0;i<24;++i)p.metrics[i]=e.metrics[i];if(!sendAll(s,&h,sizeof(h))||!sendAll(s,&p,sizeof(p))){closesocket(s);return false;}Resp r{};Prof q{};bool ok=recvAll(s,&r,sizeof(r))&&r.status==0&&r.bytes==sizeof(q)&&recvAll(s,&q,sizeof(q))&&q.ver==1;closesocket(s);if(!ok)return false;hash.store(q.hash);confidence.store(q.confidence);evidence.store(q.evidence);for(int i=0;i<5;++i)weights[i].store(q.weights[i]);return true;}
bool PreferenceClientV38::query(uint64_t id,bool clearProfile){SOCKET s;if(!connectLocal(s))return false;Req h{{'S','A','I','R'},1,(uint16_t)(clearProfile?6:5),id,0,0,48000,0,0,0,68.f,0.f,0};if(!sendAll(s,&h,sizeof(h))){closesocket(s);return false;}Resp r{};Prof q{};bool ok=recvAll(s,&r,sizeof(r))&&r.status==0&&r.bytes==sizeof(q)&&recvAll(s,&q,sizeof(q))&&q.ver==1;closesocket(s);if(!ok)return false;hash.store(q.hash);confidence.store(q.confidence);evidence.store(q.evidence);for(int i=0;i<5;++i)weights[i].store(q.weights[i]);return true;}
void PreferenceClientV38::workerMain(){std::deque<PreferenceEventWireV38>retry;uint64_t req=1;auto last=std::chrono::steady_clock::now()-std::chrono::seconds(3);while(!stop.load()){if(clearPending.exchange(false)){retry.clear();query(req++,true);}PreferenceEventWireV38 e{};while(ring.pop(e)){if(retry.size()>=64)retry.pop_front();retry.push_back(e);}if(!retry.empty()&&sendEvent(retry.front(),req++))retry.pop_front();auto now=std::chrono::steady_clock::now();if(now-last>std::chrono::seconds(2)){query(req++,false);last=now;}std::this_thread::sleep_for(std::chrono::milliseconds(40));}}
}

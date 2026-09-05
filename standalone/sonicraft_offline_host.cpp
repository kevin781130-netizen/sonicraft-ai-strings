#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include <cmath>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib,"ws2_32.lib")
using socket_t=SOCKET;
static constexpr socket_t bad_socket=INVALID_SOCKET;
#else
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
using socket_t=int;
static constexpr socket_t bad_socket=-1;
#define closesocket close
#endif
#pragma pack(push,1)
struct RequestHeader { char magic[4]; uint16_t version,msgType; uint64_t requestId; int64_t startSample,endSample; uint32_t sampleRate,eventCount; uint16_t partCount,mode; float tempo,lookahead; uint32_t flags; };
struct WireEvent { int64_t projectSample; uint8_t type,part,note,articulation; float velocity,tempo; float controls[14]; };
struct ResponseHeader { char magic[4]; uint16_t version,status; uint64_t requestId; int64_t startSample; uint32_t frames,sampleRate; uint16_t channels,flags; uint64_t payloadBytes; };
#pragma pack(pop)
static_assert(sizeof(RequestHeader)==56); static_assert(sizeof(WireEvent)==76); static_assert(sizeof(ResponseHeader)==44);

static bool sendAll(socket_t s,const void* p,size_t n){auto* b=(const char*)p;while(n){int k=::send(s,b,(int)std::min<size_t>(n,1u<<20),0);if(k<=0)return false;b+=k;n-=size_t(k);}return true;}
static bool recvAll(socket_t s,void* p,size_t n){auto* b=(char*)p;while(n){int k=::recv(s,b,(int)std::min<size_t>(n,1u<<20),0);if(k<=0)return false;b+=k;n-=size_t(k);}return true;}
static void u16(std::ofstream& f,uint16_t v){f.put(char(v&255));f.put(char((v>>8)&255));}
static void u32(std::ofstream& f,uint32_t v){for(int i=0;i<4;++i)f.put(char((v>>(8*i))&255));}
static bool writeWav(const std::string& path,const std::vector<float>& x,uint32_t sr,uint16_t ch){
  if(ch==0||x.size()%ch)return false;
  const uint32_t dataBytes=uint32_t(x.size()*2);
  std::ofstream f(path,std::ios::binary); if(!f)return false; f.write("RIFF",4);u32(f,36+dataBytes);f.write("WAVEfmt ",8);u32(f,16);u16(f,1);u16(f,ch);u32(f,sr);u32(f,sr*ch*2);u16(f,ch*2);u16(f,16);f.write("data",4);u32(f,dataBytes);
  for(float v:x){int s=int(std::lround(std::clamp(v,-1.f,1.f)*32767.f));u16(f,uint16_t(int16_t(s)));} return bool(f);
}
int main(int argc,char** argv){
  int note=69,part=0,mode=2,port=49337; double seconds=2.0,tempo=72.0; uint32_t sr=48000; std::string out="sonicraft_standalone.wav",host="127.0.0.1"; bool multi=false;
  for(int i=1;i<argc;++i){std::string a=argv[i];auto next=[&](){if(i+1>=argc){std::cerr<<"missing value for "<<a<<"\n";std::exit(2);}return std::string(argv[++i]);};
    if(a=="--note")note=std::stoi(next()); else if(a=="--part")part=std::stoi(next()); else if(a=="--seconds")seconds=std::stod(next()); else if(a=="--tempo")tempo=std::stod(next()); else if(a=="--sr")sr=uint32_t(std::stoul(next())); else if(a=="--out")out=next(); else if(a=="--host")host=next(); else if(a=="--port")port=std::stoi(next()); else if(a=="--auto")mode=1; else if(a=="--multiout")multi=true; else if(a=="--help"){std::cout<<"SONICRAFT standalone render host --note 69 --part 0 --seconds 2 --out out.wav [--host 127.0.0.1 --port 49337] [--auto] [--multiout]\n";return 0;}}
  note=std::clamp(note,0,127);part=std::clamp(part,0,3);seconds=std::clamp(seconds,.08,30.0); const int64_t end=int64_t(std::llround(seconds*sr));
#ifdef _WIN32
  WSADATA w{}; if(WSAStartup(MAKEWORD(2,2),&w)!=0)return 3;
#endif
  socket_t s=::socket(AF_INET,SOCK_STREAM,0); if(s==bad_socket){std::cerr<<"socket failed\n";return 3;} sockaddr_in a{};a.sin_family=AF_INET;a.sin_port=htons(uint16_t(std::clamp(port,1,65535)));inet_pton(AF_INET,host.c_str(),&a.sin_addr);
  if(::connect(s,(sockaddr*)&a,sizeof(a))!=0){std::cerr<<"renderer service unavailable\n";closesocket(s);return 4;}
  RequestHeader h{{'S','A','I','R'},1,1,230001,0,end,sr,2,4,uint16_t(mode),float(tempo),.25f,multi?(1u<<25):0u};
  std::array<WireEvent,2> ev{}; std::array<float,14> c{.66f,.42f,.91f,.84f,.5f,1.f,1.f,.2f,.5f,0.f,.5f,.5f,.38f,0.f};
  ev[0].projectSample=0;ev[0].type=1;ev[0].part=uint8_t(part);ev[0].note=uint8_t(note);ev[0].velocity=.78f;ev[0].tempo=float(tempo);std::copy(c.begin(),c.end(),ev[0].controls);
  ev[1]=ev[0];ev[1].projectSample=std::max<int64_t>(1,end-1);ev[1].type=2;ev[1].velocity=0.f;
  if(!sendAll(s,&h,sizeof(h))||!sendAll(s,ev.data(),sizeof(ev))){std::cerr<<"send failed\n";closesocket(s);return 5;} ResponseHeader r{}; if(!recvAll(s,&r,sizeof(r))||std::memcmp(r.magic,"SAOR",4)||r.version!=1){std::cerr<<"bad response\n";closesocket(s);return 6;}
  if((r.status!=0&&r.status!=4)||(r.channels!=2&&r.channels!=24&&r.channels!=34)||r.payloadBytes!=uint64_t(r.frames)*r.channels*sizeof(float)){std::cerr<<"renderer status="<<r.status<<" channels="<<r.channels<<"\n";closesocket(s);return 7;}
  std::vector<float> audio(size_t(r.frames)*r.channels); if(!recvAll(s,audio.data(),size_t(r.payloadBytes))){std::cerr<<"audio receive failed\n";closesocket(s);return 8;} closesocket(s);
#ifdef _WIN32
  WSACleanup();
#endif
  if(!writeWav(out,audio,r.sampleRate,r.channels)){std::cerr<<"wav write failed\n";return 9;} std::cout<<"SONICRAFT standalone PASS frames="<<r.frames<<" channels="<<r.channels<<" out="<<out<<"\n"; return 0;
}

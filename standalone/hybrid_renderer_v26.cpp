#include "hybrid_renderer_v26.h"
#include "inprocess_promotion_guard_v26.h"
#include <cstdlib>
#include <filesystem>
namespace Sonicraft::ProductShell {
namespace {std::string env(const char*k){auto*p=std::getenv(k);return p?p:"";}}
HybridRendererV26::HybridRendererV26(std::string host,int port):socket_(std::move(host),port){configureFromEnvironment();}
void HybridRendererV26::configureFromEnvironment(){native_.reset();std::filesystem::path r,d;std::string unsafe=env("SONICRAFT_INPROCESS_UNSAFE_DEV");if(unsafe=="1"){r=env("SONICRAFT_INPROCESS_RENDERER_MODEL");d=env("SONICRAFT_INPROCESS_DECODER_MODEL");}else{std::string lock=env("SONICRAFT_INPROCESS_PROMOTION_LOCK");if(lock.empty())return;InProcess::PromotionPaths pp;std::string reason;if(!InProcess::verifyPromotionLock(lock,pp,reason))return;r=pp.renderer;d=pp.decoder;}if(r.empty()||d.empty())return;auto s=InProcess::makeOrtNativeSession(r,d);if(!s||!s->ready())return;InProcess::EngineConfig cfg;std::string a=env("SONICRAFT_INPROCESS_AUTO_STEPS"),h=env("SONICRAFT_INPROCESS_HQ_STEPS");if(!a.empty())cfg.stepsAuto=std::max(1,std::atoi(a.c_str()));if(!h.empty())cfg.stepsHq=std::max(1,std::atoi(h.c_str()));native_=std::make_unique<InProcess::InProcessEngine>(std::move(s),cfg);}
bool HybridRendererV26::ping(uint32_t sr)const{return native_&&native_->ready()?true:socket_.ping(sr);}
bool HybridRendererV26::render(const std::vector<TimelineEvent>&events,int64_t start,int64_t end,uint32_t sr,const Policy&p,uint64_t req,RenderAudio&out){
    (void)req;if(native_&&native_->ready()&&sr==native_->config().sampleRate){InProcess::EngineRender y;if(native_->render(events,start,end,p,y)){out.sampleRate=y.sampleRate;out.frames=y.frames;out.channels=y.channels;out.status=0;out.interleaved=std::move(y.interleaved);return true;}}
    return socket_.render(events,start,end,sr,p,req,out);
}
std::string HybridRendererV26::backendName()const{return native_&&native_->ready()?native_->backendName():"localhost-service";}
bool HybridRendererV26::inProcessReady()const{return native_&&native_->ready();}
}

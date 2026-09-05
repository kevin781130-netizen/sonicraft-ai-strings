#include "ort_native_session_v26.h"
#include <algorithm>
#include <filesystem>
#include <fstream>
#include <sstream>
#if __has_include(<onnxruntime_cxx_api.h>)
#define SONICRAFT_HAS_ORT_NATIVE 1
#include <onnxruntime_cxx_api.h>
#else
#define SONICRAFT_HAS_ORT_NATIVE 0
#endif

namespace Sonicraft::InProcess {
#if SONICRAFT_HAS_ORT_NATIVE
namespace {
std::string fileFingerprint(const std::filesystem::path&a,const std::filesystem::path&b){
    // Release promotion performs cryptographic SHA-256. Runtime fingerprint only needs deterministic cache identity.
    std::ostringstream ss;for(auto&p:{a,b}){std::error_code ec;ss<<p.filename().string()<<':'<<std::filesystem::file_size(p,ec)<<':'<<std::filesystem::last_write_time(p,ec).time_since_epoch().count()<<';';}return ss.str();
}
class OrtNativeSession final : public NeuralSession {
public:
    OrtNativeSession(const std::filesystem::path&r,const std::filesystem::path&d)
        :env_(ORT_LOGGING_LEVEL_WARNING,"SONICRAFT"),renderer_(nullptr),decoder_(nullptr),fp_(fileFingerprint(r,d)){
        Ort::SessionOptions so;so.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);so.SetIntraOpNumThreads(1);
        // .ort and .onnx use the same public Session API. Reduced ORT builds may infer .ort automatically.
#ifdef _WIN32
        renderer_=Ort::Session(env_,r.c_str(),so);decoder_=Ort::Session(env_,d.c_str(),so);
#else
        renderer_=Ort::Session(env_,r.string().c_str(),so);decoder_=Ort::Session(env_,d.string().c_str(),so);
#endif
        auto rn=renderer_.GetOutputNameAllocated(0,allocator_);rendererOut_=rn.get();auto dn=decoder_.GetOutputNameAllocated(0,allocator_);decoderOut_=dn.get();ready_=true;
    }
    std::string name()const override{return "ort-native-inprocess";}std::string fingerprint()const override{return fp_;}bool ready()const override{return ready_;}
    bool runRenderer(const RendererInputs&in,std::vector<float>&velocity)override{
        try{if(!in.controls)return false;const auto&c=*in.controls;std::array<int64_t,3> latentShape=in.latentShape;std::array<int64_t,1> one{1};std::array<int64_t,3> rawShape{1,c.frames,kRawControls};std::array<int64_t,2> timeShape{1,c.frames};std::array<int64_t,3> ctxShape{1,kFrontierContext,c.frames};
            auto mi=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);float ft=in.flowT,fh=in.flowH;int64_t instrument=c.instrument,articulation=c.articulation,player=c.player;
            std::vector<Ort::Value> vals;vals.reserve(9);vals.emplace_back(Ort::Value::CreateTensor<float>(mi,const_cast<float*>(in.latent.data()),in.latent.size(),latentShape.data(),latentShape.size()));vals.emplace_back(Ort::Value::CreateTensor<float>(mi,&ft,1,one.data(),1));vals.emplace_back(Ort::Value::CreateTensor<float>(mi,&fh,1,one.data(),1));vals.emplace_back(Ort::Value::CreateTensor<float>(mi,const_cast<float*>(c.raw.data()),c.raw.size(),rawShape.data(),3));vals.emplace_back(Ort::Value::CreateTensor<float>(mi,const_cast<float*>(c.vibratoPhysicsKnown.data()),c.vibratoPhysicsKnown.size(),timeShape.data(),2));vals.emplace_back(Ort::Value::CreateTensor<float>(mi,const_cast<float*>(c.frontierContext.data()),c.frontierContext.size(),ctxShape.data(),3));vals.emplace_back(Ort::Value::CreateTensor<int64_t>(mi,&instrument,1,one.data(),1));vals.emplace_back(Ort::Value::CreateTensor<int64_t>(mi,&articulation,1,one.data(),1));vals.emplace_back(Ort::Value::CreateTensor<int64_t>(mi,&player,1,one.data(),1));
            // Export v2.x has articulation_curve as the 10th input; append it after player.
            vals.emplace_back(Ort::Value::CreateTensor<float>(mi,const_cast<float*>(c.articulationCurve.data()),c.articulationCurve.size(),timeShape.data(),2));
            static const char* names[]={"latent","flow_t","flow_h","controls","vibrato_physics_known","frontier_context","instrument","articulation","player","articulation_curve"};const char*outNames[]={rendererOut_.c_str()};auto y=renderer_.Run(Ort::RunOptions{nullptr},names,vals.data(),vals.size(),outNames,1);if(y.empty()||!y[0].IsTensor())return false;auto info=y[0].GetTensorTypeAndShapeInfo();size_t n=info.GetElementCount();const float*p=y[0].GetTensorData<float>();velocity.assign(p,p+n);return n==in.latent.size();
        }catch(...){return false;}}
    bool runDecoder(std::span<const float>latent,std::array<int64_t,3>shape,std::vector<float>&mono,int&sampleRate)override{
        try{auto mi=Ort::MemoryInfo::CreateCpu(OrtArenaAllocator,OrtMemTypeDefault);auto x=Ort::Value::CreateTensor<float>(mi,const_cast<float*>(latent.data()),latent.size(),shape.data(),shape.size());const char*inNames[]={"latent"};const char*outNames[]={decoderOut_.c_str()};auto y=decoder_.Run(Ort::RunOptions{nullptr},inNames,&x,1,outNames,1);if(y.empty()||!y[0].IsTensor())return false;size_t n=y[0].GetTensorTypeAndShapeInfo().GetElementCount();const float*p=y[0].GetTensorData<float>();mono.assign(p,p+n);sampleRate=48000;return !mono.empty();}catch(...){return false;}}
private:
    Ort::Env env_;Ort::AllocatorWithDefaultOptions allocator_;Ort::Session renderer_,decoder_;std::string rendererOut_,decoderOut_,fp_;bool ready_=false;
};
}
std::shared_ptr<NeuralSession> makeOrtNativeSession(const std::filesystem::path&r,const std::filesystem::path&d){try{return std::make_shared<OrtNativeSession>(r,d);}catch(...){return {};}}
bool ortNativeSdkCompiled(){return true;}
#else
std::shared_ptr<NeuralSession> makeOrtNativeSession(const std::filesystem::path&,const std::filesystem::path&){return {};}
bool ortNativeSdkCompiled(){return false;}
#endif
}

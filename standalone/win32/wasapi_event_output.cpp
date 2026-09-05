#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include "wasapi_event_output.h"
#include <windows.h>
#include <mmdeviceapi.h>
#include <audioclient.h>
#include <avrt.h>
#include <ksmedia.h>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>

namespace Sonicraft::WinAudio {
namespace {
template<class T> void rel(T*&p){if(p){p->Release();p=nullptr;}}
bool isFloat(const WAVEFORMATEX* f){if(!f)return false;if(f->wFormatTag==WAVE_FORMAT_IEEE_FLOAT&&f->wBitsPerSample==32)return true;if(f->wFormatTag==WAVE_FORMAT_EXTENSIBLE&&f->cbSize>=22){auto*x=reinterpret_cast<const WAVEFORMATEXTENSIBLE*>(f);return IsEqualGUID(x->SubFormat,KSDATAFORMAT_SUBTYPE_IEEE_FLOAT)&&f->wBitsPerSample==32;}return false;}
bool isPcm16(const WAVEFORMATEX* f){if(!f)return false;if(f->wFormatTag==WAVE_FORMAT_PCM&&f->wBitsPerSample==16)return true;if(f->wFormatTag==WAVE_FORMAT_EXTENSIBLE&&f->cbSize>=22){auto*x=reinterpret_cast<const WAVEFORMATEXTENSIBLE*>(f);return IsEqualGUID(x->SubFormat,KSDATAFORMAT_SUBTYPE_PCM)&&f->wBitsPerSample==16;}return false;}
}

bool WasapiEventOutput::openDefault(uint32_t requestedSampleRate){
    close();detail_.clear();HRESULT hr=CoInitializeEx(nullptr,COINIT_MULTITHREADED);if(SUCCEEDED(hr))coInitialized_=true;const bool coOk=SUCCEEDED(hr)||hr==RPC_E_CHANGED_MODE;IMMDeviceEnumerator* en=nullptr;IMMDevice* dev=nullptr;
    if(!coOk){detail_="CoInitializeEx failed";return false;}
    hr=CoCreateInstance(__uuidof(MMDeviceEnumerator),nullptr,CLSCTX_ALL,IID_PPV_ARGS(&en));if(FAILED(hr)){detail_="MMDeviceEnumerator failed";return false;}
    hr=en->GetDefaultAudioEndpoint(eRender,eConsole,&dev);rel(en);if(FAILED(hr)){detail_="default render endpoint unavailable";return false;}
    hr=dev->Activate(__uuidof(IAudioClient3),CLSCTX_ALL,nullptr,reinterpret_cast<void**>(&client_));rel(dev);if(FAILED(hr)){detail_="IAudioClient3 unavailable";close();return false;}
    AudioClientProperties props{};props.cbSize=sizeof(props);props.eCategory=AudioCategory_GameMedia;client_->SetClientProperties(&props);
    hr=client_->GetMixFormat(&format_);if(FAILED(hr)||!format_){detail_="GetMixFormat failed";close();return false;}
    if(format_->nChannels!=2||format_->nSamplesPerSec!=requestedSampleRate){detail_="WASAPI mix format is not 48k stereo; legacy fallback required";close();return false;}
    float32_=isFloat(format_);pcm16_=isPcm16(format_);if(!float32_&&!pcm16_){detail_="unsupported WASAPI mix sample format";close();return false;}
    UINT32 defp=0,fund=0,minp=0,maxp=0;hr=client_->GetSharedModeEnginePeriod(format_,&defp,&fund,&minp,&maxp);if(FAILED(hr)||!minp){detail_="GetSharedModeEnginePeriod failed";close();return false;}
    // Microsoft requires PeriodInFrames to be in [min,max] and a multiple of fundamental.
    periodFrames_=minp;if(fund&&periodFrames_%fund)periodFrames_=((periodFrames_+fund-1)/fund)*fund;periodFrames_=std::clamp(periodFrames_,minp,maxp);
    event_=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event_){detail_="CreateEvent failed";close();return false;}
    hr=client_->InitializeSharedAudioStream(AUDCLNT_STREAMFLAGS_EVENTCALLBACK|AUDCLNT_STREAMFLAGS_NOPERSIST,periodFrames_,format_,nullptr);if(FAILED(hr)){detail_="InitializeSharedAudioStream failed";close();return false;}
    hr=client_->SetEventHandle(static_cast<HANDLE>(event_));if(FAILED(hr)){detail_="SetEventHandle failed";close();return false;}
    hr=client_->GetBufferSize(&bufferFrames_);if(FAILED(hr)){detail_="GetBufferSize failed";close();return false;}REFERENCE_TIME hnsLatency=0;if(SUCCEEDED(client_->GetStreamLatency(&hnsLatency)))streamLatencyMs_=double(hnsLatency)/10000.0;
    hr=client_->GetService(IID_PPV_ARGS(&render_));if(FAILED(hr)){detail_="IAudioRenderClient unavailable";close();return false;}
    BYTE* p=nullptr;if(SUCCEEDED(render_->GetBuffer(bufferFrames_,&p)))render_->ReleaseBuffer(bufferFrames_,AUDCLNT_BUFFERFLAGS_SILENT);
    running_=true;ready_=true;worker_=std::thread(&WasapiEventOutput::loop,this);hr=client_->Start();if(FAILED(hr)){detail_="IAudioClient Start failed";close();return false;}
    detail_="WASAPI IAudioClient3 shared event-driven min-period";return true;
}

void WasapiEventOutput::close(){
    ready_=false;running_=false;expectAudio_=false;if(event_)SetEvent(static_cast<HANDLE>(event_));if(worker_.joinable())worker_.join();if(client_)client_->Stop();rel(render_);rel(client_);if(format_){CoTaskMemFree(format_);format_=nullptr;}if(event_){CloseHandle(static_cast<HANDLE>(event_));event_=nullptr;}std::lock_guard<std::mutex>lk(mu_);ring_.clear();bufferFrames_=periodFrames_=0;float32_=pcm16_=false;streamLatencyMs_=0.0;if(coInitialized_){CoUninitialize();coInitialized_=false;}
}

bool WasapiEventOutput::pushStereo(const std::vector<float>& x){if(!ready_||x.empty()||(x.size()&1))return false;std::lock_guard<std::mutex>lk(mu_);for(float v:x)ring_.push_back(std::clamp(v,-1.f,1.f));return true;}
size_t WasapiEventOutput::queuedFrames()const{std::lock_guard<std::mutex>lk(mu_);return ring_.size()/2;}

bool WasapiEventOutput::fillFrames(uint32_t frames,void* dst){
    if(!dst)return false;const size_t needed=size_t(frames)*2;size_t have=0;{
        std::lock_guard<std::mutex>lk(mu_);have=std::min(needed,ring_.size());
        if(float32_){auto*d=static_cast<float*>(dst);for(size_t i=0;i<have;++i){d[i]=ring_.front();ring_.pop_front();}for(size_t i=have;i<needed;++i)d[i]=0.f;}
        else {auto*d=static_cast<int16_t*>(dst);for(size_t i=0;i<have;++i){float v=ring_.front();ring_.pop_front();d[i]=int16_t(std::lround(std::clamp(v,-1.f,1.f)*32767.f));}for(size_t i=have;i<needed;++i)d[i]=0;}
    }
    if(have<needed&&expectAudio_.load())++underruns_;return have==needed;
}

void WasapiEventOutput::loop(){
    CoInitializeEx(nullptr,COINIT_MULTITHREADED);DWORD taskIndex=0;HANDLE mmcss=AvSetMmThreadCharacteristicsW(L"Pro Audio",&taskIndex);
    while(running_){DWORD w=WaitForSingleObject(static_cast<HANDLE>(event_),250);if(!running_)break;if(w!=WAIT_OBJECT_0||!client_||!render_)continue;UINT32 pad=0;if(FAILED(client_->GetCurrentPadding(&pad)))continue;UINT32 avail=bufferFrames_>pad?bufferFrames_-pad:0;if(!avail)continue;BYTE*p=nullptr;if(FAILED(render_->GetBuffer(avail,&p)))continue;fillFrames(avail,p);render_->ReleaseBuffer(avail,0);
    }
    if(mmcss)AvRevertMmThreadCharacteristics(mmcss);CoUninitialize();
}

} // namespace Sonicraft::WinAudio
#endif

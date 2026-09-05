#pragma once
#ifdef _WIN32
#include <windows.h>
#include <audioclient.h>
#include <atomic>
#include <cstdint>
#include <deque>
#include <mutex>
#include <thread>
#include <vector>
#include <string>
namespace Sonicraft::WinAudio {
class WasapiEventOutput {
public:
    ~WasapiEventOutput(){close();}
    bool openDefault(uint32_t requestedSampleRate);
    void close();
    bool pushStereo(const std::vector<float>& interleaved);
    void setActive(bool active){ expectAudio_.store(active); }
    bool ready() const { return ready_.load(); }
    uint32_t periodFrames() const { return periodFrames_; }
    double streamLatencyMs() const { return streamLatencyMs_; }
    size_t queuedFrames() const;
    uint64_t underruns() const { return underruns_.load(); }
    const char* detail() const { return detail_.c_str(); }
private:
    void loop();
    bool fillFrames(uint32_t frames, void* dst);
    std::atomic<bool> running_{false},ready_{false};
    std::thread worker_;
    mutable std::mutex mu_;
    std::deque<float> ring_;
    std::atomic<uint64_t> underruns_{0};
    std::atomic<bool> expectAudio_{false};
    void* event_=nullptr;
    IAudioClient3* client_=nullptr;
    IAudioRenderClient* render_=nullptr;
    WAVEFORMATEX* format_=nullptr;
    uint32_t bufferFrames_=0,periodFrames_=0;
    bool float32_=false,pcm16_=false,coInitialized_=false;
    double streamLatencyMs_=0.0;
    std::string detail_;
};
}
#endif

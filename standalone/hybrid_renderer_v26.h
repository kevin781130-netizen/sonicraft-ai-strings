#pragma once
#include "inprocess_neural_engine.h"
#include "ort_native_session_v26.h"
#include "realtime_shell_core.h"
#include <memory>
#include <string>
namespace Sonicraft::ProductShell {
class HybridRendererV26 {
public:
    HybridRendererV26(std::string host="127.0.0.1",int port=49337);
    void configureFromEnvironment();
    bool ping(uint32_t sr=48000) const;
    bool render(const std::vector<TimelineEvent>&events,int64_t start,int64_t end,uint32_t sr,
                const Policy&policy,uint64_t requestId,RenderAudio&out);
    std::string backendName() const;
    bool inProcessReady() const;
private:
    RendererClient socket_;
    std::unique_ptr<InProcess::InProcessEngine> native_;
};
}

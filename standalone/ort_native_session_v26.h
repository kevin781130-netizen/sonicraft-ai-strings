#pragma once
#include "inprocess_neural_engine.h"
#include <filesystem>
#include <memory>

namespace Sonicraft::InProcess {
// Returns nullptr when this build has no ONNX Runtime native SDK.
std::shared_ptr<NeuralSession> makeOrtNativeSession(const std::filesystem::path& renderer,
                                                    const std::filesystem::path& decoder);
bool ortNativeSdkCompiled();
}

#pragma once
#include "realtime_shell_core.h"
#include <cstdint>
#include <string>
#include <vector>
namespace Sonicraft::ParityV27 {
uint64_t fnv1a64(const std::string& s);
std::vector<float> normalArray(const std::string& key, size_t n);
std::string eventSeedKey(int64_t startSample,int64_t endSample,uint32_t sampleRate,int part,int voice,
                         const std::vector<ProductShell::TimelineEvent>& events);
}

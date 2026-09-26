#pragma once

#include "orchestra_conditioning_contract.h"

namespace Sonicraft::AIStrings {

class OrchestraConditionerV71 final : public IOrchestraConditioner {
public:
    void reset(double sampleRate) noexcept override;

    bool condition(
        const MusicalControlFrame& control,
        const OrchestraPerformanceState& performance,
        OrchestraConditioningFeatures& out) noexcept override;

    double sampleRate() const noexcept { return sampleRate_; }

private:
    double sampleRate_ {48000.0};
};

} // namespace Sonicraft::AIStrings

#include "orchestra_conditioning_contract.h"
#include <cassert>
#include <iostream>

using namespace Sonicraft::AIStrings;

int main() {
    static_assert(ObservedDnniBoundaryDescriptor::boundaryAccountingValid());
    static_assert(OrchestraConditioningFeatures::kObserved452 == 452);
    static_assert(OrchestraConditioningFeatures::kObserved506 == 506);
    static_assert(OrchestraConditioningFeatures::kLatent512 == 512);

    MusicalControlFrame frame{};
    assert(frame.midiPitch == 69.f);
    assert(frame.articulationBits == kArtSustain);

    OrchestraConditioningFeatures f{};
    f.branch128[0] = 1.f;
    f.feature506[0] = 2.f;
    f.clear();
    assert(f.branch128[0] == 0.f);
    assert(f.feature506[0] == 0.f);

    std::cout << "orchestra_conditioning_contract_smoke: ok\n";
    return 0;
}

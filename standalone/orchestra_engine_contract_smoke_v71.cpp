#include "orchestra_engine_contract.h"
#include <cassert>
#include <iostream>

using namespace Sonicraft::AIStrings;

int main() {
    static_assert(kOrchestraInstrumentCount == 15);
    OrchestraRenderBlock block{};
    block.performance.instrument = OrchestraInstrument::Violin;
    block.performance.tempoBpm = 96.f;
    block.performance.dynamicsCurve.push(0.f, .35f);
    block.performance.dynamicsCurve.push(4.f, .82f);
    block.performance.pitchCurve.push(0.f, 0.f);
    block.performance.pitchCurve.push(1.f, 7.f);

    OrchestraNote n{};
    n.noteId = 1;
    n.midiPitch = 69;
    n.durationBeat = 2.f;
    n.articulationBits = kArtLegato | kArtTenuto;
    assert(block.pushNote(n));
    assert(!block.valid());

    block.model.present = true;
    block.model.sourceHashVerified = true;
    block.model.weightsHashVerified = true;
    block.model.weightsOffset = 36864;
    block.model.weightsBytes = 132502456;
    assert(block.valid());

    const auto& d = orchestraInstrumentDescriptor(
        orchestraInstrumentIndexFromNormalized(
            orchestraInstrumentNormalizedFromIndex(14)));
    assert(d.instrument == OrchestraInstrument::Trombone);

    std::cout << "orchestra_engine_contract_smoke: ok\n";
    return 0;
}

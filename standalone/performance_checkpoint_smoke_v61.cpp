#include "../src/performance_checkpoint_v61.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    static_assert(kPerformanceCheckpointSchemaV61==1);
    static_assert(kCheckpointEvidenceNamespaceCountV61==5);
    static_assert(kCheckpointCompileArtifactCountV61==12);
    assert(!checkpointEmbedsAudioV61());
    assert(!checkpointEmbedsMidiBytesV61());
    assert(!checkpointReplayMutatesLiveStateV61());
    assert(checkpointRestoreIsExplicitV61());
    assert(!checkpointClaimsExactAudioReplayV61());
    assert(kCheckpointEvidenceNamespacesV61[0]=="utility_v55");
    assert(kCheckpointEvidenceNamespacesV61[4]=="mixture_v59");
    std::cout<<"SONICRAFT v6.1 performance checkpoint native contract OK\n";
    return 0;
}
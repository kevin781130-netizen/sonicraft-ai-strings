#include "../src/performance_checkpoint_v62.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    static_assert(kPerformanceCheckpointSchemaV62==1);
    static_assert(kAcousticRuntimeProvenanceSchemaV62==1);
    static_assert(kCheckpointEvidenceNamespaceCountV62==5);
    static_assert(kCheckpointCompileArtifactCountV62==12);
    assert(!checkpointEmbedsAudioV62());
    assert(!checkpointEmbedsMidiBytesV62());
    assert(!checkpointReplayMutatesLiveStateV62());
    assert(checkpointRestoreIsExplicitV62());
    assert(!checkpointClaimsExactAudioReplayV62());
    assert(checkpointBindsAcousticRuntimeV62());
    assert(checkpointBindsModelWeightsV62());
    assert(checkpointBindsRendererBuildV62());
    assert(checkpointBindsRuntimeBackendV62());
    assert(checkpointBindsDeviceCapabilityV62());
    assert(checkpointBindsRenderConfigurationV62());
    assert(kCheckpointEvidenceNamespacesV62[0]=="utility_v55");
    assert(kCheckpointEvidenceNamespacesV62[4]=="mixture_v59");
    std::cout<<"SONICRAFT v6.2 acoustic runtime provenance native contract OK\n";
    return 0;
}

#include "../src/context_similarity_transfer_v57.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(contextJaccardV57(1,2)==.5f);
    assert(contextTransferAllowedV57(true,.5f,false));
    assert(!contextTransferAllowedV57(false,.8f,false));
    assert(!contextTransferAllowedV57(true,.2f,false));
    assert(!contextTransferAllowedV57(true,.8f,true));
    const auto e=transferredEvidenceV57(10.f,.58f,1.f,1.f);
    assert(e>1.8f && e<1.9f);
    assert(!transferOnlyMayUseTop1V57(0.f));
    assert(transferOnlyMayUseTop1V57(1.5f));
    assert(falsePruneEdgeTrustV57(1.f,.06f)>.55f && falsePruneEdgeTrustV57(1.f,.06f)<.57f);
    std::cout<<"SONICRAFT v5.7 context similarity transfer native smoke OK\n";
    return 0;
}
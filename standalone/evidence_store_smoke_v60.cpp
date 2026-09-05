#include "../src/evidence_store_v60.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    static_assert(kEvidenceStoreSchemaV60==1);
    static_assert(kEvidenceNamespaceCountV60==5);
    static_assert(kEvidenceMaxCommitsV60==32);
    assert(kEvidenceNamespacesV60[0]=="utility_v55");
    assert(kEvidenceNamespacesV60[4]=="mixture_v59");
    assert(!evidenceStoreBlendsAlgorithmsV60());
    assert(!evidenceStoreIncludesRepairPolicyV49());
    assert(!evidenceStoreRequiresDOriginalChangeV60());
    std::cout<<"SONICRAFT v6.0 unified evidence store native contract OK\n";
    return 0;
}
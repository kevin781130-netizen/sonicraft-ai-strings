#include "dnni_runtime_layout.h"
#include <cassert>
#include <iostream>

using namespace Sonicraft::AIStrings;

int main() {
    const auto a = analyzeDnniObservedRuntimeLayout(132502456ull);
    assert(a.compatible && a.currentFamilyObserved);
    assert(a.candidateGroupCount == 8);
    assert(a.tailSubblockCount == 32);

    const auto b = analyzeDnniObservedRuntimeLayout(133286808ull);
    assert(b.compatible && b.currentFamilyObserved);
    assert(b.candidateGroupCount == 9);
    assert(b.tailSubblockCount == 36);

    const auto c = analyzeDnniObservedRuntimeLayout(134855512ull);
    assert(c.compatible && c.currentFamilyObserved);
    assert(c.candidateGroupCount == 11);
    assert(c.tailSubblockCount == 44);

    const auto future = analyzeDnniObservedRuntimeLayout(
        DnniObservedRuntimeLayout::kSharedCoreBytes +
        10ull * DnniObservedRuntimeLayout::kVariableGroupBytes);
    assert(future.compatible && !future.currentFamilyObserved);
    assert(future.candidateGroupCount == 10);

    assert(!analyzeDnniObservedRuntimeLayout(132502458ull).compatible);

    std::cout << "dnni_runtime_layout_smoke: ok\n";
    return 0;
}

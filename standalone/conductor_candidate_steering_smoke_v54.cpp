#include "../src/conductor_candidate_steering_v54.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    auto c=primaryBudgetV54(CandidateSectionV54::Climax);
    assert(!c.A && c.B && c.C && c.D);
    auto r=primaryBudgetV54(CandidateSectionV54::Resolution);
    assert(r.A && r.B && !r.C && r.D);
    auto b=primaryBudgetV54(CandidateSectionV54::Build);
    assert(b.A && b.B && b.C && b.D);
    assert(escalateDeferredCandidateV54(.01f));
    assert(!escalateDeferredCandidateV54(.04f));
    assert(!originalDIsSteeredV54());
    std::cout<<"SONICRAFT v5.4 conductor-steered candidate native smoke OK\n";
    return 0;
}
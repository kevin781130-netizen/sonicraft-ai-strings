#include "../src/string_selective_phrase_v51.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    assert(!selectivePhraseFallbackV51(.18f,2,.08f,.8f,.8f));
    assert(selectivePhraseFallbackV51(.60f,2,.08f,.8f,.8f));
    assert(selectivePhraseFallbackV51(.18f,2,.01f,.8f,.8f));
    assert(selectivePhraseFallbackV51(.18f,7,.08f,.8f,.8f));
    const auto f=selectiveRenderFractionV51(12.f,60.f,true);
    assert(f>.4f && f<.5f); // 4*0.2 + 1 = 1.8 full renders, 45% of v5.0 four-render round.
    std::cout<<"SONICRAFT v5.1 selective phrase native smoke OK fraction="<<f<<"\n";
    return 0;
}
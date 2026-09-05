#include "../src/string_gesture_v45.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    static_assert(kGestureAmount==122);
    assert(gestureMicroPitchFromNormalizedV45(.5f)==0.f);
    assert(gestureMicroPitchFromNormalizedV45(1.f)>49.9f);
    assert(gestureMicroPitchFromNormalizedV45(0.f)<-49.9f);
    std::cout<<"SONICRAFT v4.5 string gesture native smoke OK\n";
    return 0;
}
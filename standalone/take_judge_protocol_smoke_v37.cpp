#include "../src/retake_carousel_v32.h"
#include <cassert>
#include <cmath>
#include <cstdint>
#include <iostream>
#pragma pack(push,1)
struct JudgeConfigV37Smoke { float baseNonce; std::uint8_t favoriteMask,rejectMask; std::uint16_t reserved; };
struct JudgePayloadV37Smoke { std::uint16_t version; std::uint8_t winner,validMask; float values[24]; };
#pragma pack(pop)
int main(){
    using namespace Sonicraft::AIStrings;
    static_assert(sizeof(JudgeConfigV37Smoke)==8);
    static_assert(sizeof(JudgePayloadV37Smoke)==100);
    const float base=.37f;
    const int expected[4]={94,187,209,143};
    for(int i=0;i<4;++i){
        const int q=std::clamp(int(std::llround(double(deriveTakeNonce(base,i))*255.0)),0,255);
        assert(q==expected[i]);
    }
    std::cout<<"SONICRAFT v3.7 judge nonce/protocol smoke OK 94,187,209,143\n";
    return 0;
}

#pragma once
#include <algorithm>
#include <array>
#include <cstdint>

namespace Sonicraft::AIStrings {
// Synthetic stage perspectives derived from our own dry voice output. These
// are independently routable DAW feeds, not measured microphone recordings.
inline void renderAcousticStageFeeds(const float* masterL,const float* masterR,
                                      const std::array<float*,16>& feedsL,
                                      const std::array<float*,16>& feedsR,
                                      int frames) noexcept {
    constexpr float width[16]={.12f,.20f,.12f,.42f,.50f,.42f,.80f,.80f,.70f,.70f,.90f,.34f,.34f,.62f,.62f,.95f};
    constexpr float pan[16]={-.60f,0.f,.60f,-.40f,0.f,.40f,-.76f,.76f,-.45f,.45f,0.f,-.22f,.22f,-.38f,.38f,0.f};
    constexpr float level[16]={.75f,.88f,.75f,.67f,.76f,.67f,.52f,.52f,.43f,.43f,.34f,.61f,.61f,.37f,.37f,.29f};
    for(int feed=0;feed<16;++feed){
        if(!feedsL[feed]||!feedsR[feed])continue;
        for(int i=0;i<frames;++i){
            const float mid=.5f*(masterL[i]+masterR[i]);
            const float side=.5f*(masterL[i]-masterR[i]);
            feedsL[feed][i]=level[feed]*(mid*(1.f-pan[feed]) + side*width[feed]);
            feedsR[feed][i]=level[feed]*(mid*(1.f+pan[feed]) - side*width[feed]);
        }
    }
}
} // namespace Sonicraft::AIStrings

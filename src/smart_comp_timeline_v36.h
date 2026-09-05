#pragma once
#include "performance_memory_v35.h"
#include "retake_carousel_v32.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>

namespace Sonicraft::AIStrings {

enum SmartCompRankMode : int {
    kSmartCompConservative = 0,
    kSmartCompBalanced = 1,
    kSmartCompAdventurous = 2,
};

struct SmartTakeRank {
    int take {-1};
    float score {0.f};
    float variation {0.f};
};

inline std::uint64_t smartMix64(std::uint64_t x) noexcept {
    x += 0x9E3779B97F4A7C15ull;
    x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ull;
    x = (x ^ (x >> 27)) * 0x94D049BB133111EBull;
    return x ^ (x >> 31);
}

inline float smartSymmetricMagnitude(std::uint64_t x) noexcept {
    const std::uint64_t z=smartMix64(x);
    const double u=(static_cast<double>(z>>11)+0.5)/static_cast<double>(1ull<<53);
    return static_cast<float>(std::abs(2.0*u-1.0));
}

inline int quantizedRetakeNonceV36(float baseNonce,int take) noexcept {
    return std::clamp(static_cast<int>(std::llround(
        static_cast<double>(deriveTakeNonce(baseNonce,std::clamp(take,0,3)))*255.0)),0,255);
}

inline float retakeContractVariationV36(float baseNonce,int take,int target,float amount,
                                        bool midiAuthorityLock,std::int64_t phraseKey) noexcept {
    target=std::clamp(target,0,7);
    amount=std::clamp(amount,0.f,1.f);
    if(target==0 || amount<=0.f) return 0.f;
    const int nonce=quantizedRetakeNonceV36(baseNonce,take);
    constexpr std::array<int,6> salts{{11,23,37,41,53,67}};
    auto enabled=[&](int salt) noexcept {
        if(target==7) return salt!=41 || !midiAuthorityLock;
        if(target==1) return salt==11;
        if(target==2) return salt==23;
        if(target==3) return salt==37;
        if(target==4) return salt==41 && !midiAuthorityLock;
        if(target==5) return salt==53;
        if(target==6) return salt==67;
        return false;
    };
    float sum=0.f; int n=0;
    for(int part=0;part<4;++part) {
        for(int salt:salts) {
            if(!enabled(salt)) continue;
            // Uses the same Retake contract dimensions/salts and the same 8-bit nonce that reaches
            // the renderer. This is a deterministic variation-priority proxy, not audio-quality inference.
            std::uint64_t key=static_cast<std::uint64_t>(nonce+1);
            key ^= static_cast<std::uint64_t>(target+17)*0x9E3779B97F4A7C15ull;
            key ^= static_cast<std::uint64_t>(salt+101)*0xBF58476D1CE4E5B9ull;
            key ^= static_cast<std::uint64_t>(part+1)*0x94D049BB133111EBull;
            key ^= static_cast<std::uint64_t>(phraseKey)*0xD6E8FEB86659FD93ull;
            sum += smartSymmetricMagnitude(key); ++n;
        }
    }
    return n>0 ? std::clamp((sum/static_cast<float>(n))*amount,0.f,1.f) : 0.f;
}

inline SmartTakeRank smartRankTakeV36(const PersistentPhraseTakeComp& comp,std::int64_t phraseKey,
                                      float baseNonce,int retakeTarget,float retakeAmount,
                                      bool midiAuthorityLock,int rankMode) noexcept {
    rankMode=std::clamp(rankMode,0,2);
    const float desired = rankMode==kSmartCompConservative ? .22f :
                          (rankMode==kSmartCompBalanced ? .48f : .76f);
    PersistentTakeCompEntry entry{};
    const bool haveEntry=comp.query(phraseKey,entry);
    SmartTakeRank best{};
    float bestScore=-std::numeric_limits<float>::infinity();
    int viable=0;
    for(int take=0;take<4;++take) {
        const auto bit=static_cast<std::uint8_t>(1u<<take);
        const bool rejected=haveEntry && ((entry.rejectMask&bit)!=0);
        if(rejected) continue;
        ++viable;
        const bool favorite=haveEntry && ((entry.favoriteMask&bit)!=0);
        const float variation=retakeContractVariationV36(baseNonce,take,retakeTarget,retakeAmount,
                                                         midiAuthorityLock,phraseKey);
        const float heuristicScore=std::clamp(1.f-std::abs(variation-desired),0.f,1.f);
        float rankScore=heuristicScore;
        if(favorite) rankScore+=1.25f; // human review dominates the heuristic.
        if(haveEntry && entry.committed && entry.takeIndex==take) rankScore+=.04f; // tiny continuity tie-break.
        // Stable take-order tie-break only; does not pretend A/B/C/D have intrinsic quality.
        rankScore-=static_cast<float>(take)*1e-5f;
        if(rankScore>bestScore) {
            bestScore=rankScore;
            best={take,favorite ? 1.f : heuristicScore,variation};
        }
    }
    if(viable==0) return {-1,0.f,0.f};
    return best;
}

struct SmartTimelineWindowV36 {
    std::array<std::int64_t,8> phraseKeys{};
    int count {0};
    int cursorSlot {0};
};

inline SmartTimelineWindowV36 smartTimelineWindowV36(std::int64_t cursor,const PerformanceMemoryWindow& w) noexcept {
    SmartTimelineWindowV36 out{};
    if(!w.valid) {
        out.count=8; out.cursorSlot=3;
        for(int i=0;i<8;++i) out.phraseKeys[static_cast<std::size_t>(i)]=cursor-3+i;
        return out;
    }
    const std::int64_t total=std::max<std::int64_t>(1,std::min<std::int64_t>(8,w.lastKey-w.firstKey+1));
    std::int64_t start=cursor-3;
    const std::int64_t maxStart=std::max(w.firstKey,w.lastKey-total+1);
    start=std::clamp(start,w.firstKey,maxStart);
    out.count=static_cast<int>(total);
    for(int i=0;i<out.count;++i) out.phraseKeys[static_cast<std::size_t>(i)]=start+i;
    out.cursorSlot=static_cast<int>(std::clamp(cursor-start,std::int64_t(0),total-1));
    return out;
}

inline int uniqueFavoriteTakeV36(const PersistentPhraseTakeComp& comp,std::int64_t phraseKey) noexcept {
    PersistentTakeCompEntry e{};
    if(!comp.query(phraseKey,e)) return -1;
    int found=-1;
    for(int t=0;t<4;++t) {
        const auto bit=static_cast<std::uint8_t>(1u<<t);
        if((e.favoriteMask&bit)==0 || (e.rejectMask&bit)!=0) continue;
        if(found>=0) return -1;
        found=t;
    }
    return found;
}

} // namespace Sonicraft::AIStrings

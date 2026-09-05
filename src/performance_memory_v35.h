#pragma once
#include "persistent_take_comp_v34.h"
#include <algorithm>
#include <cmath>
#include <cstdint>

namespace Sonicraft::AIStrings {

inline std::int64_t phraseKeyStrictlyBeforeQuarterV35(double quarter,double phraseLengthQuarter) noexcept {
    const double len=std::max(0.25,phraseLengthQuarter);
    if(!std::isfinite(quarter)) return 0;
    const double q=std::nextafter(quarter,-std::numeric_limits<double>::infinity());
    return static_cast<std::int64_t>(std::floor(q/len));
}

struct PerformanceMemoryWindow {
    bool valid {false};
    std::int64_t firstKey {0};
    std::int64_t lastKey {0};
};

inline PerformanceMemoryWindow memoryWindowFromQuarters(bool valid,double startQuarter,double endQuarter,double phraseLengthQuarter) noexcept {
    PerformanceMemoryWindow w{};
    if(!valid || !std::isfinite(startQuarter) || !std::isfinite(endQuarter)) return w;
    if(endQuarter<startQuarter) std::swap(startQuarter,endQuarter);
    w.valid=true;
    w.firstKey=phraseKeyFromQuarterV34(startQuarter,phraseLengthQuarter);
    w.lastKey=endQuarter>startQuarter ? phraseKeyStrictlyBeforeQuarterV35(endQuarter,phraseLengthQuarter)
                                      : w.firstKey;
    if(w.lastKey<w.firstKey) w.lastKey=w.firstKey;
    // Browser is intentionally bounded by the persistent comp capacity.
    if(w.lastKey-w.firstKey+1>PersistentPhraseTakeComp::kCapacity)
        w.lastKey=w.firstKey+PersistentPhraseTakeComp::kCapacity-1;
    return w;
}

inline std::int64_t clampMemoryCursor(std::int64_t key,const PerformanceMemoryWindow& w) noexcept {
    if(!w.valid) return key;
    return std::clamp(key,w.firstKey,w.lastKey);
}

inline std::int64_t nextMemoryPhrase(std::int64_t current,const PerformanceMemoryWindow& w,int direction) noexcept {
    if(!w.valid) return current + (direction<0 ? -1 : 1);
    current=clampMemoryCursor(current,w);
    if(direction<0) return current<=w.firstKey ? w.lastKey : current-1;
    return current>=w.lastKey ? w.firstKey : current+1;
}

inline std::int64_t nextUnresolvedPhrase(const PersistentPhraseTakeComp& comp,std::int64_t current,
                                         const PerformanceMemoryWindow& w) noexcept {
    if(!w.valid) return current;
    const std::int64_t total=std::min<std::int64_t>(PersistentPhraseTakeComp::kCapacity,w.lastKey-w.firstKey+1);
    std::int64_t key=clampMemoryCursor(current,w);
    for(std::int64_t i=0;i<total;++i) {
        key = key>=w.lastKey ? w.firstKey : key+1;
        PersistentTakeCompEntry e{};
        if(!comp.query(key,e)) return key;
    }
    return current; // all resolved
}

struct PerformanceMemoryStatus {
    bool committed {false};
    int committedTake {-1};
    bool recallFavorite {false};
    bool recallRejected {false};
    float coverage {0.f};
    float cursorPosition {0.f};
    int totalPhrases {0};
    int committedPhrases {0};
};

inline PerformanceMemoryStatus performanceMemoryStatus(const PersistentPhraseTakeComp& comp,
                                                       std::int64_t cursorKey,int recallTake,
                                                       const PerformanceMemoryWindow& w) noexcept {
    PerformanceMemoryStatus s{};
    PersistentTakeCompEntry e{};
    if(comp.query(cursorKey,e)) {
        s.committed=e.committed;
        s.committedTake=e.committed ? static_cast<int>(e.takeIndex) : -1;
        const auto bit=static_cast<std::uint8_t>(1u<<std::clamp(recallTake,0,3));
        s.recallFavorite=(e.favoriteMask&bit)!=0;
        s.recallRejected=(e.rejectMask&bit)!=0;
    }
    if(w.valid) {
        const auto total64=std::max<std::int64_t>(1,w.lastKey-w.firstKey+1);
        s.totalPhrases=static_cast<int>(std::min<std::int64_t>(PersistentPhraseTakeComp::kCapacity,total64));
        s.committedPhrases=comp.committedCountInRange(w.firstKey,w.lastKey);
        s.coverage=std::clamp(static_cast<float>(s.committedPhrases)/static_cast<float>(s.totalPhrases),0.f,1.f);
        s.cursorPosition=s.totalPhrases<=1 ? 0.f :
            std::clamp(static_cast<float>(clampMemoryCursor(cursorKey,w)-w.firstKey)/static_cast<float>(s.totalPhrases-1),0.f,1.f);
    } else {
        s.totalPhrases=PersistentPhraseTakeComp::kCapacity;
        s.committedPhrases=comp.committedCount();
        s.coverage=std::clamp(static_cast<float>(s.committedPhrases)/static_cast<float>(PersistentPhraseTakeComp::kCapacity),0.f,1.f);
    }
    return s;
}

} // namespace Sonicraft::AIStrings

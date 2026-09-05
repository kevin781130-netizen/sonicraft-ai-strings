#pragma once
#include "retake_carousel_v32.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>

namespace Sonicraft::AIStrings {

enum TakeCompModeV34 : int {
    kTakeCompOffV34 = 0,
    kTakeCompPhraseV34 = 1,
};

struct PersistentTakeCompEntry {
    std::int64_t phraseKey {0};
    std::uint8_t takeIndex {0};
    std::uint8_t favoriteMask {0};
    std::uint8_t rejectMask {0};
    bool valid {false};
    bool committed {false};
};

inline std::int64_t phraseKeyFromQuarterV34(double quarter, double phraseLengthQuarter) noexcept {
    const double len = std::max(0.25, phraseLengthQuarter);
    if (!std::isfinite(quarter)) return 0;
    return static_cast<std::int64_t>(std::floor((quarter + 1e-9) / len));
}

class PersistentPhraseTakeComp {
public:
    static constexpr int kCapacity = 128;
    static constexpr int kHistoryDepth = 16;

    void resetAll() noexcept {
        clearEntries();
        clearHistory();
    }

    void clear() noexcept {
        pushUndo();
        clearEntries();
        redoCount_ = 0;
    }

    bool commit(std::int64_t phraseKey, int takeIndex) noexcept {
        pushUndo();
        const bool ok = commitNoHistory(phraseKey, takeIndex);
        redoCount_ = 0;
        return ok;
    }

    bool commitRange(std::int64_t firstKey, std::int64_t lastKey, int takeIndex) noexcept {
        if (lastKey < firstKey) std::swap(firstKey,lastKey);
        pushUndo();
        bool ok=true;
        int written=0;
        for (std::int64_t k=firstKey; k<=lastKey && written<kCapacity; ++k,++written)
            ok = commitNoHistory(k,takeIndex) && ok;
        redoCount_ = 0;
        return ok;
    }

    bool commitBatch(const std::array<std::int64_t,kCapacity>& keys,
                     const std::array<std::uint8_t,kCapacity>& takes,
                     int count) noexcept {
        count=std::clamp(count,0,kCapacity);
        if(count<=0) return false;
        pushUndo();
        bool ok=true;
        for(int i=0;i<count;++i) ok=commitNoHistory(keys[static_cast<std::size_t>(i)],takes[static_cast<std::size_t>(i)])&&ok;
        redoCount_=0;
        return ok;
    }

    bool lookup(std::int64_t phraseKey, int& takeIndex) const noexcept {
        const auto* e = find(phraseKey);
        if (!e || !e->committed) return false;
        takeIndex = static_cast<int>(e->takeIndex);
        return true;
    }

    bool toggleFavorite(std::int64_t phraseKey, int takeIndex) noexcept {
        takeIndex=std::clamp(takeIndex,0,3);
        pushUndo();
        auto* e = ensure(phraseKey,takeIndex);
        if (!e) return false;
        const std::uint8_t bit=static_cast<std::uint8_t>(1u<<takeIndex);
        e->favoriteMask ^= bit;
        if (e->favoriteMask & bit) e->rejectMask &= static_cast<std::uint8_t>(~bit);
        redoCount_=0;
        return true;
    }

    bool toggleReject(std::int64_t phraseKey, int takeIndex) noexcept {
        takeIndex=std::clamp(takeIndex,0,3);
        pushUndo();
        auto* e = ensure(phraseKey,takeIndex);
        if (!e) return false;
        const std::uint8_t bit=static_cast<std::uint8_t>(1u<<takeIndex);
        e->rejectMask ^= bit;
        if (e->rejectMask & bit) e->favoriteMask &= static_cast<std::uint8_t>(~bit);
        redoCount_=0;
        return true;
    }

    bool isFavorite(std::int64_t phraseKey,int takeIndex) const noexcept {
        const auto* e=find(phraseKey); if(!e) return false;
        return (e->favoriteMask & static_cast<std::uint8_t>(1u<<std::clamp(takeIndex,0,3)))!=0;
    }
    bool isRejected(std::int64_t phraseKey,int takeIndex) const noexcept {
        const auto* e=find(phraseKey); if(!e) return false;
        return (e->rejectMask & static_cast<std::uint8_t>(1u<<std::clamp(takeIndex,0,3)))!=0;
    }

    int committedCount() const noexcept {
        int n=0; for(const auto& e:entries_) if(e.valid && e.committed) ++n; return n;
    }

    int entryCount() const noexcept {
        int n=0; for(const auto& e:entries_) if(e.valid) ++n; return n;
    }

    bool query(std::int64_t phraseKey, PersistentTakeCompEntry& out) const noexcept {
        const auto* e=find(phraseKey);
        if(!e) { out={}; return false; }
        out=*e; return true;
    }

    bool erase(std::int64_t phraseKey) noexcept {
        for(auto& e:entries_) {
            if(e.valid && e.phraseKey==phraseKey) {
                pushUndo();
                e={};
                redoCount_=0;
                return true;
            }
        }
        return false;
    }

    int committedCountInRange(std::int64_t firstKey,std::int64_t lastKey) const noexcept {
        if(lastKey<firstKey) std::swap(firstKey,lastKey);
        int n=0; for(const auto& e:entries_) if(e.valid && e.committed && e.phraseKey>=firstKey && e.phraseKey<=lastKey) ++n;
        return n;
    }

    int exportEntries(std::array<PersistentTakeCompEntry,kCapacity>& out) const noexcept {
        int n=0;
        for(const auto& e:entries_) if(e.valid && n<kCapacity) out[static_cast<std::size_t>(n++)]=e;
        return n;
    }

    bool restoreEntry(std::int64_t phraseKey,int takeIndex,int favoriteMask,int rejectMask,bool committed=true) noexcept {
        auto* e=ensureNoHistory(phraseKey,takeIndex);
        if(!e) return false;
        e->takeIndex=static_cast<std::uint8_t>(std::clamp(takeIndex,0,3));
        e->favoriteMask=static_cast<std::uint8_t>(favoriteMask)&0x0Fu;
        e->rejectMask=static_cast<std::uint8_t>(rejectMask)&0x0Fu;
        e->favoriteMask &= static_cast<std::uint8_t>(~e->rejectMask);
        e->committed=committed;
        return true;
    }

    void finishRestore() noexcept { stamp_=static_cast<std::uint32_t>(std::max(1,entryCount()+1)); clearHistory(); }

    bool undo() noexcept {
        if(undoCount_<=0) return false;
        pushRedoCurrent();
        entries_=undo_[static_cast<std::size_t>(undoCount_-1)].entries;
        stamp_=undo_[static_cast<std::size_t>(undoCount_-1)].stamp;
        --undoCount_;
        return true;
    }

    bool redo() noexcept {
        if(redoCount_<=0) return false;
        pushUndoCurrentNoRedoClear();
        entries_=redo_[static_cast<std::size_t>(redoCount_-1)].entries;
        stamp_=redo_[static_cast<std::size_t>(redoCount_-1)].stamp;
        --redoCount_;
        return true;
    }

private:
    struct Snapshot {
        std::array<PersistentTakeCompEntry,kCapacity> entries {};
        std::uint32_t stamp {1};
    };

    void clearEntries() noexcept { for(auto& e:entries_) e={}; stamp_=1; }
    void clearHistory() noexcept { undoCount_=0; redoCount_=0; }

    PersistentTakeCompEntry* find(std::int64_t key) noexcept {
        for(auto& e:entries_) if(e.valid && e.phraseKey==key) return &e;
        return nullptr;
    }
    const PersistentTakeCompEntry* find(std::int64_t key) const noexcept {
        for(const auto& e:entries_) if(e.valid && e.phraseKey==key) return &e;
        return nullptr;
    }

    PersistentTakeCompEntry* ensureNoHistory(std::int64_t key,int takeIndex) noexcept {
        if(auto* e=find(key)) return e;
        for(auto& e:entries_) if(!e.valid) {e={key,static_cast<std::uint8_t>(std::clamp(takeIndex,0,3)),0,0,true,false};return &e;}
        auto& e=entries_[static_cast<std::size_t>(stamp_++ % kCapacity)];
        e={key,static_cast<std::uint8_t>(std::clamp(takeIndex,0,3)),0,0,true,false};
        return &e;
    }

    PersistentTakeCompEntry* ensure(std::int64_t key,int takeIndex) noexcept {
        return ensureNoHistory(key,takeIndex);
    }

    bool commitNoHistory(std::int64_t key,int takeIndex) noexcept {
        auto* e=ensureNoHistory(key,takeIndex);
        if(!e) return false;
        e->takeIndex=static_cast<std::uint8_t>(std::clamp(takeIndex,0,3));
        e->committed=true;
        return true;
    }

    void pushUndo() noexcept {
        pushUndoCurrentNoRedoClear();
        redoCount_=0;
    }
    void pushUndoCurrentNoRedoClear() noexcept {
        if(undoCount_==kHistoryDepth) {
            for(int i=1;i<kHistoryDepth;++i) undo_[static_cast<std::size_t>(i-1)]=undo_[static_cast<std::size_t>(i)];
            undoCount_=kHistoryDepth-1;
        }
        undo_[static_cast<std::size_t>(undoCount_++)]={entries_,stamp_};
    }
    void pushRedoCurrent() noexcept {
        if(redoCount_==kHistoryDepth) {
            for(int i=1;i<kHistoryDepth;++i) redo_[static_cast<std::size_t>(i-1)]=redo_[static_cast<std::size_t>(i)];
            redoCount_=kHistoryDepth-1;
        }
        redo_[static_cast<std::size_t>(redoCount_++)]={entries_,stamp_};
    }

    std::array<PersistentTakeCompEntry,kCapacity> entries_ {};
    std::array<Snapshot,kHistoryDepth> undo_ {};
    std::array<Snapshot,kHistoryDepth> redo_ {};
    int undoCount_ {0};
    int redoCount_ {0};
    std::uint32_t stamp_ {1};
};

inline int resolvePersistentCompTake(const PersistentPhraseTakeComp& comp,int compMode,bool insideScope,
                                     double quarter,double phraseLengthQuarter,int fallbackTake) noexcept {
    if(compMode!=kTakeCompPhraseV34 || !insideScope) return std::clamp(fallbackTake,0,3);
    int take=fallbackTake;
    if(comp.lookup(phraseKeyFromQuarterV34(quarter,phraseLengthQuarter),take)) return take;
    return std::clamp(fallbackTake,0,3);
}

} // namespace Sonicraft::AIStrings

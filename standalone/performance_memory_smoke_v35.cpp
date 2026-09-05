#include "../src/performance_memory_v35.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    PersistentPhraseTakeComp c;
    const auto w=memoryWindowFromQuarters(true,8.0,24.0,4.0); // keys 2..5
    assert(w.valid && w.firstKey==2 && w.lastKey==5);
    PersistentPhraseTakeComp reviewOnly;
    assert(reviewOnly.toggleFavorite(2,2));
    int reviewTake=-1;
    assert(!reviewOnly.lookup(2,reviewTake)); // review metadata must NOT silently commit a take
    auto reviewStatus=performanceMemoryStatus(reviewOnly,2,2,w);
    assert(!reviewStatus.committed && reviewStatus.recallFavorite);
    assert(nextMemoryPhrase(2,w,-1)==5);
    assert(nextMemoryPhrase(5,w,1)==2);
    assert(c.commit(2,2)); // C
    assert(c.commit(4,0)); // A
    assert(c.toggleFavorite(2,2));
    auto s=performanceMemoryStatus(c,2,2,w);
    assert(s.committed && s.committedTake==2 && s.recallFavorite && !s.recallRejected);
    assert(s.totalPhrases==4 && s.committedPhrases==2 && std::abs(s.coverage-.5f)<1e-6f);
    assert(nextUnresolvedPhrase(c,2,w)==3);
    assert(c.commit(3,1)); assert(c.commit(5,3));
    assert(nextUnresolvedPhrase(c,3,w)==3); // all resolved
    assert(c.erase(3));
    assert(nextUnresolvedPhrase(c,2,w)==3);
    std::cout<<"SONICRAFT v3.5 performance memory smoke OK coverage="<<performanceMemoryStatus(c,2,2,w).coverage<<"\n";
    return 0;
}

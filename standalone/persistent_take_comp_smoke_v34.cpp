#include "../src/persistent_take_comp_v34.h"
#include <array>
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    PersistentPhraseTakeComp c;
    assert(c.commit(0,2)); assert(c.commit(1,0)); assert(c.commit(2,3));
    int t=-1; assert(c.lookup(1,t)&&t==0);
    assert(c.toggleFavorite(1,0)); assert(c.isFavorite(1,0)); assert(!c.isRejected(1,0));
    assert(c.toggleReject(1,0)); assert(!c.isFavorite(1,0)); assert(c.isRejected(1,0));
    assert(c.undo()); assert(c.isFavorite(1,0)); assert(!c.isRejected(1,0));
    assert(c.redo()); assert(!c.isFavorite(1,0)); assert(c.isRejected(1,0));
    assert(c.commitRange(3,5,1));
    assert(c.lookup(4,t)&&t==1);
    std::array<PersistentTakeCompEntry,PersistentPhraseTakeComp::kCapacity> out{};
    const int n=c.exportEntries(out); assert(n>=6);
    PersistentPhraseTakeComp restored;
    for(int i=0;i<n;++i) assert(restored.restoreEntry(out[i].phraseKey,out[i].takeIndex,out[i].favoriteMask,out[i].rejectMask));
    restored.finishRestore();
    assert(restored.lookup(2,t)&&t==3);
    assert(restored.isRejected(1,0));
    assert(resolvePersistentCompTake(restored,kTakeCompPhraseV34,true,8.1,4.0,0)==3); // phrase key 2
    std::cout<<"SONICRAFT v3.4 persistent phrase comp smoke OK entries="<<n<<"\n";
    return 0;
}

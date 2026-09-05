#include "../src/smart_comp_timeline_v36.h"
#include <cassert>
#include <cmath>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    PersistentPhraseTakeComp c;
    PerformanceMemoryWindow w{true,10,19};
    auto tw=smartTimelineWindowV36(14,w);
    assert(tw.count==8 && tw.phraseKeys[0]==11 && tw.phraseKeys[7]==18 && tw.cursorSlot==3);
    auto a=smartRankTakeV36(c,14,.37f,7,.8f,true,kSmartCompBalanced);
    auto b=smartRankTakeV36(c,14,.37f,7,.8f,true,kSmartCompBalanced);
    assert(a.take>=0&&a.take<4&&a.take==b.take&&std::abs(a.score-b.score)<1e-7f);
    assert(c.toggleFavorite(14,3));
    auto fav=smartRankTakeV36(c,14,.37f,7,.8f,true,kSmartCompConservative);
    assert(fav.take==3);
    assert(c.toggleReject(14,3)); // removes favorite and marks D rejected
    auto noD=smartRankTakeV36(c,14,.37f,7,.8f,true,kSmartCompAdventurous);
    assert(noD.take>=0&&noD.take<3);
    assert(c.toggleFavorite(15,1));
    assert(uniqueFavoriteTakeV36(c,15)==1);
    assert(c.toggleFavorite(15,2));
    assert(uniqueFavoriteTakeV36(c,15)==-1);
    for(int take=0;take<4;++take) if(!c.isRejected(16,take)) assert(c.toggleReject(16,take));
    assert(smartRankTakeV36(c,16,.37f,7,.8f,true,kSmartCompBalanced).take==-1);
    std::array<std::int64_t,PersistentPhraseTakeComp::kCapacity> keys{};
    std::array<std::uint8_t,PersistentPhraseTakeComp::kCapacity> takes{};
    keys[0]=12;takes[0]=2;keys[1]=13;takes[1]=1;
    assert(c.commitBatch(keys,takes,2));
    int t=-1;assert(c.lookup(12,t)&&t==2&&c.lookup(13,t)&&t==1);
    assert(c.undo()); assert(!c.lookup(12,t)&&!c.lookup(13,t));
    assert(c.redo()); assert(c.lookup(12,t)&&t==2&&c.lookup(13,t)&&t==1);
    std::cout<<"SONICRAFT v3.6 smart comp timeline smoke OK pick="<<a.take<<" score="<<a.score<<"\n";
    return 0;
}

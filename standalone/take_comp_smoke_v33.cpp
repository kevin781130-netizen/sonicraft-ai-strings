#include "../src/take_comp_v33.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){
    PhraseTakeComp c;
    assert(c.committedCount()==0);
    assert(phraseKeyFromQuarter(0.0,4.0)==0);
    assert(phraseKeyFromQuarter(3.99,4.0)==0);
    assert(phraseKeyFromQuarter(4.0,4.0)==1);
    assert(c.commit(0,2)); // phrase 1 -> C
    assert(c.commit(1,0)); // phrase 2 -> A
    assert(c.commit(2,3)); // phrase 3 -> D
    assert(c.committedCount()==3);
    assert(resolveCompTake(c,kTakeCompPhrase,true,1.0,4.0,1)==2);
    assert(resolveCompTake(c,kTakeCompPhrase,true,5.0,4.0,1)==0);
    assert(resolveCompTake(c,kTakeCompPhrase,true,9.0,4.0,1)==3);
    assert(resolveCompTake(c,kTakeCompPhrase,false,9.0,4.0,1)==1);
    assert(c.commit(1,1)); // overwrite phrase 2 -> B
    assert(resolveCompTake(c,kTakeCompPhrase,true,5.0,4.0,0)==1);
    c.clear();
    assert(c.committedCount()==0);
    assert(resolveCompTake(c,kTakeCompPhrase,true,1.0,4.0,3)==3);
    std::cout<<"SONICRAFT v3.3 phrase take comp smoke OK\n";
    return 0;
}

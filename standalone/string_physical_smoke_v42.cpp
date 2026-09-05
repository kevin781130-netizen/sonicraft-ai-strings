#include "../src/string_physical_v42.h"
#include "../src/string_expression_v41.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
struct C {float dyn=.62f,vib=.50f,exp=.90f,leg=0.f,bend=.50f,transition=.50f,tightness=.50f,attack=.38f;};
int main(){
    C c{};
    StringPhysicalStateV42 p{};
    p.position=.72f;p.bowDirection=0.f;p.bowPressure=.82f;p.contactPoint=.72f;p.portamento=.75f;p.desk=.66f;
    auto x=applyStringPhysicalResidualsV42(c,p);
    assert(x.dyn>c.dyn);
    assert(x.attack!=c.attack);
    assert(x.transition<c.transition);
    assert(x.leg>=.69f);
    assert(x.bend>c.bend);
    StringPhysicalStateV42 open{}; open.position=0.f; open.contactPoint=.5f;
    auto o=applyStringPhysicalResidualsV42(c,open);
    assert(o.vib<=.080001f);
    std::cout<<"SONICRAFT v4.2 string physical residual smoke OK\n";
    return 0;
}
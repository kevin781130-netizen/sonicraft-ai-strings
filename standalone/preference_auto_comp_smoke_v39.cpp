#include "../src/preference_auto_comp_v39.h"
#include <cassert>
#include <iostream>
using namespace Sonicraft::AIStrings;
int main(){std::array<float,4> p{{.72f,.83f,.70f,.60f}},s{{.9f,.8f,.9f,.9f}};auto a=evaluatePreferenceAutoCompV39(true,.5f,.3f,.08f,.35f,0xF,p,s);assert(a.commit&&a.take==1&&a.margin>.10f);auto b=evaluatePreferenceAutoCompV39(true,.1f,.3f,.08f,.35f,0xF,p,s);assert(!b.commit);s[1]=.2f;auto c=evaluatePreferenceAutoCompV39(true,.5f,.3f,.08f,.35f,0xF,p,s);assert(!c.commit);auto d=evaluatePreferenceAutoCompV39(false,1.f,0.f,0.f,0.f,0xF,p,s);assert(!d.commit);std::cout<<"SONICRAFT v3.9 preference auto-comp gate smoke OK\n";}

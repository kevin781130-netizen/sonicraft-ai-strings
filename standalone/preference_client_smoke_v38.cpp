#include "../src/preference_client_v38.h"
#include <cassert>
#include <iostream>
int main(){Sonicraft::AIStrings::PreferenceProfileV38 p{};static_assert(sizeof(p.weights)==sizeof(float)*5);assert(p.confidence==0.f);std::cout<<"SONICRAFT v3.8 PreferenceClient core smoke OK\n";}

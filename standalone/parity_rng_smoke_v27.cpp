#include "portable_rng_v27.h"
#include <cstring>
#include <iomanip>
#include <iostream>
int main(){auto x=Sonicraft::ParityV27::normalArray("SONICRAFT_V27_PARITY",12);for(size_t i=0;i<x.size();++i){uint32_t u=0;std::memcpy(&u,&x[i],4);if(i)std::cout<<",";std::cout<<std::hex<<std::setw(8)<<std::setfill('0')<<u;}std::cout<<"\n";return 0;}

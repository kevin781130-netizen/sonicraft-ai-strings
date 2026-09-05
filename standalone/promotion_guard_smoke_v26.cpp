#include "inprocess_promotion_guard_v26.h"
#include "sha256_v26.h"
#include <filesystem>
#include <fstream>
#include <iostream>
using namespace Sonicraft;
int main(int argc,char**argv){
    if(argc<2)return 2;std::filesystem::path root=argv[1];std::filesystem::create_directories(root);
    auto wr=[&](const char*n,const char*s){std::ofstream f(root/n,std::ios::binary);f<<s;};wr("renderer_frontier.ort","renderer");wr("strings_vae64_decoder.ort","decoder");wr("onnxruntime.dll","runtime");
    std::ofstream lock(root/"inprocess_promotion_v26.lock");lock<<"SONICRAFT_INPROCESS_PROMOTION_V26\n"<<"promotion_id="<<std::string(64,'a')<<"\n";
    for(auto [key,name]:{std::pair{"renderer","renderer_frontier.ort"},std::pair{"decoder","strings_vae64_decoder.ort"},std::pair{"ort_runtime","onnxruntime.dll"}})lock<<key<<"="<<name<<"\n"<<key<<"_sha256="<<CryptoV26::sha256FileHex(root/name)<<"\n";lock.close();
    InProcess::PromotionPaths p;std::string reason;if(!InProcess::verifyPromotionLock(root/"inprocess_promotion_v26.lock",p,reason)){std::cerr<<reason<<"\n";return 3;}
    wr("renderer_frontier.ort","tampered");if(InProcess::verifyPromotionLock(root/"inprocess_promotion_v26.lock",p,reason)){std::cerr<<"tamper accepted\n";return 4;}
    std::cout<<"v2.6 PROMOTION GUARD PASS tamper="<<reason<<" sha256_abc="<<CryptoV26::sha256Hex(std::span<const uint8_t>((const uint8_t*)"abc",3))<<"\n";return 0;
}

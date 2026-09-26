#include "dnni_model_manifest.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iostream>

using namespace Sonicraft::AIStrings;

static void putU32(std::array<unsigned char,140>& h, int off, std::uint32_t v) {
    for(int i=0;i<4;++i) h[off+i]=static_cast<unsigned char>((v>>(8*i))&0xffu);
}
static void putU64(std::array<unsigned char,140>& h, int off, std::uint64_t v) {
    for(int i=0;i<8;++i) h[off+i]=static_cast<unsigned char>((v>>(8*i))&0xffu);
}

int main() {
    const auto root=std::filesystem::temp_directory_path()/"sonicraft_dnni_manifest_smoke";
    std::filesystem::create_directories(root);
    const auto model=root/"synthetic.dnni";
    const auto manifest=root/"sonicraft_dnni_catalog.txt";

    constexpr std::uint64_t weightsOffset=36864;
    constexpr std::uint64_t weightsBytes=4096;
    constexpr std::uint64_t fileSize=50000;

    std::array<unsigned char,140> h{};
    h[0]=0xff;h[1]=0x00;h[2]=0xca;h[3]=0x7f;
    putU32(h,4,4);putU32(h,8,140);
    putU64(h,64,140);putU64(h,72,32);
    putU64(h,80,weightsOffset);putU64(h,88,weightsBytes);
    putU64(h,96,weightsOffset+weightsBytes);putU64(h,104,128);
    putU64(h,112,weightsOffset+weightsBytes+128);putU64(h,120,fileSize-(weightsOffset+weightsBytes+128)-256);

    {
        std::ofstream f(model,std::ios::binary);
        f.write(reinterpret_cast<const char*>(h.data()),static_cast<std::streamsize>(h.size()));
        f.seekp(static_cast<std::streamoff>(fileSize-1));
        const char zero=0;f.write(&zero,1);
    }
    {
        std::ofstream f(manifest,std::ios::binary);
        f<<DnniModelManifestCatalog::kMagic<<"\n";
        f<<"3|violin|strings|Violin|小提琴|synthetic|"<<model.string()
         <<"|"<<fileSize<<"|sourcehash|"<<weightsOffset<<"|"<<weightsBytes<<"|weightshash\n";
    }

    DnniModelManifestCatalog cat;
    assert(cat.load(manifest));
    assert(cat.presentCount()==1);
    assert(cat.ready(3));
    const auto* m=cat.model(3);
    assert(m && m->weightsOffset==weightsOffset && m->weightsBytes==weightsBytes);

    std::filesystem::remove_all(root);
    std::cout<<"dnni_manifest_smoke: ok\n";
    return 0;
}

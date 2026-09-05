#include "inprocess_promotion_guard_v26.h"
#include "sha256_v26.h"
#include <fstream>
#include <map>
namespace Sonicraft::InProcess {
bool verifyPromotionLock(const std::filesystem::path&lock,PromotionPaths&out,std::string&reason){std::ifstream f(lock);if(!f){reason="promotion_lock_missing";return false;}std::string line;if(!std::getline(f,line)||line!="SONICRAFT_INPROCESS_PROMOTION_V26"){reason="bad_lock_header";return false;}std::map<std::string,std::string>kv;while(std::getline(f,line)){auto p=line.find('=');if(p!=std::string::npos)kv[line.substr(0,p)]=line.substr(p+1);}auto id=kv["promotion_id"];if(id.size()!=64){reason="bad_promotion_id";return false;}auto root=lock.parent_path();auto verify=[&](const char*key,std::filesystem::path&dst){std::string v=kv[key],prefix=std::string(key)+"_sha256";if(v.empty()||kv[prefix].size()!=64)return false;dst=root/v;if(!std::filesystem::is_regular_file(dst))return false;return CryptoV26::sha256FileHex(dst)==kv[prefix];};if(!verify("renderer",out.renderer)){reason="renderer_binding_failed";return false;}if(!verify("decoder",out.decoder)){reason="decoder_binding_failed";return false;}if(!verify("ort_runtime",out.ortRuntime)){reason="ort_runtime_binding_failed";return false;}out.promotionId=id;reason.clear();return true;}
}

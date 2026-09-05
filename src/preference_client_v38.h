#pragma once
#include <array>
#include <atomic>
#include <cstdint>
#include <thread>
#include <deque>
#include "shadow_render_client.h"

namespace Sonicraft::AIStrings {
struct PreferenceProfileV38 { uint64_t hash=0; float confidence=0.f,evidence=0.f; std::array<float,5> weights{{0,0,0,0,0}}; };
struct PreferenceEventWireV38 { uint8_t kind=0,take=0; std::array<float,24> metrics{}; };
class PreferenceClientV38 {
public:
    PreferenceClientV38(); ~PreferenceClientV38();
    void record(int kind,int take,const TakeJudgeSnapshotV37& snap) noexcept;
    void clear() noexcept;
    PreferenceProfileV38 snapshot() const noexcept;
private:
    void workerMain();
    bool sendEvent(const PreferenceEventWireV38& ev,uint64_t req);
    bool query(uint64_t req,bool clearProfile);
    template<typename T,size_t N> class Ring { public: bool push(const T&v)noexcept{auto w=wr.load(),n=(w+1)%N;if(n==rd.load())return false;d[w]=v;wr.store(n);return true;} bool pop(T&v)noexcept{auto r=rd.load();if(r==wr.load())return false;v=d[r];rd.store((r+1)%N);return true;} private:std::array<T,N>d{};std::atomic<size_t>wr{0},rd{0};};
    std::thread worker; std::atomic<bool> stop{false}; Ring<PreferenceEventWireV38,64> ring;
    std::atomic<bool> clearPending{false}; std::atomic<uint64_t> hash{0}; std::atomic<float> confidence{0},evidence{0}; std::array<std::atomic<float>,5> weights{};
};
}

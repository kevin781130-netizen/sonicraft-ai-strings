#include "inprocess_neural_engine.h"
#include "portable_rng_v27.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>
#include <map>
#include <numeric>
#include <optional>
#include <random>
#include <unordered_map>

namespace Sonicraft::InProcess {
using ProductShell::TimelineEvent;
namespace {
constexpr float kPi=3.14159265358979323846f;
constexpr int NOTE_ON=1,NOTE_OFF=2,KEYSWITCH=3,CONTROL=4,RESET=5;
constexpr const char* kRawNames[kRawControls]={
 "pitch","gate","onset","velocity","dynamics","vibrato","expression","legato","pitchbend",
 "transition_speed","short_tightness","attack_character","note_progress","phrase_position",
 "prev_interval","next_interval","bow_change_prob","vibrato_onset","tempo_bpm","seconds_per_beat",
 "note_duration_beats","transition_target_ms","speed_profile","vibrato_depth_cents","vibrato_rate_hz",
 "vibrato_jitter","dynamics_known","vibrato_known","expression_known","legato_known",
 "pitchbend_known","timing_known","articulation_known"};

int idxOf(const char* name){for(int i=0;i<kRawControls;++i)if(std::strcmp(kRawNames[i],name)==0)return i;return -1;}
float clamp01(float x){return std::clamp(x,0.f,1.f);}
int frameFor(int64_t s,int64_t start,uint32_t sr,int fps,int n){double x=(double(s-start)/double(sr))*fps;return std::clamp(int(std::llround(x)),0,std::max(0,n-1));}
void smooth(std::vector<float>& x,int radius){if(radius<=0||x.size()<3)return;std::vector<float>w(size_t(2*radius+1));float sum=0;for(int k=-radius;k<=radius;++k){float q=float(k)/std::max(1.f,radius*.45f);float a=std::exp(-.5f*q*q);w[size_t(k+radius)]=a;sum+=a;}for(float&v:w)v/=sum;auto src=x;for(size_t i=0;i<x.size();++i){float a=0;for(int k=-radius;k<=radius;++k){long j=long(i)+k;if(j>=0&&j<long(src.size()))a+=src[size_t(j)]*w[size_t(k+radius)];}x[i]=a;}}
uint64_t fnv1a64(std::string_view s){uint64_t h=1469598103934665603ull;for(unsigned char c:s){h^=c;h*=1099511628211ull;}return h;}

struct Note {int note=0,on=0,off=0;float velocity=.7f;int64_t onSample=0,offSample=0;};
struct PartState {std::vector<float> gate,pitch,onset;std::vector<std::vector<Note>> notes;};

PartState scoreState(const std::vector<TimelineEvent>& events,int64_t start,int64_t end,uint32_t sr,int fps,int n){
    PartState s; s.gate.assign(size_t(4*n),0);s.pitch.assign(size_t(4*n),0);s.onset.assign(size_t(4*n),0);s.notes.resize(4);
    std::array<std::optional<Note>,4> active{};
    auto sorted=events;std::stable_sort(sorted.begin(),sorted.end(),[](auto&a,auto&b){return a.sample<b.sample;});
    for(const auto&e:sorted){int p=int(e.part),typ=int(e.type);if(p<0||p>=4||(typ!=NOTE_ON&&typ!=NOTE_OFF))continue;bool before=e.sample<start;int i=frameFor(e.sample,start,sr,fps,n);
        if(typ==NOTE_ON){if(active[p]){auto q=*active[p];q.off=i;q.offSample=e.sample;s.notes[p].push_back(q);for(int j=q.on;j<std::max(q.on,i);++j){s.gate[size_t(p*n+j)]=1;s.pitch[size_t(p*n+j)]=float(q.note);}}
            Note q{int(e.note),before?0:i,n,e.velocity,e.sample,end};active[p]=q;if(!before)s.onset[size_t(p*n+i)]=1;
        }else if(active[p]&&active[p]->note==int(e.note)){auto q=*active[p];q.off=std::max(q.on,i);q.offSample=e.sample;s.notes[p].push_back(q);for(int j=q.on;j<q.off;++j){s.gate[size_t(p*n+j)]=1;s.pitch[size_t(p*n+j)]=float(q.note);}active[p].reset();}
    }
    for(int p=0;p<4;++p)if(active[p]){auto q=*active[p];q.off=n;q.offSample=end;s.notes[p].push_back(q);for(int j=q.on;j<n;++j){s.gate[size_t(p*n+j)]=1;s.pitch[size_t(p*n+j)]=float(q.note);}}
    return s;
}

void stageBundle(const std::vector<float>& mono,int sr,float room,int perspective,std::vector<float>& out){
    static constexpr float cfg[16][4]={{0,.02f,0,-.45f},{0,.01f,0,0},{0,.02f,0,.45f},{3.2f,.08f,.08f,-.55f},{3.8f,.07f,.09f,0},{3.2f,.08f,.08f,.55f},{7.4f,.13f,.12f,-.78f},{7.4f,.13f,.12f,.78f},{12.5f,.22f,.22f,-.62f},{13.1f,.22f,.22f,.62f},{18,.28f,.27f,0},{8.8f,.16f,.15f,-.40f},{8.8f,.16f,.15f,.40f},{21,.34f,.31f,-.64f},{21,.34f,.31f,.64f},{27,.40f,.36f,0}};
    static constexpr float preset[4][16]={{1,.7f,.7f,1,1,1,.02f,.02f,0,0,0,.08f,.08f,0,0,0},{.42f,.32f,.32f,.58f,.66f,.58f,.2f,.2f,.12f,.12f,.04f,.24f,.24f,.05f,.05f,.02f},{.3f,.22f,.22f,.48f,.55f,.48f,.52f,.52f,.24f,.24f,.08f,.35f,.35f,.12f,.12f,.05f},{.18f,.14f,.14f,.3f,.36f,.3f,.38f,.38f,.58f,.58f,.24f,.26f,.26f,.34f,.34f,.18f}};
    const size_t N=mono.size();out.assign(N*kStageChannels,0);std::vector<std::array<float,2>> master(N);float den=0;int pr=std::clamp(perspective,0,3);
    for(int m=0;m<16;++m){int d=int(std::llround(cfg[m][0]*sr/1000.));int ed=d+int(std::llround((4+1.7*(m%3))*sr/1000.));float pan=cfg[m][3],gl=std::sqrt(.5f*(1-pan)),gr=std::sqrt(.5f*(1+pan));float w=preset[pr][m];den+=w;
        float prev=0;for(size_t i=0;i<N;++i){float v=(i>=size_t(d)?mono[i-size_t(d)]:0);float air=std::clamp(cfg[m][1]+room*.18f,0.f,1.f);float y=(1-air)*v+air*.5f*(v+prev);prev=v;if(cfg[m][2]>0&&i>=size_t(ed))y+=mono[i-size_t(ed)]*(cfg[m][2]*(.45f+.55f*room));float l=y*gl,r=y*gr;out[i*kStageChannels+2+2*m]=l;out[i*kStageChannels+3+2*m]=r;master[i][0]+=l*w;master[i][1]+=r*w;}
    }
    float norm=den>0?std::sqrt(den):1;for(size_t i=0;i<N;++i){out[i*kStageChannels]=master[i][0]/norm;out[i*kStageChannels+1]=master[i][1]/norm;}
}

float medianRoom(const std::vector<TimelineEvent>& lane){std::vector<float>v;for(auto&e:lane)v.push_back(clamp01(e.controls.room));if(v.empty())return .18f;std::nth_element(v.begin(),v.begin()+v.size()/2,v.end());return v[v.size()/2];}

} // namespace

std::vector<std::vector<TimelineEvent>> allocatePolyphonicLanes(const std::vector<TimelineEvent>& events,int part,int maxVoices){
    maxVoices=std::max(1,maxVoices);std::vector<TimelineEvent> pe;for(auto&e:events)if(int(e.part)==part||int(e.type)==RESET)pe.push_back(e);std::stable_sort(pe.begin(),pe.end(),[](auto&a,auto&b){if(a.sample!=b.sample)return a.sample<b.sample;return a.type<b.type;});
    std::vector<TimelineEvent> controls;for(auto&e:pe)if(e.type==KEYSWITCH||e.type==CONTROL||e.type==RESET)controls.push_back(e);std::vector<std::vector<TimelineEvent>> lanes{size_t(maxVoices)};std::vector<bool>free(size_t(maxVoices),true);std::vector<int64_t>started(size_t(maxVoices),std::numeric_limits<int64_t>::max());std::map<int,std::vector<std::pair<int,int64_t>>> active;
    for(auto&e:pe){if(e.type!=NOTE_ON&&e.type!=NOTE_OFF)continue;int pitch=int(e.note);if(e.type==NOTE_ON){int ln=-1;for(int i=0;i<maxVoices;++i)if(free[size_t(i)]){ln=i;break;}if(ln<0){ln=int(std::min_element(started.begin(),started.end())-started.begin());for(auto it=active.begin();it!=active.end();){auto&vec=it->second;for(auto jt=vec.begin();jt!=vec.end();){if(jt->first==ln){auto off=e;off.type=NOTE_OFF;off.note=uint8_t(it->first);off.velocity=0;lanes[size_t(ln)].push_back(off);jt=vec.erase(jt);}else ++jt;}if(vec.empty())it=active.erase(it);else ++it;}}
            lanes[size_t(ln)].push_back(e);free[size_t(ln)]=false;started[size_t(ln)]=e.sample;active[pitch].push_back({ln,e.sample});
        }else{auto it=active.find(pitch);if(it==active.end()||it->second.empty())continue;auto&vec=it->second;std::stable_sort(vec.begin(),vec.end(),[](auto&a,auto&b){return a.second==b.second?a.first<b.first:a.second<b.second;});int ln=vec.front().first;vec.erase(vec.begin());lanes[size_t(ln)].push_back(e);free[size_t(ln)]=true;started[size_t(ln)]=std::numeric_limits<int64_t>::max();if(vec.empty())active.erase(it);}}
    std::vector<std::vector<TimelineEvent>> out;for(auto&l:lanes){if(l.empty())continue;int64_t last=0;for(auto&e:l)last=std::max(last,e.sample);std::vector<TimelineEvent>m=l;for(auto&c:controls)if(c.sample<=last||c.type==RESET)m.push_back(c);std::stable_sort(m.begin(),m.end(),[](auto&a,auto&b){if(a.sample!=b.sample)return a.sample<b.sample;auto ca=(a.type==KEYSWITCH||a.type==CONTROL||a.type==RESET);auto cb=(b.type==KEYSWITCH||b.type==CONTROL||b.type==RESET);return ca&&!cb;});out.push_back(std::move(m));}return out;
}

ControlBatch NativeControlBuilder::build(const std::vector<TimelineEvent>& allEvents,const std::vector<TimelineEvent>& lane,int part,int64_t start,int64_t end,uint32_t sr,const ProductShell::Policy& policy,const std::string& fingerprint) const {
    const double dur=std::max(.08,double(end-start)/sr);const int N=std::max(8,int(std::ceil(dur*fps_)));ControlBatch c;c.frames=N;c.raw.assign(size_t(N*kRawControls),0);c.vibratoPhysicsKnown.assign(size_t(N),0);c.frontierContext.assign(size_t(kFrontierContext*N),0);c.articulationCurve.assign(size_t(N),0);c.gate.assign(size_t(N),0);c.player=part;c.instrument=part<2?0:(part==2?1:2);
    std::vector<float>pitch(N,0),gate(N,0),onset(N,0),vel(N,.7f),dyn(N,.62f),vib(N,.5f),exp(N,.9f),leg(N,1),pb(N,.5f),trans(N,.5f),tight(N,.5f),attack(N,.38f),speed(N,0);std::vector<int64_t>art(N,0);std::vector<Note>notes;std::optional<Note>active;
    auto sorted=lane;std::stable_sort(sorted.begin(),sorted.end(),[](auto&a,auto&b){return a.sample<b.sample;});
    for(const auto&e:sorted){bool before=e.sample<start;int i=frameFor(e.sample,start,sr,fps_,N);for(int j=i;j<N;++j){dyn[j]=e.controls.dyn;vib[j]=e.controls.vib;exp[j]=e.controls.exp;leg[j]=e.controls.leg;pb[j]=e.controls.bend;trans[j]=e.controls.transition;tight[j]=e.controls.tightness;attack[j]=e.controls.attack;speed[j]=e.controls.speedProfile;art[j]=std::clamp<int>(e.articulation,0,11);}if(e.type==NOTE_ON){if(active){auto q=*active;q.off=i;q.offSample=e.sample;notes.push_back(q);}active=Note{int(e.note),before?0:i,N,e.velocity,e.sample,end};}else if(e.type==NOTE_OFF&&active&&active->note==int(e.note)){auto q=*active;q.off=std::max(q.on,i);q.offSample=e.sample;notes.push_back(q);active.reset();}}
    if(active)notes.push_back(*active);for(size_t j=0;j<notes.size();++j){auto&q=notes[j];int a=q.on,b=std::clamp(q.off,a,N);for(int i=a;i<b;++i){pitch[i]=float(q.note);gate[i]=1;vel[i]=q.velocity;if(i<a+2&&q.onSample>=start)onset[i]=1;}}
    std::vector<float>noteProg(N,0),durBeats(N,0),prevInt(N,0),nextInt(N,0);for(size_t j=0;j<notes.size();++j){auto&q=notes[j];int a=q.on,b=std::clamp(q.off,a,N),L=std::max(1,b-a);for(int i=a;i<b;++i){noteProg[i]=float(i-a)/L;durBeats[i]=float(L)/fps_*std::max(24.f,policy.tempo)/60.f;if(j)prevInt[i]=float(q.note-notes[j-1].note);if(j+1<notes.size())nextInt[i]=float(notes[j+1].note-q.note);}}
    std::vector<float>phrase(N);for(int i=0;i<N;++i)phrase[i]=N>1?float(i)/float(N-1):0;float assist=policy.assist<=0?0.f:(policy.assist==1?.6f:1.f);
    // Smart Dynamics (same authority rule: opt-in only).
    if(policy.assist>0&&policy.smartDynamics){auto orig=dyn;for(int i=0;i<N;++i){float reg=std::clamp((pitch[i]-48.f)/36.f,0.f,1.f),leap=std::clamp((std::abs(prevInt[i])+std::abs(nextInt[i]))/24.f,0.f,1.f),style=0;if(policy.style==1)style=.05f*std::sin(kPi*phrase[i])+.04f*std::sin(kPi*noteProg[i])-.02f*onset[i];else if(policy.style==2)style=.025f*onset[i]+.02f*(1-noteProg[i])-.01f*std::sin(kPi*phrase[i]);else if(policy.style==3)style=.08f*onset[i]+.055f*std::sin(kPi*noteProg[i])+.035f;else if(policy.style==4)style=.03f*std::max(0.f,std::sin(2*kPi*phrase[i]*4))+.03f*onset[i];else if(policy.style==5)style=.045f*std::sin(kPi*phrase[i])+.025f*std::sin(kPi*noteProg[i])-.015f*onset[i];float target=clamp01(dyn[i]+.035f*(reg-.5f)+.045f*leap+.035f*onset[i]+.025f*std::sin(kPi*noteProg[i])+style);target=target*gate[i]+dyn[i]*(1-gate[i]);float mix=policy.assist==1?.35f:.65f;dyn[i]=clamp01(orig[i]*(1-mix)+target*mix);}smooth(dyn,6);}
    // Smart articulation only alters generic authored states.
    if(policy.assist>0&&policy.smartArticulation){bool fast=policy.tempo>=118;for(int i=0;i<N;++i){bool mut=art[i]==0||art[i]==1||art[i]==3;int64_t proposed=art[i];bool sh=durBeats[i]>0&&durBeats[i]<(fast?.42f:.32f),med=durBeats[i]>=.32f&&durBeats[i]<.8f,conn=leg[i]>.55f&&std::abs(prevInt[i])<=7&&std::abs(nextInt[i])<=7;if(mut&&sh&&gate[i]>0)proposed=fast?6:5;else if(mut&&!sh&&conn&&gate[i]>0)proposed=1;else if(mut&&med&&!conn&&gate[i]>0)proposed=4;if((policy.assist==1&&art[i]==0)||policy.assist>=2)art[i]=proposed;}}
    for(int i=0;i<N;++i){if(art[i]==7){attack[i]=clamp01(attack[i]+.12f);dyn[i]=clamp01(dyn[i]+.035f);}if(art[i]==1){trans[i]=clamp01(trans[i]-.06f);dyn[i]=clamp01(dyn[i]+.02f);}if(art[i]==4){attack[i]=clamp01(attack[i]+.15f);tight[i]=clamp01(tight[i]+.1f);}}
    std::vector<float>bow(N),vibOn(N,0),vj(N,0);for(int i=0;i<N;++i)bow[i]=clamp01(onset[i]*(.18f+.37f*assist)+(1-leg[i])*onset[i]*(.10f+.25f*assist));
    // Q4 zero-weight context: density/sync/support/top/register/motion and hidden coordination.
    auto ss=scoreState(allEvents,start,end,sr,fps_,N);for(int i=0;i<N;++i){float density=0,maxOther=0,sumOther=0;int count=0,sync=0;for(int p=0;p<4;++p)if(p!=part){float g=ss.gate[size_t(p*N+i)];density+=g;if(g>0){maxOther=std::max(maxOther,ss.pitch[size_t(p*N+i)]);sumOther+=ss.pitch[size_t(p*N+i)];++count;}int r=std::max(1,int(std::round(.05*fps_)));for(int q=std::max(0,i-r);q<std::min(N,i+r+1);++q)if(ss.onset[size_t(p*N+q)]>0){++sync;break;}}density=std::clamp(density/3.f,0.f,1.f);float own=pitch[i],support=(gate[i]>0&&maxOther>own)?1.f:0.f,top=(gate[i]>0&&(maxOther<=own||maxOther==0))?1.f:0.f,mean=count?sumOther/count:own,reg=gate[i]>0?std::clamp((own-mean)/24.f,-1.f,1.f):0.f;float syncv=std::clamp(sync/3.f,0.f,1.f);float onsetAge=1.f;for(int q=i;q>=0;--q)if(onset[q]>0){onsetAge=std::min(1.f,float(i-q)/fps_/std::max(.001f,2*60.f/std::max(24.f,policy.tempo)));break;}float reentry=0;if(onset[i]>0&&i>int(.75*(60.f/std::max(24.f,policy.tempo))*fps_))reentry=1;
        float vals[kFrontierContext]={density,syncv,support,top,reg,0,phrase[i],onsetAge,std::clamp(prevInt[i]/24.f,-1.f,1.f),std::clamp(nextInt[i]/24.f,-1.f,1.f),0,0,clamp01(leg[i]),reentry};for(int k=0;k<kFrontierContext;++k)c.frontierContext[size_t(k*N+i)]=vals[k];bow[i]=clamp01(bow[i]+assist*(.12f*syncv+.08f*density*support));vibOn[i]=clamp01(vibOn[i]+assist*(.06f*top*(1-syncv)+.025f*density));}
    // v2.8 Phrase Director and per-player ensemble looseness remain zero-weight control transforms.
    if(policy.phraseDirector&&policy.assist>0){float strength=policy.assist==1?.35f:.65f;for(int i=0;i<N;++i){float arch=std::sin(kPi*std::clamp(phrase[i],0.f,1.f))*gate[i],leap=std::clamp(std::abs(nextInt[i])/12.f,0.f,1.f)*gate[i];bool cadence=noteProg[i]>.72f&&std::abs(nextInt[i])<1e-4f&&gate[i]>0;dyn[i]=clamp01(dyn[i]+strength*(.035f*arch+.018f*leap-(cadence?.025f:0.f)));attack[i]=clamp01(attack[i]+strength*(.045f*leap-(cadence?.025f:0.f)));trans[i]=clamp01(trans[i]+strength*(.035f*leap+(cadence?.055f:0.f)));vibOn[i]=clamp01(vibOn[i]+strength*(.07f*arch+(cadence?.035f:0.f)));}}
    if(policy.ensembleLooseness>0){float ph=float(part+1)*1.61803398875f;for(int i=0;i<N;++i){float d=std::sin((2*kPi*i/std::max(1,N-1))+ph)*(.035f*std::clamp(policy.ensembleLooseness,0.f,1.f));bow[i]=clamp01(bow[i]+d);vibOn[i]=clamp01(vibOn[i]-d*.55f);}}
    // v2.8 portable Retake contract: backend/model fingerprints must not change the take.
    if(policy.retakeTarget>0&&policy.retakeAmount>0){
        const auto key=[&](int salt){return std::string("retake-v28|p=")+std::to_string(part)+"|n="+std::to_string(policy.retakeNonce)+"|t="+std::to_string(policy.retakeTarget)+"|salt="+std::to_string(salt);};
        float a=policy.retakeAmount;
        if(policy.retakeTarget==1||policy.retakeTarget==7){auto noise=ParityV27::normalArray(key(11),size_t(N));smooth(noise,18);for(int i=0;i<N;++i){attack[i]=clamp01(attack[i]+noise[i]*.044f*a);tight[i]=clamp01(tight[i]+noise[i]*.03025f*a);bow[i]=clamp01(bow[i]+noise[i]*.02475f*a);}}
        if(policy.retakeTarget==2||policy.retakeTarget==7){auto noise=ParityV27::normalArray(key(23),size_t(N));smooth(noise,24);for(int i=0;i<N;++i)dyn[i]=clamp01(dyn[i]+noise[i]*.045f*a);}
        if(policy.retakeTarget==3||policy.retakeTarget==7){auto noise=ParityV27::normalArray(key(37),size_t(N));smooth(noise,16);for(int i=0;i<N;++i){vibOn[i]=clamp01(vibOn[i]+noise[i]*.022f*a);vj[i]=clamp01(vj[i]+std::abs(noise[i])*.016f*a);}}
        if((policy.retakeTarget==4||policy.retakeTarget==7)&&!policy.midiAuthorityLock){auto noise=ParityV27::normalArray(key(41),size_t(N));smooth(noise,20);for(int i=0;i<N;++i)pb[i]=clamp01(pb[i]+noise[i]*.012f*a);}
        if(policy.retakeTarget==5||policy.retakeTarget==7){auto noise=ParityV27::normalArray(key(53),size_t(N));smooth(noise,12);for(int i=0;i<N;++i)trans[i]=clamp01(trans[i]+noise[i]*.06f*a);}
        if(policy.retakeTarget==6||policy.retakeTarget==7){auto noise=ParityV27::normalArray(key(67),size_t(N));smooth(noise,10);for(int i=0;i<N;++i){attack[i]=clamp01(attack[i]+noise[i]*.075f*a);bow[i]=clamp01(bow[i]+noise[i]*.0525f*a);}}
    }
    const float bpm=std::max(24.f,policy.tempo),spb=60.f/bpm;std::array<std::vector<float>,kRawControls>v;for(auto&x:v)x.assign(size_t(N),0);v[0]=pitch;v[1]=gate;v[2]=onset;v[3]=vel;v[4]=dyn;v[5]=vib;v[6]=exp;v[7]=leg;v[8]=pb;v[9]=trans;v[10]=tight;v[11]=attack;v[12]=noteProg;v[13]=phrase;v[14]=prevInt;v[15]=nextInt;v[16]=bow;v[17]=vibOn;v[18].assign(N,bpm);v[19].assign(N,spb);v[20]=durBeats;v[22]=speed;v[25]=vj;for(int k:{26,27,28,29,30,32})v[k].assign(N,1);for(int i=0;i<N;++i)for(int k=0;k<kRawControls;++k)c.raw[size_t(i*kRawControls+k)]=v[k][i];for(int i=0;i<N;++i)c.articulationCurve[size_t(i)]=float(art[size_t(i)]);c.articulation=art.empty()?0:art[0];c.gate=gate;return c;
}

InProcessEngine::InProcessEngine(std::shared_ptr<NeuralSession>s,EngineConfig cfg):session_(std::move(s)),cfg_(cfg),controls_(cfg.controlFps){}
bool InProcessEngine::ready()const{return session_&&session_->ready();}
std::string InProcessEngine::backendName()const{return session_?session_->name():"none";}

bool InProcessEngine::render(const std::vector<TimelineEvent>&events,int64_t start,int64_t end,const ProductShell::Policy&policy,EngineRender&out){
    if(!ready()||end<=start)return false;const int frames=int(end-start);const int outCh=policy.multiOut?kStageChannels:2;std::vector<float>mix(size_t(frames*outCh),0);int calls=0,voices=0;const int steps=std::max(1,policy.mode==1?cfg_.stepsAuto:cfg_.stepsHq);const float guidance=policy.mode==1?cfg_.cfgAuto:cfg_.cfgHq;std::string fp=session_->fingerprint();
    for(int part=0;part<4;++part){auto lanes=policy.polyphony?allocatePolyphonicLanes(events,part,cfg_.maxVoices):std::vector<std::vector<TimelineEvent>>{{}};if(!policy.polyphony){for(auto&e:events)if(int(e.part)==part||int(e.type)==RESET)lanes[0].push_back(e);}for(size_t voice=0;voice<lanes.size();++voice){auto c=controls_.build(events,lanes[voice],part,start,end,cfg_.sampleRate,policy,fp);if(c.gate.empty()||*std::max_element(c.gate.begin(),c.gate.end())<=0)continue;++voices;int tlat=std::max(2,int(std::ceil(double(frames)/cfg_.sampleRate*cfg_.latentHz)));std::array<int64_t,3>shape{1,cfg_.latentChannels,tlat};std::vector<float>x=ParityV27::normalArray(ParityV27::eventSeedKey(start,end,cfg_.sampleRate,part,int(voice),lanes[voice]),size_t(cfg_.latentChannels*tlat));float dt=1.f/steps;
            auto velocity=[&](const std::vector<float>&xin,float t,std::vector<float>&v){RendererInputs ri{xin,shape,t,dt,&c};++calls;return session_->runRenderer(ri,v);};
            for(int i=0;i<steps;++i){std::vector<float>v0;if(!velocity(x,float(i)/steps,v0)||v0.size()!=x.size())return false;if(std::abs(guidance-1.f)>1e-6f)return false;if(cfg_.solver==Solver::Heun&&i<steps-1){auto xp=x;for(size_t k=0;k<x.size();++k)xp[k]+=v0[k]*dt;std::vector<float>v1;if(!velocity(xp,float(i+1)/steps,v1)||v1.size()!=x.size())return false;for(size_t k=0;k<x.size();++k)x[k]+=(v0[k]+v1[k])*.5f*dt;}else for(size_t k=0;k<x.size();++k)x[k]+=v0[k]*dt;}
            std::vector<float>mono;int codecSr=cfg_.codecSampleRate;if(!session_->runDecoder(x,shape,mono,codecSr)||mono.empty())return false;if(codecSr!=int(cfg_.sampleRate)||int(mono.size())!=frames){std::vector<float> res(size_t(frames), 0.f);double scale=double(mono.size())/frames;for(int i=0;i<frames;++i){double p=i*scale;int a=std::clamp(int(p),0,int(mono.size())-1),b=std::min(a+1,int(mono.size())-1);float f=float(p-a);res[size_t(i)]=mono[size_t(a)]*(1-f)+mono[size_t(b)]*f;}mono.swap(res);}else mono.resize(size_t(frames));
            std::vector<float>stage;stageBundle(mono,int(cfg_.sampleRate),medianRoom(lanes[voice]),policy.stagePerspective,stage);float base[4]={-.45f,-.15f,.12f,.38f};float spread=(float(voice)-float(lanes.size()-1)*.5f)*.055f,pan=std::clamp(base[part]+spread,-.92f,.92f),gl=std::sqrt(.5f*(1-pan)),gr=std::sqrt(.5f*(1+pan));float norm=1.f/std::sqrt(std::max<size_t>(1,lanes.size()));int pairs=policy.multiOut?17:1;for(int i=0;i<frames;++i)for(int j=0;j<pairs;++j){mix[size_t(i*outCh+2*j)]+=stage[size_t(i*kStageChannels+2*j)]*gl*norm;mix[size_t(i*outCh+2*j+1)]+=stage[size_t(i*kStageChannels+2*j+1)]*gr*norm;}
        }}
    for(float&x:mix)x=std::clamp(x,-.98f,.98f);out.sampleRate=cfg_.sampleRate;out.frames=uint32_t(frames);out.channels=uint16_t(outCh);out.interleaved=std::move(mix);out.voicesRendered=voices;out.neuralCalls=calls;out.backend=session_->name();return true;
}

bool DeterministicMockSession::runRenderer(const RendererInputs&in,std::vector<float>&v){v.resize(in.latent.size());float dyn=.62f,gate=0;if(in.controls&&in.controls->frames>0){int T=in.controls->frames;for(int i=0;i<T;++i){dyn+=in.controls->raw[size_t(i*kRawControls+4)];gate+=in.controls->raw[size_t(i*kRawControls+1)];}dyn/=float(T+1);gate/=float(T);}for(size_t i=0;i<v.size();++i)v[i]=.035f*std::tanh(in.latent[i])+.018f*dyn+.006f*gate+.002f*in.flowH;return true;}
bool DeterministicMockSession::runDecoder(std::span<const float>latent,std::array<int64_t,3>shape,std::vector<float>&mono,int&sampleRate){sampleRate=48000;int t=int(shape[2]);int frames=std::max(1,t*1600);mono.resize(size_t(frames));float amp=0;for(float x:latent)amp+=std::abs(x);amp=std::clamp(amp/std::max<size_t>(1,latent.size())*.025f,.005f,.06f);for(int i=0;i<frames;++i){float ph=2*kPi*220.f*i/sampleRate;float env=std::min(1.f,float(i)/240.f)*std::min(1.f,float(frames-i)/480.f);mono[size_t(i)]=std::sin(ph)*amp*env;}return true;}

} // namespace Sonicraft::InProcess

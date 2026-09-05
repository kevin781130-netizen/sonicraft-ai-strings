#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <mmsystem.h>
#include <algorithm>
#include <cmath>
#include <atomic>
#include <chrono>
#include <list>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#include "../realtime_shell_core.h"
#include "../low_latency_engine.h"
#include "wasapi_event_output.h"
#pragma comment(lib,"winmm.lib")
#pragma comment(lib,"comctl32.lib")

using namespace Sonicraft::ProductShell;
using namespace Sonicraft::LowLatency;
namespace {
constexpr UINT WM_APP_MIDI=WM_APP+10;
enum : int { IDC_MIDI=100,IDC_AUDIO,IDC_PART,IDC_ASSIST,IDC_STYLE,IDC_RETAKE,IDC_RETAKE_AMOUNT,IDC_SMART_DYN,IDC_SMART_ART,IDC_POLY,IDC_START,IDC_NEW_TAKE,IDC_STATUS,IDC_MASTER=200,IDC_FEED0=210 };
struct AudioBlock { WAVEHDR hdr{}; std::vector<int16_t> pcm; };
struct App {
    HWND hwnd{}; Timeline timeline; RendererClient client; Policy policy; MixerState mixer;
    std::atomic<bool> running{false}; std::thread worker; std::atomic<int64_t> renderCursor{0};
    uint32_t sr=48000; std::atomic<int> quantumMs{80}; std::atomic<int64_t> quantumFrames{3840}; std::atomic<uint64_t> req{250000};
    HMIDIIN midi{}; HWAVEOUT wave{}; UINT midiDevice=UINT(-1),audioDevice=WAVE_MAPPER;
    std::mutex audioMu; std::list<std::unique_ptr<AudioBlock>> audio;
    Sonicraft::WinAudio::WasapiEventOutput wasapi; bool useWasapi=true;
    AdaptiveQuantumController quantumCtl; MidiTimestampCalibrator midiClock; GlitchGuard glitch{48};
    std::atomic<bool> freshAttack{false}; std::atomic<double> lastRenderMs{0.0};
    int tailBlocks=0; int underruns=0;
};
App* g=nullptr;

void setText(HWND h,const std::wstring&s){SetWindowTextW(h,s.c_str());}
HWND add(HWND p,const wchar_t* cls,const wchar_t* text,DWORD style,int x,int y,int w,int h,int id){return CreateWindowExW(0,cls,text,WS_CHILD|WS_VISIBLE|style,x,y,w,h,p,(HMENU)(INT_PTR)id,GetModuleHandleW(nullptr),nullptr);}
void comboAdd(HWND h,const wchar_t*s){SendMessageW(h,CB_ADDSTRING,0,(LPARAM)s);}
int comboSel(HWND h){return int(SendMessageW(h,CB_GETCURSEL,0,0));}

void closeMidi(){if(g&&g->midi){midiInStop(g->midi);midiInReset(g->midi);midiInClose(g->midi);g->midi=nullptr;}}
void CALLBACK midiCb(HMIDIIN,UINT msg,DWORD_PTR instance,DWORD_PTR p1,DWORD_PTR p2){if(msg==MIM_DATA){auto*a=(App*)instance;if(a&&a->hwnd)PostMessageW(a->hwnd,WM_APP_MIDI,WPARAM(p1),LPARAM(p2));}}
void openMidi(){closeMidi();if(!g)return;HWND cb=GetDlgItem(g->hwnd,IDC_MIDI);int sel=comboSel(cb);if(sel<0)return;g->midiDevice=UINT(sel);if(midiInOpen(&g->midi,g->midiDevice,(DWORD_PTR)midiCb,(DWORD_PTR)g,CALLBACK_FUNCTION)==MMSYSERR_NOERROR){g->midiClock.reset(g->sr,g->renderCursor.load(),0);midiInStart(g->midi);}else g->midi=nullptr;}

void cleanupAudio(bool all=false){if(!g)return;std::lock_guard<std::mutex> lk(g->audioMu);for(auto it=g->audio.begin();it!=g->audio.end();){auto&b=**it;if(all||(b.hdr.dwFlags&WHDR_DONE)){if(g->wave)waveOutUnprepareHeader(g->wave,&b.hdr,sizeof(b.hdr));it=g->audio.erase(it);}else ++it;}}
size_t queuedWaveBlocks(){if(!g)return 0;cleanupAudio(false);std::lock_guard<std::mutex>lk(g->audioMu);return g->audio.size();}
size_t queuedAudioFrames(){if(!g)return 0;if(g->useWasapi&&g->wasapi.ready())return g->wasapi.queuedFrames();return queuedWaveBlocks()*size_t(std::max<int64_t>(1,g->quantumFrames.load()));}
void closeWave(){if(!g||!g->wave)return;waveOutReset(g->wave);cleanupAudio(true);waveOutClose(g->wave);g->wave=nullptr;}
bool openWave(){if(!g)return false;closeWave();WAVEFORMATEX f{};f.wFormatTag=WAVE_FORMAT_PCM;f.nChannels=2;f.nSamplesPerSec=g->sr;f.wBitsPerSample=16;f.nBlockAlign=4;f.nAvgBytesPerSec=f.nSamplesPerSec*f.nBlockAlign;return waveOutOpen(&g->wave,g->audioDevice,&f,0,0,CALLBACK_NULL)==MMSYSERR_NOERROR;}
bool queueWave(const std::vector<float>&x){if(!g||!g->wave||x.empty())return false;auto b=std::make_unique<AudioBlock>();b->pcm.resize(x.size());for(size_t i=0;i<x.size();++i)b->pcm[i]=int16_t(std::lround(std::clamp(x[i],-1.f,1.f)*32767.f));b->hdr.lpData=(LPSTR)b->pcm.data();b->hdr.dwBufferLength=DWORD(b->pcm.size()*sizeof(int16_t));if(waveOutPrepareHeader(g->wave,&b->hdr,sizeof(b->hdr))!=MMSYSERR_NOERROR)return false;if(waveOutWrite(g->wave,&b->hdr,sizeof(b->hdr))!=MMSYSERR_NOERROR){waveOutUnprepareHeader(g->wave,&b->hdr,sizeof(b->hdr));return false;}std::lock_guard<std::mutex>lk(g->audioMu);g->audio.push_back(std::move(b));return true;}
bool openAudio(){if(!g)return false;g->wasapi.close();closeWave();g->useWasapi=(comboSel(GetDlgItem(g->hwnd,IDC_AUDIO))==0);if(g->useWasapi&&g->wasapi.openDefault(g->sr))return true;g->useWasapi=false;int sel=comboSel(GetDlgItem(g->hwnd,IDC_AUDIO));g->audioDevice=sel<=1?WAVE_MAPPER:UINT(sel-2);return openWave();}
bool queueAudio(std::vector<float> x,bool hardRelease=false){if(!g||x.empty())return false;g->glitch.processStereo(x,hardRelease);if(g->useWasapi&&g->wasapi.ready())return g->wasapi.pushStereo(x);return queueWave(x);}
void closeAudio(){if(!g)return;g->wasapi.close();closeWave();}

void renderLoop(){double previousMs=0.0;bool deadlineMiss=false;while(g&&g->running.load()){
    bool active=g->timeline.anyActiveNotes();if(active)g->tailBlocks=3;if(g->useWasapi&&g->wasapi.ready())g->wasapi.setActive(active||g->tailBlocks>0);if(!active&&g->tailBlocks<=0){std::this_thread::sleep_for(std::chrono::milliseconds(2));continue;}
    size_t queued=queuedAudioFrames();const bool attack=g->freshAttack.exchange(false);auto dec=g->quantumCtl.choose(attack,previousMs,deadlineMiss,queued>0?1:0);g->quantumMs.store(dec.quantumMs);int64_t qFrames=int64_t(g->sr)*dec.quantumMs/1000;g->quantumFrames.store(qFrames);
    const size_t maxAhead=size_t(g->sr)*120/1000;if(queued>maxAhead){std::this_thread::sleep_for(std::chrono::milliseconds(1));continue;}
    if(queued==0&&g->renderCursor.load()>0)++g->underruns;
    int64_t start=g->renderCursor.load(),end=start+qFrames;auto ev=g->timeline.contextFor(start,end,int64_t(g->sr)*5);if(ev.empty()){std::this_thread::sleep_for(std::chrono::milliseconds(1));continue;}
    RenderAudio a;auto p=g->policy;p.multiOut=true;p.lookahead=std::min(.08f,float(dec.quantumMs)/1000.f);auto t0=std::chrono::steady_clock::now();bool ok=g->client.render(ev,start,end,g->sr,p,g->req.fetch_add(1),a);previousMs=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-t0).count();g->lastRenderMs.store(previousMs);deadlineMiss=previousMs>dec.quantumMs;
    if(ok){auto y=mixToStereo(a,g->mixer);bool finalRelease=!active&&g->tailBlocks<=1;queueAudio(std::move(y),finalRelease);g->renderCursor.store(end);if(!active)--g->tailBlocks;}else std::this_thread::sleep_for(std::chrono::milliseconds(8));
    cleanupAudio(false);
}}
void startEngine(){if(!g||g->running.load())return;g->timeline.reset();g->renderCursor=0;g->tailBlocks=0;g->underruns=0;g->quantumCtl.reset();g->glitch.reset();g->freshAttack=false;g->quantumMs=80;g->quantumFrames=int64_t(g->sr)*80/1000;if(!openAudio()){MessageBoxW(g->hwnd,L"Could not open WASAPI low-latency output or the selected legacy output.",L"SONICRAFT",MB_ICONERROR);return;}g->running=true;g->worker=std::thread(renderLoop);}
void stopEngine(){if(!g)return;g->running=false;if(g->worker.joinable())g->worker.join();closeAudio();g->timeline.reset();}

void populateDevices(HWND w){HWND m=GetDlgItem(w,IDC_MIDI);SendMessageW(m,CB_RESETCONTENT,0,0);UINT nm=midiInGetNumDevs();for(UINT i=0;i<nm;++i){MIDIINCAPSW c{};if(midiInGetDevCapsW(i,&c,sizeof(c))==MMSYSERR_NOERROR)comboAdd(m,c.szPname);}if(nm)SendMessageW(m,CB_SETCURSEL,0,0);HWND a=GetDlgItem(w,IDC_AUDIO);SendMessageW(a,CB_RESETCONTENT,0,0);comboAdd(a,L"WASAPI Default · event-driven low latency");comboAdd(a,L"Legacy Windows Default (waveOut)");UINT na=waveOutGetNumDevs();for(UINT i=0;i<na;++i){WAVEOUTCAPSW c{};if(waveOutGetDevCapsW(i,&c,sizeof(c))==MMSYSERR_NOERROR)comboAdd(a,c.szPname);}SendMessageW(a,CB_SETCURSEL,0,0);}
void syncPolicy(HWND w){g->timeline.setSelectedPart(std::max(0,comboSel(GetDlgItem(w,IDC_PART))));g->policy.assist=std::max(0,comboSel(GetDlgItem(w,IDC_ASSIST)));g->policy.style=std::max(0,comboSel(GetDlgItem(w,IDC_STYLE)));g->policy.retakeTarget=std::max(0,comboSel(GetDlgItem(w,IDC_RETAKE)));g->policy.smartDynamics=SendMessageW(GetDlgItem(w,IDC_SMART_DYN),BM_GETCHECK,0,0)==BST_CHECKED;g->policy.smartArticulation=SendMessageW(GetDlgItem(w,IDC_SMART_ART),BM_GETCHECK,0,0)==BST_CHECKED;g->policy.polyphony=SendMessageW(GetDlgItem(w,IDC_POLY),BM_GETCHECK,0,0)==BST_CHECKED;g->policy.retakeAmount=float(SendMessageW(GetDlgItem(w,IDC_RETAKE_AMOUNT),TBM_GETPOS,0,0))/100.f;g->mixer.master=float(SendMessageW(GetDlgItem(w,IDC_MASTER),TBM_GETPOS,0,0))/100.f;for(int i=0;i<11;++i)g->mixer.feed[i]=float(SendMessageW(GetDlgItem(w,IDC_FEED0+i),TBM_GETPOS,0,0))/100.f;}

void buildUi(HWND w){
    add(w,L"STATIC",L"SONICRAFT AI STRINGS · v2.5 ULTRA-LOW-LATENCY ENGINE",SS_LEFT,18,14,640,28,-1);
    add(w,L"STATIC",L"MIDI Input",0,18,54,100,20,-1);add(w,WC_COMBOBOXW,L"",CBS_DROPDOWNLIST|WS_VSCROLL,118,50,250,160,IDC_MIDI);
    add(w,L"STATIC",L"Audio Output",0,386,54,100,20,-1);add(w,WC_COMBOBOXW,L"",CBS_DROPDOWNLIST|WS_VSCROLL,486,50,270,160,IDC_AUDIO);
    add(w,L"BUTTON",L"Start Realtime Preview",BS_PUSHBUTTON,776,48,180,28,IDC_START);
    add(w,L"STATIC",L"Part",0,18,100,60,20,-1);HWND part=add(w,WC_COMBOBOXW,L"",CBS_DROPDOWNLIST,70,96,130,140,IDC_PART);for(auto*s:{L"Vln I",L"Vln II",L"Viola",L"Cello"})comboAdd(part,s);SendMessageW(part,CB_SETCURSEL,0,0);
    add(w,L"STATIC",L"AI Assist",0,220,100,70,20,-1);HWND assist=add(w,WC_COMBOBOXW,L"",CBS_DROPDOWNLIST,292,96,120,140,IDC_ASSIST);for(auto*s:{L"Manual",L"Assist",L"Auto"})comboAdd(assist,s);SendMessageW(assist,CB_SETCURSEL,1,0);
    add(w,L"STATIC",L"Style",0,432,100,50,20,-1);HWND st=add(w,WC_COMBOBOXW,L"",CBS_DROPDOWNLIST,482,96,150,170,IDC_STYLE);for(auto*s:{L"Neutral",L"Adagio",L"Allegro",L"con Fuoco",L"Pop",L"Ballade"})comboAdd(st,s);SendMessageW(st,CB_SETCURSEL,0,0);
    add(w,L"STATIC",L"Retake",0,650,100,60,20,-1);HWND rt=add(w,WC_COMBOBOXW,L"",CBS_DROPDOWNLIST,710,96,130,150,IDC_RETAKE);for(auto*s:{L"Off",L"Timbre",L"Dynamics",L"Vibrato",L"All"})comboAdd(rt,s);SendMessageW(rt,CB_SETCURSEL,0,0);add(w,L"BUTTON",L"New Take",BS_PUSHBUTTON,850,95,106,25,IDC_NEW_TAKE);
    add(w,L"BUTTON",L"Smart Dynamics",BS_AUTOCHECKBOX,18,136,140,24,IDC_SMART_DYN);add(w,L"BUTTON",L"Smart Articulation",BS_AUTOCHECKBOX,166,136,150,24,IDC_SMART_ART);HWND poly=add(w,L"BUTTON",L"Independent Polyphony",BS_AUTOCHECKBOX,324,136,170,24,IDC_POLY);SendMessageW(poly,BM_SETCHECK,BST_CHECKED,0);
    add(w,L"STATIC",L"Retake Amount",0,520,138,100,20,-1);HWND ra=add(w,TRACKBAR_CLASSW,L"",TBS_AUTOTICKS,620,132,220,30,IDC_RETAKE_AMOUNT);SendMessageW(ra,TBM_SETRANGE,TRUE,MAKELPARAM(0,100));SendMessageW(ra,TBM_SETPOS,TRUE,0);
    add(w,L"STATIC",L"SCORING STAGE MIXER · Master is the default; raise aux feeds only when you want to build your own perspective.",0,18,184,900,24,-1);
    const wchar_t* names[]={L"Master",L"Spot L",L"Spot C",L"Spot R",L"Tree L",L"Tree C",L"Tree R",L"Wide L",L"Wide R",L"Room L",L"Room R",L"Rear"};
    for(int i=0;i<12;++i){int col=i/6,row=i%6,x=18+col*470,y=218+row*48;add(w,L"STATIC",names[i],0,x,y,78,20,-1);HWND sl=add(w,TRACKBAR_CLASSW,L"",TBS_AUTOTICKS,x+82,y-4,340,32,i==0?IDC_MASTER:IDC_FEED0+i-1);SendMessageW(sl,TBM_SETRANGE,TRUE,MAKELPARAM(0,100));SendMessageW(sl,TBM_SETPOS,TRUE,i==0?100:0);}
    add(w,L"STATIC",L"Strict MIDI Authority: notes, pitch bend and authored CC remain yours. Smart Dynamics / Articulation are OFF by default.",0,18,520,920,26,-1);
    add(w,L"STATIC",L"Adaptive neural windows start at 40 ms for fresh attacks and expand only when stability requires it. Final AUTO/HQ acoustic promotion remains unchanged.",0,18,550,920,26,-1);
    add(w,L"STATIC",L"Service: checking…",0,18,590,900,26,IDC_STATUS);
    populateDevices(w);syncPolicy(w);
}

LRESULT CALLBACK proc(HWND w,UINT msg,WPARAM wp,LPARAM lp){switch(msg){
case WM_CREATE:g->hwnd=w;buildUi(w);SetTimer(w,1,600,nullptr);return 0;
case WM_APP_MIDI:{DWORD m=DWORD(wp);uint8_t st=uint8_t(m&255),d1=uint8_t((m>>8)&255),d2=uint8_t((m>>16)&255);uint32_t ts=uint32_t(lp);int64_t s=std::max<int64_t>(g->midiClock.sampleFor(ts),g->renderCursor.load());if((st&0xF0)==0x90&&d2>0){g->freshAttack=true;if(queuedAudioFrames()==0&&s>g->renderCursor.load())g->renderCursor.store(s);}g->timeline.pushMidiShort(st,d1,d2,s,g->policy.tempo);return 0;}
case WM_COMMAND:{int id=LOWORD(wp);if(id==IDC_MIDI&&HIWORD(wp)==CBN_SELCHANGE){if(g->running)openMidi();}else if(id==IDC_AUDIO&&HIWORD(wp)==CBN_SELCHANGE){if(g->running){stopEngine();startEngine();openMidi();}}else if(id==IDC_START){if(g->running){closeMidi();stopEngine();setText(GetDlgItem(w,IDC_START),L"Start Realtime Preview");}else{syncPolicy(w);startEngine();openMidi();setText(GetDlgItem(w,IDC_START),L"Stop Realtime Preview");}}else if(id==IDC_NEW_TAKE){g->policy.retakeNonce=(g->policy.retakeNonce+1)&255;}else syncPolicy(w);return 0;}
case WM_HSCROLL:syncPolicy(w);return 0;
case WM_TIMER:{syncPolicy(w);bool ready=g->client.ping(g->sr);std::wstring t=ready?L"Service: READY":L"Service: OFFLINE";t+=g->useWasapi&&g->wasapi.ready()?L" · WASAPI EVENT":L" · LEGACY AUDIO";t+=L" · q="+std::to_wstring(g->quantumMs.load())+L"ms · queued="+std::to_wstring(queuedAudioFrames())+L"fr · underruns="+std::to_wstring(g->underruns+(g->useWasapi?int(g->wasapi.underruns()):0))+L" · render="+std::to_wstring(int(g->lastRenderMs.load()))+L"ms";setText(GetDlgItem(w,IDC_STATUS),t);return 0;}
case WM_DESTROY:KillTimer(w,1);closeMidi();stopEngine();PostQuitMessage(0);return 0;}return DefWindowProcW(w,msg,wp,lp);}
}

int WINAPI wWinMain(HINSTANCE h,HINSTANCE,LPWSTR,int show){INITCOMMONCONTROLSEX ic{sizeof(ic),ICC_BAR_CLASSES};InitCommonControlsEx(&ic);App app;g=&app;WNDCLASSW wc{};wc.lpfnWndProc=proc;wc.hInstance=h;wc.lpszClassName=L"SonicraftProductShellV25";wc.hCursor=LoadCursor(nullptr,IDC_ARROW);wc.hbrBackground=(HBRUSH)(COLOR_WINDOW+1);RegisterClassW(&wc);HWND w=CreateWindowExW(0,wc.lpszClassName,L"SONICRAFT AI Strings Q4 · Ultra-Low-Latency Product Shell",WS_OVERLAPPED|WS_CAPTION|WS_SYSMENU|WS_MINIMIZEBOX,CW_USEDEFAULT,CW_USEDEFAULT,990,680,nullptr,nullptr,h,nullptr);if(!w)return 2;ShowWindow(w,show);UpdateWindow(w);MSG m{};while(GetMessageW(&m,nullptr,0,0)>0){TranslateMessage(&m);DispatchMessageW(&m);}g=nullptr;return int(m.wParam);}
#endif

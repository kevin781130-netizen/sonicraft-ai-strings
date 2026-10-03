#include "score_editor_view_v70.h"
#include "controller.h"
#include "ids.h"
#include "score_document_v70.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cwctype>
#include <iterator>
#include <cstring>
#include <filesystem>
#include <string>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commdlg.h>
#endif

namespace Sonicraft::AIStrings {
using namespace VSTGUI;

namespace {
constexpr CColor kBg{9,13,18,255};
constexpr CColor kPanel{20,27,36,255};
constexpr CColor kPanel2{16,23,32,255};
constexpr CColor kLine{43,55,70,255};
constexpr CColor kLineStrong{66,82,102,255};
constexpr CColor kText{243,245,247,255};
constexpr CColor kMuted{137,151,168,255};
constexpr CColor kGold{215,173,99,255};
constexpr CColor kGold2{239,203,138,255};
constexpr CColor kBlue{123,180,213,255};
constexpr CColor kGreen{119,199,155,255};
constexpr CColor kRed{210,122,122,255};
constexpr CColor kGhost{76,91,110,110};

void fill(CDrawContext* c,const CRect&r,const CColor&color){
    c->setFillColor(color); c->drawRect(r,kDrawFilled);
}
void stroke(CDrawContext* c,const CRect&r,const CColor&color,double width=1.){
    c->setFrameColor(color); c->setLineWidth(width); c->drawRect(r,kDrawStroked);
}
void text(CDrawContext* c,const std::string&s,const CRect&r,const CColor&color,
          CHoriTxtAlign align=kLeftText,double size=10.){
    c->setFont(kNormalFontSmall,size); c->setFontColor(color); c->drawString(s.c_str(),r,align,true);
}
void button(CDrawContext*c,const CRect&r,const std::string&s,bool active=false,const CColor&accent=kGold){
    fill(c,r,active?CColor{42,37,27,255}:CColor{21,30,40,255});
    stroke(c,r,active?accent:kLine);
    text(c,s,r,active?kText:CColor{203,211,219,255},kCenterText,9.);
}
bool inside(const CRect&r,const CPoint&p){return r.pointInside(p);}
double clampd(double x,double a,double b){return std::max(a,std::min(b,x));}
}

ScoreEditorViewV70::ScoreEditorViewV70(const CRect& size, Controller* controller)
: CView(size), controller_(controller) {
    setWantsFocus(true);
    setTransparency(false);
    activePart_=controllerActivePart();
    if(controller_)controller_->registerScoreEditorView(this);
}
ScoreEditorViewV70::~ScoreEditorViewV70() noexcept {
    if(controller_)controller_->unregisterScoreEditorView(this);
}

ScoreEditorViewV70::Layout ScoreEditorViewV70::layout() const {
    const auto r=getViewSize();
    Layout l{};
    l.all=r;
    l.toolbar=CRect(r.left+8,r.top+8,r.right-8,r.top+43);
    l.articulation=CRect(r.left+8,r.bottom-42,r.right-8,r.bottom-8);
    l.inspector=CRect(r.right-252,r.top+51,r.right-8,l.articulation.top-8);
    l.piano=CRect(r.left+8,r.top+51,l.inspector.left-8,l.articulation.top-8);
    return l;
}
int ScoreEditorViewV70::ppq() const noexcept {
    if(!controller_)return 480;
    return std::max(24,controller_->scoreDocument().ppq);
}
std::uint32_t ScoreEditorViewV70::snapTick(std::int64_t tick) const noexcept {
    const auto q=std::max(1,ppq()/std::max(1,snapDivision_));
    if(tick<=0)return 0;
    return static_cast<std::uint32_t>(((tick+q/2)/q)*q);
}
int ScoreEditorViewV70::controllerActivePart() const noexcept {
    if(!controller_)return 0;
    return std::clamp(static_cast<int>(std::lround(controller_->getParamNormalized(kParamActivePart)*3.0)),0,3);
}
void ScoreEditorViewV70::setActivePart(int part){
    activePart_=std::clamp(part,0,3);
    selected_=-1;
    if(controller_)controller_->performUiParamEdit(kParamActivePart,static_cast<double>(activePart_)/3.0);
    invalidateSelf();
}
void ScoreEditorViewV70::syncSelectedToHost(){
    if(!controller_||selected_<0)return;
    auto& d=controller_->scoreDocument();
    if(static_cast<std::size_t>(selected_)>=d.notes.size())return;
    const auto& n=d.notes[static_cast<std::size_t>(selected_)];
    controller_->performUiParamEdit(kParamActivePart,static_cast<double>(n.part)/3.0);
    controller_->performUiParamEdit(partParam(kParamPartArticulationBase,n.part),
                                    static_cast<double>(n.articulation)/11.0);
}
void ScoreEditorViewV70::invalidateSelf(){invalid();}
void ScoreEditorViewV70::ensureSelectionValid(){
    if(!controller_){selected_=-1;return;}
    const auto& n=controller_->scoreDocument().notes;
    if(selected_<0||static_cast<std::size_t>(selected_)>=n.size())selected_=-1;
}
CRect ScoreEditorViewV70::toolRect(int index) const {
    auto t=layout().toolbar;
    const double w=62., gap=5.;
    return CRect(t.left+6+index*(w+gap),t.top+5,t.left+6+index*(w+gap)+w,t.bottom-5);
}
CRect ScoreEditorViewV70::partRect(int part) const {
    auto t=layout().toolbar;
    const double w=57.,gap=4.,start=t.left+282;
    return CRect(start+part*(w+gap),t.top+5,start+part*(w+gap)+w,t.bottom-5);
}
CRect ScoreEditorViewV70::navRect(int index) const {
    auto t=layout().toolbar;
    const double w=29., start=t.right-166;
    return CRect(start+index*(w+4),t.top+5,start+index*(w+4)+w,t.bottom-5);
}
CRect ScoreEditorViewV70::snapRect() const {
    auto t=layout().toolbar;
    return CRect(t.right-94,t.top+5,t.right-5,t.bottom-5);
}
CRect ScoreEditorViewV70::velocityRect() const {
    auto i=layout().inspector;
    return CRect(i.left+16,i.top+184,i.right-16,i.top+204);
}
CRect ScoreEditorViewV70::deleteRect() const {
    auto i=layout().inspector;
    return CRect(i.left+16,i.bottom-42,i.right-16,i.bottom-12);
}
CRect ScoreEditorViewV70::articulationRect(int articulation) const {
    auto a=layout().articulation;
    const double x0=a.left+86;
    const double available=std::max(12.0,a.getWidth()-94.0);
    const double w=available/12.0;
    return CRect(x0+articulation*w,a.top+5,x0+(articulation+1)*w-3,a.bottom-5);
}
CRect ScoreEditorViewV70::noteRect(std::size_t index) const {
    CRect none{};
    if(!controller_)return none;
    const auto& d=controller_->scoreDocument();
    if(index>=d.notes.size())return none;
    const auto& n=d.notes[index];
    const auto p=layout().piano;
    constexpr double keyboard=50.;
    constexpr int hi=84,lo=43;
    const double row=(p.getHeight()-22.)/double(hi-lo+1);
    const double startQ=double(n.startTick)/double(ppq());
    const double durQ=double(n.durationTick)/double(ppq());
    const double x=p.left+keyboard+(startQ-scrollQuarter_)*beatWidth_;
    const double y=p.top+22.+double(hi-n.pitch)*row;
    return CRect(x,y,x+std::max(6.,durQ*beatWidth_),y+std::max(4.,row-1.));
}
int ScoreEditorViewV70::hitNote(const CPoint& where,bool* onResizeEdge) const {
    if(onResizeEdge)*onResizeEdge=false;
    if(!controller_)return -1;
    const auto& notes=controller_->scoreDocument().notes;
    for(std::size_t ri=notes.size();ri>0;--ri){
        const auto i=ri-1;
        const auto& n=notes[i];
        if(n.part!=activePart_)continue;
        const auto r=noteRect(i);
        if(r.pointInside(where)){
            if(onResizeEdge)*onResizeEdge=(where.x>r.right-8.);
            return static_cast<int>(i);
        }
    }
    return -1;
}
int ScoreEditorViewV70::pitchAt(const CPoint& where) const noexcept {
    const auto p=layout().piano;
    constexpr int hi=84,lo=43;
    const double row=(p.getHeight()-22.)/double(hi-lo+1);
    return std::clamp(hi-static_cast<int>(std::floor((where.y-(p.top+22.))/std::max(1.,row))),lo,hi);
}
std::uint32_t ScoreEditorViewV70::tickAt(const CPoint& where) const noexcept {
    const auto p=layout().piano;
    constexpr double keyboard=50.;
    const double q=scrollQuarter_+(where.x-(p.left+keyboard))/beatWidth_;
    const auto raw=static_cast<std::int64_t>(std::llround(std::max(0.,q)*double(ppq())));
    return snapTick(raw);
}
void ScoreEditorViewV70::addNoteAt(const CPoint& where){
    if(!controller_)return;
    auto& d=controller_->scoreDocument();
    ScoreV70::Note n{};
    n.part=activePart_; n.pitch=pitchAt(where); n.startTick=tickAt(where);
    n.durationTick=static_cast<std::uint32_t>(std::max(1,ppq()/std::max(1,snapDivision_)));
    n.velocity=90;
    const auto art=controller_->getParamNormalized(partParam(kParamPartArticulationBase,activePart_));
    n.articulation=std::clamp(static_cast<int>(std::lround(art*11.0)),0,11);
    d.notes.push_back(n);
    selected_=static_cast<int>(d.notes.size()-1);
    status_="Added "+pitchName(n.pitch)+" to "+partName(n.part);
    syncSelectedToHost();
    controller_->scoreDocumentChanged();
    invalidateSelf();
}
void ScoreEditorViewV70::eraseSelected(){
    if(!controller_||selected_<0)return;
    auto& notes=controller_->scoreDocument().notes;
    if(static_cast<std::size_t>(selected_)>=notes.size())return;
    notes.erase(notes.begin()+selected_);
    selected_=-1;dragMode_=DragMode::None;
    status_="Note deleted";
    controller_->scoreDocumentChanged();
    invalidateSelf();
}
void ScoreEditorViewV70::setSelectedArticulation(int articulation){
    if(!controller_||selected_<0)return;
    auto& notes=controller_->scoreDocument().notes;
    if(static_cast<std::size_t>(selected_)>=notes.size())return;
    auto& n=notes[static_cast<std::size_t>(selected_)];
    n.articulation=std::clamp(articulation,0,11);
    controller_->performUiParamEdit(partParam(kParamPartArticulationBase,n.part),
                                    static_cast<double>(n.articulation)/11.0);
    status_=std::string("Articulation: ")+articulationShort(n.articulation);
    controller_->scoreDocumentChanged();
    invalidateSelf();
}
void ScoreEditorViewV70::setSelectedVelocityFromX(double x){
    if(!controller_||selected_<0)return;
    auto& notes=controller_->scoreDocument().notes;
    if(static_cast<std::size_t>(selected_)>=notes.size())return;
    const auto r=velocityRect();
    const double n=clampd((x-r.left)/std::max(1.,r.getWidth()),0.,1.);
    notes[static_cast<std::size_t>(selected_)].velocity=std::clamp(static_cast<int>(std::lround(1.+126.*n)),1,127);
    controller_->scoreDocumentChanged();
    invalidateSelf();
}

void ScoreEditorViewV70::importScore(){
#ifdef _WIN32
    wchar_t path[32768]{};
    OPENFILENAMEW ofn{};
    ofn.lStructSize=sizeof(ofn);
    ofn.hwndOwner=nullptr;
    ofn.lpstrFile=path;
    ofn.nMaxFile=static_cast<DWORD>(std::size(path));
    ofn.lpstrFilter=L"MusicXML / MIDI\0*.musicxml;*.xml;*.mid;*.midi\0MusicXML\0*.musicxml;*.xml\0MIDI\0*.mid;*.midi\0All files\0*.*\0";
    ofn.Flags=OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST|OFN_EXPLORER;
    if(!GetOpenFileNameW(&ofn)){status_="Import cancelled";invalidateSelf();return;}
    ScoreV70::Document d;
    std::string error;
    const std::filesystem::path p(path);
    auto ext=p.extension().wstring();
    std::transform(ext.begin(),ext.end(),ext.begin(),[](wchar_t c){return static_cast<wchar_t>(towlower(c));});
    const bool ok=(ext==L".mid"||ext==L".midi")
        ? ScoreV70::importMidiFile(p,d,error)
        : ScoreV70::importMusicXmlFile(p,d,error);
    if(!ok){status_="Import failed: "+error;invalidateSelf();return;}
    controller_->scoreDocument()=std::move(d);
    selected_=-1;
    scrollQuarter_=0.;
    const auto counts=controller_->scoreDocument().sectionCounts();
    status_="Imported "+std::to_string(controller_->scoreDocument().notes.size())+
            " notes  V1 "+std::to_string(counts[0])+" V2 "+std::to_string(counts[1])+
            " Va "+std::to_string(counts[2])+" Vc "+std::to_string(counts[3]);
    controller_->scoreDocumentChanged();
    invalidateSelf();
#else
    status_="File import is available on the Windows RC host.";
    invalidateSelf();
#endif
}

void ScoreEditorViewV70::draw(CDrawContext* c){
    ensureSelectionValid();
    activePart_=controllerActivePart();
    const auto l=layout();
    fill(c,l.all,kBg);

    // Toolbar
    fill(c,l.toolbar,kPanel);stroke(c,l.toolbar,kLine);
    button(c,toolRect(0),"SELECT",tool_==Tool::Select);
    button(c,toolRect(1),"DRAW",tool_==Tool::Draw);
    button(c,toolRect(2),"ERASE",tool_==Tool::Erase);
    button(c,toolRect(3),"IMPORT",false,kGreen);
    text(c,"SECTION",CRect(l.toolbar.left+272,l.toolbar.top,l.toolbar.left+340,l.toolbar.top+12),kMuted,kLeftText,8.);
    for(int p=0;p<4;++p)button(c,partRect(p),partName(p),p==activePart_,p==0?kGold:(p==1?CColor{158,146,214,255}:(p==2?kBlue:kGreen)));
    button(c,navRect(0),"<",false);
    button(c,navRect(1),">",false);
    char snap[32]{};
    std::snprintf(snap,sizeof(snap),"SNAP 1/%d",4*std::max(1,snapDivision_));
    button(c,snapRect(),snap,false,kBlue);

    // Piano roll body
    fill(c,l.piano,CColor{11,16,22,255});stroke(c,l.piano,kLine);
    constexpr double keyboard=50.;
    constexpr int hi=84,lo=43;
    const double row=(l.piano.getHeight()-22.)/double(hi-lo+1);
    const double gridLeft=l.piano.left+keyboard;
    fill(c,CRect(l.piano.left,l.piano.top,gridLeft,l.piano.bottom),CColor{17,24,33,255});
    text(c,"PIANO ROLL",CRect(l.piano.left+6,l.piano.top+2,gridLeft-3,l.piano.top+18),kMuted,kLeftText,7.5);

    for(int pitch=hi;pitch>=lo;--pitch){
        const int r=hi-pitch;
        const double y=l.piano.top+22.+r*row;
        const bool black=(pitch%12==1||pitch%12==3||pitch%12==6||pitch%12==8||pitch%12==10);
        fill(c,CRect(l.piano.left,y,gridLeft,y+row-1),black?CColor{15,21,29,255}:CColor{26,34,44,255});
        if(pitch%12==0){
            text(c,pitchName(pitch),CRect(l.piano.left+5,y,gridLeft-4,y+row),black?kMuted:kText,kLeftText,std::max(6.,row-1.));
        }
        c->setFrameColor(CColor{28,39,51,255});c->setLineWidth(1.);
        c->drawLine(CPoint(gridLeft,y),CPoint(l.piano.right,y));
    }
    const int beats=static_cast<int>(std::ceil((l.piano.right-gridLeft)/beatWidth_))+2;
    const int firstBeat=static_cast<int>(std::floor(scrollQuarter_));
    for(int i=0;i<beats;++i){
        const int beat=firstBeat+i;
        const double x=gridLeft+(double(beat)-scrollQuarter_)*beatWidth_;
        const bool bar=(beat%4)==0;
        c->setFrameColor(bar?kLineStrong:CColor{32,44,57,255});
        c->setLineWidth(bar?1.3:1.);
        c->drawLine(CPoint(x,l.piano.top),CPoint(x,l.piano.bottom));
        if(bar){
            text(c,std::to_string(beat/4+1),CRect(x+4,l.piano.top+2,x+35,l.piano.top+18),kMuted,kLeftText,8.);
        }
    }

    // Ghost melodies first, active track notes second.
    if(controller_){
        const auto& notes=controller_->scoreDocument().notes;
        for(std::size_t i=0;i<notes.size();++i){
            if(notes[i].part==activePart_)continue;
            auto r=noteRect(i);
            if(r.right<gridLeft||r.left>l.piano.right||r.bottom<l.piano.top||r.top>l.piano.bottom)continue;
            fill(c,r,kGhost);
        }
        for(std::size_t i=0;i<notes.size();++i){
            const auto& n=notes[i];
            if(n.part!=activePart_)continue;
            auto r=noteRect(i);
            if(r.right<gridLeft||r.left>l.piano.right||r.bottom<l.piano.top||r.top>l.piano.bottom)continue;
            const bool sel=static_cast<int>(i)==selected_;
            fill(c,r,sel?kGold2:kGold);
            stroke(c,r,sel?kText:CColor{160,121,61,255});
            const auto label=std::string(articulationShort(n.articulation))+" "+pitchName(n.pitch);
            text(c,label,CRect(r.left+4,r.top,r.right-6,r.bottom),CColor{17,21,26,255},kLeftText,7.5);
            if(sel)fill(c,CRect(r.right-5,r.top+2,r.right-2,r.bottom-2),CColor{255,243,205,255});
        }
    }

    // Inspector modeled after a dedicated note properties panel.
    fill(c,l.inspector,kPanel);stroke(c,l.inspector,kLine);
    text(c,"NOTE PROPERTIES",CRect(l.inspector.left+14,l.inspector.top+10,l.inspector.right-14,l.inspector.top+29),kText,kLeftText,11.);
    if(controller_&&selected_>=0&&static_cast<std::size_t>(selected_)<controller_->scoreDocument().notes.size()){
        const auto& n=controller_->scoreDocument().notes[static_cast<std::size_t>(selected_)];
        const double startQ=double(n.startTick)/double(ppq());
        const double durQ=double(n.durationTick)/double(ppq());
        char b[128]{};
        std::snprintf(b,sizeof(b),"%s  %s",partName(n.part),pitchName(n.pitch).c_str());
        text(c,b,CRect(l.inspector.left+14,l.inspector.top+38,l.inspector.right-14,l.inspector.top+60),kGold2,kLeftText,12.);
        std::snprintf(b,sizeof(b),"Bar %d  Beat %.2f",(int)(startQ/4.)+1,std::fmod(startQ,4.)+1.);
        text(c,b,CRect(l.inspector.left+14,l.inspector.top+66,l.inspector.right-14,l.inspector.top+84),kMuted,kLeftText,9.);
        std::snprintf(b,sizeof(b),"Duration %.2f beats",durQ);
        text(c,b,CRect(l.inspector.left+14,l.inspector.top+91,l.inspector.right-14,l.inspector.top+109),kMuted,kLeftText,9.);
        std::snprintf(b,sizeof(b),"Velocity %d",n.velocity);
        text(c,b,CRect(l.inspector.left+14,l.inspector.top+142,l.inspector.right-14,l.inspector.top+160),kText,kLeftText,9.);
        auto vr=velocityRect();
        fill(c,vr,CColor{38,50,64,255});
        auto vf=vr;vf.right=vr.left+vr.getWidth()*double(n.velocity)/127.;
        fill(c,vf,kBlue);stroke(c,vr,kLine);
        text(c,std::string("Articulation  ")+articulationShort(n.articulation),
             CRect(l.inspector.left+14,l.inspector.top+218,l.inspector.right-14,l.inspector.top+239),kText,kLeftText,9.);
        button(c,deleteRect(),"DELETE NOTE",false,kRed);
    }else{
        text(c,"Select a note to edit pitch,",CRect(l.inspector.left+14,l.inspector.top+48,l.inspector.right-14,l.inspector.top+66),kMuted,kLeftText,9.);
        text(c,"position, length, velocity",CRect(l.inspector.left+14,l.inspector.top+68,l.inspector.right-14,l.inspector.top+86),kMuted,kLeftText,9.);
        text(c,"and articulation.",CRect(l.inspector.left+14,l.inspector.top+88,l.inspector.right-14,l.inspector.top+106),kMuted,kLeftText,9.);
    }

    // Articulation strip
    fill(c,l.articulation,kPanel);stroke(c,l.articulation,kLine);
    text(c,"ARTICULATION",CRect(l.articulation.left+10,l.articulation.top,l.articulation.left+82,l.articulation.bottom),kMuted,kLeftText,8.);
    int selectedArt=-1;
    if(controller_&&selected_>=0&&static_cast<std::size_t>(selected_)<controller_->scoreDocument().notes.size())
        selectedArt=controller_->scoreDocument().notes[static_cast<std::size_t>(selected_)].articulation;
    for(int a=0;a<12;++a)button(c,articulationRect(a),articulationShort(a),a==selectedArt,kGold);

    // Status line overlays lower inspector edge without stealing controls.
    text(c,status_,CRect(l.piano.left+8,l.piano.bottom-18,l.piano.right-8,l.piano.bottom-3),CColor{125,143,163,255},kRightText,7.5);
    setDirty(false);
}

CMouseEventResult ScoreEditorViewV70::onMouseDown(CPoint& where,const CButtonState& buttons){
    if(!buttons.isLeftButton())return kMouseEventNotHandled;
    takeFocus();
    for(int i=0;i<4;++i){
        if(inside(toolRect(i),where)){
            if(i==0)tool_=Tool::Select;
            else if(i==1)tool_=Tool::Draw;
            else if(i==2)tool_=Tool::Erase;
            else importScore();
            invalidateSelf();
            return kMouseEventHandled;
        }
    }
    for(int p=0;p<4;++p)if(inside(partRect(p),where)){setActivePart(p);return kMouseEventHandled;}
    if(inside(navRect(0),where)){scrollQuarter_=std::max(0.,scrollQuarter_-4.);invalidateSelf();return kMouseEventHandled;}
    if(inside(navRect(1),where)){scrollQuarter_+=4.;invalidateSelf();return kMouseEventHandled;}
    if(inside(snapRect(),where)){
        snapDivision_=(snapDivision_==4?2:(snapDivision_==2?1:(snapDivision_==1?8:4)));
        invalidateSelf();return kMouseEventHandled;
    }
    for(int a=0;a<12;++a)if(inside(articulationRect(a),where)){setSelectedArticulation(a);return kMouseEventHandled;}
    if(inside(deleteRect(),where)&&selected_>=0){eraseSelected();return kMouseEventHandled;}
    if(inside(velocityRect(),where)&&selected_>=0){
        dragMode_=DragMode::Velocity;setSelectedVelocityFromX(where.x);return kMouseEventHandled;
    }

    const auto p=layout().piano;
    if(!inside(p,where))return kMouseEventHandled;
    bool edge=false;
    const int hit=hitNote(where,&edge);
    if(tool_==Tool::Erase){
        if(hit>=0){selected_=hit;eraseSelected();}
        return kMouseEventHandled;
    }
    if(hit>=0){
        selected_=hit;syncSelectedToHost();
        if(tool_==Tool::Select&&controller_){
            auto& n=controller_->scoreDocument().notes[static_cast<std::size_t>(hit)];
            dragStart_=where;dragOrigStart_=n.startTick;dragOrigDuration_=n.durationTick;
            dragOrigPitch_=n.pitch;dragOrigVelocity_=n.velocity;
            dragMode_=edge?DragMode::Resize:DragMode::Move;
        }
        invalidateSelf();return kMouseEventHandled;
    }
    if(tool_==Tool::Draw||buttons.isDoubleClick()){addNoteAt(where);return kMouseEventHandled;}
    selected_=-1;dragMode_=DragMode::None;invalidateSelf();
    return kMouseEventHandled;
}

CMouseEventResult ScoreEditorViewV70::onMouseMoved(CPoint& where,const CButtonState& buttons){
    if(dragMode_==DragMode::None)return kMouseEventHandled;
    if(dragMode_==DragMode::Velocity){setSelectedVelocityFromX(where.x);return kMouseEventHandled;}
    if(!controller_||selected_<0||static_cast<std::size_t>(selected_)>=controller_->scoreDocument().notes.size())
        return kMouseEventHandled;
    auto& n=controller_->scoreDocument().notes[static_cast<std::size_t>(selected_)];
    if(dragMode_==DragMode::Resize){
        const auto delta=static_cast<std::int64_t>(std::llround((where.x-dragStart_.x)/beatWidth_*double(ppq())));
        const auto value=static_cast<std::int64_t>(dragOrigDuration_)+delta;
        n.durationTick=std::max<std::uint32_t>(static_cast<std::uint32_t>(std::max(1,ppq()/std::max(1,snapDivision_))),
                                               snapTick(std::max<std::int64_t>(1,value)));
    }else{
        const auto dx=static_cast<std::int64_t>(std::llround((where.x-dragStart_.x)/beatWidth_*double(ppq())));
        const auto q=std::max<std::int64_t>(0,static_cast<std::int64_t>(dragOrigStart_)+dx);
        n.startTick=snapTick(q);
        const auto p=layout().piano;
        constexpr int hi=84,lo=43;
        const double row=(p.getHeight()-22.)/double(hi-lo+1);
        const int dy=static_cast<int>(std::lround((where.y-dragStart_.y)/std::max(1.,row)));
        n.pitch=std::clamp(dragOrigPitch_-dy,0,127);
    }
    controller_->scoreDocumentChanged(false);
    invalidateSelf();
    return kMouseEventHandled;
}
CMouseEventResult ScoreEditorViewV70::onMouseUp(CPoint&,const CButtonState&){
    if(dragMode_!=DragMode::None&&controller_)controller_->scoreDocumentChanged();
    dragMode_=DragMode::None;invalidateSelf();return kMouseEventHandled;
}
int32_t ScoreEditorViewV70::onKeyDown(VstKeyCode& keyCode){
    if(keyCode.virt==VKEY_DELETE||keyCode.virt==VKEY_BACK){eraseSelected();return 1;}
    if(keyCode.character=='1'){tool_=Tool::Select;invalidateSelf();return 1;}
    if(keyCode.character=='2'){tool_=Tool::Draw;invalidateSelf();return 1;}
    if(keyCode.character=='3'){tool_=Tool::Erase;invalidateSelf();return 1;}
    if(keyCode.virt==VKEY_LEFT){scrollQuarter_=std::max(0.,scrollQuarter_-1.);invalidateSelf();return 1;}
    if(keyCode.virt==VKEY_RIGHT){scrollQuarter_+=1.;invalidateSelf();return 1;}
    return -1;
}

const char* ScoreEditorViewV70::partName(int part) noexcept {
    static const char* k[]={"Vln I","Vln II","Viola","Cello"};
    return k[std::clamp(part,0,3)];
}
const char* ScoreEditorViewV70::articulationShort(int a) noexcept {
    static const char* k[]={"SUS","LEG","PORT","EXP","MARC","STAC","SPIC","TREM","PIZZ","TRILL","HARM","FLAUT"};
    return k[std::clamp(a,0,11)];
}
std::string ScoreEditorViewV70::pitchName(int midi){
    static const char* n[]={"C","C#","D","D#","E","F","F#","G","G#","A","A#","B"};
    midi=std::clamp(midi,0,127);
    return std::string(n[midi%12])+std::to_string(midi/12-1);
}

} // namespace Sonicraft::AIStrings

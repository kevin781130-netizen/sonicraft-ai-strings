#pragma once
#include "public.sdk/source/vst/vsteditcontroller.h"
#include "pluginterfaces/vst/ivstmidicontrollers.h"
#include "pluginterfaces/vst/ivstnoteexpression.h"
#include "vstgui/plugin-bindings/vst3editor.h"
#include "score_document_v70.h"

namespace Sonicraft::AIStrings {
class Controller : public Steinberg::Vst::EditControllerEx1,
                   public Steinberg::Vst::IMidiMapping,
                   public Steinberg::Vst::IKeyswitchController,
                   public VSTGUI::VST3EditorDelegate {
public:
    static Steinberg::FUnknown* createInstance(void*) { return (Steinberg::Vst::IEditController*)new Controller(); }
    Steinberg::tresult PLUGIN_API initialize(Steinberg::FUnknown* context) override;
    Steinberg::tresult PLUGIN_API setComponentState(Steinberg::IBStream* state) override;
    Steinberg::tresult PLUGIN_API setState(Steinberg::IBStream* state) override;
    Steinberg::tresult PLUGIN_API getState(Steinberg::IBStream* state) override;
    Steinberg::IPlugView* PLUGIN_API createView(Steinberg::FIDString name) override;

    VSTGUI::CView* createCustomView(VSTGUI::UTF8StringPtr name,
                                    const VSTGUI::UIAttributes& attributes,
                                    const VSTGUI::IUIDescription* description,
                                    VSTGUI::VST3Editor* editor) override;

    ScoreV70::Document& scoreDocument() noexcept { return scoreDocument_; }
    const ScoreV70::Document& scoreDocument() const noexcept { return scoreDocument_; }
    void scoreDocumentChanged(bool markHostDirty=true);
    void registerScoreEditorView(VSTGUI::CView* view) noexcept { scoreEditorView_=view; }
    void unregisterScoreEditorView(VSTGUI::CView* view) noexcept { if(scoreEditorView_==view)scoreEditorView_=nullptr; }
    void performUiParamEdit(Steinberg::Vst::ParamID id, Steinberg::Vst::ParamValue value);

    Steinberg::tresult PLUGIN_API getMidiControllerAssignment(
        Steinberg::int32 busIndex, Steinberg::int16 channel,
        Steinberg::Vst::CtrlNumber midiControllerNumber,
        Steinberg::Vst::ParamID& id) override;

    // Lets Cubase/Nuendo import the 12 C0-B0 articulation keyswitches directly
    // from the VST3 instead of requiring a manually maintained articulation map.
    Steinberg::int32 PLUGIN_API getKeyswitchCount(
        Steinberg::int32 busIndex, Steinberg::int16 channel) override;
    Steinberg::tresult PLUGIN_API getKeyswitchInfo(
        Steinberg::int32 busIndex, Steinberg::int16 channel,
        Steinberg::int32 keySwitchIndex,
        Steinberg::Vst::KeyswitchInfo& info) override;

    OBJ_METHODS(Controller, Steinberg::Vst::EditControllerEx1)
    DEFINE_INTERFACES
        DEF_INTERFACE(Steinberg::Vst::IMidiMapping)
        DEF_INTERFACE(Steinberg::Vst::IKeyswitchController)
    END_DEFINE_INTERFACES(Steinberg::Vst::EditControllerEx1)
    REFCOUNT_METHODS(Steinberg::Vst::EditControllerEx1)

private:
    ScoreV70::Document scoreDocument_{};
    VSTGUI::CView* scoreEditorView_{nullptr};
};
}

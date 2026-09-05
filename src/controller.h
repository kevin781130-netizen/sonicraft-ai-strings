#pragma once
#include "public.sdk/source/vst/vsteditcontroller.h"
#include "pluginterfaces/vst/ivstmidicontrollers.h"
#include "pluginterfaces/vst/ivstnoteexpression.h"
#include "vstgui/plugin-bindings/vst3editor.h"

namespace Sonicraft::AIStrings {
class Controller : public Steinberg::Vst::EditControllerEx1,
                   public Steinberg::Vst::IMidiMapping,
                   public Steinberg::Vst::IKeyswitchController {
public:
    static Steinberg::FUnknown* createInstance(void*) { return (Steinberg::Vst::IEditController*)new Controller(); }
    Steinberg::tresult PLUGIN_API initialize(Steinberg::FUnknown* context) override;
    Steinberg::tresult PLUGIN_API setComponentState(Steinberg::IBStream* state) override;
    Steinberg::IPlugView* PLUGIN_API createView(Steinberg::FIDString name) override;

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
    REFCOUNT_METHODS(Controller)
};
}

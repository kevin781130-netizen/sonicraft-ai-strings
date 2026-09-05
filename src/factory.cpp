#include "processor.h"
#include "controller.h"
#include "ids.h"
#include "public.sdk/source/main/pluginfactory.h"

#define stringCompanyName "SONICRAFT"
#define stringCompanyWeb "https://bffmusicstudio.com"
#define stringCompanyEmail ""
#define stringPluginName "SONICRAFT AI Strings Q4"
#define FULL_VERSION_STR "1.2.0-rc2"

using namespace Steinberg::Vst;
using namespace Sonicraft::AIStrings;

BEGIN_FACTORY_DEF(stringCompanyName, stringCompanyWeb, stringCompanyEmail)
DEF_CLASS2(INLINE_UID_FROM_FUID(kProcessorUID), PClassInfo::kManyInstances, kVstAudioEffectClass,
    stringPluginName, Vst::kDistributable, "Instrument|Synth", FULL_VERSION_STR, kVstVersionString, Processor::createInstance)
DEF_CLASS2(INLINE_UID_FROM_FUID(kControllerUID), PClassInfo::kManyInstances, kVstComponentControllerClass,
    stringPluginName " Controller", 0, "", FULL_VERSION_STR, kVstVersionString, Controller::createInstance)
END_FACTORY

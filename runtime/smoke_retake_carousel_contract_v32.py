from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ui=(ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text(encoding='utf-8')
helper=(ROOT/'src/retake_carousel_v32.h').read_text(encoding='utf-8')
for token in ['kParamTakeCarouselMode = 123','kParamTakeCarouselSelect = 124','kParamTakeCarouselFreeze = 125']:
    assert token in ids, token
for token in ['Take Bank Mode','Take Select','Freeze Current Take']:
    assert token in ctl, token
for token in ['TakeCarouselMode','TakeCarouselSelect','TakeCarouselFreeze']:
    assert token in ui, token
for token in ['deriveTakeNonce','detectCycleWrap','RetakeCarouselTracker','resolveCarouselNonce']:
    assert token in helper, token
assert any(x in proc for x in ['constexpr int kStateVersion = 8;','constexpr int kStateVersion = 9;','constexpr int kStateVersion = 10;','constexpr int kStateVersion = 11;','constexpr int kStateVersion = 12;','constexpr int kStateVersion = 13;'])
assert 'ProcessContext::kCycleActive' in proc
assert 'case kParamTakeCarouselMode:' in proc
assert 'case kParamTakeCarouselSelect:' in proc
assert 'case kParamTakeCarouselFreeze:' in proc
assert proc.count('std::size_t scopeBoundaryIndex = 0;') == 1, 'duplicate scopeBoundaryIndex regression'
print('SONICRAFT v3.2 retake carousel source contract OK')

from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ui=(ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text(encoding='utf-8')
helper=(ROOT/'src/take_comp_v33.h').read_text(encoding='utf-8')
for token in ['kParamTakeCompMode = 126','kParamTakeCompCommit = 127','kParamTakeCompClear = 128','kParamTakeCompPhraseLength = 129']:
    assert token in ids, token
for token in ['Take Comp Mode','Commit Current Phrase','Clear Phrase Comp','Comp Phrase Length']:
    assert token in ctl, token
for token in ['TakeCompMode','TakeCompCommit','TakeCompClear','TakeCompPhraseLength']:
    assert token in ui, token
for token in ['PhraseTakeComp','phraseKeyFromQuarter','resolveCompTake']:
    assert token in helper, token
assert any(x in proc for x in ['constexpr int kStateVersion = 9;','constexpr int kStateVersion = 10;','constexpr int kStateVersion = 11;','constexpr int kStateVersion = 12;','constexpr int kStateVersion = 13;'])
assert 'phraseTakeComp.commit' in proc
assert 'phraseTakeComp.clear' in proc
assert 'resolveCompTake' in proc or 'resolvePersistentCompTake' in proc
print('SONICRAFT v3.3 phrase take comp source contract OK')

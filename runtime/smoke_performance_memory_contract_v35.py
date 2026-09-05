from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ui=(ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text(encoding='utf-8')
helper=(ROOT/'src/performance_memory_v35.h').read_text(encoding='utf-8')
comp=(ROOT/'src/persistent_take_comp_v34.h').read_text(encoding='utf-8')

for token in [
    'kParamMemoryFollowPlayhead = 135','kParamMemoryPrev = 136','kParamMemoryNext = 137',
    'kParamMemoryNextUnresolved = 138','kParamMemoryRecallTake = 139','kParamMemoryRecallApply = 140',
    'kParamMemoryCommitRecall = 141','kParamMemoryFavoriteRecall = 142','kParamMemoryRejectRecall = 143',
    'kParamMemoryCommittedTake = 144','kParamMemoryRecallFavorite = 145','kParamMemoryRecallRejected = 146',
    'kParamMemoryCoverage = 147','kParamMemoryCursorPosition = 148','kParamMemoryClearPhrase = 149'
]:
    assert token in ids, token

for token in ['PerformanceMemoryWindow','nextMemoryPhrase','nextUnresolvedPhrase','PerformanceMemoryStatus','performanceMemoryStatus']:
    assert token in helper, token
for token in ['query(','erase(','committedCountInRange']:
    assert token in comp, token

for token in [
    'Memory Follow Playhead','Memory Previous Phrase','Memory Next Phrase','Memory Next Unresolved',
    'Memory Recall Take','Memory Audition Recall','Memory Commit Recall','Memory Favorite Recall',
    'Memory Reject Recall','Memory Committed Take','Memory Locator Coverage','Memory Cursor Position','Memory Clear Phrase'
]:
    assert token in ctl, token

for token in [
    'MemoryFollowPlayhead','MemoryPrev','MemoryNext','MemoryNextUnresolved','MemoryRecallTake',
    'MemoryRecallApply','MemoryCommitRecall','MemoryFavoriteRecall','MemoryRejectRecall',
    'MemoryCommittedTake','MemoryRecallFavorite','MemoryRecallRejected','MemoryCoverage','MemoryCursorPosition','MemoryClearPhrase'
]:
    assert token in ui, token

assert any(x in proc for x in ['constexpr int kStateVersion = 11;','constexpr int kStateVersion = 12;','constexpr int kStateVersion = 13;'])
assert any(x in ctl for x in ['(version<3||version>11)','(version<3||version>12)','(version<3||version>13)'])
assert 'data.outputParameterChanges->addParameterData' in proc
assert 'emitOutputParam(kParamMemoryCommittedTake' in proc
assert 'emitOutputParam(kParamMemoryCoverage' in proc
assert 'nextUnresolvedPhrase(phraseTakeComp' in proc
assert 'phraseTakeComp.erase(memoryCursorKey)' in proc
assert 'e->committed=true' in comp
assert 'if (!e || !e->committed) return false;' in comp
assert 'version>=11 && !s.readInt32(committed)' in proc
assert 'committed=1' in proc  # v10 migration defaults historical entries to committed
assert 'version>=11&&!s.readInt32(committed)' in ctl
assert 'phraseKeyStrictlyBeforeQuarterV35(hostWindow.endQuarter,len)' in proc
assert 'phraseKeyStrictlyBeforeQuarterV35' in helper and 'endQuarter-1e-9' not in helper

# v11 order: memory settings/cursor must be serialized before the existing v10 comp payload.
write_pos=proc.index('s.writeFloat(memoryFollowPlayhead)')
cursor_pos=proc.index('s.writeInt32(static_cast<int32>(memoryCursorKey))')
comp_pos=proc.index('const int compCount=phraseTakeComp.exportEntries')
assert write_pos < cursor_pos < comp_pos
state=ctl[ctl.index('setComponentState'):]
read_mem=state.index('s.readFloat(mem[0])')
read_comp=state.index('s.readInt32(compCount)')
assert read_mem < read_comp

# v3.4 clipping regression: controller and UIDESC must agree on the expanded browser height.
assert any(x in ctl for x in ['VSTGUI::CPoint(900, 740), VSTGUI::CPoint(1500, 1080)','VSTGUI::CPoint(900, 820), VSTGUI::CPoint(1500, 1180)','VSTGUI::CPoint(900, 900), VSTGUI::CPoint(1500, 1280)' if 'VSTGUI::CPoint(900, 900), VSTGUI::CPoint(1500, 1280)' in ctl else 'VSTGUI::CPoint(900, 1000), VSTGUI::CPoint(1500, 1400)'])
assert any(x in ui for x in ['size="1120,880" minSize="900,740" maxSize="1500,1080"','size="1120,980" minSize="900,820" maxSize="1500,1180"','size="1120,1090" minSize="900,900" maxSize="1500,1280"','size="1120,1210" minSize="900,1000" maxSize="1500,1400"'])
assert any(x in ui for x in ['origin="28,576" size="1064,260"','origin="28,576" size="1064,360"','origin="28,576" size="1064,470"','origin="28,576" size="1064,590"'])

print('SONICRAFT v3.5 Performance Memory/browser source contract OK')

from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ui=(ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text(encoding='utf-8')
helper=(ROOT/'src/persistent_take_comp_v34.h').read_text(encoding='utf-8')

for token in [
    'kParamTakeCompUndo = 130','kParamTakeCompRedo = 131','kParamTakeCompFavorite = 132',
    'kParamTakeCompReject = 133','kParamTakeCompCommitAll = 134'
]:
    assert token in ids, token

for token in ['PersistentPhraseTakeComp','toggleFavorite','toggleReject','commitRange','undo()','redo()','exportEntries','restoreEntry']:
    assert token in helper, token

for token in ['Undo Comp Edit','Redo Comp Edit','Favorite Current Take','Reject Current Take','Commit Take Across Locator']:
    assert token in ctl, token

for token in ['TakeCompUndo','TakeCompRedo','TakeCompFavorite','TakeCompReject','TakeCompCommitAll']:
    assert token in ui, token

assert any(x in proc for x in ['constexpr int kStateVersion = 10;','constexpr int kStateVersion = 11;','constexpr int kStateVersion = 12;','constexpr int kStateVersion = 13;'])
assert any(x in ctl for x in ['(version<3||version>10)','(version<3||version>11)','(version<3||version>12)','(version<3||version>13)']), 'controller must accept current processor state'
assert 'phraseTakeComp.exportEntries' in proc
assert 'phraseTakeComp.restoreEntry' in proc
assert 'compCount>PersistentPhraseTakeComp::kCapacity' in proc
assert 'compCount>128' in ctl
assert 'phraseTakeComp.undo()' in proc and 'phraseTakeComp.redo()' in proc
assert 'phraseTakeComp.toggleFavorite' in proc and 'phraseTakeComp.toggleReject' in proc
assert 'phraseTakeComp.commitRange' in proc
assert 'high != takeCompCommitLatch' in proc and 'high != takeCompUndoLatch' in proc and 'high != takeCompCommitAllLatch' in proc

# Serialized v10 comp records are four int32 values: phrase, take, favorite mask, reject mask.
proc_write = proc[proc.index('const int compCount=phraseTakeComp.exportEntries'):]
assert proc_write.count('s.writeInt32') >= 5
ctl_state = ctl[ctl.index('setComponentState'):]
assert 'for(int32 i=0;i<compCount;++i)' in ctl_state
assert 's.readInt32(phrase)' in ctl_state and 's.readInt32(take)' in ctl_state and 's.readInt32(fav)' in ctl_state and 's.readInt32(rej)' in ctl_state

print('SONICRAFT v3.4 persistent comp/state-alignment source contract OK')

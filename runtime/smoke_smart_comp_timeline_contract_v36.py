from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ids=(ROOT/'src/ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src/processor.cpp').read_text(encoding='utf-8')
ctl=(ROOT/'src/controller.cpp').read_text(encoding='utf-8')
ui=(ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc').read_text(encoding='utf-8')
helper=(ROOT/'src/smart_comp_timeline_v36.h').read_text(encoding='utf-8')
comp=(ROOT/'src/persistent_take_comp_v34.h').read_text(encoding='utf-8')

for token in [
    'kParamTimelineCommittedBase = 150','kParamTimelineSmartPickBase = 158',
    'kParamSmartRankMode = 166','kParamSmartAudition = 167','kParamSmartCommit = 168',
    'kParamSmartScore = 169','kParamTimelineCursorSlot = 170',
    'kParamCommitUniqueFavorites = 171','kParamAutoCompUnresolved = 172',
    'kParamSmartVariation = 173','kParamTimelineUnresolved = 174'
]:
    assert token in ids, token

for token in [
    'smartRankTakeV36','retakeContractVariationV36','smartTimelineWindowV36',
    'uniqueFavoriteTakeV36','quantizedRetakeNonceV36'
]:
    assert token in helper, token

assert 'commitBatch' in comp
assert any(x in proc for x in ['constexpr int kStateVersion = 12;','constexpr int kStateVersion = 13;'])
assert any(x in ctl for x in ['(version<3||version>12)','(version<3||version>13)'])
assert 'if(version>=12){ if(!s.readFloat(smartRankMode))' in proc
assert 'if(version>=12){float rank=0;if(!s.readFloat(rank))' in ctl
assert 's.writeFloat(smartRankMode)' in proc

for token in ['Smart Rank Mode','Smart Audition Suggested','Smart Commit Suggested',
              'Commit Unique Favorites','Heuristic Auto Comp Unresolved',
              'Smart Candidate Score','Smart Variation Priority']:
    assert token in ctl, token

for token in ['TimelineCommit1','TimelineCommit8','TimelineSmart1','TimelineSmart8',
              'SmartRankMode','SmartAudition','SmartCommit','CommitUniqueFavorites',
              'AutoCompUnresolved','SmartScore','SmartVariation','TimelineUnresolved']:
    assert token in ui, token

assert 'phraseTakeComp.commitBatch(keys,takes,count)' in proc
assert 'uniqueFavoriteTakeV36(phraseTakeComp,key)' in proc
assert 'smartRankTakeV36(phraseTakeComp,key' in proc
assert 'timelineParam(kParamTimelineCommittedBase,slot)' in proc
assert 'timelineParam(kParamTimelineSmartPickBase,slot)' in proc
assert 'static_cast<float>(std::clamp(timeline.cursorSlot,0,7))/7.f' in proc
assert 'favorite ? 1.f : heuristicScore' in helper

# Rank is a priority heuristic tied to renderer contract dimensions, not a quality claim.
assert 'not audio-quality inference' in helper
assert 'same Retake contract dimensions/salts' in helper

# v12 state ordering: browser state -> rank mode -> comp payload.
write_cursor=proc.index('s.writeInt32(static_cast<int32>(memoryCursorKey))')
write_rank=proc.index('s.writeFloat(smartRankMode)')
write_comp=proc.index('const int compCount=phraseTakeComp.exportEntries')
assert write_cursor < write_rank < write_comp
state=ctl[ctl.index('setComponentState'):]
read_mem=state.index('s.readFloat(mem[0])')
read_rank=state.index('s.readFloat(rank)')
read_comp=state.index('s.readInt32(compCount)')
assert read_mem < read_rank < read_comp

# Expanded timeline must fit the editor constraints.
assert any(x in ui for x in ['size="1120,980" minSize="900,820" maxSize="1500,1180"','size="1120,1090" minSize="900,900" maxSize="1500,1280"','size="1120,1210" minSize="900,1000" maxSize="1500,1400"'])
assert any(x in ui for x in ['origin="28,576" size="1064,360"','origin="28,576" size="1064,470"','origin="28,576" size="1064,590"'])
assert any(x in ctl for x in ['VSTGUI::CPoint(900, 820), VSTGUI::CPoint(1500, 1180)','VSTGUI::CPoint(900, 900), VSTGUI::CPoint(1500, 1280)' if 'VSTGUI::CPoint(900, 900), VSTGUI::CPoint(1500, 1280)' in ctl else 'VSTGUI::CPoint(900, 1000), VSTGUI::CPoint(1500, 1400)'])

print('SONICRAFT v3.6 Smart Comp Timeline source contract OK')

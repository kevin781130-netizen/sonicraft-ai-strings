from __future__ import annotations
from pathlib import Path
import importlib.util, json, re, sys, tempfile, xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
errors=[]
def require(ok,msg):
    if not ok: errors.append(msg)

# VSTGUI contract
ui=ROOT/'resource'/'SONICRAFT_AI_Strings_Q4.uidesc'
root=ET.parse(ui).getroot()
templates={x.attrib.get('name') for x in root.findall('template')}
for name in ('MainView','PageScore','PagePerform','PageRetakes','PageMix','PartV1','PartV2','PartVa','PartVc'):
    require(name in templates,f'missing UI template {name}')
tags={x.attrib.get('name'):int(x.attrib.get('tag')) for x in root.find('control-tags')}
for name,val in [('UiPage',800),('StageMixerEnable',810),('StageMaster',811),('StageOutput',828)]:
    require(tags.get(name)==val,f'{name} tag mismatch')
for i in range(1,17):require(tags.get(f'Mic{i:02d}')==811+i,f'Mic{i:02d} tag mismatch')

# Browser editor surface / JS contract
html=(ROOT/'frontend'/'index.html').read_text(encoding='utf-8')
for token in ('NOTE EDITOR','PREDICTIVE DYNAMICS','AI Performance Retake','Scoring Stage Mixer','parseMusicXML','parseMidi','writeMidi','/api/compile','/api/auto-loop'):
    require(token in html,f'frontend missing {token}')

# Stage mixer state contract
ids=(ROOT/'src'/'ids.h').read_text(encoding='utf-8')
proc=(ROOT/'src'/'processor.cpp').read_text(encoding='utf-8')
ctrl=(ROOT/'src'/'controller.cpp').read_text(encoding='utf-8')
require('kParamStageFeedGainBase = 812' in ids,'stage feed ParamID base missing')
require('constexpr int kStateVersion = 14' in proc,'state version 14 missing')
require('stageMixerEnable>=.5f' in proc,'stage mixer processing branch missing')
require('version>14' in ctrl,'controller state v14 gate missing')

# Editor -> MusicXML -> existing score parser integration
spec=importlib.util.spec_from_file_location('editor_server',ROOT/'frontend'/'editor_server.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
sys.path.insert(0,str(ROOT/'runtime'))
from score_expression_graph_v40 import parse_score
sample={'tempo':72,'notes':[
 {'track':0,'start':0,'duration':2,'pitch':69,'velocity':82,'dynamics':64,'articulation':'Legato'},
 {'track':1,'start':1,'duration':1,'pitch':62,'velocity':74,'dynamics':58,'articulation':'Sustain'},
 {'track':2,'start':2,'duration':1,'pitch':57,'velocity':72,'dynamics':62,'articulation':'Pizzicato'},
 {'track':3,'start':0,'duration':4,'pitch':45,'velocity':78,'dynamics':66,'articulation':'Flautando'}]}
with tempfile.TemporaryDirectory() as td:
    target=mod.project_to_musicxml(sample,Path(td)/'smoke.musicxml')
    g=parse_score(target)
    require(len(g.notes)==4,'editor bridge note count mismatch')
    require({n.part for n in g.notes}=={0,1,2,3},'editor bridge section mapping mismatch')

print(json.dumps({'ok':not errors,'version':'7.0.0-rc2','checks':{
 'vstgui_templates':len(templates),'control_tags':len(tags),'editor_bridge':'PASS' if not errors else 'CHECK'
},'errors':errors},ensure_ascii=False,indent=2))
raise SystemExit(0 if not errors else 1)

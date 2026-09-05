from __future__ import annotations
"""Winner-take-all acoustic promotion contract for SONICRAFT v2.0."""
from typing import Mapping
import hashlib,json

PROMOTION_SCHEMA=1
PROMOTION_VERSION='acoustic_promotion_v20'
PROMOTABLE_RUNTIME_CODECS={'strings_vae64','dac44'}

def _canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
def _id(parts):return hashlib.sha256(b'|'.join(_canonical(x) for x in parts)).hexdigest()

def build_promotion(sound_forge:Mapping,segment_report:Mapping,codec_tournament:Mapping,codec_abx:Mapping,generated_abx:Mapping,*,shipping_codec:str):
    reasons=[];shipping=str(shipping_codec).lower();winner=str(codec_tournament.get('winner_kind','')).lower()
    if not sound_forge.get('release_pass'):reasons.append('sound_forge_failed')
    if not segment_report.get('release_pass'):reasons.append('segmentation_failed')
    if int(segment_report.get('real_segments',0))<1:reasons.append('no_real_segments')
    if int(codec_tournament.get('schema',0))!=2 or not codec_tournament.get('promotion_pass'):reasons.append('codec_tournament_failed')
    if winner!=shipping:reasons.append('shipping_codec_is_not_tournament_winner')
    if shipping not in PROMOTABLE_RUNTIME_CODECS:reasons.append('winner_has_no_audited_runtime_adapter')
    for label,r in (('codec_abx',codec_abx),('generated_real_abx',generated_abx)):
        if int(r.get('schema',0))!=2 or not r.get('transparency_pass'):reasons.append(label+'_failed')
        if int(r.get('listener_count',0))<5 or int(r.get('trial_count',0))<60:reasons.append(label+'_underpowered')
    pid=_id([sound_forge,segment_report,codec_tournament,codec_abx,generated_abx,{'shipping_codec':shipping}])
    return {'schema':PROMOTION_SCHEMA,'promotion_version':PROMOTION_VERSION,'promotion_id':pid,'promotion_pass':not reasons,'shipping_codec':shipping,
            'winner':codec_tournament.get('winner'),'winner_kind':winner,'winner_quality':codec_tournament.get('winner_quality'),
            'real_anchor_count':codec_tournament.get('real_anchor_count'),'codec_abx_accuracy':codec_abx.get('accuracy'),
            'generated_real_abx_accuracy':generated_abx.get('accuracy'),'loser_policy':'not_shipped_or_loaded_by_consumer_runtime','reasons':reasons,
            'contract':'sound wins first; footprint only breaks perceptual ties; only audited runtime adapters can ship'}

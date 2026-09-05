"""SONICRAFT v4.5 Continuous String Gesture Graph.

Strings-only note-internal gesture planning. The graph creates a small number of normalized
anchors per note for bow speed, pressure, contact point, dynamics energy, vibrato evolution,
micro-pitch drift and portamento trajectory. It is deterministic and inspectable; it does not
claim learned continuous acoustic dimensions that are absent from the current model/data.
"""
from __future__ import annotations
import hashlib,math
from score_expression_graph_v40 import PPQ

ANCHORS=(0.0,.10,.24,.42,.62,.80,1.0)

def _clamp(x,a=0.0,b=1.0):return max(a,min(b,float(x)))
def _smoothstep(x):
    x=_clamp(x);return x*x*(3.0-2.0*x)
def _hash_phase(source_id):
    h=hashlib.sha256((source_id or 'gesture').encode('utf-8')).digest()
    return int.from_bytes(h[:4],'little')/4294967296.0*math.tau

def _is_bowed(n):return n.base_art!=8
def _is_expressive(n):return bool((n.stack&8) or n.base_art in (3,11))
def _is_accented(n):return bool((n.stack&1) or n.base_art in (4,5,6))
def _is_legato(n):return bool(n.slur or (n.stack&2) or n.base_art in (1,2))

def _note_profile(n):
    if not _is_bowed(n):return 'pizzicato-static'
    if n.base_art==7:return 'tremolo-energy'
    if n.base_art==11:return 'flautando-air'
    if n.base_art==2 or n.portamento_route>.55:return 'portamento-arc'
    if _is_expressive(n):return 'expressive-swell'
    if _is_accented(n):return 'accent-decay'
    if _is_legato(n):return 'legato-arc'
    return 'sustain-breathe'

def _energy_shape(profile,u):
    if profile=='accent-decay':return .88-.28*_smoothstep(u)
    if profile=='expressive-swell':return .50+.34*math.sin(math.pi*_clamp(u))
    if profile=='legato-arc':return .58+.20*math.sin(math.pi*_clamp(u))
    if profile=='tremolo-energy':return .72+.10*math.sin(math.pi*_clamp(u))
    if profile=='flautando-air':return .43+.13*math.sin(math.pi*_clamp(u))
    if profile=='portamento-arc':return .56+.22*math.sin(math.pi*_clamp(u))
    return .60+.12*math.sin(math.pi*_clamp(u))

def plan_continuous_string_gestures(g):
    by_lane={}
    for n in g.notes:by_lane.setdefault((n.part,n.lane_channel),[]).append(n)
    for _,notes in by_lane.items():
        notes.sort(key=lambda n:(n.start_tick,n.pitch))
        for i,n in enumerate(notes):
            profile=_note_profile(n);n.gesture_profile=profile
            dur_beats=max(1/PPQ,(n.end_tick-n.start_tick)/float(PPQ))
            if not _is_bowed(n):
                n.gesture_amount=0.0;n.gesture_anchors=[];n.gesture_risk=0.0;continue
            amount=.58 if dur_beats<.35 else (.78 if dur_beats<.8 else 1.0)
            if n.base_art in (5,6):amount=min(amount,.50)
            n.gesture_amount=amount
            phase=_hash_phase(n.source_id)
            base_dyn=_clamp(n.cc1/127.0)
            base_vib=_clamp(n.cc3/127.0)
            base_pressure=_clamp(n.bow_pressure)
            base_contact=_clamp(n.contact_point)
            porta=_clamp(n.portamento_route)
            anchors=[]
            for u in ANCHORS:
                energy=_clamp(base_dyn*.62+_energy_shape(profile,u)*.38)
                # Bow speed is a planning dimension. Faster speed tends to carry energy with less pressure.
                bow_speed=_clamp(.42+energy*.42)
                if profile=='accent-decay':bow_speed=_clamp(bow_speed+.16*(1-_smoothstep(u)))
                if profile=='flautando-air':bow_speed=_clamp(bow_speed+.08)
                if profile=='tremolo-energy':bow_speed=_clamp(.76+.07*math.sin(math.tau*u*2))
                pressure=_clamp(base_pressure+(energy-.5)*.20-(bow_speed-.55)*.08)
                contact=_clamp(base_contact+(pressure-.5)*.08)
                if profile=='flautando-air':contact=_clamp(contact-.14)
                if profile=='tremolo-energy':contact=_clamp(contact+.08)
                vib_env=_smoothstep(min(1.0,u/.35))*_smoothstep(min(1.0,(1.02-u)/.20))
                vibrato=_clamp(base_vib*vib_env*(1.10 if _is_expressive(n) else 1.0))
                # Micro-pitch is intentionally bounded: organic bow/finger drift, not a fake full glissando.
                drift=math.sin(phase+u*math.tau*1.35)*2.2 + math.sin(phase*.37+u*math.tau*2.1)*1.1
                micro_cents=max(-6.0,min(6.0,drift*(.55+.45*amount)))
                port_curve=porta*_smoothstep(u)
                if profile=='portamento-arc':
                    micro_cents += (1.0-_smoothstep(min(1.0,u/.30)))*(-8.0 if n.shift_semitones>=0 else 8.0)
                    micro_cents=max(-14.0,min(14.0,micro_cents))
                kinetic=_clamp(.45+.38*bow_speed+.20*pressure-.12*contact)
                anchors.append({
                    'u':round(u,6),'bow_speed':round(bow_speed,6),'bow_pressure':round(pressure,6),
                    'contact_point':round(contact,6),'dynamics_energy':round(energy,6),
                    'vibrato_depth':round(vibrato,6),'micro_pitch_cents':round(micro_cents,6),
                    'portamento':round(port_curve,6),'kinetic_response':round(kinetic,6),
                })
            n.gesture_anchors=anchors
            # Risk only expresses aggressive curve movement; it is not a quality score.
            max_delta=0.0
            for a,b in zip(anchors,anchors[1:]):
                max_delta=max(max_delta,abs(a['bow_pressure']-b['bow_pressure']),abs(a['contact_point']-b['contact_point']),abs(a['dynamics_energy']-b['dynamics_energy']))
            n.gesture_risk=_clamp(max_delta/.35)
    return g

def gesture_note_dict(n):
    return {'source_id':n.source_id,'profile':n.gesture_profile,'amount':round(float(n.gesture_amount),6),
            'risk':round(float(n.gesture_risk),6),'anchors':list(n.gesture_anchors)}

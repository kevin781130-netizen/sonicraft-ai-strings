from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v60 import compile_file

XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1"><measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="90"/></direction>\n<note><pitch><step>G</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>E</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="continue"/><glissando type="start"/></notations></note>\n<note><pitch><step>A</step><octave>3</octave></pitch><duration>4</duration><notations><slur type="continue"/></notations></note>\n<note><pitch><step>D</step><octave>6</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note>\n</measure>\n<measure number="2"><note><rest/><duration>8</duration></note>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><notations><slur type="stop"/></notations></note></measure>\n</part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'

with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"archetype.musicxml";src.write_text(XML)
    r=compile_file(src,td/"archetype_R1.mid",td/"policy.json",1)
    assert r["archetype_json"].exists()
    a=json.loads(r["archetype_json"].read_text())
    q=json.loads(r["judge_queue_json"].read_text())
    s=json.loads(r["score_json"].read_text())
    assert a["version"]=="6.0"
    assert a["classification"]["label"] in ("intimate","ballad","dramatic","chamber","cinematic")
    assert 0<=a["classification"]["confidence"]<=1
    assert set(a["classification"]["features"])=={"dynamic","contrast","vibrato","rate","bow","desk","transition","role_focus"}
    assert q["cross_song_archetype_memory"]["supported"] is True
    assert q["cross_song_archetype_memory"]["archetype_only_top1_forbidden"] is True
    assert q["cross_song_archetype_memory"]["control_profile_only"] is True
    assert s["performance_archetype"]["label"]==a["classification"]["label"]
    assert s["performance_archetype"]["sidecar"]==r["archetype_json"].name
    m=json.loads(r["mixture_json"].read_text())
    assert m["version"]=="6.0"
    assert 1<=len(m["soft_mixture"]["components"])<=3
    assert abs(sum(float(x["weight"]) for x in m["soft_mixture"]["components"])-1.0)<2e-6
    assert m["hard_limits"]["mixture_only_top1_forbidden"] is True
    assert q["soft_archetype_mixture"]["supported"] is True
    assert q["soft_archetype_mixture"]["mixture_only_top1_forbidden"] is True
    assert q["unified_evidence_store"]["supported"] is True
    assert q["unified_evidence_store"]["atomic_multi_namespace_commit"] is True
    assert q["unified_evidence_store"]["rollback"] is True
    assert q["unified_evidence_store"]["quarantine"] is True
    assert q["unified_evidence_store"]["namespaces"]==["utility_v55","audit_v56","similarity_v57","archetype_v58","mixture_v59"]
    assert s["performance_archetype_mixture"]["sidecar"]==r["mixture_json"].name
    assert s["performance_archetype_mixture"]["components"]==m["soft_mixture"]["components"]
    # Persistent memory privacy boundary: project sidecar may report aggregate features,
    # but it contains no note sequence/audio/file identity fields.
    raw=r["archetype_json"].read_text().lower()
    for forbidden in ['"audio":','"midi":','"notes":','"filename":']:
        assert forbidden not in raw,forbidden
    print("SONICRAFT v6.0 compiler/evidence-store capability smoke OK",
          a["classification"]["label"],a["classification"]["confidence"],r["archetype_json"].name)

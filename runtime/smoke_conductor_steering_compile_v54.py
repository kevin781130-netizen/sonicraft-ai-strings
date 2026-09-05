from pathlib import Path
import tempfile,json
from compile_musicxml_strings_v54 import compile_file
from string_repair_policy_v49 import RepairPolicyMemoryV49

XML='<?xml version="1.0"?>\n<score-partwise version="4.0">\n<part-list>\n<score-part id="P1"><part-name>Violin 1</part-name></score-part>\n<score-part id="P2"><part-name>Violin 2</part-name></score-part>\n<score-part id="P3"><part-name>Viola</part-name></score-part>\n<score-part id="P4"><part-name>Cello</part-name></score-part>\n</part-list>\n<part id="P1">\n<measure number="1"><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="84"/></direction>\n<direction><direction-type><dynamics><p/></dynamics></direction-type></direction>\n<note><pitch><step>G</step><octave>4</octave></pitch><duration>8</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>A</step><octave>4</octave></pitch><duration>8</duration><notations><slur type="stop"/></notations></note></measure>\n<measure number="2"><direction><direction-type><dynamics><mp/></dynamics></direction-type></direction>\n<note><pitch><step>B</step><octave>4</octave></pitch><duration>8</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>D</step><octave>5</octave></pitch><duration>8</duration><notations><slur type="stop"/></notations></note></measure>\n<measure number="3"><direction><direction-type><dynamics><mf/></dynamics></direction-type></direction>\n<note><pitch><step>E</step><octave>5</octave></pitch><duration>8</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>F</step><octave>5</octave></pitch><duration>8</duration><notations><slur type="stop"/></notations></note></measure>\n<measure number="4"><direction><direction-type><dynamics><ff/></dynamics></direction-type></direction>\n<note><pitch><step>A</step><octave>5</octave></pitch><duration>8</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>G</step><octave>5</octave></pitch><duration>8</duration><notations><slur type="stop"/></notations></note></measure>\n<measure number="5"><direction><direction-type><dynamics><mp/></dynamics></direction-type></direction>\n<note><pitch><step>D</step><octave>5</octave></pitch><duration>8</duration><notations><slur type="start"/></notations></note>\n<note><pitch><step>B</step><octave>4</octave></pitch><duration>8</duration><notations><slur type="stop"/></notations></note></measure>\n</part>\n<part id="P2"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure><measure number="3"><note><rest/><duration>16</duration></note></measure><measure number="4"><note><rest/><duration>16</duration></note></measure><measure number="5"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P3"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure><measure number="3"><note><rest/><duration>16</duration></note></measure><measure number="4"><note><rest/><duration>16</duration></note></measure><measure number="5"><note><rest/><duration>16</duration></note></measure></part>\n<part id="P4"><measure number="1"><attributes><divisions>4</divisions></attributes><note><rest/><duration>16</duration></note></measure><measure number="2"><note><rest/><duration>16</duration></note></measure><measure number="3"><note><rest/><duration>16</duration></note></measure><measure number="4"><note><rest/><duration>16</duration></note></measure><measure number="5"><note><rest/><duration>16</duration></note></measure></part>\n</score-partwise>'
with tempfile.TemporaryDirectory() as td:
    td=Path(td);src=td/"macro.musicxml";src.write_text(XML)
    policy=td/"policy.json"
    r1=compile_file(src,td/"macro_R1.mid",policy,1)
    assert r1["conductor_json"].exists()
    c1=json.loads(r1["conductor_json"].read_text())
    q1=json.loads(r1["judge_queue_json"].read_text())
    s1=json.loads(r1["score_json"].read_text())
    assert c1["version"]=="5.3"
    assert 2<=len(c1["sections"])<=8
    assert 1<=c1["climax_section_id"]<=len(c1["sections"])
    assert q1["conductor_intent_lock"]["intent_hash"]==c1["intent_hash"]
    assert s1["conductor_intent"]["intent_hash"]==c1["intent_hash"]
    assert q1["conductor_intent_lock"]["long_line_direction_lock"] is True
    assert q1["conductor_intent_lock"]["dynamic_ceiling_lock"] is True

    # Update only repair policy. D Original and its extracted conductor intent must remain stable.
    m=RepairPolicyMemoryV49(policy)
    rr=m.learn("C",.10,.90,.90);assert rr["learned"]
    r2=compile_file(src,td/"macro_R2.mid",policy,2)
    c2=json.loads(r2["conductor_json"].read_text())
    assert c2["intent_hash"]==c1["intent_hash"],(c1["intent_hash"],c2["intent_hash"])
    assert c2["climax_section_id"]==c1["climax_section_id"]
    assert [(x["start_tick"],x["end_tick"],x["character"]) for x in c2["sections"]]==[(x["start_tick"],x["end_tick"],x["character"]) for x in c1["sections"]]
    assert r2["policy_snapshot"].generation==1
    st1=json.loads(r1["steering_json"].read_text())
    st2=json.loads(r2["steering_json"].read_text())
    assert st1["version"]=="5.4" and st2["version"]=="5.4"
    assert st1["intent_hash"]==c1["intent_hash"]
    assert st2["intent_hash"]==c2["intent_hash"]
    assert "climax" in st1["active_slot_policy"]
    assert st1["active_slot_policy"]["climax"]["primary"]==["B","C","D"]
    assert st1["active_slot_policy"]["resolution"]["primary"]==["A","B","D"]
    q54=json.loads(r1["judge_queue_json"].read_text())
    assert q54["conductor_steered_generation"]["progressive_candidate_budget"] is True
    assert q54["conductor_steered_generation"]["D_original_never_steered"] is True
    assert q54["conductor_steered_generation"]["intent_hash"]==c1["intent_hash"]
    assert set(r1["steered_scores"])==set("ABC")
    print("SONICRAFT v5.4 steering compiler/hash stability smoke OK",
          "sections",len(c1["sections"]),"climax",c1["climax_section_id"],
          "hash",c1["intent_hash"],"policy_gen",r2["policy_snapshot"].generation)

from __future__ import annotations

"""Executable truth audit for special-technique semantics in the frozen v7 parser.

The audit uses tiny MusicXML fixtures and checks what the parser actually preserves.
It intentionally distinguishes generic harmonic semantics from natural/artificial
harmonic identity, and does not infer muted-string support from unparsed text.
"""

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / "runtime" / "score_expression_graph_v40.py"
STATUS = ROOT / "release" / "special_technique_status_v7.0.json"


def load_parser():
    spec = importlib.util.spec_from_file_location("score_expression_graph_v40_semantic_audit", PARSER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load score_expression_graph_v40.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def score_xml(*, words: str | None = None, notation: str = "", technical: str = "") -> str:
    direction = ""
    if words is not None:
        direction = f"<direction><direction-type><words>{words}</words></direction-type></direction>"
    notations = ""
    body = notation
    if technical:
        body += f"<technical>{technical}</technical>"
    if body:
        notations = f"<notations>{body}</notations>"
    return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<score-partwise version=\"4.0\">
  <part-list><score-part id=\"P1\"><part-name>Violin I</part-name></score-part></part-list>
  <part id=\"P1\"><measure number=\"1\">
    <attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes>
    {direction}
    <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><voice>1</voice>{notations}</note>
  </measure></part>
</score-partwise>
"""


def parse(mod, xml: str):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "fixture.musicxml"
        p.write_text(xml, encoding="utf-8")
        return mod.parse_score(p)


def warning_techniques(graph) -> list[str]:
    return [str(x.get("technique", "")).lower() for x in graph.warnings if x.get("type") == "unsupported_string_technique"]


def main() -> int:
    mod = load_parser()
    errors: list[str] = []

    observed: dict[str, dict] = {}
    for label in ("col legno", "sul ponticello", "sul tasto"):
        g = parse(mod, score_xml(words=label))
        tech = [str(x).lower() for x in g.notes[0].technical] if g.notes else []
        ok = any(label in x for x in tech) and any(label in x for x in warning_techniques(g))
        observed[label.replace(" ", "_")] = {
            "semantic_support": ok,
            "detail": "direction text is preserved on note.technical and emitted as unsupported_string_technique warning",
        }
        if not ok:
            errors.append(f"parser no longer preserves {label} as semantic warning")

    harmonic_generic = parse(mod, score_xml(technical="<harmonic><natural/></harmonic>"))
    harmonic_generic_ok = bool(harmonic_generic.notes and harmonic_generic.notes[0].base_art == 10)
    observed["generic_harmonic"] = {
        "semantic_support": harmonic_generic_ok,
        "detail": "MusicXML harmonic is mapped to one generic Harmonic articulation",
    }
    if not harmonic_generic_ok:
        errors.append("parser no longer preserves generic harmonic articulation")

    natural = parse(mod, score_xml(technical="<harmonic><natural/></harmonic>"))
    artificial = parse(mod, score_xml(technical="<harmonic><artificial/></harmonic>"))
    natural_signature = (
        natural.notes[0].base_art if natural.notes else None,
        tuple(natural.notes[0].technical) if natural.notes else (),
    )
    artificial_signature = (
        artificial.notes[0].base_art if artificial.notes else None,
        tuple(artificial.notes[0].technical) if artificial.notes else (),
    )
    harmonic_distinction = natural_signature != artificial_signature
    observed["natural_harmonics"] = {
        "semantic_support": harmonic_distinction,
        "detail": "exact natural-vs-artificial identity is not preserved" if not harmonic_distinction else "distinction preserved",
    }
    observed["artificial_harmonics"] = {
        "semantic_support": harmonic_distinction,
        "detail": "exact natural-vs-artificial identity is not preserved" if not harmonic_distinction else "distinction preserved",
    }

    sordino = parse(mod, score_xml(words="con sordino"))
    sordino_tech = [str(x).lower() for x in sordino.notes[0].technical] if sordino.notes else []
    sordino_ok = any("sord" in x or "mute" in x for x in sordino_tech) or any(
        "sord" in x or "mute" in x for x in warning_techniques(sordino)
    )
    observed["con_sordino"] = {
        "semantic_support": sordino_ok,
        "detail": "no dedicated con-sordino semantic token/warning is preserved" if not sordino_ok else "semantic token preserved",
    }

    gliss = parse(mod, score_xml(notation='<glissando type="start">gliss.</glissando>'))
    slide = parse(mod, score_xml(notation='<slide type="start">port.</slide>'))
    portamento_ok = bool(
        gliss.notes and slide.notes and gliss.notes[0].base_art == 2 and slide.notes[0].base_art == 2
    )
    observed["portamento_transition_variants"] = {
        "semantic_support": portamento_ok,
        "detail": "MusicXML glissando/slide map to the Portamento articulation",
    }
    if not portamento_ok:
        errors.append("parser no longer maps glissando/slide to Portamento")

    status = json.loads(STATUS.read_text(encoding="utf-8"))
    techniques = status.get("techniques") or {}
    expected = {
        "col_legno": observed["col_legno"]["semantic_support"],
        "sul_ponticello": observed["sul_ponticello"]["semantic_support"],
        "sul_tasto": observed["sul_tasto"]["semantic_support"],
        "natural_harmonics": observed["natural_harmonics"]["semantic_support"],
        "artificial_harmonics": observed["artificial_harmonics"]["semantic_support"],
        "con_sordino": observed["con_sordino"]["semantic_support"],
        "portamento_transition_variants": observed["portamento_transition_variants"]["semantic_support"],
    }
    for name, value in expected.items():
        item = techniques.get(name) or {}
        if item.get("semantic_support") is not value:
            errors.append(
                f"status mismatch for {name}: file says semantic_support={item.get('semantic_support')!r}, parser audit says {value!r}"
            )

    print(json.dumps({"schema": 1, "release": "7.0.0-rc2", "observed": observed}, indent=2, ensure_ascii=False))
    if errors:
        print("SONICRAFT v7.0 SPECIAL TECHNIQUE SEMANTIC AUDIT: BLOCKED")
        for error in errors:
            print(" -", error)
        return 2
    print("SONICRAFT v7.0 SPECIAL TECHNIQUE SEMANTIC AUDIT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

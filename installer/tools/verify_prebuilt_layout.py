from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def pe64(p: Path) -> bool:
    try:
        b=p.read_bytes()[:0x1000]
        if b[:2]!=b'MZ': return False
        off=int.from_bytes(b[0x3c:0x40],'little')
        if off+6>len(b):
            with p.open('rb') as f:
                f.seek(off); sig=f.read(6)
            return sig[:4]==b'PE\0\0' and sig[4:6]==b'\x64\x86'
        return b[off:off+4]==b'PE\0\0' and b[off+4:off+6]==b'\x64\x86'
    except Exception: return False

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root'); ap.add_argument('--require-models',action='store_true'); a=ap.parse_args()
    root=Path(a.root)
    errs=[]
    app=root/'App'; vstroot=root/'VST3'/'SONICRAFT AI Strings Q4.vst3'
    for rel in ['Manager/SONICRAFT_AI_Strings_Manager.exe','Manager/manager.ps1','Frontend/index.html','Frontend/editor_server.py','Tools/OPEN_INSTRUMENT_EDITOR.bat','Runtime/renderer_service.py','Runtime/audio_take_judge_v37.py','Runtime/judge_memory_v38.py','Runtime/score_expression_graph_v40.py','Runtime/compile_musicxml_strings_v41.py','Runtime/compile_musicxml_strings_v42.py','Runtime/string_physical_graph_v42.py','Runtime/string_physical_runtime_v42.py','Runtime/string_constraint_solver_v43.py','Runtime/compile_musicxml_strings_v43.py','Runtime/string_ensemble_solver_v44.py','Runtime/string_ensemble_runtime_v44.py','Runtime/compile_musicxml_strings_v44.py','Runtime/string_gesture_graph_v45.py','Runtime/string_gesture_runtime_v45.py','Runtime/compile_musicxml_strings_v45.py','Runtime/string_transition_graph_v46.py','Runtime/string_transition_runtime_v46.py','Runtime/compile_musicxml_strings_v46.py','Runtime/string_phrase_longline_v47.py','Runtime/string_phrase_runtime_v47.py','Runtime/compile_musicxml_strings_v47.py','Runtime/string_performance_critic_v48.py','Runtime/compile_musicxml_strings_v48.py','Runtime/string_repair_policy_v49.py','Runtime/audio_io_v49.py','Runtime/midi_judge_adapter_v49.py','Runtime/compile_musicxml_strings_v49.py','Runtime/iterate_strings_v49.py','Runtime/shadow_render_auto_v50.py','Runtime/compile_musicxml_strings_v50.py','Runtime/auto_loop_strings_v50.py','Runtime/selective_phrase_search_v51.py','Runtime/shadow_render_selective_v51.py','Runtime/selective_midi_merge_v51.py','Runtime/compile_musicxml_strings_v51.py','Runtime/auto_loop_strings_v51.py','Runtime/global_performance_coherence_v52.py','Runtime/compile_musicxml_strings_v52.py','Runtime/auto_loop_strings_v52.py','Runtime/conductor_intent_v53.py','Runtime/compile_musicxml_strings_v53.py','Runtime/auto_loop_strings_v53.py','Runtime/conductor_candidate_steering_v54.py','Runtime/compile_musicxml_strings_v54.py','Runtime/auto_loop_strings_v54.py','Runtime/candidate_utility_predictor_v55.py','Runtime/compile_musicxml_strings_v55.py','Runtime/auto_loop_strings_v55.py','Runtime/counterfactual_auditor_v56.py','Runtime/compile_musicxml_strings_v56.py','Runtime/auto_loop_strings_v56.py','Runtime/context_similarity_transfer_v57.py','Runtime/compile_musicxml_strings_v57.py','Runtime/auto_loop_strings_v57.py','Runtime/performance_archetype_memory_v58.py','Runtime/compile_musicxml_strings_v58.py','Runtime/auto_loop_strings_v58.py','Runtime/archetype_mixture_v59.py','Runtime/compile_musicxml_strings_v59.py','Runtime/auto_loop_strings_v59.py','Runtime/evidence_store_v60.py','Runtime/compile_musicxml_strings_v60.py','Runtime/auto_loop_strings_v60.py','Runtime/performance_checkpoint_v61.py','Runtime/compile_musicxml_strings_v61.py','Runtime/auto_loop_strings_v61.py','Runtime/acoustic_runtime_provenance_v62.py','Runtime/performance_checkpoint_v62.py','Runtime/compile_musicxml_strings_v62.py','Runtime/auto_loop_strings_v62.py','Runtime/compile_midi_performance_v29.py','Runtime/model_backend.py','Runtime/flow_sampler.py','Runtime/quartet_interaction.py','Runtime/frontier_context.py','Runtime/tile_cache.py','Runtime/instrument_x_cleanroom.py','Runtime/polyphony.py','Runtime/stage_renderer.py','Runtime/stage_renderer_np.py','Runtime/control_builder_np.py','Runtime/ort_model_backend.py','Runtime/runtime_backend_selector_v24.py','Runtime/musicxml_import.py','Runtime/models/ballad_flow_renderer.py','Runtime/models/string_vae64.py','Tools/COMPILE_MUSICXML_STRINGS_v41.bat','Tools/COMPILE_MUSICXML_STRINGS_v42.bat','Tools/COMPILE_MUSICXML_STRINGS_v43.bat','Tools/COMPILE_MUSICXML_STRINGS_v44.bat','Tools/COMPILE_MUSICXML_STRINGS_v45.bat','Tools/COMPILE_MUSICXML_STRINGS_v46.bat','Tools/COMPILE_MUSICXML_STRINGS_v47.bat','Tools/COMPILE_MUSICXML_STRINGS_v48.bat','Tools/COMPILE_MUSICXML_STRINGS_v49.bat','Tools/ITERATE_STRINGS_v49.bat','Tools/COMPILE_MUSICXML_STRINGS_v50.bat','Tools/AUTO_LOOP_STRINGS_v50.bat','Tools/COMPILE_MUSICXML_STRINGS_v51.bat','Tools/AUTO_LOOP_STRINGS_v51.bat','Tools/COMPILE_MUSICXML_STRINGS_v52.bat','Tools/AUTO_LOOP_STRINGS_v52.bat','Tools/COMPILE_MUSICXML_STRINGS_v53.bat','Tools/AUTO_LOOP_STRINGS_v53.bat','Tools/COMPILE_MUSICXML_STRINGS_v54.bat','Tools/AUTO_LOOP_STRINGS_v54.bat','Tools/COMPILE_MUSICXML_STRINGS_v55.bat','Tools/AUTO_LOOP_STRINGS_v55.bat','Tools/COMPILE_MUSICXML_STRINGS_v56.bat','Tools/AUTO_LOOP_STRINGS_v56.bat','Tools/COMPILE_MUSICXML_STRINGS_v57.bat','Tools/AUTO_LOOP_STRINGS_v57.bat','Tools/COMPILE_MUSICXML_STRINGS_v58.bat','Tools/AUTO_LOOP_STRINGS_v58.bat','Tools/COMPILE_MUSICXML_STRINGS_v59.bat','Tools/AUTO_LOOP_STRINGS_v59.bat','Tools/COMPILE_MUSICXML_STRINGS_v60.bat','Tools/AUTO_LOOP_STRINGS_v60.bat','Tools/EVIDENCE_STORE_V60.bat','Tools/COMPILE_MUSICXML_STRINGS_v61.bat','Tools/AUTO_LOOP_STRINGS_v61.bat','Tools/PERFORMANCE_CHECKPOINT_V61.bat','Tools/COMPILE_MUSICXML_STRINGS_v62.bat','Tools/AUTO_LOOP_STRINGS_v62.bat','Tools/PERFORMANCE_CHECKPOINT_V62.bat']:
        if not (app/rel).is_file(): errs.append(f'missing App/{rel}')
    shell=app/'Standalone'/'SonicraftAIStringsProductShell.exe'
    if not shell.is_file(): errs.append('missing App/Standalone/SonicraftAIStringsProductShell.exe')
    elif not pe64(shell): errs.append('Realtime Product Shell is not a valid PE32+ x64 image')
    bins=list((vstroot/'Contents'/'x86_64-win').glob('*.vst3')) if (vstroot/'Contents'/'x86_64-win').is_dir() else []
    if not bins: errs.append('missing prebuilt VST3 binary under VST3/.../Contents/x86_64-win/*.vst3')
    elif not all(pe64(p) for p in bins): errs.append('VST3 binary is not a valid PE32+ x64 image')
    vp=root/'validator-pass.json'
    if not vp.is_file(): errs.append('missing validator-pass.json')
    else:
        try:
            v=json.loads(vp.read_text(encoding='utf-8-sig'))
            if not v.get('passed'): errs.append('validator-pass.json does not say passed=true')
        except Exception as e: errs.append(f'invalid validator-pass.json: {e}')
    if a.require_models:
        mp=root/'Models'/'release_model_manifest.json'
        if not mp.is_file(): errs.append('missing Models/release_model_manifest.json')
        else:
            try:
                m=json.loads(mp.read_text(encoding='utf-8-sig'))
                if not (m.get('commercial_safe') and m.get('release_approved')): errs.append('model manifest is not commercial_safe + release_approved')
                for f in m.get('files',[]):
                    p=root/'Models'/f['name']
                    if not p.is_file() or sha256(p).lower()!=str(f['sha256']).lower(): errs.append(f'model missing/hash mismatch: {f.get("name")}')
            except Exception as e: errs.append(f'invalid model manifest: {e}')
    if errs:
        print('PREBUILT RELEASE BLOCKED')
        for e in errs: print(' -',e)
        return 2
    print('PREBUILT RELEASE READY')
    print(' VST3:',bins[0])
    print(' validator: PASS')
    return 0
if __name__=='__main__': raise SystemExit(main())

from __future__ import annotations
import re, subprocess, tempfile, xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
notes: list[str] = []

def fail(msg: str) -> None:
    errors.append(msg)

def need_text(rel: str) -> str:
    p = ROOT / rel
    if not p.is_file():
        fail(f'missing {rel}')
        return ''
    return p.read_text(encoding='utf-8', errors='ignore')

def pair(value: str) -> tuple[int, int]:
    a,b=value.split(',',1)
    return int(float(a)), int(float(b))

# -----------------------------------------------------------------------------
# Browser/Standalone editor: structural and responsive-layout contract.
# -----------------------------------------------------------------------------
html = need_text('frontend/index.html')
for token in [
    '*{box-sizing:border-box;min-width:0}',
    '.page.active{display:flex;flex-direction:column',
    'flex-wrap:wrap',
    'grid-template-columns:repeat(16,68px)',
    '@media(max-width:1320px)',
    '@media(max-width:1120px)',
    '@media(max-width:930px)',
    '@media(max-width:720px)',
    '@media(max-height:800px)',
    'overflow-wrap:anywhere',
    'text-overflow:ellipsis',
]:
    if token not in html:
        fail(f'frontend responsive contract missing token: {token}')
for forbidden in [
    '.page.active{display:contents}',
    'min-width:1080px',
    '@media(max-width:1100px){:root{--sidebar:160px;--inspector:250px}',
]:
    if forbidden in html:
        fail(f'frontend contains deprecated overflow hazard: {forbidden}')
ids = re.findall(r'\bid=["\']([^"\']+)["\']', html)
for ident,count in Counter(ids).items():
    if count > 1:
        fail(f'duplicate HTML id {ident!r} x{count}')
# JS syntax (use the actual node parser when available).
scripts = re.findall(r'<script>(.*?)</script>', html, flags=re.S|re.I)
if not scripts:
    fail('frontend has no inline script')
else:
    try:
        with tempfile.NamedTemporaryFile('w', suffix='.js', encoding='utf-8', delete=False) as f:
            f.write('\n'.join(scripts)); js_path=f.name
        cp=subprocess.run(['node','--check',js_path],capture_output=True,text=True,timeout=20)
        if cp.returncode != 0:
            fail('frontend JavaScript syntax failed: '+(cp.stderr or cp.stdout).strip())
    except FileNotFoundError:
        notes.append('node unavailable; JS syntax check skipped')

# -----------------------------------------------------------------------------
# VSTGUI: no child beyond parent, no obvious text/segment clipping, no fake
# editor controls reusing audio parameters, and no unsupported window shrinking.
# -----------------------------------------------------------------------------
ui_path=ROOT/'resource/SONICRAFT_AI_Strings_Q4.uidesc'
try:
    ui_root=ET.parse(ui_path).getroot()
except Exception as e:
    fail(f'VSTGUI XML parse failed: {e}')
    ui_root=None

if ui_root is not None:
    fonts_node=ui_root.find('fonts')
    fonts={f.attrib['name']:float(f.attrib['size']) for f in (list(fonts_node) if fonts_node is not None else [])}
    templates={t.attrib.get('name'):t for t in ui_root.findall('template')}
    main=templates.get('MainView')
    if main is None:
        fail('VSTGUI MainView missing')
    else:
        if main.attrib.get('size')!='1440,900' or main.attrib.get('minSize')!='1440,900' or main.attrib.get('maxSize')!='1440,900':
            fail('VSTGUI fixed-layout safety contract must stay locked to 1440x900 until real-host scaling is validated')

    def walk(node, parent_size: tuple[int,int] | None, path: str) -> None:
        this_size=pair(node.attrib['size']) if 'size' in node.attrib else parent_size
        for i,ch in enumerate([x for x in list(node) if x.tag=='view']):
            x,y=pair(ch.attrib.get('origin','0,0')); w,h=pair(ch.attrib.get('size','0,0'))
            if this_size:
                pw,ph=this_size
                if x < 0 or y < 0 or x+w > pw or y+h > ph:
                    fail(f'VSTGUI child overflow {path}/{i}: {ch.attrib.get("title") or ch.attrib.get("control-tag") or ch.attrib.get("class")} rect={x},{y},{w},{h} parent={pw},{ph}')
            walk(ch,(w,h),f'{path}/{i}')
    for name,t in templates.items():
        walk(t,pair(t.attrib.get('size','0,0')),name)

    for v in ui_root.iter('view'):
        cls=v.attrib.get('class','')
        tag=v.attrib.get('control-tag','')
        title=v.attrib.get('title','')
        if cls=='CTextLabel':
            if '\\n' in title:
                fail(f'VSTGUI pseudo-multiline label still contains literal \\n: {title!r}')
            w,_=pair(v.attrib.get('size','0,0')); fs=fonts.get(v.attrib.get('font','Small'),9.0)
            factor=.60 if v.attrib.get('font') in {'Title','Head2','Head'} else .56
            est=len(title)*fs*factor+4
            if title and est > w*1.08:
                fail(f'VSTGUI text clipping risk: {title!r} est={est:.1f}px width={w}px')
        elif cls=='CSegmentButton':
            w,_=pair(v.attrib.get('size','0,0')); names=v.attrib.get('segment-names','').split(','); fs=fonts.get(v.attrib.get('font','Small'),9.0)
            each=w/max(1,len(names))
            for name in names:
                est=len(name)*fs*.58+8
                if name and est > each*1.06:
                    fail(f'VSTGUI segment clipping risk {tag}:{name!r} est={est:.1f}px cell={each:.1f}px')
            if tag=='Mode' and v.attrib.get('segment-names')!='LIVE,AUTO,HQ':
                fail('VSTGUI Mode parameter is reused by a non-engine segment control')
        if tag=='LookAhead' and cls=='CSlider' and v.attrib.get('origin')=='430,53':
            fail('VSTGUI Score editor zoom still reuses LookAhead audio parameter')
        if tag=='V1Speed' and cls=='CSlider':
            fail('VSTGUI discrete V1Speed profile must not be presented as a continuous slider')

# -----------------------------------------------------------------------------
# WinForms Manager and Win32 Product Shell DPI safety.
# -----------------------------------------------------------------------------
manager=need_text('manager_release.ps1')
for token in [
    'AutoScaleMode]::Dpi',
    '[System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea',
    '$form.AutoScroll = $true',
    '$tabs.Anchor=',
    '$tp.AutoScroll=$true',
    '$close.Anchor=',
    'UseCompatibleTextRendering=$true',
]:
    if token not in manager:
        fail(f'Manager DPI/layout safety missing: {token}')

shell=need_text('standalone/win32/sonicraft_product_shell_win32_v26.cpp')
for token in [
    'DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2',
    'WM_DPICHANGED',
    'GetDpiForWindow',
    'GetDpiForSystem',
    'dpiPx(',
    'reflowUi()',
    'updateUiScaleForWorkArea',
    'SPI_GETWORKAREA',
    'gUiScale',
    'Segoe UI',
]:
    if token not in shell:
        fail(f'Product Shell DPI/layout safety missing: {token}')

# Base-layout numeric controls must fit the 1000x700 logical shell. Dynamic
# mixer controls are covered by the explicit 3x6 layout formula in source.
for m in re.finditer(r'add\(w,.*?,\s*(-?\d+),\s*(-?\d+),\s*(\d+),\s*(\d+),\s*(?:IDC_[A-Z0-9_]+|-1)\)', shell):
    x,y,w,h=map(int,m.groups())
    if x < 0 or y < 0 or x+w > 1000 or y+h > 700:
        fail(f'Product Shell base child overflow: rect={x},{y},{w},{h} base=1000,700')
if 'x=18+col*320,y=244+row*44' not in shell or 'x+74,y-4,225,32' not in shell:
    fail('Product Shell mixer layout formula changed without layout-gate review')

if errors:
    print('SONICRAFT v7.0 FRONTEND LAYOUT GATE: BLOCKED')
    for e in errors:
        print(' -',e)
    for n in notes:
        print(' note:',n)
    raise SystemExit(2)

print('SONICRAFT v7.0 FRONTEND LAYOUT GATE: PASS')
print(' Browser responsive constraints: PASS')
print(' HTML IDs + JS syntax: PASS')
print(' VSTGUI bounds/text/segment contract: PASS')
print(' VSTGUI audio-param UI collision guard: PASS')
print(' WinForms Manager DPI/resize contract: PASS')
print(' Win32 Product Shell Per-Monitor DPI contract: PASS')
for n in notes:
    print(' note:',n)

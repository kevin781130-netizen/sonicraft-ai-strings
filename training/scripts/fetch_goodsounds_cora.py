from __future__ import annotations
import argparse, pathlib, urllib.request, zipfile, sys

DOI='doi:10.34810/DATA2314'
BASE='https://dataverse.csuc.cat'
API=f'{BASE}/api/access/dataset/:persistentId/?persistentId={DOI}'

def main():
    ap=argparse.ArgumentParser(description='Download the 2025 CORA Good-sounds distribution only (CC BY 4.0).')
    ap.add_argument('--out',default='data/good_sounds_cora_2025')
    ap.add_argument('--url',default=API,help='Override only if the official Dataverse endpoint changes.')
    args=ap.parse_args()
    out=pathlib.Path(args.out); out.mkdir(parents=True,exist_ok=True)
    z=out/'good_sounds_cora_2025.zip'
    print('SOURCE DOI:',DOI)
    print('Expected license for this distribution: CC BY 4.0. Do not substitute the legacy Zenodo CC-BY-NC archive.')
    try:
        urllib.request.urlretrieve(args.url,z)
    except Exception as e:
        print('Automatic Dataverse download failed:',e,file=sys.stderr)
        print('Open https://doi.org/10.34810/DATA2314 and download the 2025 CORA dataset manually into:',out,file=sys.stderr)
        raise SystemExit(2)
    with zipfile.ZipFile(z) as f: f.extractall(out)
    (out/'SOURCE_PROVENANCE.txt').write_text(
        'dataset=Good-sounds dataset\nversion=CORA V1 2025\ndoi=10.34810/DATA2314\nlicense=CC BY 4.0\n'
        'legacy_zenodo_copy_must_not_be_substituted=true\n',encoding='utf-8')
    print('Done:',out)
if __name__=='__main__': main()

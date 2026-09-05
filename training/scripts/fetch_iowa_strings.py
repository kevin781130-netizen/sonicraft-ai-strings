from __future__ import annotations
import argparse, re, zipfile
from pathlib import Path
from urllib.parse import urljoin
import requests

PAGES = {
    'violin': 'https://theremin.music.uiowa.edu/MISviolin2012.html',
    'viola': 'https://theremin.music.uiowa.edu/MISviola2012.html',
    'cello': 'https://theremin.music.uiowa.edu/MIScello2012.html',
}
KEEP = ('arco.stereo.2496.zip', 'pizz.stereo.2496.zip')

def download(url: str, dest: Path):
    if dest.exists() and dest.stat().st_size > 0:
        print('exists', dest); return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=90) as r:
        r.raise_for_status()
        with dest.open('wb') as f:
            for chunk in r.iter_content(1024*1024):
                if chunk: f.write(chunk)
    print('downloaded', dest)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default='datasets/raw/IowaMIS'); a=ap.parse_args()
    root=Path(a.out)
    for inst,page in PAGES.items():
        html=requests.get(page,timeout=60).text
        hrefs=re.findall(r'href=[\"\']([^\"\']+)[\"\']', html, flags=re.I)
        urls=[]
        for href in hrefs:
            low=href.lower()
            if any(k in low for k in KEEP): urls.append(urljoin(page,href))
        urls=sorted(set(urls))
        if not urls:
            raise RuntimeError(f'No 24/96 arco/pizz ZIP links found on {page}; site layout may have changed.')
        outdir=root/inst; outdir.mkdir(parents=True,exist_ok=True)
        for url in urls:
            zpath=outdir/url.split('/')[-1]
            download(url,zpath)
            extract=outdir/zpath.stem
            marker=extract/'.extracted'
            if not marker.exists():
                extract.mkdir(parents=True,exist_ok=True)
                with zipfile.ZipFile(zpath) as z: z.extractall(extract)
                marker.write_text(url+'\n',encoding='utf-8')
                print('extracted',extract)
    (root/'SOURCE_AND_TERMS.txt').write_text(
        'University of Iowa Musical Instrument Samples\n'
        'Source: https://theremin.music.uiowa.edu/MIS.html\n'
        'The source site states recordings may be downloaded and used for any projects, without restrictions.\n'
        'Preserve this provenance file with training manifests.\n',encoding='utf-8')
if __name__=='__main__': main()

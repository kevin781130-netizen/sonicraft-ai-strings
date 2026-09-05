from __future__ import annotations
import argparse,json,urllib.parse,urllib.request,hashlib
from pathlib import Path

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--seed',default='training/wikimedia_pd_quartet_seed.json');ap.add_argument('--out',default='datasets/raw/wikimedia_pd_quartets');a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True); rows=[]
    for item in json.loads(Path(a.seed).read_text(encoding='utf-8')):
        q={'action':'query','format':'json','prop':'imageinfo','iiprop':'url|extmetadata','titles':item['title']}
        api='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(q)
        data=json.load(urllib.request.urlopen(api)); page=next(iter(data['query']['pages'].values())); ii=page['imageinfo'][0]; meta=ii.get('extmetadata',{})
        lic=' '.join(str((meta.get(k) or {}).get('value','')) for k in ['LicenseShortName','UsageTerms','Copyrighted']).lower()
        if not any(k in lic for k in ['cc0','public domain','pd-old','pd mark']):
            print('BLOCK license not PD/CC0',item['title'],lic); continue
        url=ii['url']; name=Path(urllib.parse.urlparse(url).path).name; dest=out/name
        urllib.request.urlretrieve(url,dest); sha=hashlib.sha256(dest.read_bytes()).hexdigest();print('ok',dest.name,sha)
        rows.append({'audio':str(dest.resolve()),'dataset':'wikimedia_pd_quartets','license':lic,'source_page':item['source_page'],'sha256':sha,'release_blocked':False,'role':'realism_critic_only'})
    mf=out/'manifest.jsonl';mf.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8');print('manifest',mf,'rows',len(rows))
if __name__=='__main__':main()

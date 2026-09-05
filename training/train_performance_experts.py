from __future__ import annotations
import argparse,json,random,sys
from pathlib import Path
import numpy as np, torch
from torch.utils.data import Dataset,DataLoader,WeightedRandomSampler
from models.performance_experts import PerformanceExperts
from source_policy import validate_index
from performance_timing import speed_quantile

class DS(Dataset):
    def __init__(self,index): self.rows=[json.loads(x) for x in Path(index).read_text(encoding='utf-8').splitlines() if x.strip()]
    def __len__(self): return len(self.rows)
    def __getitem__(self,i):
        r=self.rows[i];d=np.load(r['file']);n=len(d['pitch'])
        def arr(k,default): return torch.from_numpy((d[k] if k in d.files else np.full(n,default,np.float32)).astype('float32'))
        speed=arr('speed_quantile',.5)
        if 'speed_quantile' not in d.files and 'speed_profile' in d.files:
            sp=np.asarray(d['speed_profile'],float); speed=torch.from_numpy(np.where(sp<.17,.5,np.where(sp<.5,.8,np.where(sp<.84,.5,.2))).astype('float32'))
        ctx=(arr('pitch',64),arr('dynamics',.6),arr('note_progress',.5),arr('phrase_position',.5),
             arr('prev_interval',0),arr('next_interval',0),arr('tempo_bpm',68),arr('note_duration_beats',2),
             speed,arr('transition_speed',.5),arr('attack_character',.38),arr('legato',0),arr('velocity',.7),torch.tensor(int(d['instrument'])))
        leg=torch.stack([arr('legato_transition_beats',.09)/.40,arr('legato_overlap_ratio',.3),arr('legato_attack_suppression',.5),arr('legato_continuity',.8)],-1)
        port=torch.stack([arr('portamento_transition_beats',.25)/.80,arr('portamento_slide_extent_ratio',1),arr('portamento_curve_shape',.5),arr('portamento_arrival_softness',.6)],-1)
        bow=torch.stack([arr('bow_change_beats',.05)/.25,arr('bow_change_strength',.4),arr('bow_brightness_delta',0),arr('bow_continuity',.75)],-1)
        # Per-output masks prevent a derived timing label from accidentally supervising
        # fabricated overlap/attack/softness values. Legacy generic *_physics_known is used
        # only as a timing fallback, never as blanket permission for all four dimensions.
        lg=arr('legato_physics_known',0); pg=arr('portamento_physics_known',0); bg=arr('bow_physics_known',0)
        lmask=torch.stack([arr('legato_transition_known',0) if 'legato_transition_known' in d.files else lg,
                           arr('legato_overlap_known',0),arr('legato_attack_known',0),arr('legato_continuity_known',0)],-1)
        pmask=torch.stack([arr('portamento_transition_known',0) if 'portamento_transition_known' in d.files else pg,
                           arr('portamento_slide_extent_known',0),arr('portamento_curve_shape_known',0),arr('portamento_arrival_softness_known',0)],-1)
        bmask=torch.stack([arr('bow_timing_known',0) if 'bow_timing_known' in d.files else bg,
                           arr('bow_strength_known',0),arr('bow_brightness_known',0),arr('bow_continuity_known',0)],-1)
        return (*ctx,leg,port,bow,lmask,pmask,bmask,r.get('dataset',''))

def collate(batch):
    cols=list(zip(*batch));out=[torch.stack(c) for c in cols[:-1]];out.append(list(cols[-1]));return tuple(out)

def masked_mse(pred,target,mask):
    m=mask.clamp(0,1)
    if m.ndim==pred.ndim-1: m=m[...,None]
    return ((pred-target).pow(2)*m).sum()/m.sum().clamp_min(1.0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--index',required=True);ap.add_argument('--out',default='checkpoints/performance_experts_v07.pt')
    ap.add_argument('--registry',default='training/dataset_registry.json');ap.add_argument('--epochs',type=int,default=100);ap.add_argument('--batch',type=int,default=16);ap.add_argument('--lr',type=float,default=2e-4);ap.add_argument('--seed',type=int,default=1337)
    a=ap.parse_args();validate_index(a.index,a.registry);random.seed(a.seed);np.random.seed(a.seed);torch.manual_seed(a.seed)
    ds=DS(a.index); known=[0.,0.,0.]
    mask_keys=(
        ('legato_transition_known','legato_overlap_known','legato_attack_known','legato_continuity_known','legato_physics_known'),
        ('portamento_transition_known','portamento_slide_extent_known','portamento_curve_shape_known','portamento_arrival_softness_known','portamento_physics_known'),
        ('bow_timing_known','bow_strength_known','bow_brightness_known','bow_continuity_known','bow_physics_known'))
    for r in ds.rows:
        d=np.load(r['file'])
        for i,keys in enumerate(mask_keys):
            # Count explicit dimension masks when present; otherwise generic mask counts only as timing.
            explicit=[k for k in keys[:-1] if k in d.files]
            if explicit: known[i]+=sum(float(np.asarray(d[k]).sum()) for k in explicit)
            elif keys[-1] in d.files: known[i]+=float(np.asarray(d[keys[-1]]).sum())
    if sum(known)<1:
        print('[NO_PHYSICAL_TRANSITION_SUPERVISION] Need rights-cleared aligned Legato/Portamento/Bow-change labels.');sys.exit(3)
    weights=[]
    for r in ds.rows:
        src=str(r.get('dataset','')).lower();weights.append({'custom_owned_session':14.,'good_sounds_cora_2025':4.,'ghent_ar_violin_2023':2.,'iowa_mis':1.}.get(src,1.))
    dl=DataLoader(ds,batch_size=a.batch,sampler=WeightedRandomSampler(weights,max(len(ds),64),replacement=True),collate_fn=collate)
    dev='cuda' if torch.cuda.is_available() else 'cpu';m=PerformanceExperts().to(dev);opt=torch.optim.AdamW(m.parameters(),a.lr,weight_decay=.01);best=1e9
    for ep in range(a.epochs):
        m.train();tot=0.;steps=0
        for batch in dl:
            *vals,names=batch; vals=[x.to(dev) for x in vals]
            pitch,dyn,nprog,phr,pi,ni,bpm,durb,sq,ts,attack,leg,vel,ins,lt,pt,bt,lm,pm,bm=vals
            pred=m(pitch,dyn,nprog,phr,pi,ni,bpm,durb,sq,ts,attack,leg,vel,ins)
            losses=[]
            if known[0]>0: losses.append(1.0*masked_mse(pred['legato'],lt,lm))
            if known[1]>0: losses.append(1.15*masked_mse(pred['portamento'],pt,pm))
            if known[2]>0: losses.append(.85*masked_mse(pred['bow'],bt,bm))
            loss=sum(losses)
            opt.zero_grad(set_to_none=True);loss.backward();torch.nn.utils.clip_grad_norm_(m.parameters(),1.0);opt.step();tot+=float(loss.detach());steps+=1
        score=tot/max(1,steps);print(f'epoch {ep+1:03d} performance_expert_loss={score:.6f} known={known}')
        ck={'model':m.state_dict(),'epoch':ep+1,'schema_version':7,'known_frames':known,
            'outputs':{'legato':['transition_beats/.40','overlap_ratio','attack_suppression','continuity'],
                       'portamento':['transition_beats/.80','slide_extent_ratio','curve_shape_norm','arrival_softness'],
                       'bow':['transition_beats/.25','transient_strength','brightness_delta','continuity']}}
        Path(a.out).parent.mkdir(parents=True,exist_ok=True);torch.save(ck,a.out)
        if score<best:best=score;torch.save(ck,str(Path(a.out).with_name(Path(a.out).stem+'_best.pt')))
if __name__=='__main__':main()

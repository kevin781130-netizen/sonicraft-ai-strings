import torch
from models.adaptive_flow_dit import AdaptiveFlowDiT

def main():
    torch.manual_seed(4)
    m=AdaptiveFlowDiT(dim=64,depth=2,heads=4)
    x=torch.randn(2,31,64,requires_grad=True); t=torch.rand(2); c=torch.randn(2,64)
    y=m(x,t,c); loss=y.square().mean(); loss.backward()
    assert y.shape==x.shape and torch.isfinite(y).all() and x.grad is not None
    # AdaLN-Zero initialization should initially behave close to normalized identity.
    print("v1.4 AdaptiveFlowDiT smoke PASS", tuple(y.shape), "params", sum(p.numel() for p in m.parameters()))
if __name__=="__main__": main()

import torch


def mrstft_loss(x,y,resolutions=None):
    """Multi-resolution magnitude + log-magnitude STFT reconstruction loss."""
    resolutions = resolutions or [(512,128),(1024,256),(2048,512)]
    loss=x.new_tensor(0.)
    for n_fft,hop in resolutions:
        win=torch.hann_window(n_fft,device=x.device,dtype=x.dtype)
        X=torch.stft(x.squeeze(1),n_fft,hop,window=win,return_complex=True)
        Y=torch.stft(y.squeeze(1),n_fft,hop,window=win,return_complex=True)
        mx,my=X.abs().clamp_min(1e-5),Y.abs().clamp_min(1e-5)
        loss += (mx-my).abs().mean() + (mx.log()-my.log()).abs().mean()
    return loss/max(1,len(resolutions))


def codec_mrstft_loss(x,y):
    # Mirrors the broad spectral supervision used by strong MIT waveform VAEs,
    # with more emphasis on low/mid FFT sizes important to bow transients.
    return mrstft_loss(x,y,[(32,8),(64,16),(128,32),(256,64),(512,128),(1024,256),(2048,512)])

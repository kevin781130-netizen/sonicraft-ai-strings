# v2.0 Source Scout — Reconstruction Frontier

v2.0 does not add another generic generation backbone. Public/permissive work is used only where it can improve reconstruction training, evaluation or deployment without increasing the shipping neural surface.

## Active codec challengers

- **SONICRAFT VAE64** — current audited shipping candidate: 48 kHz, 64 latent channels, 30 Hz latent rate.
- **Oobleck / ACE-Step-style 25 Hz challenger** — compact continuous VAE path; research winner must still receive an audited SONICRAFT runtime adapter before it can ship.
- **Descript DAC** — MIT code and trainable codec baseline retained as a reconstruction challenger/legacy runtime path.
- **APCodec Reborn** — MIT, 48 kHz amplitude/phase codec challenger, source-pinned for training/reference. It does not ship by default.
- **EnCodec** — MIT code challenger/reference already present in the permissive source lock.

## Evaluation ideas absorbed without runtime dependency

Stereo correlation, mid/side width and phase-derivative errors are first-class v2.0 codec metrics. These are implemented independently in SONICRAFT and remain development-time evaluation only.

## Exclusion rule

Non-commercial or unclear-license implementations/weights do not enter the commercial core. A paper can motivate a test, but code, weights, datasets and rendered assets remain excluded unless separately permissive and audited.

## Source lock

`training/third_party/mit_sources.lock.json` contains exact commits and explicit include/exclude patterns. The v2.0 source lock has no floating `HEAD`; third-party weights/audio are excluded from the lean source package.

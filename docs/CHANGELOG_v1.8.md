# v1.8 Frontier Sound Core

- Added a 5,160-parameter zero-start Frontier Context Adapter and phrase look-back context while preserving the v1.7 output at initialization.
- Added independent clean-room bowed-string and multi-player section teachers with 12 exact physics/dispersion labels; training-only probe weights never ship.
- Locked acoustic training probability to REAL 0.80 / MODELED 0.20 with lane-preserving quality/coverage curriculum.
- Real recordings are the sole final-timbre/adversarial-real authority; modeled reconstruction is down-weighted and modeled data primarily teaches physics/rare transitions.
- Propagated the 80/20 contract through codec, renderer, distillation, reflow and shortcut training.
- Added schema-5 fail-closed release policy so ratio drift or modeled-timbre/adversarial misuse blocks model-pack creation.
- Added ACE-Step 1.5 VAE as an MIT-pinned codec challenger; no upstream weight enters the product pack.
- Updated ORT export bridge for v1.8 frontier context. ORT remains benchmark-gated, not the default consumer runtime.

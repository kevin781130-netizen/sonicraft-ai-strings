# v1.0

- Wired AUTO/HQ from VST3 to an actual local Shadow Renderer path.
- Added lock-free VST audio-thread event/cache bridge.
- Added shared localhost Renderer Service and binary protocol.
- Added Compact AUTO / HQ model selection and strings DAC decode path.
- Split inference budget: AUTO defaults to 8 Euler steps; HQ defaults to 24 for quality.
- Added persistent content-addressed phrase cache with bounded pruning.
- Added concurrent client acceptance + serialized shared CUDA inference for multiple VST instances.
- Added ~22 ms shadow-audio crossfade while LIVE remains the fallback.
- Added optional-large AI runtime installer and native Renderer Service launcher EXE.
- Added Manager AI Runtime controls/status.
- Preserved exact 12-articulation and CC1/CC3/CC11/CC20 Cubase workflow.
- Corrected plug-in semantic version to 1.0.0.
- Documented that standard VST processing cannot magically inspect arbitrary future MIDI.

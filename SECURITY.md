# Security Policy

## Supported release line

Security fixes for the current commercial-release candidate target the `v7.0` line. Historical development versions are not supported as commercial distributions.

## Reporting a vulnerability

Do not disclose a suspected vulnerability in a public issue before the maintainer has had a reasonable opportunity to assess it.

Prefer GitHub's private security-advisory / private vulnerability-reporting flow for this repository when available. If that flow is unavailable, contact the repository owner privately through an established project contact channel rather than posting exploit details publicly.

A useful report includes:

- affected SONICRAFT version and commit;
- Windows version and relevant DAW/host version when applicable;
- whether the issue affects the VST3, Manager, ProductShell, local editor, renderer service, installer, model/runtime loading, or release tooling;
- reproduction steps;
- impact and expected behavior;
- logs or crash information with secrets, personal data, licensed model files, and third-party proprietary content removed.

## Release handling

A security fix that changes the VST3 binary, installer, runtime, model pack, or other hash-bound commercial artifact invalidates prior release evidence for that artifact. The affected release gates must be rerun for the new hashes before distribution.

No security report or fix should be used to bypass `FINAL_GATE_V70` or `PUBLIC_RELEASE_GATE_V70`.

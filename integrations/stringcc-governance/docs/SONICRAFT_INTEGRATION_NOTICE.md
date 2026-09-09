# Sonicraft Integration Notice

StringCC Engine v1.1 contains **no copied Sonicraft AI Strings source code, models, or assets**.

The Sonicraft repository was reviewed at upstream commit:
`4f9f1915d6179ffb3d669bbb3a483c4e30643fbf`.

At review time, no project-level `LICENSE`, `LICENSE.md`, or `COPYING` file was found at the repository root/tree. Third-party license notices under Sonicraft's `licenses/` directory do not establish a license for Sonicraft's own source code.

The `stringcc.governance` package is an independent, clean-room implementation of generic governance concepts such as conductor intent, candidate steering, evidence-based ranking, counterfactual auditing, and provenance. These are implemented against StringCC's own parameter model and codebase.

`SonicraftExternalAdapter` is optional and communicates with a separately installed external process through JSON files. Users are responsible for ensuring they have permission to install and use that external software.

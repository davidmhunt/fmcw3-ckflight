# fnd-03: Repeatable environment (setup guide, pinned Docker image, run wrapper, .env)
Status: done
Goal: foundation
Node: any
Deliverable: code
Verify: ./run --docker checks/run_checks.sh && ./run --native checks/run_checks.sh && ./run uv run pytest tests -q && test -f .env.example && ! git ls-files --error-unmatch .env
Hardware: none

## Goal
Anyone can set up a new Linux machine from `docs/setup.md` and get the same check results, either
with native KiCad 10.0.5 or with a pinned Docker image. It holds when the checks pass both ways
through the `./run` wrapper.

## Steps
1. `docker/Dockerfile`: based on the official KiCad image pinned to an exact 10.0.x tag and
   digest (confirm the tag that matches 10.0.5 exists; if not, record the nearest and why), plus
   Python, `uv`, `pandoc` and a PDF engine, `git-lfs`. Image name `fmcw3-tools`. Record
   `kicad-cli version` from inside the image in `docker/README.md`.
2. `run` (root, executable): `./run <cmd...>` runs the command in the container with the repo
   mounted and the caller's uid, passing `.env` when present; `--native` runs it on the host;
   with no flag it uses Docker when available and falls back to native. Builds the image on
   first use.
3. `pyproject.toml` and `uv.lock` for the repo's Python tooling (pytest, pyyaml, python-pptx,
   matplotlib, requests); `tests/` with a test of the baseline comparison logic in
   `checks/run_checks.sh` (fixture JSON: equal, more errors, fewer errors, unconnected > 0).
4. `.env.example` listing every key the tools read (DigiKey client id and secret now; JLCPCB or
   others later) with empty values and a comment per key. `.env` is gitignored. Port
   `parts/check_digikey.py` to read `.env`; the old `.digikey.env` name is dropped.
5. `docs/setup.md`: install KiCad 10.0.5 on Ubuntu (PPA and version pin), pointers for
   macOS/Windows, Docker, git-lfs, uv; how to get DigiKey API keys step by step and fill `.env`;
   how to run checks natively and in Docker; the rule that the GUI must be closed when tools
   edit project files. Have a fresh container follow the Docker path of the guide as a test.
6. Compare native and Docker ERC/DRC results once and record any difference in `checks/README.md`.
   Update `README.md` and `CLAUDE.md` with the `./run` commands.

## Out of scope
- Running the KiCad GUI in Docker.
- Simulation tools in the image (fnd-05 decides those).
- CI on GitHub.

## Allowed commands
- `docker build -t fmcw3-tools* *`
- `./run *`

## Log

### 2026-11-20
Commits:
- b1935a0 fnd-03: pinned fmcw3-tools Docker image on kicad/kicad:10.0.5
- 0c9b997 fnd-03: run wrapper (Docker or native, caller uid, .env passthrough)
- 8d63fee fnd-03: pyproject/uv.lock and tests of the baseline comparison logic
- 613805f fnd-03: .env.example and check_digikey.py reads .env or DIGIKEY_* env vars
- e6d723e fnd-03: docs/setup.md (KiCad 10.0.5, Docker, uv, git-lfs, DigiKey keys, GUI rule)
- fdcdbfe fnd-03: native vs Docker ERC/DRC comparison in checks/README.md; ./run commands in README and CLAUDE.md
- 430a2a0 fnd-03: ./run --native unsets PYTHONPATH; setup guide notes pytest tmpdir
Notes:
- Step 5 fresh-container test (2026-11-20): ./run --docker kicad-cli version -> 10.0.5; ./run --docker uv run pytest tests -q -> 6 passed; ./run --docker checks/run_checks.sh -> ERC errors 1 (baseline 1), DRC errors 4 (baseline 4), PASS.
- Native pytest on this host also needs a writable /tmp/pytest-of-david (it is root-owned here); host state, not a repo defect.
Verify: Verify passed: ./run --docker checks/run_checks.sh && ./run --native checks/run_checks.sh && ./run uv run pytest tests -q && test -f .env.example && ! git ls-files --error-unmatch .env
Independent review: not recorded
Blocked: review gaps remain: commit 221b9d15224d12989546f63041eba5830f351439 (docs/surveys/upstream-survey.md): 'friday commits fnd-03' still lists this commit as 'untracked'. It has no 'Directive: fnd-03' line and touches more than plan docs. It is fnd-01 work (the user's Safe-to-delete decisions) that falls inside the range only because review base 76be142 sits before the fnd-01 and fnd-02 history. It touches no file fnd-03 touches, so the fix is the review base or attribution, not fnd-03's code.; commit e88157fffb023671f97b40eafb599110544f9fa5 (.claude/friday.json): 'friday commits fnd-03' still lists this commit as 'untracked'. It has no Directive line and touches a non-plan file. It is friday infrastructure (repo rules and the bash_file_io deny) committed before fnd-03's first commit b1935a0, not fnd-03 work. As with the commit above, the fix is the review base or attribution.

### 2026-11-20
Unblocked: was blocked: review gaps remain: commit 221b9d15224d12989546f63041eba5830f351439 (docs/surveys/upstream-survey.md): 'friday commits fnd-03' still lists this commit as 'untracked'. It has no 'Directive: fnd-03' line and touches more than plan docs. It is fnd-01 work (the user's Safe-to-delete decisions) that falls inside the range only because review base 76be142 sits before the fnd-01 and fnd-02 history. It touches no file fnd-03 touches, so the fix is the review base or attribution, not fnd-03's code.; commit e88157fffb023671f97b40eafb599110544f9fa5 (.claude/friday.json): 'friday commits fnd-03' still lists this commit as 'untracked'. It has no Directive line and touches a non-plan file. It is friday infrastructure (repo rules and the bash_file_io deny) committed before fnd-03's first commit b1935a0, not fnd-03 work. As with the commit above, the fix is the review base or attribution.

### 2026-11-20
Commits:
- b1935a0 fnd-03: pinned fmcw3-tools Docker image on kicad/kicad:10.0.5
- 0c9b997 fnd-03: run wrapper (Docker or native, caller uid, .env passthrough)
- 8d63fee fnd-03: pyproject/uv.lock and tests of the baseline comparison logic
- 613805f fnd-03: .env.example and check_digikey.py reads .env or DIGIKEY_* env vars
- e6d723e fnd-03: docs/setup.md (KiCad 10.0.5, Docker, uv, git-lfs, DigiKey keys, GUI rule)
- fdcdbfe fnd-03: native vs Docker ERC/DRC comparison in checks/README.md; ./run commands in README and CLAUDE.md
- 430a2a0 fnd-03: ./run --native unsets PYTHONPATH; setup guide notes pytest tmpdir
Notes:
- Step 5 fresh-container test (2026-11-20): ./run --docker kicad-cli version -> 10.0.5; ./run --docker uv run pytest tests -q -> 6 passed; ./run --docker checks/run_checks.sh -> ERC errors 1 (baseline 1), DRC errors 4 (baseline 4), PASS.
- Native pytest on this host also needs a writable /tmp/pytest-of-david (it is root-owned here); host state, not a repo defect.
Verify: Verify passed: ./run --docker and ./run --native checks/run_checks.sh PASS (ERC errors 1/1, DRC errors 4/4, unconnected 0, parity 0); ./run uv run pytest tests -q 6 passed; .env.example present, .env untracked
Independent review: Independent review: all fnd-03 gaps fixed (fresh-container test of docs/setup.md recorded; ./run --native unsets PYTHONPATH). Remaining: 221b9d1 and e88157f listed untracked; both are main-session commits made before fnd-03 started (ancestors of runs/fnd-03/start), not fnd-03 work. friday issue davidmhunt/friday#30.

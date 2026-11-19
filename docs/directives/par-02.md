# par-02: Datasheet manifest and download script for the critical parts
Status: proposed
Goal: parts
Node: any
Deliverable: code
Verify: ./run uv run pytest tests/test_datasheets.py -q && ./run datasheets/fetch.py --verify-manifest
Hardware: none

## Goal
`./run datasheets/fetch.py` gives every collaborator the same datasheet revisions for the
critical parts, without committing the PDFs. It holds when every manifest row downloads and
matches its recorded SHA-256.

## Steps
1. `datasheets/manifest.csv`: ref, part, manufacturer, document title, revision or date, URL,
   SHA-256, file name. Rows: the ten critical parts of the review plan (ADF4158, HMC431LP4,
   TQP5525, SKY65404, TRF37A73, ADL5802, 5400BL15B0050, LT6232, LTC2292, XC7A35T/100T), the
   regulators (LMR51420, LP5907, LD3920), the reference oscillator and clock buffer, FT2232H,
   the flash, the attenuator pads and the ferrite beads. Take URLs from the manufacturer's site,
   not a distributor mirror, where one exists.
2. `datasheets/fetch.py`: downloads missing files into `datasheets/pdf/` (gitignored), checks
   hashes, reports changed or dead links clearly; `--verify-manifest` checks every row without
   keeping files; `--add URL --part X` appends a row with the computed hash.
3. Also fetch simulation inputs where vendors publish them (S-parameter files for the RF parts,
   SPICE models named in `docs/analysis-tools.md`) into `datasheets/models/` through the same
   manifest, marked by type.
4. Tests against a local HTTP fixture: good hash, changed hash, dead link. `datasheets/README.md`.

## Out of scope
- Committing vendor PDFs or models.
- Datasheets for generic passives.

## Allowed commands
- `./run *`

## Log

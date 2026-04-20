# Phase 1 Plan — Below Hardware Build

BUILD: BUILD_cluster-max.md
Phase 1: Hardware Installation, BIOS & Overclocking

Physical hardware phase. No code is written this session. Plan =
sequenced checklist walkthrough + artifact capture. Parts F (MS-A2)
and G (final verification) are deferred to a follow-up session
once Below is stable.

## Scope This Session

Parts A → E on **Below** (Windows workhorse, 10.0.1.105):

| Part | What                                   | Blocking Constraint                                   |
| ---- | -------------------------------------- | ----------------------------------------------------- |
| A    | Z390-E BIOS update (v1302 → latest)    | MUST complete before 3090s go in                      |
| B    | PSU swap AX860 → RM1200x SHIFT         | Full shutdown + PSU switch off; photograph wiring     |
| C    | RAM upgrade 32GB → 64GB (4× DIMM)      | Memtest 1 pass, 0 errors                              |
| D    | Dual RTX 3090 FE + NVLink P3669        | TWO separate PCIe cables per card — never daisy-chain |
| E    | MSI Afterburner OC + fan/power profile | Temps <83°C core, VRAM <100°C                         |

## Sequencing (strict)

1. **A (BIOS)** — no hardware touched yet; USB flash + settings only
2. **B (PSU)** — case open, full cable swap, test boot with NO GPU
3. **C (RAM)** — add 2× DIMMs, verify 64GB in BIOS, memtest
4. **D (GPUs)** — pull 2080 Ti, install both 3090s + NVLink, first boot
5. **E (OC)** — software-only on Windows; Afterburner profile

Parts B and C happen in the same case-open session. A is software-
only so it runs first from the desk.

## Artifacts to Capture

Folder: `.buildrunner/artifacts/phase-1/below/`

- A.1 — Photo: BIOS POST screen showing new version
- A.2 — File: `nvidia-smi --query-gpu=index,name,memory.total --format=csv` (Above-4G-Decoding check — canonical)
- A.3 — File: PowerShell `Get-PnpDevice -Class Display | Format-List Name,InstanceId > phase-1-display-pnp.txt`
- B.1 — Photo: old AX860 cabling (pre-swap)
- B.2 — Photo: new RM1200x cabling, no GPU connected, POST confirmed
- C.1 — Screenshot: BIOS showing 64GB, XMP enabled
- C.2 — File: memtest result (0 errors, 1 pass min)
- D.1 — File: `nvidia-smi topo -m` (MUST show `NV#` between GPU 0/1 — not `PHB`)
- D.2 — File: `nvidia-smi` showing 24GB per card
- D.3 — File: 5-min stability log (FurMark or 3DMark) — both GPUs <83°C core
- E.1 — Screenshot: Afterburner profile (Power +15%, Core +75MHz, Mem +300MHz)
- E.2 — File: `nvidia-smi -q -d TEMPERATURE` after 1000×10 qwen3:8b run

## Roles This Session

- **You (physical):** open case, swap parts, flash BIOS, cable, boot
- **Me (Claude on Muddy):** coach each step in order, file artifacts as you drop them in, sanity-check `nvidia-smi` output, log decisions

Flow: you run the command on Below (or take the photo), paste/save
it here, I file it into `.buildrunner/artifacts/phase-1/below/` with
a consistent name and record it in the phase log.

## Abort Rules (hard stops)

- NEVER power off Below mid-BIOS-flash — corruption.
- NEVER daisy-chain one PCIe cable to both 8-pin connectors on a 3090.
- If `nvidia-smi topo -m` shows `PHB` instead of `NV#` — reseat the bridge; do not proceed to E until NVLink is confirmed.
- If temps hit >83°C core during Part D stability test — stop, check airflow, do not apply OC.

## Tests

This phase has no code, so no unit tests. Verification is the Part G
checklist (deferred to the follow-up session after all Below parts
done + MS-A2 assembled):

- `nvidia-smi topo -m` shows `NV#` between GPU 0 and GPU 1
- `nvidia-smi --query-gpu=memory.total` shows 24576 MiB × 2
- Memtest: 0 errors over 1 pass
- 5-min sustained load: both GPUs <83°C core, VRAM <100°C

These are exercised programmatically during Phase 2 by
`below-verify.sh` (written then, not now), but the raw artifacts are
captured here.

## Done When (this session's slice)

- [ ] Part A: BIOS updated + artifacts A.1–A.3 filed
- [ ] Part B: PSU swapped + artifacts B.1–B.2 filed
- [ ] Part C: 64GB RAM verified + artifacts C.1–C.2 filed
- [ ] Part D: dual 3090 + NVLink confirmed via `NV#` + artifacts D.1–D.3 filed
- [ ] Part E: OC profile saved + artifacts E.1–E.2 filed
- [ ] `decisions.log` entry: `Phase 1 Below slice — BIOS vX, dual 3090 NVLink NV# confirmed, RM1200x installed, OC Profile 1 active`
- [ ] Phase 1 lock KEPT (MS-A2 Part F + Part G full verification still pending)

Phase 1 final completion (Status → COMPLETE) happens only after
Part F (MS-A2) and Part G (full checklist + Claude artifact review)
are done in a follow-up session.

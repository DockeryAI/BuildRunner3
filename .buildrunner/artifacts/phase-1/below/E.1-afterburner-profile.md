# Afterburner OC Profile — Staged for GUI apply

Power limit already applied via nvidia-smi (400W, +14.3%).
Clock offsets require MSI Afterburner GUI — install then apply these values.

## Install

Download: https://www.msi.com/Landing/afterburner/graphics-cards
Run the installer, reboot when prompted.

## Profile 1 (both GPUs)

- Power Limit: **100%** (already 400W via nvidia-smi — leave Afterburner at 100, don't stack)
- Core Clock offset: **+75 MHz**
- Memory Clock offset: **+300 MHz**
- Fan: **Auto / stock curve** (3090 FE cooler handles 400W fine)
- Apply to: both GPU 0 and GPU 1 (click the "sync settings" chain icon)

Save as Profile 1, check "Apply at Windows startup" and "Apply at system tray".

## Validation (after apply)

Re-run stress: `powershell -File C:\Users\cluster\below_stress.ps1`
Expect: GPU 0 core ~1935 MHz (1860 + 75), no black screens, no artifacts.
If black screen → OC unstable, reduce core offset to +50.

## Already applied (no Afterburner needed)

- Power limit 400W on both GPUs ✓
- PCIe ASPM disabled (Ultimate Performance plan) ✓
- Ghost 2080 Ti device removed ✓

# PSoC Edge M33/M55 TinyCNN Workspace

This repository is a complete workspace mirror containing:

- `edgi-talk-m33led/`: Cortex-M33 BSP and its independent build copy.
- `Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision/`: Cortex-M55/Ethos-U55 BSP and its independent build copy.
- `tinycnn-executorch/`: TinyCNN ExecuTorch deployment, RT-AK-style packaging work, E84 runtime integration evidence, and E84/FVP validation reports.

The repository intentionally retains the vendor BSP files, bundled build tools, libraries, executable utilities, generated files, and local build outputs needed to reproduce the current development environment.

## Current Final Status

| Item | Status |
| --- | --- |
| PT2E INT8 | PASS |
| TOSA/Vela | PASS |
| FVP | PASS |
| PTE C array | PASS |
| E84 ExecuTorch Runtime | PASS |
| Ethos-U55 board inference | PASS |
| IRQ/RT-Thread Semaphore | PASS |
| E84/FVP Top-1 comparison | PASS |
| 1e-6 numerical consistency | PASS |
| Float Bit-Exact | Not verified |
| Real dataset accuracy | Not applicable |
| Production-grade stability | Not verified |

## Key Evidence

- `tinycnn-executorch/docs/12_first_inference_journey.md`
- `tinycnn-executorch/docs/13_e84_fvp_final_validation.md`
- `tinycnn-executorch/tinycnn/reports/e84_fvp_final_validation.md`
- `tinycnn-executorch/tinycnn/reports/fvp_e84_final_compare.log`
- `tinycnn-executorch/tinycnn/reports/e84_first_inference_serial.log`
- `tinycnn-executorch/scripts/validate_e84_fvp_output.py`

The final comparison result is:

```text
TINYCNN_E84_FVP_FINAL_COMPARE=PASS
```

## Reproduction Boundary

The E84 BSP currently depends on ExecuTorch and Ethos-U static libraries built in the WSL workspace. The default compatible path remains:

```text
//wsl$/Ubuntu-22.04/home/zwb/work/ethosu_tinycnn
```

It can be overridden with `EXECUTORCH_WS_ROOT`. This repository may not contain a complete standalone copy of all ExecuTorch static libraries; build the runner and related `.a` files in WSL before rebuilding the BSP.

The original Git metadata of the former M55 and TinyCNN child repositories was backed up outside this repository before conversion to this monorepo.
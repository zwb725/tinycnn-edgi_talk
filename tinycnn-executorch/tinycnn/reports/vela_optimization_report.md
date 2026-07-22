# TinyCNN Vela Optimization Report

## Control Variables

- Model: custom random-weight TinyCNN from `tinycnn/model.py`; no ExecuTorch official example model is used.
- Weights: fixed by `torch.manual_seed(20260716)` for every variant.
- Calibration: 32 fixed random tensors with generator seed `20260716`.
- Target profile: `ethos-u55-128`, `Ethos_U55_High_End_Embedded`, `Shared_Sram`.
- FVP mode: embedded-PTE runner on `FVP_Corstone_SSE-300_Ethos-U55`.
- Baseline output for `max_abs_error`: the `default` 96x96 FVP output. `input_64` is marked `N/A` because it uses a different input resolution.

## Vela Parameters

| variant | input | Vela flags |
| --- | --- | --- |
| default | 96x96 | Vela default strategy |
| size | 96x96 | `--optimise=Size` |
| input_64 | 64x64 | Vela default strategy |

The local API inspection is recorded in `tinycnn/reports/vela_api_inspection.md`. `--arena-cache-size` was not run because the required Default/Size comparison already produced a clear Size tradeoff and the U55 Shared_Sram profile does not need an arbitrary cache sweep for the main deliverable.

## Results

| variant | input_shape | PTE bytes | SRAM KiB | Off-chip Flash KiB | NPU ops | CPU ops | FVP | FVP Top-1 | max abs vs default | FVP PMU cycles |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| default | (1, 3, 96, 96) | 31712 | 78.203125 | 25.328125 | 7 | 0 | PASS | 1 | 0 | 247546 |
| size | (1, 3, 96, 96) | 36432 | 54 | 25.328125 | 7 | 0 | PASS | 1 | 0 | 475583 |
| input_64 | (1, 3, 64, 64) | 31120 | 48.21875 | 25.34375 | 7 | 0 | PASS | 1 | N/A | 119909 |

Full machine-readable results are in `tinycnn/reports/optimization_results.csv`.

## Default vs Size

- Size SRAM delta: `-30.95%` (78.203125 KiB -> 54 KiB).
- Size PTE delta: `14.88%` (31712 bytes -> 36432 bytes).
- Size off-chip Flash estimate delta: `0.00%` (25.328125 KiB -> 25.328125 KiB).
- Default and Size FVP output vectors are identical at the printed precision, and both keep Top-1 = 1.
- The honest conclusion is a space/performance tradeoff, not a free optimization: `--optimise=Size` reduces Vela SRAM usage but increases the PTE size and the FVP PMU cycle counter in this run.

## 96x96 vs 64x64

- The 64x64 variant keeps the same channel counts, convolution layers, activations, classifier head, and parameter count `23844` because the model uses `AdaptiveAvgPool2d((1, 1))`.
- Compared with 96x96 default, 64x64 SRAM delta is `-38.34%` and PTE delta is `-1.87%`.
- 64x64 output is not required to match 96x96 numerically because the input tensor shape and data differ. It was validated for legal output, Top-1 extraction, NPU delegation, and FVP completion.

## Data Boundaries

- `total_sram_kib`, `offchip_flash_kib`, MAC counts, and Vela bandwidth/cycle fields are Vela compiler estimates for the delegated network.
- `fvp_status`, output vectors, delegation count, and `ethosu_pmu_cycle_cntr` come from Corstone-300 Ethos-U55 FVP logs.
- CPU cycle ratios printed by the runner are not used as board timing. The runner log itself warns that CPU cycle values and ratios require FPGA and identical CPU/NPU frequency.
- None of these measurements are PSoC Edge E84 board measurements, and this project does not claim an ExecuTorch Runtime port to E84.

## Evidence

### default

- PTE: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/default/tinycnn_default.pte`
- Export log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/default/export.log`
- FVP log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/default/fvp_embedded.log`
- Metadata: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/default/metadata.json`

### size

- PTE: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/size/tinycnn_size.pte`
- Export log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/size/export.log`
- FVP log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/size/fvp_embedded.log`
- Metadata: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/size/metadata.json`

### input_64

- PTE: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/input_64/tinycnn_input_64.pte`
- Export log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/input_64/export.log`
- FVP log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/input_64/fvp_embedded.log`
- Metadata: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/input_64/metadata.json`

# TinyCNN Baseline Summary

## Protected Artifacts

SHA256 manifest: `/home/zwb/work/ethosu_tinycnn/tinycnn/reports/baseline_artifacts.sha256`

Protected baseline files include:

- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte`
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_embedded.log`
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_qspi.log`
- `/home/zwb/work/ethosu_tinycnn/tinycnn/export_ethosu.py`
- `/home/zwb/work/ethosu_tinycnn/tinycnn/model.py`
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/runner/arm_executor_runner`
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/runner_qspi/arm_executor_runner`

## Model Structure

The model is a custom random-weight TinyCNN, not an ExecuTorch official example model.

```text
Input [1, 3, 96, 96]
Conv2d 3->16, kernel=3, stride=2, padding=1
ReLU
Conv2d 16->32, kernel=3, stride=2, padding=1
ReLU
Conv2d 32->64, kernel=3, stride=2, padding=1
ReLU
AdaptiveAvgPool2d(1, 1)
Flatten
Linear 64->4
Output [1, 4]
```

Parameter count: `23844`.

## Baseline Numerical Result

- FP32 Top-1: `1`
- PT2E INT8 Top-1: `1`
- Fixed test-input max absolute FP32-vs-PT2E error: `0.00024946779012680054`
- FP32 smoke recheck log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fp32_recheck.log`

The fixed-input comparison only validates numerical consistency for this synthetic test input. It is not an accuracy evaluation and must not be described as accuracy preservation.

## Delegate / TOSA / Vela Result

- Ethos-U delegated subgraphs: `1`
- Delegated EXIR nodes: `29`
- Non-delegated EXIR boundary nodes: `3`
- Vela delegated network: `CPU operators = 0`, `NPU operators = 7`
- PTE: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte`
- PTE size: `31696` bytes

The `29` delegated EXIR nodes and `7` Vela NPU operators are not contradictory: the first is an ExecuTorch graph partitioning count, while the second is Vela's compiled NPU operator count inside the delegated command stream.

## FVP Loading Modes

### Embedded PTE

- Baseline log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_embedded.log`
- Recheck log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_embedded_recheck.log`
- Status: `PASS`
- Evidence: `NPU delegations: 1 (1.00 per inference)` and `Program complete, exiting.`
- Output: `[-0.020373, 0.067080, -0.059627, 0.062111]`

### QSPI `--data` PTE

- Baseline log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_qspi.log`
- Recheck log: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_qspi_recheck.log`
- Status: `PASS`
- Evidence: `NPU delegations: 1 (1.00 per inference)` and `Program complete, exiting.`
- Output: `[-0.020373, 0.067080, -0.059627, 0.062111]`

## Fixed Issues

- Enabled Cortex-M55 FPU/MVE access in startup before GCC-emitted MVE instructions execute.
- Relocated the vector table to writable RAM for FVP target setup paths using `NVIC_SetVector`.
- Added guarded FVP semihost traces for target and runner bring-up.
- Fixed semihost trace inline assembly by marking `r0` as an in/out register.
- Added semihost-compatible stdout/stderr/exit paths for FVP diagnostics.
- Disabled the Cortex-M/CMSIS-NN dependency path for this environment because external GitHub dependency fetches were unstable; the validated path is Ethos-U delegate only.

## Remaining Linker Warnings

The runner still links with warnings about `.data`, `.sram.data`, `.rodata` segment allocation and an RWX LOAD segment. FVP execution is validated, but these warnings mean the linker layout is not yet production-clean. They must not be presented as a completed production firmware memory layout.

## Minimal Export Recheck

To avoid overwriting protected baseline PTE/logs, this baseline stage only recompiled the existing export script with `py_compile`. Full export revalidation is performed in the new variant directories under `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/`.

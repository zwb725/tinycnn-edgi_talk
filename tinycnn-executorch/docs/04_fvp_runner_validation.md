# FVP Runner Validation

## Runner Build

The runner is built through ExecuTorch's Arm helper script with the Corstone-300 / Ethos-U55 target profile. The validated baseline artifacts are:

- Embedded runner: `tinycnn/build/runner/arm_executor_runner`
- QSPI runner: `tinycnn/build/runner_qspi/arm_executor_runner`
- Default variant runner: `tinycnn/build/variants/default/runner/arm_executor_runner`

The build intentionally disables the Cortex-M/CMSIS-NN path in this environment and validates the Ethos-U delegate path.

## Embedded-PTE Mode

Baseline embedded FVP log:

- `tinycnn/build/fvp_embedded.log`
- Recheck: `tinycnn/build/fvp_embedded_recheck.log`

Evidence in the log:

```text
PTE Model data loaded. Size: 31696 bytes.
NPU delegations: 1 (1.00 per inference)
Output[0][0]: (float) -0.020373
Output[0][1]: (float) 0.067080
Output[0][2]: (float) -0.059627
Output[0][3]: (float) 0.062111
Program complete, exiting.
```

## QSPI `--data` Mode

Baseline QSPI FVP log:

- `tinycnn/build/fvp_qspi.log`
- Recheck: `tinycnn/build/fvp_qspi_recheck.log`

The PTE is supplied with `--data tinycnn_u55.pte@0x38000000`. The runner reports the expected PTE address and completes successfully.

## FVP vs Board

These are Corstone-300 Ethos-U55 FVP results. They are not PSoC Edge E84 board measurements. The runner prints CPU cycle ratio warnings; only the FVP log values are recorded as simulator evidence, not as board timing.

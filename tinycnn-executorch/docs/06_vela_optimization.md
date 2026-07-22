# Vela Optimization

Canonical report: `tinycnn/reports/vela_optimization_report.md`
Machine-readable CSV: `tinycnn/reports/optimization_results.csv`

## Result Table

| variant | input | PTE bytes | SRAM KiB | Flash KiB | FVP | FVP output | PMU cycles |
| --- | --- | --- | --- | --- | --- | --- | --- |
| default | (1, 3, 96, 96) | 31712 | 78.203125 | 25.328125 | PASS | [-0.020373, 0.067080, -0.059627, 0.062111] | Corstone-300 FVP ethosu_pmu_cycle_cntr=247546; not E84 board timing |
| size | (1, 3, 96, 96) | 36432 | 54 | 25.328125 | PASS | [-0.020373, 0.067080, -0.059627, 0.062111] | Corstone-300 FVP ethosu_pmu_cycle_cntr=475583; not E84 board timing |
| input_64 | (1, 3, 64, 64) | 31120 | 48.21875 | 25.34375 | PASS | [-0.020281, 0.067272, -0.058863, 0.060842] | Corstone-300 FVP ethosu_pmu_cycle_cntr=119909; not E84 board timing |

## Interpretation

`--optimise=Size` is a real tradeoff in this project. It reduces Vela SRAM usage from `78.203125 KiB` to `54 KiB`, while PTE size increases from `31712` to `36432` bytes. Default and Size produce the same FVP output at printed precision and keep Top-1 `1`.

The 64x64 experiment keeps the same parameter count and model topology, but lowers activation memory and FVP PMU count. Its output is not compared numerically with 96x96 because the input resolution and tensor values differ.

## Data Boundaries

- SRAM, Flash, MAC, and Vela cycle/bandwidth values are compiler estimates.
- FVP output, completion status, NPU delegation count, and PMU counter values are Corstone-300 FVP evidence.
- These values are not PSoC Edge E84 board latency or throughput.

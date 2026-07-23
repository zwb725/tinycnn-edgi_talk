# Project Status

This status page is split by repository phase so historical facts remain clear.

## Phase 1: `zwb725/tinycnn`

The original TinyCNN repository completed the model/compiler/FVP and RT-AK-style packaging stage.

| Task | Status | Evidence Path | Notes |
| --- | --- | --- | --- |
| Baseline SHA256 manifest | PASS | `tinycnn/reports/baseline_artifacts.sha256` | Protected baseline artifacts hashed. |
| Baseline summary | PASS | `tinycnn/reports/baseline_summary.md` | Includes model, quantization, delegate, Vela, FVP, fixed issues, linker warnings. |
| Default variant export/FVP | PASS | `tinycnn/build/variants/default/` | PTE 31712 bytes, FVP PASS. |
| Size variant export/FVP | PASS | `tinycnn/build/variants/size/` | PTE 36432 bytes, FVP PASS. |
| 64x64 controlled experiment | PASS | `tinycnn/build/variants/input_64/` | Executed as extended comparison. |
| Optimization CSV/report | PASS | `tinycnn/reports/optimization_results.csv`, `tinycnn/reports/vela_optimization_report.md` | Generated from logs and metadata. |
| Linker warning analysis | PASS | `tinycnn/reports/linker_layout_analysis.md` | Analysis only; no risky script rewrite retained. |
| RT-AK CLI and manifest | PASS | `rtak_plugin_executorch/rt_ai_tools/platforms/executorch_ethosu/` | CLI validates PTE, SHA, size, overwrite policy. |
| Embedded PTE C array | PASS | `rtak_plugin_executorch/examples/tinycnn/generated/embedded/` | Demo validation reconstructs original PTE bytes. |
| QSPI resource mode | PASS | `rtak_plugin_executorch/examples/tinycnn/generated/qspi/` | PTE copy SHA matches baseline. |
| Kconfig/SConscript/backend prototype | PASS | `rtak_plugin_executorch/backend_executorch/` | Original repository stage provided the target interface and packaging prototype. |
| pytest | PASS | `rtak_plugin_executorch/reports/test.log` | `13 passed`; capture disabled due local pytest temp-file issue. |
| Demo validation | PASS | `rtak_plugin_executorch/reports/demo_validation.md` | Manifest, SHA, embedded, qspi, backend files checked. |
| Multi-runtime architecture | PASS | `docs/multi_runtime_architecture.md`, `docs/09_multi_runtime_architecture.md` | Separates original FVP/prototype stage from board-runtime work. |
| Production linker cleanup | BLOCKED | `tinycnn/reports/linker_layout_analysis.md` | Would require non-minimal PHDR/VMA/LMA cleanup; not safe as optional patch in that pass. |
| E84 ExecuTorch Runtime port in original repo | HISTORICAL_BLOCKED | `docs/08_rtak_backend_prototype.md` | This was blocked/out of scope in `zwb725/tinycnn`, then completed in `zwb725/tinycnn-edgi_talk`. |

## Phase 2: `zwb725/tinycnn-edgi_talk`

The follow-up repository completed the E84 BSP integration, real ExecuTorch Runtime lifecycle, Ethos-U55 board inference, and E84/FVP numerical comparison.

| Task | Status | Evidence Path | Notes |
| --- | --- | --- | --- |
| E84 BSP integration | PASS | `C:\tinycnn\Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision` | BSP-specific integration, not a generic production RT-AK Backend. |
| E84 ExecuTorch Runtime | PASS | `docs/12_first_inference_journey.md` | `Program::load`, `load_method`, tensor binding, `Method::execute()` return path. |
| Ethos-U55 board inference | PASS | `docs/12_first_inference_journey.md` | Real serial log shows output float bits and `[TinyCNN] inference PASS`. |
| IRQ/RT-Thread semaphore | PASS | `docs/12_first_inference_journey.md` | IRQ 38 return path allowed `Method::execute()` to complete. |
| E84/FVP Top-1 comparison | PASS | `tinycnn/reports/e84_fvp_final_validation.md` | E84 Top-1 `1`, FVP Top-1 `1`. |
| 1e-6 numerical consistency | PASS | `scripts/validate_e84_fvp_output.py` | Max abs error `4.993568659e-07`, tolerance `1e-6`. |
| Float Bit-Exact | NOT_VERIFIED | `tinycnn/reports/e84_fvp_final_validation.md` | FVP log prints decimal floats, not full float bits. |
| Real dataset accuracy | NOT_APPLICABLE | `tinycnn/model.py` | TinyCNN uses fixed random weights. |
| Production-grade stability | NOT_VERIFIED | `docs/13_e84_fvp_final_validation.md` | Single fixed-input validation, not stress testing. |
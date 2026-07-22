# Project Status

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
| Kconfig/SConscript/backend stub | PASS | `rtak_plugin_executorch/backend_executorch/` | Target runtime intentionally returns not implemented. |
| pytest | PASS | `rtak_plugin_executorch/reports/test.log` | `13 passed`; capture disabled due local pytest temp-file issue. |
| Demo validation | PASS | `rtak_plugin_executorch/reports/demo_validation.md` | Manifest, SHA, embedded, qspi, backend files checked. |
| Multi-runtime architecture | PASS | `docs/multi_runtime_architecture.md`, `docs/09_multi_runtime_architecture.md` | Separates E84 runtime chain from ExecuTorch FVP chain. |
| Production linker cleanup | BLOCKED | `tinycnn/reports/linker_layout_analysis.md` | Would require non-minimal PHDR/VMA/LMA cleanup; not safe as optional patch in this pass. |
| E84 ExecuTorch Runtime port | BLOCKED | `docs/08_rtak_backend_prototype.md` | Explicitly out of current scope; target-side code is a stub. |

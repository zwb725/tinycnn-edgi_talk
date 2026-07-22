# RT-AK ExecuTorch Prototype Demo Validation

- Source PTE: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte`
- Source PTE SHA256: `5523dd345ee3b99dab80a454cb039f79d4484d3c19a4d1700332959d50b654c2`
- Embedded generated project: `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded`
- QSPI generated project: `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi`

| Check | Status | Evidence |
| --- | --- | --- |
| embedded manifest schema | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/model_manifest.json` |
| embedded validation platform | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/model_manifest.json` |
| embedded sha256 | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/model_manifest.json` |
| qspi manifest mode | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi/model_manifest.json` |
| qspi sha256 | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi/model_manifest.json` |
| embedded C array reconstructs PTE | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/models/tinycnn/rt_ai_tinycnn_model_data.c` |
| qspi resource copy | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi/resources/tinycnn_u55.pte` |
| embedded Kconfig exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/backend_executorch/Kconfig` |
| embedded SConscript exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/backend_executorch/SConscript` |
| embedded backend header exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/backend_executorch/include/rt_ai_executorch_backend.h` |
| embedded backend source exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded/backend_executorch/src/rt_ai_executorch_backend.c` |
| qspi Kconfig exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi/backend_executorch/Kconfig` |
| qspi SConscript exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi/backend_executorch/SConscript` |
| qspi backend header exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi/backend_executorch/include/rt_ai_executorch_backend.h` |
| qspi backend source exists | PASS | `/home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/qspi/backend_executorch/src/rt_ai_executorch_backend.c` |

## Boundary

This demo validates packaging and generated files only. It does not validate an ExecuTorch Runtime port on PSoC Edge E84 and does not claim E84 execution.

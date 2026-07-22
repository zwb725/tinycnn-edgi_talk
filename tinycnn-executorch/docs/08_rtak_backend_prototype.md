# RT-AK ExecuTorch Backend Prototype

## Goal

The prototype packages an already validated ExecuTorch PTE for RT-AK-style deployment workflows. It is not an E84 ExecuTorch Runtime port.

## Structure

```text
rtak_plugin_executorch/
  rt_ai_tools/platforms/executorch_ethosu/
    cli.py
    deploy.py
    manifest.py
    pte_embed.py
  backend_executorch/
    include/rt_ai_executorch_backend.h
    src/rt_ai_executorch_backend.c
    Kconfig
    SConscript
  examples/tinycnn/generated/
    embedded/
    qspi/
  tests/
  reports/
```

## Tools Plugin Side

The CLI validates the PTE, computes SHA256, records size, refuses overwrite without `--force`, and generates a manifest. It supports `embedded`, `qspi`, `manifest-only`, and `dry-run` modes.

Verified command pattern:

```bash
PYTHONPATH=rtak_plugin_executorch python -m rt_ai_tools.platforms.executorch_ethosu.cli \
  --pte /home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte \
  --project /home/zwb/work/ethosu_tinycnn/rtak_plugin_executorch/examples/tinycnn/generated/embedded \
  --model-name tinycnn \
  --input-shape 1,3,96,96 \
  --output-shape 1,4 \
  --target ethos-u55-128 \
  --load-mode embedded \
  --force
```

## Manifest

The manifest uses `classification_benchmark`, `ExecuTorch PTE`, `Corstone-300 Ethos-U55 FVP`, tensor shapes, PTE filename, size, SHA256, load mode, delegate counts, and explicit limitations. It does not label TinyCNN as gesture recognition.

## Embedded and QSPI Modes

Embedded mode generates a 16-byte aligned `const uint8_t` C array and a header. QSPI mode copies the PTE into a `resources/` directory and records the relative load path in the manifest.

## Lib Plugin Side

`backend_executorch` provides Kconfig/SConscript and lifecycle functions:

- `rt_ai_executorch_init()`
- `rt_ai_executorch_get_input()`
- `rt_ai_executorch_run()`
- `rt_ai_executorch_get_output()`
- `rt_ai_executorch_deinit()`

The implementation returns `RT_AI_EXECUTORCH_ENOSYS` for inference paths. Future work must add Program loading, Method loading, MemoryAllocator setup, Ethos-U delegate registration, tensor binding, and embedded/QSPI PTE loading.

## Test Result

`rtak_plugin_executorch/reports/test.log` records `13 passed`. Demo validation is in `rtak_plugin_executorch/reports/demo_validation.md`.

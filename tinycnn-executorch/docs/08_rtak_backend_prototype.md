# RT-AK ExecuTorch Backend Prototype

## Scope

The original `zwb725/tinycnn` repository built an RT-AK-style packaging prototype for an already validated ExecuTorch PTE. In that phase, the target-side runtime path was intentionally not a completed E84 ExecuTorch Runtime port.

The follow-up `zwb725/tinycnn-edgi_talk` repository completed the BSP-specific E84 integration: real ExecuTorch Runtime lifecycle, Ethos-U55 board inference, IRQ/RT-Thread semaphore return, and E84/FVP numerical comparison.

This distinction is important: the project now has a completed E84 BSP-specific runtime path, but it should not be described as a generic production RT-AK Backend release.

## Prototype Structure

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
    src/rt_ai_executorch_runtime.cpp
    Kconfig
    SConscript
  examples/tinycnn/generated/
    embedded/
    qspi/
  tests/
  reports/
```

## Tools Plugin Side

The CLI validates the PTE, computes SHA256, records size, rejects overwrite without `--force`, and generates a manifest. It supports `embedded`, `qspi`, `manifest-only`, and `dry-run` modes.

Validated command mode:

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

The manifest records `classification_benchmark`, `ExecuTorch PTE`, `Corstone-300 Ethos-U55 FVP`, tensor shapes, PTE filename, size, SHA256, load mode, delegate counts, and explicit limits. It must not label TinyCNN as gesture recognition or claim real dataset accuracy.

## Embedded and QSPI Modes

Embedded mode generates a 16-byte aligned `const uint8_t` C array and header. QSPI mode copies the PTE into `resources/` and records a relative load path in the manifest.

## Target Runtime History

Original repository phase:

- Provided Kconfig/SConscript and lifecycle function declarations.
- Kept the inference path as a clear not-implemented/stub boundary.
- Did not claim E84 board execution.

Follow-up `tinycnn-edgi_talk` phase:

- Added `rt_ai_executorch_runtime.cpp` for `Program::load`, method loading, allocator setup, tensor binding, and `Method::execute()`.
- Added the PSoC/E84 Ethos-U platform bridge for IRQ 38 and RT-Thread semaphore return.
- Validated real E84 inference with serial output float bits.
- Validated E84/FVP Top-1 and `1e-6` numerical agreement.

Final evidence:

- `docs/12_first_inference_journey.md`
- `docs/13_e84_fvp_final_validation.md`
- `tinycnn/reports/e84_fvp_final_validation.md`
- `scripts/validate_e84_fvp_output.py`

## Test Result

`rtak_plugin_executorch/reports/test.log` records `13 passed` for the original packaging prototype. The final E84/FVP comparison is covered separately by `scripts/validate_e84_fvp_output.py` and `tests/test_validate_e84_fvp_output.py`.
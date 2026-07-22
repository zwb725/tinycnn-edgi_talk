# RT-AK ExecuTorch Ethos-U Prototype

This is a minimal RT-AK-style prototype for packaging a validated ExecuTorch PTE. It provides a PC-side CLI, model manifest generation, embedded C-array or QSPI resource modes, RT-Thread Kconfig/SConscript files, and target-side backend stubs.

It does not port ExecuTorch Runtime to PSoC Edge E84 and does not claim E84 execution. Current validation data belongs to the custom TinyCNN running on Corstone-300 Ethos-U55 FVP.

## Example

```bash
PYTHONPATH=rtak_plugin_executorch python -m rt_ai_tools.platforms.executorch_ethosu.cli \
  --pte /home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte \
  --project /tmp/rtak_tinycnn_generated \
  --model-name tinycnn \
  --input-shape 1,3,96,96 \
  --output-shape 1,4 \
  --target ethos-u55-128 \
  --load-mode embedded
```

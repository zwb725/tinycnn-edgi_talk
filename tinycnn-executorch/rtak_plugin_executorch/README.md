# RT-AK ExecuTorch Ethos-U Prototype

This is an RT-AK-style prototype for packaging a validated ExecuTorch PTE. It provides a PC-side CLI, model manifest generation, embedded C-array or QSPI resource modes, RT-Thread Kconfig/SConscript files, and target-side backend interfaces.

Historical boundary: in the original `zwb725/tinycnn` phase this package was a packaging prototype and did not claim PSoC Edge E84 execution. The follow-up `zwb725/tinycnn-edgi_talk` phase completed the BSP-specific E84 ExecuTorch Runtime and Ethos-U55 board inference path.

Do not describe this as a generic production RT-AK Backend. The final E84/FVP closure is documented in:

- `../docs/12_first_inference_journey.md`
- `../docs/13_e84_fvp_final_validation.md`
- `../tinycnn/reports/e84_fvp_final_validation.md`
- `../scripts/validate_e84_fvp_output.py`

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
# TinyCNN PT2E Quantization Report

- Input shape: `(1, 3, 96, 96)`
- Calibration samples: `32` fixed random tensors
- Quantized ops library: `/home/zwb/work/ethosu_tinycnn/.venv/lib/python3.10/site-packages/executorch/kernels/quantized/libquantized_ops_aot_lib.so`
- FP32 output: `[[-0.009458765387535095, 0.06498293578624725, -0.05907968804240227, 0.05788669362664223]]`
- PT2E INT8 output: `[[-0.009440915659070015, 0.06509262323379517, -0.05912994220852852, 0.05813616141676903]]`
- Output shape: `(1, 4)`
- FP32 Top-1: `1`
- INT8 Top-1: `1`
- Top-1 match: `True`
- Max absolute error: `0.00024946779012680054`

## Quantize / Dequantize Nodes

- `quantize_per_tensor_default: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default: quantized_decomposed.dequantize_per_tensor.default`
- `dequantize_per_channel_default: quantized_decomposed.dequantize_per_channel.default`
- `dequantize_per_channel_default_1: quantized_decomposed.dequantize_per_channel.default`
- `quantize_per_tensor_default_1: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_1: quantized_decomposed.dequantize_per_tensor.default`
- `dequantize_per_channel_default_2: quantized_decomposed.dequantize_per_channel.default`
- `dequantize_per_channel_default_3: quantized_decomposed.dequantize_per_channel.default`
- `quantize_per_tensor_default_2: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_2: quantized_decomposed.dequantize_per_tensor.default`
- `dequantize_per_channel_default_4: quantized_decomposed.dequantize_per_channel.default`
- `dequantize_per_channel_default_5: quantized_decomposed.dequantize_per_channel.default`
- `quantize_per_tensor_default_3: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_3: quantized_decomposed.dequantize_per_tensor.default`
- `quantize_per_tensor_default_4: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_4: quantized_decomposed.dequantize_per_tensor.default`
- `quantize_per_tensor_default_5: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_5: quantized_decomposed.dequantize_per_tensor.default`
- `quantize_per_tensor_default_6: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_6: quantized_decomposed.dequantize_per_tensor.default`
- `quantize_per_tensor_default_7: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_7: quantized_decomposed.dequantize_per_tensor.default`
- `dequantize_per_channel_default_6: quantized_decomposed.dequantize_per_channel.default`
- `dequantize_per_channel_default_7: quantized_decomposed.dequantize_per_channel.default`
- `quantize_per_tensor_default_8: quantized_decomposed.quantize_per_tensor.default`
- `dequantize_per_tensor_default_8: quantized_decomposed.dequantize_per_tensor.default`

## Warnings

- Yes. Non-fatal export warnings were observed in `tinycnn/build/export_ethosu.log`.
- Observed warning classes include PyTorch pytree deprecation, torch.tensor copy construction, LeafSpec deprecation, and guard_size_oblivious deprecation.

## Artifacts

- Quantized graph: `/home/zwb/work/ethosu_tinycnn/tinycnn/reports/quantized_graph.txt`
- PTE: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte` (31696 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/out.tosa` (36352 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/output/out_summary_Ethos_U55_High_End_Embedded.csv` (1553 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/output/out_vela.npz` (36232 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/output_tag0_TOSA-1.0+INT+int16+int4+u55.tosa` (36352 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/partition_report.txt` (0 bytes)

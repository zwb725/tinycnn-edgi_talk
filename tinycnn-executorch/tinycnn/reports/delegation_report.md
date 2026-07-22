# TinyCNN Ethos-U Delegation Report

Total delegated subgraphs: 1
Number of delegated nodes: 29
Number of non-delegated nodes: 3

## Operator Delegation

| op_type | delegated | non_delegated |
| --- | --- | --- |
| aten_avg_pool2d_default | 1 | 0 |
| aten_convolution_default | 3 | 0 |
| aten_linear_default | 1 | 0 |
| aten_relu_default | 3 | 0 |
| aten_view_copy_default | 1 | 0 |
| getitem | 0 | 1 |
| quantized_decomposed_dequantize_per_channel_default | 8 | 0 |
| quantized_decomposed_dequantize_per_tensor_default | 6 | 1 |
| quantized_decomposed_quantize_per_tensor_default | 6 | 1 |
| Total | 29 | 3 |

## CPU Fallback Operators

These are EXIR nodes left outside the Ethos-U delegate. The Vela summary for the delegated network reports `CPU operators = 0` and `NPU operators = 7`; no coverage percentage is estimated here.

| op_type | non_delegated |
| --- | --- |
| getitem | 1 |
| quantized_decomposed_dequantize_per_tensor_default | 1 |
| quantized_decomposed_quantize_per_tensor_default | 1 |

## Delegate Subgraphs

- Delegated subgraph dump: `/home/zwb/work/ethosu_tinycnn/tinycnn/reports/delegated_subgraphs.txt`
- Lowered edge graph: `/home/zwb/work/ethosu_tinycnn/tinycnn/reports/edge_lowered_graph.txt`

## TOSA / Vela Artifacts

- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/out.tosa` (36352 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/output/out_summary_Ethos_U55_High_End_Embedded.csv` (1553 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/output/out_vela.npz` (36232 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/output_tag0_TOSA-1.0+INT+int16+int4+u55.tosa` (36352 bytes)
- `/home/zwb/work/ethosu_tinycnn/tinycnn/build/intermediates/partition_report.txt` (0 bytes)

## PTE

- Path: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte`
- Size: `31696` bytes

## Warnings

- Yes. Non-fatal export warnings were observed in `tinycnn/build/export_ethosu.log`.
- Observed warning classes include PyTorch pytree deprecation, torch.tensor copy construction, LeafSpec deprecation, and guard_size_oblivious deprecation.

# ExecuTorch PT2E Pipeline

The baseline exporter is `tinycnn/export_ethosu.py`; parameterized experiments use `tinycnn/export_variants.py`.

| Stage | Input | Output | Evidence |
| --- | --- | --- | --- |
| PyTorch model | `TinyCNN.eval()` | callable FP32 module | `tinycnn/model.py` |
| `torch.export` | model + fixed example input | exported program / FX graph | export logs |
| `EthosUCompileSpec` | target profile | Vela compiler flags | `tinycnn/reports/vela_api_inspection.md` |
| `prepare_pt2e` | exported graph + `EthosUQuantizer` | observer-inserted graph | export logs |
| Calibration | 32 fixed random tensors | calibrated observers | `Calibration: 32/32` in logs |
| `convert_pt2e` | prepared graph | PT2E INT8 graph | quantization reports |
| Quantized check | fixed input | INT8 output and Top-1 | `tinycnn/reports/quantization_report.md` |
| Re-export | quantized module | exported quantized program | export logs |
| `EthosUPartitioner` | quantized exported program | delegated EXIR subgraph | delegation reports |
| TOSA/Vela | delegated subgraph | `out.tosa`, `out_vela.npz`, summary CSV | variant intermediates |
| `to_executorch` | lowered edge program | ExecuTorch program manager | export logs |
| `save_pte_program` | program manager | `.pte` file | PTE paths and hashes |

The current local `EthosUCompileSpec` supports `extra_flags`; the Size experiment passes `extra_flags=["--optimise=Size"]`.

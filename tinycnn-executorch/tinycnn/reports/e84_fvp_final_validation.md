# TinyCNN E84/FVP 最终数值对账报告

## 1. 最终结论

`TINYCNN_E84_FVP_FINAL_COMPARE=PASS`

同一份 TinyCNN ExecuTorch PTE 已分别在 PSoC Edge E84 CM55 + Ethos-U55 真板路径和 Corstone-300 Ethos-U55 FVP 路径完成运行。两端 Top-1 均为 `1`，四个输出 float 在 `1e-6` 容差内数值一致。

当前结论只证明固定输入、固定随机权重 TinyCNN 的 E84/FVP 数值一致性；尚未证明 Float Bit-Exact，也不代表真实数据集准确率或生产级稳定性。

## 2. 证据来源

| 证据 | 路径 / 来源 | 说明 |
| --- | --- | --- |
| FVP 原始日志 | `tinycnn/reports/fvp_e84_final_compare.log` | 从 `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_e84_final_compare.log` 复制保存。 |
| E84 串口数据 | `docs/12_first_inference_journey.md` | E84 数据来自该文档中保存的真实串口日志。 |
| E84 独立日志 | `tinycnn/reports/e84_first_inference_serial.log` | 从 `docs/12_first_inference_journey.md` 的真实串口日志块提取，未重新生成或伪造。 |
| 自动对账脚本 | `scripts/validate_e84_fvp_output.py` | 解析 FVP float 输出和 E84 `float_bits`，计算 Top-1 和误差。 |

## 3. PTE Artifact

| 项目 | 值 |
| --- | --- |
| PTE 大小 | `31696 bytes` |
| ExecuTorch Header | `ET12` |
| FNV-1a32 | `0xdc0bdb6e` |
| SHA256 | `5523dd345ee3b99dab80a454cb039f79d4484d3c19a4d1700332959d50b654c2` |

FVP 和 E84 使用的是同一份 TinyCNN ExecuTorch PTE 语义产物。

## 4. FVP 运行证据

关键日志：

```text
PTE Model data loaded. Size: 31696 bytes.
NPU Inferences : 1
NPU delegations: 1 (1.00 per inference)
ethos-u : cycle_cnt : 18301 cycles (18301.00 per inference)
ethosu_pmu_cycle_cntr : 247553 (247553.00 per inference)
Program complete, exiting.
```

FVP 打印输出：

```text
Output[0][0]: (float) -0.020373
Output[0][1]: (float) 0.067080
Output[0][2]: (float) -0.059627
Output[0][3]: (float) 0.062111
```

FVP Top-1：

```text
1
```

## 5. PSoC Edge E84 运行证据

E84 串口日志中的关键片段：

```text
[executorch] pre-call tick=9095
[executorch] post-call tick=9132 status=0
[executorch] execute done status=0
[executorch] output0 float top1=1
[executorch] output0[0] float_bits=0xbca6e43b
[executorch] output0[1] float_bits=0x3d896156
[executorch] output0[2] float_bits=0xbd743b44
[executorch] output0[3] float_bits=0x3d7e6867
[TinyCNN] inference PASS
```

将 E84 `float_bits` 按 IEEE-754 float32 解码后：

| Index | Float Bits | Float32 |
| ---: | --- | ---: |
| 0 | `0xbca6e43b` | `-0.0203725006` |
| 1 | `0x3d896156` | `0.0670801848` |
| 2 | `0xbd743b44` | `-0.0596268326` |
| 3 | `0x3d7e6867` | `0.0621112846` |

E84 Top-1：

```text
1
```

## 6. E84/FVP 数值对账

| Index | E84 Float32 | FVP Float | 绝对误差 |
| ---: | ---: | ---: | ---: |
| 0 | `-0.0203725006` | `-0.020373` | `4.993568659e-07` |
| 1 | `0.0670801848` | `0.067080` | `1.848173141e-07` |
| 2 | `-0.0596268326` | `-0.059627` | `1.673955917e-07` |
| 3 | `0.0621112846` | `0.062111` | `2.845838070e-07` |

| 检查项 | 结果 |
| --- | --- |
| 最大绝对误差 | `4.993568659e-07` |
| 验收阈值 | `1e-6` |
| 输出数值一致性 | `PASS` |
| Top-1 一致性 | `PASS` |
| FVP 完整运行 | `PASS` |

自动对账输出：

```text
pte_loaded=PASS
npu_delegate=PASS
program_complete=PASS
top1_match=PASS
output_match=PASS
max_abs_error=4.993568659e-07
TINYCNN_E84_FVP_FINAL_COMPARE=PASS
```

## 7. 已验证链路

```text
TinyCNN fixed random weights
  -> PT2E INT8
  -> ExecuTorch EXIR
  -> TOSA
  -> Vela
  -> Ethos-U55 delegate PTE
  -> PTE C array
  -> E84 BSP .cy_ml_model_data
  -> ExecuTorch Program::load
  -> Program::load_method
  -> MemoryManager
  -> input/output tensor binding
  -> Method::execute()
  -> Ethos-U55 delegate/core driver
  -> IRQ 38
  -> RT-Thread semaphore
  -> [1,4] float32 output
  -> E84/FVP numerical comparison
```

## 8. 边界说明

### 8.1 数值一致不是位级一致

本报告证明的是：

```text
E84 与 FVP 的四个输出 float 在 1e-6 容差内一致。
```

本报告没有证明：

```text
E84 与 FVP 的输出 float bits 完全一致。
```

原因是 FVP 日志只打印六位小数 float 文本，没有打印完整 `uint32_t float_bits`。

### 8.2 37 ms 不是纯 NPU 时间

E84 日志：

```text
pre-call tick=9095
post-call tick=9132
```

差值 `37 ms` 是 `Method::execute()` 从调用前到返回后的端到端时间，包含 ExecuTorch Runtime、Ethos-U Backend、core driver、NPU 执行、IRQ 38、RT-Thread semaphore 唤醒和返回路径。它不是纯 Ethos-U55 NPU 计算时间。

正确表述：

```text
Method::execute() 端到端耗时 37 ms。
```

不要表述为：

```text
Ethos-U55 纯 NPU 延迟 37 ms。
```

### 8.3 模型和稳定性边界

- TinyCNN 使用固定随机权重，只用于部署链路验证。
- 当前输入是单一固定输入，不是真实数据集评测。
- 不声明真实任务准确率。
- 不声明生产级稳定性。
- 不声明通用生产级 RT-AK Backend 完成。

## 9. 最终状态

```text
PTE artifact validation: PASS
ExecuTorch Runtime init: PASS
Method load: PASS
Tensor binding: PASS
Ethos-U delegate execution: PASS
Ethos-U55 board inference: PASS
IRQ/RT-Thread semaphore return: PASS
E84 output collection: PASS
FVP output collection: PASS
Top-1 comparison: PASS
1e-6 numerical comparison: PASS
Float Bit-Exact: NOT_VERIFIED
Dataset accuracy: NOT_APPLICABLE
Production stability: NOT_VERIFIED

TINYCNN_E84_FVP_FINAL_COMPARE=PASS
```
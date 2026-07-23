# E84/FVP 最终数值对账复现

## 1. 验证目标

本验证用于确认同一份 TinyCNN ExecuTorch PTE 在两个路径上的输出是否自洽：

- PSoC Edge E84 CM55 + Ethos-U55 真板串口日志；
- Corstone-300 Ethos-U55 FVP runner 日志。

通过条件是：FVP 完整加载并执行 PTE，E84/FVP Top-1 一致，四个输出 float 的最大绝对误差不超过 `1e-6`。

## 2. 输入日志来源

| 日志 | 路径 | 来源 |
| --- | --- | --- |
| FVP 日志 | `tinycnn-executorch/tinycnn/reports/fvp_e84_final_compare.log` | 从 `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_e84_final_compare.log` 复制保存。 |
| E84 串口日志 | `tinycnn-executorch/tinycnn/reports/e84_first_inference_serial.log` | 从 `tinycnn-executorch/docs/12_first_inference_journey.md` 中保存的真实串口日志块提取。 |

E84 日志不是重新运行脚本生成的模拟数据，也不是手写的伪造输出；它来自首次真板推理文档里已经保存的真实串口记录。

## 3. 一键验证命令

在仓库根目录 `C:\tinycnn` 下运行：

```powershell
python tinycnn-executorch/scripts/validate_e84_fvp_output.py `
    --fvp-log tinycnn-executorch/tinycnn/reports/fvp_e84_final_compare.log `
    --e84-log tinycnn-executorch/tinycnn/reports/e84_first_inference_serial.log `
    --tolerance 1e-6
```

Bash/WSL 写法：

```bash
python tinycnn-executorch/scripts/validate_e84_fvp_output.py \
    --fvp-log tinycnn-executorch/tinycnn/reports/fvp_e84_final_compare.log \
    --e84-log tinycnn-executorch/tinycnn/reports/e84_first_inference_serial.log \
    --tolerance 1e-6
```

## 4. 预期关键输出

```text
pte_loaded=PASS
npu_delegate=PASS
program_complete=PASS
top1_match=PASS
output_match=PASS
max_abs_error=4.993568659e-07
TINYCNN_E84_FVP_FINAL_COMPARE=PASS
```

任何关键项为 `FAIL` 时，脚本退出码非 0。

## 5. 没有独立 E84 日志文件时

优先使用已保存的独立日志：

```text
tinycnn-executorch/tinycnn/reports/e84_first_inference_serial.log
```

如果该文件不存在，可以从以下文档的“本次成功时刻的真实串口日志”代码块提取原始串口内容：

```text
tinycnn-executorch/docs/12_first_inference_journey.md
```

提取后应只保存真实串口行，例如 `output0[i] float_bits=0x...`、`execute done status=0` 和 `[TinyCNN] inference PASS`。不得自行编造 E84 输出或补写没有出现在真实日志中的字段。

## 6. 结果边界

- 证明的是 E84/FVP 在 `1e-6` 容差内数值一致，不是 Float Bit-Exact。
- FVP 日志只打印六位小数 float 文本，没有完整 float bits。
- 当前输入是单一固定输入。
- TinyCNN 使用固定随机权重，不是真实任务分类模型。
- 本验证不是真实数据集准确率评估。
- 本验证不是生产级稳定性测试。
- E84 日志中的 `37 ms` 是 `Method::execute()` 端到端耗时，不是纯 NPU 延迟。

## 7. 复现依赖

当前 E84 BSP 的 SCons 工程会引用 WSL 中已构建好的 ExecuTorch/runner 静态库。默认兼容路径为：

```text
//wsl$/Ubuntu-22.04/home/zwb/work/ethosu_tinycnn
```

可通过环境变量覆盖：

```powershell
$env:EXECUTORCH_WS_ROOT='//wsl$/Ubuntu-22.04/home/zwb/work/ethosu_tinycnn'
```

GitHub 仓库本身未必包含完整 ExecuTorch 静态库。复现 E84 BSP 编译前，需要先在 WSL 侧构建 runner 和相关 `.a`，包括 `libexecutorch.a`、`libexecutorch_core.a`、`libexecutorch_delegate_ethos_u.a`、quantized/portable kernels 以及 `libethosu_core_driver.a`。
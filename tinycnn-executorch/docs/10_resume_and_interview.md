# Resume and Interview Material

## A. Project Name

基于 RT-AK 风格部署工具的 Cortex-M55 + Ethos-U55 TinyCNN ExecuTorch 验证系统

## B. Resume Project Description

围绕 Cortex-M55 + Ethos-U55 端侧 AI 部署，完成两阶段工程闭环。第一阶段在 `zwb725/tinycnn` 中完成自定义 TinyCNN 从 PyTorch、PT2E INT8、ExecuTorch、TOSA、Vela、PTE 到 Corstone-300 Ethos-U55 FVP 的开放编译链路，并补充 RT-AK 风格 PTE 打包原型。第二阶段在 `zwb725/tinycnn-edgi_talk` 中完成 PSoC Edge E84 BSP 集成、真实 ExecuTorch Runtime 生命周期、Ethos-U55 真板推理、IRQ/RT-Thread semaphore 返回路径，以及 E84/FVP 数值对账。

## C. Three-Bullet Version

- 完成自定义 TinyCNN 从 `torch.export`、PT2E INT8、Ethos-U/TOSA/Vela 到 ExecuTorch PTE 的部署链路，并在 Corstone-300 Ethos-U55 FVP 上验证 embedded-PTE 与 QSPI `--data` 两种加载模式。
- 设计 RT-AK 风格 ExecuTorch PTE 打包原型，支持 manifest、embedded C 数组、QSPI 资源、Kconfig/SConscript 和 pytest 覆盖；原仓库阶段 target runtime 曾是明确的 stub 边界。
- 在后续 `tinycnn-edgi_talk` 仓库完成 E84 BSP-specific ExecuTorch Runtime，真板串口输出 4 个 float bits，E84/FVP Top-1 均为 `1`，最大绝对误差 `4.993568659e-07`，通过 `1e-6` 数值一致性验收。

## D. Five-Bullet Version

- 构建自定义 TinyCNN，不依赖 ExecuTorch 官方示例模型；参数量 `23844`，输入 `(1,3,96,96)`，输出 `(1,4)`。
- 完成 PT2E INT8 量化与 Ethos-U 委托：固定测试输入下 FP32 与 INT8 Top-1 一致，最大绝对输出误差 `0.000249`；ExecuTorch 委托为 1 个 subgraph / 29 nodes，Vela 为 7 个 NPU ops / 0 CPU ops。
- 在 Corstone-300 Ethos-U55 FVP 验证 PTE 加载、NPU delegation 和输出向量，日志包含 `PTE Model data loaded. Size: 31696 bytes.`、`NPU delegations: 1` 和 `Program complete, exiting.`。
- 在 PSoC Edge E84 上接入真实 ExecuTorch Runtime 生命周期，跑通 `Program::load`、`load_method`、tensor binding、`Method::execute()`、IRQ 38 和 RT-Thread semaphore 返回路径。
- 增加 E84/FVP 自动对账脚本和报告，确认 Top-1 一致且 4 个输出在 `1e-6` 容差内数值一致；不声明 Float Bit-Exact、真实数据集准确率或生产级稳定性。

## E. One-Minute Interview Version

我做的是 Cortex-M55 + Ethos-U55 部署工程。先在 `tinycnn` 仓库里把自定义 TinyCNN 跑通到 PT2E INT8、TOSA、Vela、ExecuTorch PTE 和 Corstone-300 FVP，并做了 RT-AK 风格的 PTE 打包工具。这个阶段没有声称 E84 Runtime 已完成。后续在 `tinycnn-edgi_talk` 仓库里，我把同一类 PTE 接入 PSoC Edge E84 BSP，补齐真实 ExecuTorch Runtime 生命周期、Ethos-U55 delegate、IRQ 和 RT-Thread semaphore 返回路径，最终真板输出 4 个 float bits，并和 FVP 输出做了 `1e-6` 容差内数值对账。

## F. Common Questions

| Question | Answer |
| --- | --- |
| 为什么不用官方 MobileNet 示例？ | 目标是证明自定义模型链路，所以使用自己定义的 TinyCNN。 |
| 29 delegated nodes 和 7 NPU ops 为什么不同？ | 29 是 ExecuTorch EXIR 节点计数，7 是 Vela lower/fusion 后的 NPU operator 计数。 |
| 量化后准确率是否无损？ | 不能这么说。这里只能说固定测试输入下 FP32 与 INT8 Top-1 一致，最大绝对输出误差为 `0.000249`。 |
| FVP 周期能代表真板吗？ | 不能。FVP 日志和 PMU 计数是模拟器证据，不是 PSoC Edge E84 板级性能。 |
| ExecuTorch 是否已经跑在 E84？ | 是，后续 `tinycnn-edgi_talk` 阶段已经在 E84 BSP-specific runtime 中完成一次 TinyCNN 真板推理，并输出 float bits。原 `tinycnn` 阶段曾是未完成/stub 边界。 |
| E84 和 FVP 是否 bit-exact？ | 尚未证明。当前证明的是 `1e-6` 容差内数值一致，因为 FVP 日志只打印六位小数 float 文本。 |
| 37 ms 是 NPU 延迟吗？ | 不是纯 NPU 延迟。它是 `Method::execute()` 调用前到返回后的端到端时间。 |
| RT-AK 原型的价值是什么？ | 它把模型产物、元数据、加载方式和目标侧接口标准化；后续 E84 集成是在 BSP-specific 工程中完成的，不应夸大为通用生产级 RT-AK Backend。 |

## G. Statements Not To Use

- 不要写“TinyCNN 是真实手势识别模型”。
- 不要写“量化准确率无损”。
- 不要把 FVP 数据写成 PSoC Edge E84 真板性能。
- 不要把 `37 ms` 写成纯 NPU 延迟。
- 不要写“E84/FVP Float Bit-Exact 已验证”。
- 不要写“通用生产级 RT-AK Backend 已完成”。
- 不要写“生产级稳定性已验证”。

## H. Real Numbers You Can Use

- TinyCNN 参数量：`23844`。
- 输入/输出：`(1,3,96,96)` -> `(1,4)`。
- 固定测试输入：FP32 Top-1 `1`，INT8 Top-1 `1`，最大绝对输出误差 `0.000249`。
- Baseline PTE：`31696 bytes`。
- ExecuTorch Header：`ET12`。
- FNV-1a32：`0xdc0bdb6e`。
- SHA256：`5523dd345ee3b99dab80a454cb039f79d4484d3c19a4d1700332959d50b654c2`。
- ExecuTorch delegate：1 subgraph, 29 delegated nodes。
- Vela：7 NPU operators, 0 CPU operators。
- FVP 输出：`[-0.020373, 0.067080, -0.059627, 0.062111]`。
- E84 float bits：`0xbca6e43b`, `0x3d896156`, `0xbd743b44`, `0x3d7e6867`。
- E84 解码输出：`[-0.0203725006, 0.0670801848, -0.0596268326, 0.0621112846]`。
- E84/FVP Top-1：`1` / `1`。
- 最大绝对误差：`4.993568659e-07`。
- 验收阈值：`1e-6`。
- 最终结论：`TINYCNN_E84_FVP_FINAL_COMPARE=PASS`。

## I. Industrial Vision Algorithm Positioning

这个项目的价值不在于 TinyCNN 的识别精度，而在于把模型、量化、编译器、NPU delegate、FVP 验证、板端 BSP 集成、RTOS 同步、部署产物管理和证据报告串成可复现闭环。面试工业视觉算法岗位时，可以强调你理解算法模型落地时的算子选择、量化误差边界、NPU 支持范围、内存布局、启动调试、硬件/仿真对账和部署产物管理。
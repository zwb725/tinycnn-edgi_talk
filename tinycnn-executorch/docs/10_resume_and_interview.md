# Resume and Interview Material

## A. Project Name

基于RT-AK的Cortex-M55+Ethos-U55视觉模型多Runtime部署系统

## B. Resume Project Description

围绕 Cortex-M55 + Ethos-U55 端侧 AI 部署，完成两条互补链路：一条是真实 E84 应用链路中的 TFLM/DeepCraft/IMAI 模型部署与摄像头/LCD流程，另一条是自定义 TinyCNN 经 PyTorch、PT2E INT8、ExecuTorch、TOSA、Vela、PTE 到 Corstone-300 Ethos-U55 FVP 的开放编译链路。项目补充了 Vela 资源优化对比、FVP bring-up 问题定位、RT-AK 风格 ExecuTorch PTE 打包原型和完整工程文档。

## C. Three-Bullet Version

- 完成自定义 TinyCNN 从 PyTorch `torch.export`、PT2E INT8、Ethos-U/TOSA/Vela 到 ExecuTorch PTE 的部署闭环，并在 Corstone-300 Ethos-U55 FVP 上验证 embedded-PTE 与 QSPI `--data` 两种加载模式。
- 定位并修复 Cortex-M55 FPU/MVE 未启用、semihost inline asm clobber、FVP trace/retarget 等 bring-up 问题，形成可复现日志和验证报告。
- 设计 RT-AK 风格 ExecuTorch Backend 原型，支持 PTE manifest、embedded C 数组、QSPI 资源、Kconfig/SConscript、目标侧 stub 接口和 pytest 覆盖。

## D. Five-Bullet Version

- 构建自定义 TinyCNN，不依赖 ExecuTorch 官方示例模型；参数量 `23844`，输入 `(1,3,96,96)`，输出 `(1,4)`。
- 完成 PT2E INT8 量化与 Ethos-U 委托：固定测试输入下 FP32 与 INT8 Top-1 一致，最大绝对输出误差 `0.000249`；ExecuTorch 委托为 1 个 subgraph / 29 nodes，Vela 为 7 个 NPU ops / 0 CPU ops。
- 在 Corstone-300 Ethos-U55 FVP 验证 embedded-PTE 和 QSPI `--data` 两种运行方式，输出向量为 `[-0.020373, 0.067080, -0.059627, 0.062111]`，日志显示 `NPU delegations: 1` 和 `Program complete, exiting.`
- 对比 Vela Default、`--optimise=Size` 与 64x64 输入变体，形成 CSV 和报告；结论是 Size 降低 SRAM 但增加 PTE/PMU 计数，不夸大为无代价优化。
- 实现 RT-AK ExecuTorch PTE 打包原型与 13 个 pytest，用 manifest、SHA256、embedded 数组可逆校验和 QSPI 资源模式明确区分 PC 侧生成工具与未完成的 E84 Runtime 移植。

## E. One-Minute Interview Version

我做的是 Cortex-M55 + Ethos-U55 视觉模型部署工程。真实应用链路侧，我理解并整理了 E84 上的 TFLM/DeepCraft/IMAI 模型执行流程；开放工具链侧，我自己写了 TinyCNN，跑通 PyTorch 到 PT2E INT8、ExecuTorch、TOSA、Vela、PTE，再到 Corstone-300 Ethos-U55 FVP。过程中修了 M55 FPU/MVE 初始化和 semihost trace 问题，做了 Vela Size 优化对比，并补了一个 RT-AK 风格的 PTE 打包原型。需要强调的是，ExecuTorch 目前验证在 FVP，不是 E84 真板 Runtime 移植。

## F. Three-Minute Interview Expansion

这个项目拆成两部分。第一部分是部署闭环：自定义 TinyCNN 用固定随机权重，经过 `torch.export` 捕获图，再用 PT2E 做 INT8 量化，之后通过 Ethos-U partitioner 把可支持子图 lower 到 TOSA，再由 Vela 生成 Ethos-U55 命令流，最终保存为 ExecuTorch PTE。这个 PTE 被编进 Cortex-M55 runner，或者通过 QSPI `--data` 加载，在 Corstone-300 FVP 上运行。

第二部分是工程化和 RT-AK 原型。我没有声称已经把 ExecuTorch Runtime 移植到 E84，而是先做 PC 侧部署工具：校验 PTE、生成 manifest、生成 embedded C 数组或 QSPI 资源，再生成 Kconfig、SConscript 和目标侧 backend stub。stub 明确返回未实现错误，避免误导为能直接推理。

优化方面，我对比了 Vela Default 和 `--optimise=Size`。真实结果是 SRAM 从 78.203125 KiB 降到 54 KiB，但 PTE 从 31712 bytes 增加到 36432 bytes，FVP PMU 计数也上升，所以这是资源权衡，不是单向提升。

## G. Common Questions

| Question | Answer |
| --- | --- |
| 为什么不用官方 MobileNet 示例？ | 目标是证明自定义模型链路，所以使用自己定义的 TinyCNN。 |
| 29 delegated nodes 和 7 NPU ops 为什么不同？ | 29 是 ExecuTorch EXIR 节点计数，7 是 Vela lower/fusion 后的 NPU operator 计数。 |
| 量化后准确率是否无损？ | 不能这么说。这里只能说固定测试输入下 FP32 与 INT8 Top-1 一致，最大绝对输出误差为 0.000249。 |
| FVP 周期能代表真板吗？ | 不能。FVP 日志和 PMU 计数是模拟器证据，不是 PSoC Edge E84 板级性能。 |
| ExecuTorch 是否已经跑在 E84？ | 没有。当前 ExecuTorch Runtime 验证在 Corstone-300 FVP；E84 Runtime porting 是后续工作。 |
| RT-AK 原型的价值是什么？ | 它把模型产物、元数据、加载方式和目标侧接口标准化，为后续接入真实 Runtime 降低工程不确定性。 |

## H. Statements Not To Use

- 不要写“TinyCNN 是真实手势识别模型”。
- 不要写“量化准确率无损”。
- 不要写“ExecuTorch Runtime 已移植到 E84”。
- 不要把 FVP 数据写成 PSoC Edge E84 真板数据。
- 不要把 Linux wall-clock 时间写成 NPU 推理周期。

## I. Real Numbers You Can Use

- TinyCNN 参数量：`23844`。
- 输入/输出：`(1,3,96,96)` -> `(1,4)`。
- 固定测试输入：FP32 Top-1 `1`，INT8 Top-1 `1`，最大绝对输出误差 `0.000249`。
- Baseline PTE：`31696 bytes`。
- ExecuTorch delegate：1 subgraph, 29 delegated nodes。
- Vela：7 NPU operators, 0 CPU operators。
- Baseline FVP 输出：`[-0.020373, 0.067080, -0.059627, 0.062111]`。
- Vela Size：SRAM `78.203125 KiB -> 54 KiB`，PTE `31712 -> 36432 bytes`。
- RT-AK 原型 pytest：`13 passed`。

## J. Industrial Vision Algorithm Positioning

这个项目的价值不在于 TinyCNN 的识别精度，而在于你能把模型、量化、编译器、NPU delegate、裸机 runner、FVP 验证、资源报告和部署工具串成证据闭环。面试工业视觉算法岗位时，可以强调你理解算法模型落地时的算子选择、量化误差边界、NPU 支持范围、内存布局、启动调试和部署产物管理。

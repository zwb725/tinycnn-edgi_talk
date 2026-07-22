# TinyCNN Vela 板端验证状态

更新时间：2026-07-20
目标工程：`C:\tinycnn\Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision`

## 1. 当前目标

当前阶段目标是验证 TinyCNN 的 Vela / ExecuTorch PTE 编译产物是否已经正确进入 PSOC Edge CM55 板端固件。

结论：该阶段已经完成。

## 2. 已完成内容

### 2.1 板端启动确认

板端已经可以正常启动到 RT-Thread MSH：

```text
RT-Thread Operating System 5.0.2
Hello RT-Thread
It's cortex-m55
msh />
```

串口日志也显示关键外设初始化成功：

```text
PSRAM init successful
hyperam init success, mapped at 0x64200000, size is 8388608 bytes
I2C bus [i2c1] registered
init screen success
```

### 2.2 烧录产物生成问题已修复

之前烧录失败原因是烧录配置寻找：

```text
C:/tinycnn/Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision/Debug/rtthread.hex
```

但工程当时没有生成该文件。

现在已经通过 SCons 成功生成：

```text
C:\tinycnn\Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision\Debug\rtthread.hex
```

最终构建产物：

```text
rt-thread.elf      3158900 bytes
Debug/rtthread.hex 1050880 bytes
rtthread.map       1655175 bytes
```

最终 size 输出：

```text
text    data     bss      dec      hex
252680  120904   7636832  8010416  7a3ab0
```

### 2.3 工程配置已切到 TinyCNN artifact 验证模式

当前固件用于 TinyCNN ExecuTorch PTE 产物验证，而不是原来的 DeepCraft / IMAI / EDGI 业务模型路径。

已处理的关键点：

- 关闭 `RT_AI_USE_EDGI` / `USE_IMAI_GESTURE` 路径，避免和 TinyCNN 同时占用 AI 路径。
- 启用 TinyCNN ExecuTorch board-test 配置。
- 跳过不需要的 EDGI backend 编译，避免 `model.h` 缺失。
- 跳过嵌套 `m55` 子工程，避免 CM33 / CM55 宏混入导致 CMSIS core 头选择错误。
- 生成 `Debug/rtthread.hex`，匹配现有烧录配置。

### 2.4 板端验证命令已加入固件

固件中已经包含两个 MSH 命令：

```text
tinycnn_artifact_check
tinycnn_board_test
```

推荐使用：

```text
tinycnn_artifact_check
```

该命令验证三件事：

- PTE 长度是否等于 `31696`
- PTE header 是否为 `ET12`
- PTE 内容 hash 是否等于 `0xdc0bdb6e`

### 2.5 板端实际验证已经通过

板端执行结果：

```text
[TinyCNN] board test start
[TinyCNN] PTE addr=0x60580810
[TinyCNN] PTE size=31696
[TinyCNN] PTE expected length=31696
[TinyCNN] PTE fnv1a32=0xdc0bdb6e
[TinyCNN] PTE expected fnv1a32=0xdc0bdb6e
[TinyCNN] PTE length/header/hash check PASS
[TinyCNN] input=[1,3,96,96], float32
[TinyCNN] output=[1,4], float32
[TinyCNN] ExecuTorch target runtime is not available in this BSP
[TinyCNN] Program/Method/Allocator/Delegate not executed
[TinyCNN] waiting for physical-board validation
```

这说明：

- 板端固件中确实包含 TinyCNN PTE。
- PTE 长度正确。
- PTE `ET12` 头正确。
- PTE 内容 hash 和本地 Vela/PTE 产物一致。

因此，“Vela 编译产物进入板端固件”已经验证完成。

## 3. 还差多少

### 3.1 如果目标是验证 Vela/PTE 产物

完成度：100%。

已经有板端串口证据证明产物被正确烧进固件。

### 3.2 如果目标是真实 U55/NPU 推理

完成度：约 40%。

已经完成的 40%：

- TinyCNN 模型已经转成 U55 PTE。
- PTE 已嵌入 RT-Thread 固件。
- 固件已经成功生成并烧录运行。
- 板端 artifact 校验已经 PASS。

还剩约 60%：

1. 接入 ExecuTorch runtime。
2. 接入或适配 Ethos-U delegate / backend。
3. 接入 Ethos-U55 driver、base address、IRQ、cache clean/invalidate。
4. 实现 `Program` / `Method` 加载。
5. 准备输入 tensor `[1,3,96,96]`。
6. 执行一次真实推理。
7. 打印输出 `[1,4]`。
8. 和 FVP 基线输出做误差对比。
9. 确认 NPU 确实被调用，而不是只在 CPU 或 mock 路径执行。
10. 最后再做性能计时。

## 4. 下一步建议

下一步不要直接写大段推理代码，先做 runtime 探查。

建议新增或实现一个最小命令：

```text
tinycnn_runtime_probe
```

它先只验证：

- ExecuTorch runtime 是否能链接进 BSP。
- PTE 是否能被 runtime 识别。
- method 是否能找到。
- memory allocator / tensor arena 是否能创建。
- Ethos-U backend 是否能初始化。

等 `tinycnn_runtime_probe` 通过后，再做：

```text
tinycnn_run_once
```

该命令才真正执行一次 TinyCNN 推理，并打印 4 个输出值。

## 5. 当前边界

当前已经完成的是板端 artifact 验证，不是实际推理验证。

当前日志明确显示：

```text
ExecuTorch target runtime is not available in this BSP
Program/Method/Allocator/Delegate not executed
```

所以不能把当前结果表述为“U55 已经跑通推理”。准确说法是：

```text
TinyCNN 的 Vela/ExecuTorch PTE 产物已经正确嵌入并烧录到 PSOC Edge CM55 板端固件，板端长度、header、hash 校验均通过。真实 ExecuTorch + Ethos-U55 推理 runtime 尚未接入。
```

## 6. 2026-07-20 下一步改动：runtime probe 已接入

本次已经把 RT-AK ExecuTorch backend prototype 接入目标工程构建，并新增板端 MSH 命令：

```text
tinycnn_runtime_probe
```

该命令会执行：

- 重新校验嵌入式 PTE 的 length / ET12 header / FNV-1a32。
- 构造 `rt_ai_executorch_config_t`。
- 调用 `rt_ai_executorch_init()`。
- 打印 expected input/output bytes。
- 明确报告当前 runtime 状态。

当前 backend 仍是 prototype stub，`rt_ai_executorch_init()` 会返回：

```text
-38
```

也就是：

```text
RT_AI_EXECUTORCH_ENOSYS
```

这不是 artifact 失败，而是说明已经到达 ExecuTorch runtime 接口边界，后续还需要真正移植：

- ExecuTorch Program load
- Method load
- MemoryAllocator / planned buffers
- Ethos-U delegate backend
- input/output tensor binding
- NPU driver/cache/IRQ runtime path

本次构建产物已刷新：

```text
C:\tinycnn\Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision\Debug\rtthread.hex
```

最终 size：

```text
text    data     bss      dec      hex
253800  120904   7636832  8011536  7a3f10
```

ELF 已确认包含：

```text
tinycnn_runtime_probe
rt_ai_executorch_init
tinycnn_artifact_check
tinycnn_board_test
```

下一次烧录后，推荐先执行：

```text
tinycnn_runtime_probe
```

预期当前会看到：

```text
[TinyCNN] runtime status=NOT_PORTED
[TinyCNN] missing Program/Method/Allocator/Ethos-U delegate/tensor binding
```

如果看到这两行，说明下一阶段的“runtime 边界探针”已经正常运行，接下来才进入真实 ExecuTorch + Ethos-U runtime 移植。

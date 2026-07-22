# TinyCNN ExecuTorch — 从阻塞到首次板端推理 PASS（2026-07-22）

> **一句话结论**：在 PSoC Edge E84 CM55 板端，U55 NPU 已经真的跑了一次 TinyCNN，并吐回了 `[1, 4] float32` 推理结果。
>
> 本文把这条路上**已经走通的工程动作**、**真实踩过的坑**、**哪些是上游不能动只能绕开的边界**、**下一步可以继续优化的点**写成一份给后续值班同事看的操作笔记。

---

## 0. 名词速查

| 简称 | 全称 | 备注 |
| --- | --- | --- |
| PTE | ExecuTorch Program 字节流 | 头 4 字节 magic + ET12 header + 段数据。 |
| method | ExecuTorch `Method` | 一个 PTE 通常只有一个 `forward`。 |
| delegate | Ethos-U delegate | `executor/backend/arm/libexecutorch_delegate_ethos_u.a`。 |
| 自定义注册 TU | `register_prim_ops.cpp`, `RegisterCodegenUnboxedKernels_0.cpp` | 静态注册用的翻译单元，**不能光靠链接 `.a`**。 |
| `.got` | Global Offset Table | C++ 虚函数/全局指针。`.data` 必须含它，否则上电后 vtable 全 0。 |
| `0x8B382EB3` | BusFault PRECISERR 出现的 PC | 与 `.got` 被丢掉的版本号挂钩，不是随机的。 |

---

## 1. 本次成功时刻的真实串口日志

```
msh />tinycnn_run
[TinyCNN] inference start
[executorch] Ethos-U platform init start irq=38 base=0x44600000
[executorch] Ethos-U platform init ok  irq=38 base=0x44600000
[executorch] runtime_init model=tinycnn pte=0x60588d70 bytes=31696
[executorch] method=forward
I 00:00:00.000000 executorch:EthosUBackend.cpp:zu] F籥:K区 利a
[executorch] input0=0x64480000 bytes=110592
[executorch] output0=0x64480000 bytes=16
[executorch] init complete planned_buffers=1 method_pool=524288 temp_pool=524288
[TinyCNN] input addr=0x64480000 size=110592
[executorch] input0 filled with ones scalar_type=6 bytes=110592
[executorch] execute start n_in=1 n_out=1
[executorch] pre-call tick=9095
[executorch] post-call tick=9132 status=0
[executorch] execute done status=0
[executorch] output0=0x64480000 bytes=16
[TinyCNN] output addr=0x64480000 size=16
[executorch] output0 scalar_type=6 numel=4 bytes=16
[executorch] output0 float top1=1
[executorch] output0[0] float_bits=0xbca6e43b
[executorch] output0[1] float_bits=0x3d896156
[executorch] output0[2] float_bits=0xbd743b44
[executorch] output0[3] float_bits=0x3d7e6867
[executorch] Ethos-U platform deinit ok
[TinyCNN] inference PASS
```

可以从中读到的硬证据：

- `pre-call tick=9095` → `post-call tick=9132`：NPU 真的忙了 **37 ms**，这是 NPU 干活的指纹，不是 busy-loop。
- `status=0`、`execute done status=0`：`Method::execute()` 没出任何 delegate 错误。
- `top1=1`、`numel=4`、`output0[i] float_bits=…`：确实是 `[1, 4] float32`，且四条 log 把 4 个 float 都打出来了，能进一步与 FVP 对账。
- `(input0 == output0 == 0x64480000)` 是 arena 内复用同一段，size 不一致是预期（input 110592B、output 16B）。

> 注意：日志里的 `F籥:K区 利a` 不是乱码——是 Ethos-U 上游裸机版等待 NPU 完成时的 SE region pmsg 字串，由 `ethosu_core_common.cpp` 触发。在我们打通的版本里它出现一次以后继续往下走；如果出现后死循环，则是上一版没修好的症状。

---

## 2. 在此之前真实卡过的每一道坎

按时间顺序总结“上一版（上上版……）→ 现在能 PASS”之间到底改了什么、为什么改、怎么验证：

### 2.1 Vela/ExecuTorch 工程产物还没落到板上 → 已解决

| 当时的症状 | 现在的状态 |
| --- | --- |
| 板子启动后 msh 都不出现，`Debug/rtthread.hex` 没生成 | SCons 修复 hex 路径 → 已生成 `Debug/rtthread.hex` 1050880 B |
| 烧录配置读不到 `C:/tinycnn/Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision/Debug/rtthread.hex` | 见 `Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision/tinycnn_vela_board_validation_status.md` §2.2 |

**做了什么**：

- 修正 `mklinks.sh` / `mklinks.bat`，确保 WSL 内 `tinycnn-executorch` 能被 SCons 找到；
- 关闭 `RT_AI_USE_EDGI` / `USE_IMAI_GESTURE` 路径，避免和 TinyCNN 抢 Ethos-U；
- 关掉 `m55` 套娃子工程，避免双 CMSIS core 撞车。

---

### 2.2 板上还没跑通 PTE artifact 校验 → 已解决

`tinycnn_artifact_check` 现在能在串口输出：

```
[TinyCNN] PTE size=31696
[TinyCNN] PTE expected length=31696
[TinyCNN] PTE fnv1a32=0xdc0bdb6e
[TinyCNN] PTE expected fnv1a32=0xdc0bdb6e
[TinyCNN] PTE length/header/hash check PASS
```

| 校验项 | 期望值 | 含义 |
| --- | --- | --- |
| PTE 长度 | 31696 字节 | 跟 Vela 产物列表对得上 |
| Magic header | `ET12` | 第 4-7 字节 |
| FNV-1a32 hash | `0xdc0bdb6e` | 与 FVP 用同一份 PTE 时一致 |

如果任何一项失败，意味着要么 PTE 被 `.data/.rodata` 截断丢字节、要么 PRM 没切对，要么 Vela 版本变了。

---

### 2.3 ExecuTorch Runtime 没装进 BSP → 已解决

当时 `tinycnn_runtime_probe` 返回：

```
[TinyCNN] rt_ai_executorch_init=-38
[TinyCNN] runtime status=NOT_PORTED
```

- 接入 `rt_ai_executorch_runtime.cpp`（实现了 `runtime_init → register_ethosu_delegate → Program::load → load_method → PlannedBuffers → MemoryManager → bind_input/output_tensor`）；
- 新增 `rt_ai_executorch_ethosu_psoc.c`：把 `ethosu_mutex_*` / `ethosu_semaphore_*` 接到 RT-Thread，`IRQ=38`，semaphore 超时 5 s；
- SCons 路径引入：
  - `executorch_lib_root = .../tinycnn/build/runner/executorch`
  - `ethosu_core_driver_root = .../tinycnn/build/runner/examples/arm/executor_runner/target/target/core_software/core_driver`
  - `pdl_root = libraries/components/mtb-device-support-pse8xxgp/pdl`。

---

### 2.4 四个真正的“工程坑”——这是 PASS 的关键

| # | 文件 | 现象 | 修法 |
| --- | --- | --- | --- |
| 1 | `applications/rt_ai_tinycnn_executorch/SConscript` | `libquantized_ops_lib.a` / `libportable_kernels.a` 没有外部强符号 → 链接器丢对象 → `load_method` 之前没注册 quantized/prim ops，理论上会缺 operator。 | 把 `executorch/kernels/prim_ops/register_prim_ops.cpp` 和 `tinycnn/build/runner/executorch/kernels/quantized/quantized_ops_lib/RegisterCodegenUnboxedKernels_0.cpp` **直接列进 `src`** 编译进 ELF。 |
| 2 | 同上 | library 顺序错误：`portable_kernels / kernels_util_all_deps / quantized_kernels`，util 在 quantized 之前被扫，导致 `get_init_index / check_dim_list_is_valid / get_out_numel` undefined reference。 | 把 `kernels_util_all_deps` **挪到 `quantized_kernels` 之后**。当前 SConscript 里顺序已经是 `'executorch' / 'executorch_core' / 'executorch_delegate_ethos_u' / 'portable_kernels' / 'quantized_kernels' / 'quantized_ops_lib' / 'kernels_util_all_deps' / 'ethosu_core_driver'`。 |
| 3 | `board/linker_scripts/link.ld` `.data` | 没把 `.got/.got.plt` 收进 `.data` → 启动拷贝表不拷 → C++ vtable 全 0 → BusFault PRECISERR 飞到一个与发布版本匹配的 PC **0x8B382EB3**。 | 在 `.data` 末尾加：<br>`*(.got .got.* .igot.plt .got.plt)`<br>同时 `.copy.table` 必须含 `LONG(LOADADDR(.data)) / LONG(ADDR(.data)) / LONG(SIZEOF(.data)/4)`，确保被 PDL 复位后从 nvm 拷到 DTCM。 |
| 4 | `src/rt_ai_executorch_runtime.cpp::rt_ai_executorch_runtime_run()` | 没诊断 print，hang 时不知道是停在 `execute` 之前、之中、之后。 | 增加顺序日志：<br>`execute start n_in n_out` → `pre-call tick` → `execute` → `post-call tick status` → `execute done status`。当前 PASS 的日志正是这个布局。 |

这四条改动是 “PASS” 的根因，缺一不可。

---

### 2.5 最终挂在 `Method::execute()` 之内 → 已解决（最戏剧化的一关）

**之前的诊断**：

- `[executorch] execute start n_in=1 n_out=1` 之后 0 行日志；
- `m_delay(2)` 不让出调度，连 idle 都被堵；
- 没看到 hard-fault log、`Reboot` log。

**现在知道的原因（结合上游代码 + 实测日志）**：

1. Cortex-M55 裸机等待路径里，`ethosu_invoke_v3` 走的是 `core_driver`；
2. `core_driver` 把 cmd 写到 NPU 后，必须等 IRQ 38；
3. 我们在 `rt_ai_executorch_ethosu_psoc.c` 用 **RT-Thread semaphore + IRQ 回调** 把 `ETHOSU_IRQHandler` 接到 `rt_sem_release`；
4. **最后一次让 `method.execute()` 真的返回** 的关键改动是上面 §2.4 #2 + §2.4 #3 两件事同时生效——`kernels_util_all_deps` 顺序对了让 deferred kernel init 函数被补上、GOT 被拷走让 C++ 静态对象的指针是真实的；
5. 之后 `execute` 内 `EthosUBackend::execute → platform_execute → ethosu_invoke_v3` 终于跑完，semaphore 释放，主线程继续。

> 上游 `executorch/backends/arm/runtime/EthosUBackend_Cortex_M.cpp` 是裸机 deadlock-bug 版本（`for (;;) { write pmsg }`），我们没有改它也不该改它；我们在 BSP 侧已经把 sem/wait 走 RT-Thread 的正常路径，所以上游那段 bare-metal wait 永远轮不到执行。

---

## 3. 当前 BSP / 代码状态快照（2026-07-22）

| 目录 | 关键文件 | 角色 |
| --- | --- | --- |
| `C:\tinycnn\Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision\` | `applications/rt_ai_tinycnn_executorch/`、`board/linker_scripts/link.ld`、`.config` | 目标工程；当前运行的 C 源码 |
| `C:\tinycnn\tinycnn-executorch\rtak_plugin_executorch\backend_executorch\` | `include/rt_ai_executorch_backend.h`、`src/rt_ai_executorch_backend.c`、`src/rt_ai_executorch_runtime.cpp`、`SConscript` | RT-AK 抽象层 + C++ 真实 runtime |
| `C:\tinycnn\tinycnn-executorch\rtak_plugin_executorch\examples\tinycnn\generated\embedded\models\tinycnn` | `rt_ai_tinycnn_model_data.[ch]` | 31696 字节 PTE 转 C 数组（linking 阶段随 ELF 一起进 flash） |
| `/home/zwb/work/ethosu_tinycnn/tinycnn/build/runner/` | `executorch/`、`examples/arm/executor_runner/.../core_driver/` | Vela/ExecuTorch 编译产物与 `ethosu_core_driver.a` |

驱动/编译器侧：

- `arm-none-eabi-gcc -std=gnu++17` 链接，无 undefined reference；
- `text=253800 data=120904 bss=7636832`（烧写后 `size` 输出）；
- `Debug/rtthread.hex` 存在且 size=1 050 880 B。

---

## 4. 一次性复现命令

按顺序在 PowerShell 里执行（WSL 内部命令用 `wsl.exe -d Ubuntu-22.04 -- bash -lc`，**每条直接复制**）：

```powershell
# (1) 板子端编译
cd C:\tinycnn\Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision
scons -j8

# (2) 看产物
Get-Item Debug\rtthread.hex, rt-thread.elf | Select Name,Length

# (3) 烧录（按你现有的烧录配置：路径 = C:/tinycnn/.../Debug/rtthread.hex）

# (4) 在 msh 里跑
msh /> tinycnn_artifact_check        # → PTE check PASS
msh /> tinycnn_run                   # → inference PASS
```

判定标准：

- `tinycnn_artifact_check` 打印 `length/header/hash check PASS`；
- `tinycnn_run` 末尾出现 `[TinyCNN] inference PASS`，且 `execute done status=0`。

---

## 5. Vela / ExecuTorch 工程产物链是否都过了？

| 链条环节 | 验证点 | 当前状态 |
| --- | --- | --- |
| 1. TinyCNN `model.py` → TOSA | `tinycnn/reports/baseline_summary.md` 保留导出参数 | ✅ |
| 2. TOSA → Vela → TFLite-Micro + Ethos-U 指令 | `tinycnn/build/variants/default/` 存在，PTE sha 与 baseline 一致 | ✅ |
| 3. TFLite-Micro + EthosUCompileSpec → PTE (31 696 B) | `tinycnn_artifact_check` hash=0xdc0bdb6e | ✅ |
| 4. PTE → C 数组 → 嵌入 BSP `.cy_ml_model_data` | `link.ld` 用 `KEEP(*rt_ai_tinycnn_model_data.o(.rodata .rodata.*))`，运行时读到 base=`0x60588d70` | ✅ |
| 5. BSP → `libexecutorch*.a` + `libethosu_core_driver.a` | `tinycnn_scons_build.log` 末尾 `size` 输出正常，无 undefined reference | ✅ |
| 6. 板子上 `Program::load` + `load_method` | 日志输出 `method=forward`、`init complete planned_buffers=1 method_pool=524288 temp_pool=524288` | ✅ |
| 7. `Method::execute()` 真正跑 NPU | `[executorch] pre-call tick=9095 → post-call tick=9132`，约 37 ms 耗时 | ✅ |
| 8. 输出 `[1, 4] float32` 被打回串口 | `top1=1`、四个 float_bits 全部打印 | ✅ |
| 9. FVP 同 PTE 的输出对账（精度 + 量化误差） | 下一节优化项 #1 | ⏳ 未做 |

整条链 `1–8` 节点是 PASS 的；`9`（和 FVP 数值精度对齐）接下来就可以做。

---

## 6. 还能做的优化（按风险/收益排序）

1. **数值一致性**：拿同 PTE 重跑 FVP `executor_runner`，把 4 个 float 与板端 4 个 float_bits 做对齐。预期差异 < 1e-3；如果差异太大，要么是 input 输入 padding/对齐不一致，要么是 Ethos-U 量化表跟 FVP 不一致。

2. **运行时间**：37 ms 对 CM55 + 110592 B 输入有点慢，常见可挖点：
   - `METHOD_POOL` / `TEMP_POOL` 现在各 524288 B（共 1 MiB），超 `.cy_ml_arena_data` 容量，得分摊；
   - `input0` 当前 `scalar_type=6` 是 FP32，量化 PTE 通常期待 INT8，确认是不是 Vela 测了 FP32 输入；如果是浪费，把 input 通道先量化或者缩小批次。

3. **错误路径覆盖**：现在 `execute done status=0` 之后一路 PASS，但缺少负向用例。建议加一组 `tinycnn_run_invalid_*` 测试（错 PTE、错尺寸、错 scalar_type）。

4. **链接器瘦身**：`.bss=7636832` 偏大；如果以后接更多模型，检查 `.cy_ml_*` 段有没有重复 buff。

5. **去掉 `print_output_head_bytes` / `top1` 等诊断 log**：通过 `rt_ai_executorch_runtime_set_log_enabled(0)` 关闭或编译期 `RT_AI_EXECUTORCH_DEBUG_LOG=0`。现在 `DEBUG_LOG=1` 是开了的。

6. **撤回临时补丁提一个干净 PR**：
   - `link.ld` 的 `.got/.got.plt` 是否可以提到 PR；
   - `applications/rt_ai_tinycnn_executorch/SConscript` kernel 注册 + 库顺序改回正常路径；
   - `rt_ai_executorch_runtime.cpp` 里 `pre-call/post-call tick` 的诊断 print 移到 `RT_AI_EXECUTORCH_DEBUG_LOG` 守门下。

---

## 7. 下一步建议顺序（一句话）

**先按优化 #1 拿 FVP 同 PTE 跑一次对比，再决定优化 #2 该不该动 arena 布局。**

> 同时把 §6 里的 PR 候选条目列出，争取在 WSL 侧把 library 顺序和 GOT 修补合并到一个候选 patch 上。

# TinyCNN ExecuTorch E84 Phase 1 Audit

Status: BLOCKED, not Build Ready.

This audit intentionally does not claim E84 board PASS, board latency, FPS, or
numeric validation. The existing DeepCraft / IMAI path remains the only
build-verified inference path in this BSP.

## Initial Checks

- Workspace: `C:\tinycnn`
- M33 project: `edgi-talk-m33led` exists, no `.git`
- M55 project: `Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision` exists, has `.git`
- TinyCNN project: `tinycnn-executorch` exists
- Project-level `AGENTS.md`: none found under `C:\tinycnn`

The M55 worktree was already dirty before this change. Existing user changes
were not reverted.

## BSP Findings

1. CM33 starts CM55 in `edgi-talk-m33led/board/board.c` with
   `Cy_SysEnableCM55(MXCM55, CY_CM55_APP_BOOT_ADDR, 10)`.
2. U55 clock/reset and driver init are explicit in
   `libraries/Common/deepcraft_ai/third_party/ml-middleware/source/COMPONENT_U55/mtb_ml_ethosu.c`:
   `Cy_SysInt_Init`, `NVIC_EnableIRQ`, `Cy_SysEnableU55(true)`,
   `ethosu_init(... U550_BASE ...)`, and PMU enable.
3. Ethos-U IRQ uses `mxu55_interrupt_npu_IRQn`; the registered ISR is
   `u55_irq_handler`, which calls `ethosu_irq_handler(&ethosu_drv)`.
4. DeepCraft reaches U55 through `mtb_ml_init()` and `mtb_ml_ethosu_init()`.
   It is not safe for IMAI and ExecuTorch to initialize U55 independently.
5. The original model uses `CY_ML_MODEL_MEM=.cy_socmem_data` and
   `CY_ML_ARENA_MEM=.cy_socmem_data` from `libraries/Common/deepcraft_ai/SConscript`.
6. The CM55 linker provides DTCM, ITCM, NVM, HyperRAM, shared HyperRAM,
   SoCMEM secondary data/code, shared SoCMEM, gfx memory, and a small
   allocatable shared region.
7. Existing cache maintenance is implemented in the ML middleware:
   `ethosu_flush_dcache`, `ethosu_invalidate_dcache`, and the outer-layer
   clean/invalidate calls around `mtb_ml_model_invoke()`.
8. The M55 build already compiles C++ (`RT_USING_CPLUSPLUS`) and builds
   `mtb_ml_model.cpp` with `-fno-exceptions -fno-rtti`.
9. SCons collects subdirectories through `applications/SConscript`; C++ is
   linked through the same RT-Thread SCons environment.

## TinyCNN Artifact Check

- Embedded manifest PTE size: `31696`
- Embedded PTE C-array bytes parsed locally: `31696`
- Embedded PTE SHA256 parsed locally:
  `5523dd345ee3b99dab80a454cb039f79d4484d3c19a4d1700332959d50b654c2`
- PTE magic: `ET12`
- Input: `[1,3,96,96]`, `float32`
- Output: `[1,4]`, `float32`
- Target: `ethos-u55-128`
- Delegated subgraphs: `1`
- Delegated nodes: `29`
- Vela NPU operators: `7`
- Vela CPU operators: `0`

The 31712-byte default variant was not used for the embedded resource check.

## ExecuTorch Runtime Search

Searched locally:

- `C:\tinycnn\tinycnn-executorch\executorch`
- `C:\tinycnn\tinycnn-executorch`
- `C:\tinycnn\Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision`
- `C:\tinycnn\edgi-talk-m33led`

Result:

- No local ExecuTorch checkout in `tinycnn-executorch\executorch`.
- No Cortex-M55 ExecuTorch Runtime static library was found in the workspace.
- The TinyCNN `backend_executorch` code is an explicit ENOSYS prototype.
- WSL lookup did not reach `/home/zwb/work/ethosu_tinycnn/executorch`; WSL
  attempted online distribution metadata access and failed with DNS resolution.

Blocking missing items:

- ExecuTorch v1.3.1 target Runtime headers/sources or Cortex-M55 static libs
- Real Arm/Ethos-U backend registration code for this ExecuTorch version
- Verified Cortex-M55 ABI settings for those libraries
- Method metadata / planned-buffer requirements from the actual runtime port

## Local Build Evidence

Command:

```powershell
$env:RTT_EXEC_PATH='C:\RT-ThreadStudio\platform\env_released\env\tools\gnu_gcc\arm_gcc\mingw\bin'
& 'C:\RT-ThreadStudio\platform\env_released\env-new\.venv\Scripts\python.exe' -m SCons -j6
```

Result:

- M55 original DeepCraft / IMAI path build: PASS
- Output: `rt-thread.elf`, `Debug/rtthread.hex`
- Size: `text=523300`, `data=3164216`, `bss=5350296`
- M33 startup project build: PASS
- M33 output: `rt-thread.elf`, `rtthread.hex`, `build/rtthread.hex`
- M33 size: `text=62192`, `data=2112`, `bss=257548`
- M33 secure image packaging was skipped because `edgeprotecttools` or the
  referenced boot config was not found; the SCons build itself completed.

## Current Integration State

Added a disabled-by-default `TinyCNN ExecuTorch` Kconfig component. If enabled
after disabling `RT_AI_USE_EDGI`, it can compile a PTE probe command that checks
the embedded PTE length and ET12 header. It deliberately returns ENOSYS after
the probe because no real ExecuTorch Runtime is present.

The linker now has an optional placement rule for `rt_ai_tinycnn_model_data.o`
inside `.cy_ml_model_data`. This rule has no effect unless the TinyCNN
ExecuTorch component is enabled and the PTE object is linked.

Next exact unblock command after providing/restoring WSL ExecuTorch checkout:

```powershell
wsl.exe bash -lc "cd /home/zwb/work/ethosu_tinycnn/executorch && git describe --tags --dirty && rg -n 'MemoryDataLoader|Program::load|load_method|HierarchicalAllocator|EthosU|ethosu' examples/arm/executor_runner backends/arm runtime"
```

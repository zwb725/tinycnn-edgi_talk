# TinyCNN Ethos-U55 FVP Validation Report

## Scope

- Model: custom `tinycnn.model.TinyCNN`, not an ExecuTorch example model.
- Export path: ExecuTorch EXIR -> TOSA -> Vela -> Ethos-U55 delegate -> `.pte`.
- Target: `ethos-u55-128`, `Ethos_U55_High_End_Embedded`, `Shared_Sram`.
- FVP: `FVP_Corstone_SSE-300_Ethos-U55`.

## Export Result

- PTE: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte`
- PTE size: `31696` bytes
- Input shape: `(1, 3, 96, 96)`
- Output shape: `(1, 4)`
- FP32 Top-1: `1`
- PT2E INT8 Top-1: `1`
- Max absolute FP32 vs PT2E error: `0.00024946779012680054`
- Delegated subgraphs: `1`
- Delegated nodes: `29`
- Non-delegated EXIR boundary nodes: `3`
- Vela delegated network summary from export: `CPU operators = 0`, `NPU operators = 7`

## Runner Builds

### Embedded PTE Runner

Command:

```bash
source ../.venv/bin/activate
source examples/arm/arm-scratch/setup_path.sh
./backends/arm/scripts/build_executor_runner.sh   --pte=/home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte   --target=ethos-u55-128   --build_type=Release   --system_config=Ethos_U55_High_End_Embedded   --memory_mode=Shared_Sram   --output=/home/zwb/work/ethosu_tinycnn/tinycnn/build/runner   --extra_build_flags="-DEXECUTORCH_BUILD_CORTEX_M=OFF -DCMSIS_VER=5 -DCMSIS_PATH=/home/zwb/work/ethosu_tinycnn/executorch/examples/arm/arm-scratch/ethos-u/core_software/cmsis -DTINYCNN_FVP_SEMIHOSTING=ON -DTINYCNN_FVP_TRACE_SETUP=ON -DTINYCNN_FVP_TRACE_RUNNER=ON"
```

Artifact: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/runner/arm_executor_runner`

`arm-none-eabi-size`:

```text
text=373340 data=65046804 bss=25832 dec=65445976
```

### QSPI Address PTE Runner

Command:

```bash
source ../.venv/bin/activate
source examples/arm/arm-scratch/setup_path.sh
./backends/arm/scripts/build_executor_runner.sh   --pte=0x38000000   --target=ethos-u55-128   --build_type=Release   --system_config=Ethos_U55_High_End_Embedded   --memory_mode=Shared_Sram   --output=/home/zwb/work/ethosu_tinycnn/tinycnn/build/runner_qspi   --extra_build_flags="-DEXECUTORCH_BUILD_CORTEX_M=OFF -DCMSIS_VER=5 -DCMSIS_PATH=/home/zwb/work/ethosu_tinycnn/executorch/examples/arm/arm-scratch/ethos-u/core_software/cmsis -DTINYCNN_FVP_SEMIHOSTING=ON -DTINYCNN_FVP_TRACE_SETUP=ON -DTINYCNN_FVP_TRACE_RUNNER=ON"
```

Artifact: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/runner_qspi/arm_executor_runner`

`arm-none-eabi-size`:

```text
text=343568 data=65015024 bss=25828 dec=65384420
```

## FVP Validation

### Embedded PTE

Command:

```bash
source .venv/bin/activate
source executorch/examples/arm/arm-scratch/setup_path.sh
FVP_Corstone_SSE-300_Ethos-U55   -C ethosu.num_macs=128   -C mps3_board.visualisation.disable-visualisation=1   -C mps3_board.telnetterminal0.start_telnet=0   -C mps3_board.uart0.out_file="-"   -C mps3_board.uart0.shutdown_on_eot=1   -C cpu0.semihosting-enable=1   -a /home/zwb/work/ethosu_tinycnn/tinycnn/build/runner/arm_executor_runner   --timelimit 120
```

Result: `PASS`

Evidence from `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_embedded.log`:

- `PTE @ 0x73e00000 [----ET12]`
- `PTE Model data loaded. Size: 31696 bytes.`
- `NPU delegations: 1 (1.00 per inference)`
- `ethos-u : cycle_cnt : 18301 cycles (18301.00 per inference)`
- `ethosu_pmu_cycle_cntr : 247553 (247553.00 per inference)`
- Output: `[-0.020373, 0.067080, -0.059627, 0.062111]`
- `Program complete, exiting.`

### QSPI Address PTE

Command:

```bash
source .venv/bin/activate
source executorch/examples/arm/arm-scratch/setup_path.sh
FVP_Corstone_SSE-300_Ethos-U55   -C ethosu.num_macs=128   -C mps3_board.visualisation.disable-visualisation=1   -C mps3_board.telnetterminal0.start_telnet=0   -C mps3_board.uart0.out_file="-"   -C mps3_board.uart0.shutdown_on_eot=1   -C cpu0.semihosting-enable=1   -a /home/zwb/work/ethosu_tinycnn/tinycnn/build/runner_qspi/arm_executor_runner   --data /home/zwb/work/ethosu_tinycnn/tinycnn/build/tinycnn_u55.pte@0x38000000   --timelimit 120
```

Result: `PASS`

Evidence from `/home/zwb/work/ethosu_tinycnn/tinycnn/build/fvp_qspi.log`:

- `PTE @ 0x38000000 [----ET12]`
- `NPU delegations: 1 (1.00 per inference)`
- `ethos-u : cycle_cnt : 18028 cycles (18028.00 per inference)`
- `ethosu_pmu_cycle_cntr : 247550 (247550.00 per inference)`
- Output: `[-0.020373, 0.067080, -0.059627, 0.062111]`
- `Program complete, exiting.`

## Fixes Required For FVP

- Enabled FPU/MVE coprocessor access in `SystemInit`; GCC emits MVE/FPU-register instructions for Cortex-M55 and the FVP otherwise faults before runner setup completes.
- Relocated the vector table to writable RAM before `NVIC_SetVector` paths run.
- Added guarded direct semihost trace output for target setup and runner validation.
- Fixed the semihost trace inline assembly to mark `r0` as an in/out register; without this, repeated `bkpt 0xAB` calls can reuse a clobbered semihost operation code.
- Added an FVP semihost-compatible retarget path for stdout/stderr and exit.
- Disabled the unavailable Cortex-M/CMSIS-NN dependency path for this build because GitHub dependency fetches timed out in this environment.

## Caveats

- FVP CPU cycle ratios are simulator guidance only; the runner itself prints the same warning that CPU cycle values require FPGA and identical CPU/NPU frequency.
- The linker still emits existing warnings about `.data`, `.sram.data`, `.rodata` segment allocation and RWX LOAD permissions. Both validated ELFs execute correctly under FVP, but the linker script should be cleaned before treating this as production firmware layout.
- The QSPI-address runner reports `model_pte_program_size` as `268435456` bytes because `ET_MODEL_PTE_ADDR` mode does not know the exact PTE length at compile time. The embedded-PTE runner reports the exact `31696` bytes.

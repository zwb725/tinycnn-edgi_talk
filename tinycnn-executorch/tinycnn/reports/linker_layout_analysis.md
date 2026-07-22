# TinyCNN Runner Linker Layout Analysis

## Scope

This report analyzes the existing linker warnings for the Cortex-M55 / Ethos-U55 FVP runner. It does not claim a production firmware memory layout. No linker script cleanup experiment was retained because the warning source spans PHDR grouping, VMA/LMA placement, executable code placement, and DDR permissions; changing that safely is larger than a minimal reversible patch.

## Linker Script Path

The runner CMake selects the Corstone-300 script when `SYSTEM_CONFIG` contains `U55`:

- Input script: `/home/zwb/work/ethosu_tinycnn/executorch/examples/arm/executor_runner/Corstone-300.ld`
- Generated script used by the default variant build: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/default/runner/examples/arm/executor_runner/platform.ld`
- Map file: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/default/runner/examples/arm/executor_runner/arm_executor_runner.map`
- Example analyzed ELF: `/home/zwb/work/ethosu_tinycnn/tinycnn/build/variants/default/runner/arm_executor_runner`

The scratch tree also contains `/home/zwb/work/ethosu_tinycnn/executorch/examples/arm/arm-scratch/ethos-u/core_platform/targets/corstone-300/platform.ld`, which describes the same Corstone-300 memory model.

## Memory Regions

From the generated `platform.ld`:

| Region | Attributes | Origin | Length | Intended Use |
| --- | --- | --- | --- | --- |
| ITCM | `rx` | `0x10000000` | `0x00080000` | reset vector and executable text |
| BRAM | `rw` | `0x11000000` | `0x00100000` | `.sram.data`, including selected op text in this build |
| DTCM | `rw` | `0x30000000` | `0x00080000` | `.data`, `.rodata`, `.bss`, heap, stack |
| SRAM | `rw` | `0x31000000` | `0x00200000` | `.sram.bss`, optional arena/scratch |
| QSPI | `rw` | `0x38000000` | `0x00800000` | external PTE address in QSPI `--data` mode |
| DDR | `rwx` | `0x70000000` | `0x60000000` | tensor arena, embedded PTE, command/data sections |

The script defines three program headers only: `rom_exec PT_LOAD`, `rom_dram PT_LOAD`, and `null PT_NULL`. This is the root of several coarse segment mappings.

## Observed Section Layout

From `arm-none-eabi-objdump -h` on the default variant runner:

| Section | Size | VMA | LMA | Flags / Meaning |
| --- | ---: | --- | --- | --- |
| `.text` | `0x00028ae4` | `0x10000000` | `0x10000000` | executable text in ITCM |
| `.copy.table` | `0x00000024` | `0x10028de8` | `0x10028de8` | startup copy records |
| `.zero.table` | `0x00000008` | `0x10028e0c` | `0x10028e0c` | startup zero records |
| `.data` | `0x00000c48` | `0x30000000` | `0x30000000` | runtime initialized data in DTCM; script requests `AT(__etext)` |
| `.ddr` | `0x03e07c5c` | `0x70000000` | `0x70000000` | tensor arena plus embedded PTE/model section |
| `.sram.data` | `0x0001e9d0` | `0x11000000` | `0x11000000` | BRAM section; includes `op_*.cpp.obj (*.text*)` |
| `.rodata` | `0x0000c5f8` | `0x30000c48` | `0x30000c48` | read-only constants in DTCM; script requests `AT > DDR` |
| `.bss` | `0x000064e0` | `0x3000d400` | `0x3000d400` | zero-initialized data in DTCM |
| `.heap` | `0x00008000` | `0x300138e0` | `0x300138e0` | runtime heap reservation |
| `.stack` | `0x00008000` | `0x30078000` | `0x30078000` | stack reservation |

`arm-none-eabi-readelf -lS` shows two `PT_LOAD` segments, both marked `RWE`:

| Segment | VirtAddr | FileSiz / MemSiz | Flags | Mapped sections |
| --- | --- | --- | --- | --- |
| `LOAD` | `0x10000000` | `0x29a5c` | `RWE` | `.text`, `.ARM.extab`, `.ARM.exidx`, `.copy.table`, `.zero.table` |
| `LOAD` | `0x70000000` | `0x3e32c28` | `RWE` | `.ddr`, `.asan_shadow` |

The warnings report that `.data`, `.sram.data`, and `.rodata` cannot be allocated into the requested load segments, so they appear as loadable sections but are not cleanly covered by the coarse program headers.

## Warning Causes

### `.data` Segment Allocation Warning

The script places `.data` at DTCM VMA `0x30000000` while assigning it to `:rom_exec` and giving it an initialization load address with `AT(__etext)`. The `rom_exec` program header starts in ITCM near `0x10000000`. This creates a non-contiguous VMA jump inside one `PT_LOAD` segment, so `ld` warns:

```text
section `.data' can't be allocated in segment 1
LOAD: .text .ARM.extab .ARM.exidx .copy.table .zero.table .data
```

### `.sram.data` and `.rodata` Segment Allocation Warnings

The script places `.sram.data` at BRAM VMA `0x11000000` and `.rodata` at DTCM VMA `0x30000c48`, both with load addresses in DDR and both assigned to `:rom_dram`. The `rom_dram` program header starts at DDR VMA `0x70000000`. These VMA ranges are not contiguous with the DDR segment, so `ld` warns:

```text
section `.sram.data' can't be allocated in segment 2
section `.rodata' can't be allocated in segment 2
LOAD: .ddr .sram.data .rodata
```

### RWX LOAD Warning

Both `PT_LOAD` segments are `RWE`. The first becomes writable because `.copy.table` and `.zero.table` are not marked read-only in the output section flags. The second inherits broad permissions from the DDR region declared as `(rwx)` and from mixed content; `.sram.data` also collects `op_*.cpp.obj (*.text*)`, so executable code is involved in the same logical load grouping. A production linker layout should avoid load segments that are simultaneously readable, writable, and executable.

## Why FVP Still Runs

The Corstone-300 FVP `-a` ELF loader and current startup path are permissive enough for this debug runner layout. The startup code reads `.copy.table` to copy initialized data from load addresses to runtime VMAs, and `.zero.table` to zero `.bss`. The FVP logs prove the runner reaches `Program complete, exiting.` and prints valid outputs for baseline and all variant ELFs.

This success does not make the memory layout production-clean. A flashing tool or bootloader that relies strictly on program headers rather than section headers could mishandle sections that `ld` failed to allocate into the intended `PT_LOAD` segments.

## Startup Copy and Zero Relationships

The generated script emits three copy records:

1. `__etext -> __data_start__` for `.data` in DTCM.
2. `__eddr_data -> __sram_data_start__` for `.sram.data` in BRAM.
3. `__eddr_data + sizeof(.sram.data) -> __rodata_start__` for `.rodata` in DTCM.

It also emits one zero record for `.bss`:

```text
__bss_start__ -> __bss_end__
```

In a production layout, those records must be consistent with actual flash/load images and bootloader copy behavior.

## Embedded PTE vs QSPI `--data` Mode

Embedded-PTE mode includes `network_model_sec` inside `.ddr` when `ETHOSU_MODEL == 1`; the model is compiled into the ELF and the FVP log shows it at a DDR-backed address such as `0x73e00000`.

QSPI mode builds the runner with `--pte=0x38000000`; the model is not baked into the ELF in the same way and the FVP command supplies the PTE separately with:

```text
--data tinycnn_u55.pte@0x38000000
```

The same linker warnings still exist in QSPI mode because they come from the runner's generic linker script and PHDR layout, not only from the embedded model blob. QSPI mode mainly changes where the PTE bytes are loaded and how the runner finds them.

## Ideal Production Direction

A production firmware layout should separate:

- RX executable regions: vector table, `.text`, exception tables, read-only constants when appropriate.
- RO load image regions: immutable constants and model resources stored in flash/QSPI/DDR image memory.
- RW runtime regions: `.data` runtime VMA, `.bss`, heap, stack, tensor arena, Ethos-U scratch.
- NOLOAD regions: large scratch/tensor arenas that the image loader should not fill from the firmware binary.

It should also define PHDRs or omit custom PHDRs so that each non-contiguous VMA/LMA group has a clean load segment, and DDR should not be declared `rwx` unless executable DDR is intentionally required.

## Recommended Cleanup Steps For Real Board Porting

1. Create a dedicated linker script variant for the target board instead of editing the validated FVP baseline in place.
2. Split `rom_exec`, `rom_rodata`, `rom_data_load`, and runtime RW/NOLOAD regions explicitly.
3. Mark copy/zero tables read-only if they live with executable text.
4. Move read-only constants into an RX/RO segment or give them a matching load segment.
5. Decide whether selected operator code should execute from ITCM, BRAM, or flash, then place it in a region with execute permission and a matching PHDR.
6. Keep tensor arenas and scratch buffers as `NOLOAD` runtime memory where possible.
7. Rebuild and require both reduced linker warnings and FVP PASS before replacing the current script.
8. Revalidate on the actual board boot chain, because FVP section loading is not equivalent to a production bootloader or flash programming path.

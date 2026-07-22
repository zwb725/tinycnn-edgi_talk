# Local Vela / ExecuTorch API Inspection

This note records the local APIs used before adding `tinycnn/export_variants.py`.

## EthosUCompileSpec

Local signature from `.venv` / project checkout:

```text
EthosUCompileSpec(target: str, system_config: str | None = None, memory_mode: str | None = None, extra_flags: list[str] | None = None, config_ini: str | None = "Arm/vela.ini")
```

The current baseline exporter uses:

```python
EthosUCompileSpec(
    target="ethos-u55-128",
    system_config="Ethos_U55_High_End_Embedded",
    memory_mode="Shared_Sram",
)
```

## Passing Extra Vela Arguments

The local `EthosUCompileSpec` stores raw Vela arguments through `extra_flags`. Its internal flag builder prepends `extra_flags`, then appends the accelerator, config, output format, system config, and memory mode flags.

The Vela help in this environment exposes:

```text
--optimise {Size,Performance}
--arena-cache-size ARENA_CACHE_SIZE
```

The Size variant therefore uses one explicit extra flag:

```python
extra_flags=["--optimise=Size"]
```

## Intermediate Artifacts

The local API for preserving TOSA/Vela intermediates is:

```python
compile_spec.dump_intermediate_artifacts_to(str(intermediate_dir))
```

The baseline output confirmed this creates files such as:

```text
intermediates/out.tosa
intermediates/output/out_vela.npz
intermediates/output/out_summary_Ethos_U55_High_End_Embedded.csv
```

## Local Vela Summary Fields

The summary CSV contains compiler-estimated fields including `sram_memory_used`, `off_chip_flash_memory_used`, `cycles_total`, `cycles_npu`, `cycles_sram_access`, and the configured memory model. Values are treated as Vela estimates, not PSoC Edge E84 board measurements.

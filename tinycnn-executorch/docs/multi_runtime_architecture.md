# Multi-Runtime Architecture

This project is best described as two related but separate backend chains under one deployment theme. They share packaging ideas and interface concepts, but they do not share the same runtime, model artifact, platform validation, or performance baseline.

```mermaid
flowchart LR
  subgraph A["Chain A: Real E84 Application"]
    A1["Vela-compiled INT8 gesture model"] --> A2["TFLM / DeepCraft / IMAI runtime"]
    A2 --> A3["PSoC Edge E84 board"]
    A3 --> A4["UVC camera"]
    A4 --> A5["YUYV to RGB888"]
    A5 --> A6["Ethos-U55 inference"]
    A6 --> A7["Postprocess"]
    A7 --> A8["LCD display"]
  end

  subgraph B["Chain B: Open Compiler Toolchain"]
    B1["Custom TinyCNN"] --> B2["PyTorch torch.export"]
    B2 --> B3["PT2E INT8"]
    B3 --> B4["ExecuTorch EXIR"]
    B4 --> B5["TOSA lowering"]
    B5 --> B6["Vela compile"]
    B6 --> B7["ExecuTorch PTE"]
    B7 --> B8["Corstone-300 Ethos-U55 FVP"]
  end

  M["Shared engineering layer"] --> M1["Model manifest"]
  M --> M2["Lifecycle interface"]
  M --> M3["Target profile"]
  M --> M4["Code generation pattern"]
  M --> M5["Report format"]
```

## What Is Shared

- A model manifest can describe task, tensor shapes, quantization, target profile, artifact hash, and validation platform.
- A lifecycle interface can normalize `init`, `get_input`, `run`, `get_output`, and `deinit`.
- A target profile can capture accelerator, memory mode, and validation notes.
- Code generation can package model resources for embedded arrays or external storage.
- Reports can use a common evidence-first format.

## What Is Not Shared

- Chain A records the E84 board application/runtime path; Chain B records the ExecuTorch PTE and Corstone-300 FVP path. The later `tinycnn-edgi_talk` closure connects them through E84/FVP numerical comparison.
- The model artifacts are different: Vela/TFLite/IMAI resources versus ExecuTorch PTE.
- The current project does not run the same model through both runtimes for a fair performance comparison.
- In the original `zwb725/tinycnn` phase, ExecuTorch Runtime was not ported to E84; the follow-up `zwb725/tinycnn-edgi_talk` phase completed the BSP-specific E84 runtime path and board inference.
- Latency from different models, runtimes, and platforms must not be compared directly.

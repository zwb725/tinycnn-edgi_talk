# RT-AK ExecuTorch Backend

This directory is generated target-side integration scaffolding for the TinyCNN ExecuTorch artifact.

Historical boundary: in the original `zwb725/tinycnn` phase, this generated backend was an interface prototype and returned explicit not-implemented errors unless `RT_AI_EXECUTORCH_RUNTIME_READY` was enabled. The follow-up `zwb725/tinycnn-edgi_talk` phase completed the BSP-specific E84 Runtime path and board inference.

When `RT_AI_EXECUTORCH_RUNTIME_READY=n`, the C API remains a clear not-implemented boundary. When `RT_AI_EXECUTORCH_RUNTIME_READY=y` in the E84 BSP integration, the runtime path uses `rt_ai_executorch_runtime.cpp` for `BufferDataLoader`, `Program::load()`, method metadata, planned-buffer allocation, `MemoryManager`, Arm Ethos-U delegate registration, tensor binding, and `Method::execute()`.

This is not a generic production RT-AK Backend release. Float Bit-Exact, real dataset accuracy, and production-grade stability are not verified.
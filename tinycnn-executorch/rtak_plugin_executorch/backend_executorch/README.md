# RT-AK ExecuTorch Backend Prototype

This directory contains the target-side interface and BSP-specific runtime integration used by the TinyCNN ExecuTorch closure.

Historical boundary: in the original `zwb725/tinycnn` phase, this directory was only a target-side interface prototype and the inference functions returned explicit not-implemented errors. In the follow-up `zwb725/tinycnn-edgi_talk` phase, `RT_AI_EXECUTORCH_RUNTIME_READY` is used with the real runtime implementation for E84 BSP validation.

Current verified scope is BSP-specific:

- `Program::load` and method loading;
- allocator and tensor binding setup;
- Ethos-U delegate execution;
- IRQ 38 and RT-Thread semaphore return;
- one fixed TinyCNN inference on PSoC Edge E84;
- E84/FVP Top-1 and `1e-6` numerical comparison.

This is not a generic production RT-AK Backend release. Float Bit-Exact, real dataset accuracy, and production-grade stability are not verified.
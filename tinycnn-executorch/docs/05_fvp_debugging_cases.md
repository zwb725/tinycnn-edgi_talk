# FVP Debugging Cases

## Case 1: Cortex-M55 FPU/MVE Not Enabled

Symptom: early FVP fault or hang before useful runner output.

Cause: the Cortex-M55 target can execute compiler-emitted FPU/MVE register instructions. If coprocessor access is not enabled early, the CPU faults before the ExecuTorch runner can start.

Fix: enable FPU/MVE in `SystemInit` before those instructions can execute. The current baseline summary records this as a required FVP fix.

## Case 2: Semihost Inline Assembly Clobber

Symptom: semihost trace path was unstable.

Cause: the inline assembly used for semihost operations did not correctly mark the `r0` operand as read/write.

Fix: guard the semihost trace path and mark the operand as `+r`, so the compiler understands the register is modified.

## Case 3: Guarded Trace and Retarget

The runner and target setup now include guarded trace points so failures can be localized without always enabling noisy diagnostics. The retarget path provides semihost-compatible stdout/stderr/exit, which is why FVP logs reliably show setup, program load, method load, delegate execution, output, and exit.

## Debugging Order

Use this order when FVP hangs or faults:

1. Startup: vector table, stack, FPU/MVE, reset handler.
2. Target setup: UART, timing adapters, Ethos-U driver, NVIC, MPU.
3. Runtime: ExecuTorch runtime initialization and logging.
4. Program: PTE address, header, size, Program load.
5. Method: method metadata, allocator, planned buffers.
6. Delegate: Ethos-U backend initialization and execution.
7. Output: tensor binding, printed values, semihost exit.

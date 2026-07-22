# Blockers and Deferred Items

| Item | Status | Reason |
| --- | --- | --- |
| Production linker cleanup | BLOCKED | The existing warnings require non-minimal PHDR/VMA/LMA restructuring; no safe tiny patch was retained because all FVP paths already pass and a broad linker rewrite would risk the baseline. |
| PSoC Edge E84 ExecuTorch Runtime port | BLOCKED | This run created packaging tools and target-side stubs only. A real port still needs Program loading, Method loading, MemoryAllocator setup, Ethos-U delegate registration, tensor binding, and board validation. |
| E84 board performance numbers | BLOCKED | No E84 hardware run was performed in this project; current performance evidence is limited to Vela estimates and Corstone-300 FVP logs. |

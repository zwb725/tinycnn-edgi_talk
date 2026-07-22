# RT-AK ExecuTorch Prototype Architecture

The prototype separates host-side artifact generation from target-side runtime porting. Host tools validate a PTE, generate a manifest, and create embedded or QSPI resources. Target files expose lifecycle functions that intentionally return not-implemented until a real ExecuTorch Runtime integration exists.

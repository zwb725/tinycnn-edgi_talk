# TOSA / Vela Delegation

## Verified Delegation

- Ethos-U delegated subgraphs: `1`
- Delegated EXIR nodes: `29`
- Non-delegated EXIR boundary nodes: `3`
- Vela NPU operators: `7`
- Vela CPU operators: `0`

Evidence:

- `tinycnn/reports/delegation_report.md`
- `tinycnn/reports/delegated_subgraphs.txt`
- `tinycnn/build/variants/default/reports/delegation_report.md`

## Why 29 and 7 Are Both Correct

`29` is an ExecuTorch graph partitioning count. It includes quantize/dequantize nodes, convolutions, ReLUs, average pooling, linear, and view-like graph nodes inside the delegated EXIR subgraph.

`7` is Vela's compiled NPU operator count after lowering and fusion. Vela sees a lower-level optimized network, so several EXIR nodes can become one NPU operation or be folded into command-stream metadata.

## CPU Fallback

The ExecuTorch delegation report lists boundary/non-delegated nodes such as `getitem` and quantize/dequantize edges outside the delegated graph. The delegated Vela network itself reports `CPU operators = 0`, so there is no Vela CPU fallback inside the compiled NPU command stream.

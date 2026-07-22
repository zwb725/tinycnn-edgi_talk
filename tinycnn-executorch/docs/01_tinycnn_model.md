# TinyCNN Model

## Network Structure

The model is defined in `tinycnn/model.py`. It is a custom random-weight benchmark network for deployment-chain validation, not a real gesture model.

| Layer | 96x96 Output Shape | Params | Notes |
| --- | --- | ---: | --- |
| Input | `[1, 3, 96, 96]` | 0 | float32 input tensor |
| Conv2d 3->16, k3/s2/p1 | `[1, 16, 48, 48]` | 448 | supported convolution pattern |
| ReLU | `[1, 16, 48, 48]` | 0 | simple activation |
| Conv2d 16->32, k3/s2/p1 | `[1, 32, 24, 24]` | 4640 | downsample |
| ReLU | `[1, 32, 24, 24]` | 0 | simple activation |
| Conv2d 32->64, k3/s2/p1 | `[1, 64, 12, 12]` | 18496 | final feature map |
| ReLU | `[1, 64, 12, 12]` | 0 | simple activation |
| AdaptiveAvgPool2d(1,1) | `[1, 64, 1, 1]` | 0 | enables 96x96 and 64x64 variants |
| Flatten | `[1, 64]` | 0 | classifier input |
| Linear 64->4 | `[1, 4]` | 260 | benchmark classes |

Total parameters: `448 + 4640 + 18496 + 260 = 23844`.

For the 64x64 controlled experiment, convolution output sizes become `[32, 32]`, `[16, 16]`, and `[8, 8]`; the parameter count remains `23844` because weights do not depend on spatial resolution.

## Operator Choice

The model intentionally uses common deployment operators: convolution, ReLU, adaptive average pooling, flatten/view, and linear. This keeps the test focused on PT2E quantization, Ethos-U partitioning, TOSA lowering, Vela compilation, and runner validation.

## Accuracy Boundary

TinyCNN uses random fixed weights and no dataset. The only numerical statement allowed is:

> Fixed test input: FP32 and INT8 Top-1 are both `1`, and max absolute output error is `0.00024946779012680054`.

This is not an accuracy evaluation and must not be described as accuracy preservation.

from __future__ import annotations

import torch

from model import (
    INPUT_SHAPE,
    NUM_CLASSES,
    create_example_input,
    create_model,
)


def main() -> None:
    model = create_model()
    example_input = create_example_input()

    with torch.no_grad():
        output = model(example_input)

    expected_output_shape = (INPUT_SHAPE[0], NUM_CLASSES)

    if tuple(example_input.shape) != INPUT_SHAPE:
        raise RuntimeError(
            f"Unexpected input shape: {tuple(example_input.shape)}"
        )

    if tuple(output.shape) != expected_output_shape:
        raise RuntimeError(
            f"Unexpected output shape: {tuple(output.shape)}"
        )

    print("=" * 60)
    print("TinyCNN FP32 smoke test passed")
    print("Input shape :", tuple(example_input.shape))
    print("Input dtype :", example_input.dtype)
    print("Output shape:", tuple(output.shape))
    print("Output dtype:", output.dtype)
    print("Output      :", output)
    print("Top-1 index :", int(output.argmax(dim=1).item()))
    print("Parameters  :", sum(p.numel() for p in model.parameters()))
    print("=" * 60)


if __name__ == "__main__":
    main()

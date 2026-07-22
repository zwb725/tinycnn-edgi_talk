from __future__ import annotations

import torch
from torch import nn


INPUT_SHAPE = (1, 3, 96, 96)
NUM_CLASSES = 4


class TinyCNN(nn.Module):
    """
    用于验证 ExecuTorch + TOSA + Vela + Ethos-U55
    部署链路的轻量视觉卷积网络。

    输入:
        float32 Tensor [N, 3, 96, 96]

    输出:
        float32 Tensor [N, 4]
    """

    def __init__(self, num_classes: int = NUM_CLASSES) -> None:
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(
                in_channels=3,
                out_channels=16,
                kernel_size=3,
                stride=2,
                padding=1,
                bias=True,
            ),
            nn.ReLU(),

            nn.Conv2d(
                in_channels=16,
                out_channels=32,
                kernel_size=3,
                stride=2,
                padding=1,
                bias=True,
            ),
            nn.ReLU(),

            nn.Conv2d(
                in_channels=32,
                out_channels=64,
                kernel_size=3,
                stride=2,
                padding=1,
                bias=True,
            ),
            nn.ReLU(),

            nn.AdaptiveAvgPool2d((1, 1)),
        )

        self.classifier = nn.Linear(
            in_features=64,
            out_features=num_classes,
            bias=True,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = torch.flatten(x, start_dim=1)
        return self.classifier(x)


def create_model() -> TinyCNN:
    torch.manual_seed(20260716)
    return TinyCNN().eval()


def create_example_input() -> torch.Tensor:
    generator = torch.Generator()
    generator.manual_seed(20260716)

    return torch.rand(
        INPUT_SHAPE,
        generator=generator,
        dtype=torch.float32,
    )

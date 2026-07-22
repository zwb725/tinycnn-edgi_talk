# Edgi RT-AK Backend



## 1. 当前目标



本目录用于放置 Edgi Talk / DeepCraft / Imagimob / Cortex-M55 / Ethos-U55 对接 RT-AK 的最小 backend 草图。



当前 backend 只封装 DeepCraft / Imagimob 运行时入口：



\- `IMAI\_init`

\- `IMAI\_compute`

\- `IMAI\_finalize`



\## 2. 当前提供的接口



```c

int backend\_edgi\_init(const backend\_edgi\_config\_t \*config);

int backend\_edgi\_run(const void \*input, void \*output);

int backend\_edgi\_deinit(void);



void \*backend\_edgi\_get\_input(uint32\_t index);

void \*backend\_edgi\_get\_output(uint32\_t index);


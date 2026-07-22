# Edgi 工程 RT-AK 适配前代码梳理

> 目标：把 Edgi_Talk_M55_DEEPCRAFT_Deploy_Vision 中的 AI 推理链路迁移到 RT-AK，
> 做一个新的 RT-AK 平台后端。本文档只做静态代码梳理，不修改任何源码。
>
> 阅读对象：本工程 `main -> RT-Thread 启动 -> CherryUSB UVC -> DeepCraft AI runtime -> LCD overlay` 完整路径。
>
> 硬件平台：Infineon PSOC Edge E84（CM55 内核 + Ethos-U55 NPU + GFXSS LCD + HyperRAM）。
> 工具链：GCC Arm Cortex-M55 + Helium/MVE，硬浮点。
> 板级 SDK：`libs/TARGET_APP_KIT_PSE84_EVAL_EPC2`，内核：`rt-thread/`，AI/USB 板级代码：`libraries/Common/`，Infineon 组件：`libraries/components/`。

## 1. 工程目录结构

| 顶层目录 | 作用 | 适配 RT-AK 时是否需要修改 |
| --- | --- | --- |
| `applications/` | 业务层入口。`main.c`、`uvc_ai_app.c`、`uvc_ai_ethosu_rtos.c`。 | **是**：业务侧。 |
| `board/` | 板级初始化（`board.c/h`、`SConscript`、`linker_scripts/link.ld`）。包含 `cy_bsp_all_init`、GPIO power-on 时序。 | 否（链接脚本是事实标准）。 |
| `rt-thread/` | RT-Thread 5.x 内核源码。 | 否。 |
| `packages/` | 启用的 RT-Thread 软件包（当前只用了 `rt_vsnprintf_full`）。 | 否。 |
| `libraries/HAL_Drivers/` | 板级外设驱动（UART/SPI/PWM/LCD/Touch/USB PHY 等）。 | 否。 |
| `libraries/M55_Config/` | 板级 Kconfig 入口，含 `BSP_USING_DEEPCRAFT_AI` 等开关。 | 否（只读）。 |
| `libraries/Common/board/` | 板级公共驱动：`audio/`、`display_panels/`、`fal/`、`filesystem/`、`lvgl/`、`usb/`。`usb/` 同时承担 CherryUSB UVC 适配层。 | **是**：AI 集成入口在 `libraries/Common/board/ports/usb/` 里。 |
| `libraries/Common/deepcraft_ai/` | **DeepCraft AI runtime + 编译出来的 TFLite 模型**。`src/uvc_ai.c`（AI 处理主循环）、`include/uvc_ai.h`（对外 API）、`model/model.c/.h`（Imagimob 编译生成的 TFLM 模型权重 + 调用 API）、`third_party/ml-middleware`（Infineon mtb-ml 封装）、`third_party/ml-tflite-micro`（TFLM + Ethos-U55 后端）。 | **是**：核心适配点。 |
| `libraries/components/` | 第三方组件：`CherryUSB-1.6.0`、`mtb-device-support-pse8xxgp`（PDL/HAL/GFXSS）、`mtb-ipc`、`mtb-srf`、`Infineon_retarget-io-latest`、`serial-memory` 等。 | 否（CherryUSB 已经是预编译 `.a`）。 |
| `libs/TARGET_APP_KIT_PSE84_EVAL_EPC2/` | BSP 预编译库与生成头（CM33 启动链、CM55 链接脚本、PDL 头）。 | 否（链接脚本 `pse84_ns_cm55.ld` 决定了 memory map，必须看）。 |
| `tools/edgeprotecttools/` | 量产安全烧录工具。 | 否。 |
| `build/` | SCons 中间产物。 | 否。 |
| `Debug/` | Eclipse 调试工程元数据。 | 否。 |
| `figures/` | README 截图。 | 否。 |
| 顶层文件 | `SConstruct`、`SConscript`、`Kconfig`、`rtconfig.h`、`rtconfig.py`、`mklinks.{sh,bat}`。 | 否。 |

**关键判定**：

- 平台 runtime（CherryUSB + TFLM/Ethos-U + 板级 BSP）目前都是 RT-AK 适配中的"目标平台资源"，**不需要修改**。
- 业务/应用层（`applications/` 和 `libraries/Common/board/ports/usb/` 中与 AI 联动的那部分）就是要替换成 RT-AK 后端的部分。
- 模型本身（`libraries/Common/deepcraft_ai/model/model.c`）是 ImagiNet Compiler 5.7 生成的 TFLM 可加载模型，**接口名固定**为 `IMAI_init / IMAI_compute / IMAI_finalize / IMAI_api`。

## 2. 启动流程

下表中 "段" 表示 RT-Thread 在 `rt_components_board_init` / `rt_components_init` / `rt_application_init` 三轮里按 `INIT_*_EXPORT` 序号触发的回调。CM55 启动链参考 `libs/.../COMPONENT_CM55/.../pse84_ns_cm55.ld`，`.copy.table` 负责把 flash 中的 `.data / .cy_socmem_data / .cy_uvc_stream_data / .cy_ml_model_data / .app_code_itcm / .app_code_socmem` 拷贝到对应 RAM。

```
Reset_Handler (psoc_edge startup_CM55)
  -> _start() in board/board.c
       -> cy_bsp_all_init()                // 初始化时钟/电源/外设 (cybsp_init)
       -> entry()                          // RT-Thread 内核入口
            -> rt_hw_board_init()          // 板级 CPU/堆栈/sys tick
            -> rt_components_board_init()  // INIT_BOARD_EXPORT
                 -> en_gpio()              // board/board.c 中由 INIT_BOARD_EXPORT 注册: 拉起 LCD BL/DISPLAY, WiFi, Audio 电源
                 -> drv_common_init, ...   // HAL_Drivers/drivers/init 全部驱动
            -> rt_components_init()        // INIT_DEVICE_EXPORT / INIT_COMPONENTS_EXPORT / INIT_APP_EXPORT
                 -> usbh_initialize(0, USBHS_BASE, NULL)  // 在 main() 中手动调用, 见 applications/main.c
            -> rt_application_init()
                 -> main_thread -> main()  // applications/main.c
                      -> rt_kprintf("Hello RT-Thread\r\n")
                      -> usbh_initialize(0, USBHS_BASE, NULL)   // CherryUSB DWC2 主机栈注册
                      -> 循环闪烁 LED (16-6)
                 -> MSH tshell 启动
```

注意：

- `applications/main.c` 中 `usbh_initialize(0, USBHS_BASE, NULL)` **直接由 `main()` 调用**，并不是通过任何 `INIT_*_EXPORT`，所以 USB 主机栈在 `rt_application_init` 之后立即被启动。
- `MSH_CMD_EXPORT_ALIAS` 在 `libraries/Common/board/ports/usb/usbh_uvc_app.c` 中注册两条 MSH 命令：
  - `usbh_uvc_start [fmt] [w] [h]` — 创建/启动 CherryUSB UVC 流、起两个线程（`uvc_fps` 优先级 20、`uvc_frm` 优先级 22）。
  - `usbh_uvc_stop` — 置位 `uvc_app_running = 0` 让两条线程退出。
- `INIT_BOARD_EXPORT` 当前只有 `en_gpio`（在 `board/board.c`），没有 AI 相关的自动初始化 hook，**AI 的全部初始化都从 `usbh_uvc_app.c -> uvc_ai_app_start()` 触发**。
- AI 静态区（模型 `_K3[]`、arena `_state[]`、input 缓冲 `g_model_input_u8`）由链接脚本的 `.copy.table` 在 `Reset_Handler` 阶段从 flash 复制到 `m55_data_secondary`（SoCMEM）和 `gfx_mem`，运行时不再做 `mtb_ml_model_init` 之外的额外加载。

`INIT_*_EXPORT` 触发一览（仅项目自身代码）：

| 宏 | 文件 | 函数 | 阶段 |
| --- | --- | --- | --- |
| `INIT_BOARD_EXPORT` | `board/board.c` | `en_gpio` | `rt_components_board_init` |
| `MSH_CMD_EXPORT` | `board/board.c` | `poweroff` | MSH 注册 |
| `MSH_CMD_EXPORT_ALIAS` | `libraries/Common/board/ports/usb/usbh_uvc_app.c` | `cmd_usbh_uvc_start` (`usbh_uvc_start`) | MSH 注册 |
| `MSH_CMD_EXPORT_ALIAS` | `libraries/Common/board/ports/usb/usbh_uvc_app.c` | `cmd_usbh_uvc_stop` (`usbh_uvc_stop`) | MSH 注册 |

驱动侧的所有 `INIT_*_EXPORT` 由 `libraries/components/mtb-device-support-pse8xxgp/hal/source` 和 `libraries/HAL_Drivers/` 内置，不在本文档展开。

## 3. AI 推理完整调用链

> MSH 用户在串口敲 `usbh_uvc_start 0 320 240` 之后，UVC 帧开始进入 `uvc_frame_thread_entry()` 的循环，每次拿到一帧就把数据丢给 AI worker，再由 LCD 线程渲染。

```
[UVC 摄像头] --(USB HS ISO)--> [CherryUSB usbh_video 驱动]
                                   |
                                   v
                       usbh_video_stream_dequeue()
                                   |
                                   v
                uvc_frame_thread_entry()    -- 优先级 22, 栈 64 KB
                (libraries/Common/board/ports/usb/usbh_uvc_app.c)
                                   |
                                   v
              uvc_ai_app_process_frame(frame)
              (applications/uvc_ai_app.c)
                  - 校验 fmt == YUYV
                  - frame_counter++, 每 UVC_AI_FRAMES_TO_SKIP(4) 帧取 1 帧
                  - 拷贝到 worker_buf (320*240*2 = 153600 B, DTCM/堆)
                  - rt_sem_release(uvc_aiwk)
                                   |
                                   v
              uvc_ai_app_worker_thread_entry()   -- 优先级 8, 栈 64 KB (DTCM)
              (applications/uvc_ai_app.c)
                  - rt_sem_take(uvc_aiwk, FOREVER)
                  - 同步调用:
                        uvc_ai_process_yuyv(buf, UVC_AI_FRAME_BYTES, &result)
                                   |
                                   v
              uvc_ai_process_yuyv()       [libraries/Common/deepcraft_ai/src/uvc_ai.c]
                  1. 参数与长度校验 (>= 320*240*2)
                  2. 预处理 (uvc_ai_yuyv_to_rgb888_320x320_u8)
                       - 查表 YUV->RGB888 (298/516/-100/409/-208 LUT, .cy_dtcm)
                       - 仅填上面 320*240, 底部 80 行黑边保留 0 (事先 memset 一次)
                       - 写入 g_model_input_u8[307200] (gfx_mem, .cy_ml_input_data)
                  3. 同步 NPU 计算:
                       IMAI_compute(g_model_input_u8, g_model_output)
                       - 内部走 tflite::MicroInterpreter
                       - 委托到 Ethos-U55 NPU (libtensorflow-microlite.a 中的 ethosu.o)
                       - 输出 float[40] (5 列 × 8 anchors) 写回 g_model_output (.cy_dtcm)
                  4. 后处理:
                       - IMAI_api() 读取模型元数据 (rank/shape/label)
                       - 遍历 8 个 anchor, 取 detection_flag 第一个非 0
                       - x,y,w,h -> xmin/ymin/xmax/ymax (在 320x320 模型空间)
                       - 类别 = argmax(score[0..2]) (3 类)
                       - 置信度 = max score
                       - 填进 uvc_ai_result_t (bbox_int16[]、class_id[]、conf[]、class_string[])
                  5. 计算并打印 "AI inference %.1f ms (prep %.1f ms, npu %.1f ms), det=%u"
                                   |
                                   v
              uvc_ai_app_publish_result()    // 临界区覆盖 latest_result
              return RT_EOK
                                   |
                                   v
              uvc_display_run_overlay_callback()  (usbh_uvc_display.c, 在 uvc_display_frame 末尾)
                  - 调用 uvc_ai_app_overlay_cb() (applications/uvc_ai_app.c)
                  - snapshot_result() 拷出临界区安全的 uvc_ai_result_t
                  - 用 5x7 自绘字体画框 + 类别 + 置信度
                  - 左上角绘制 "Model %.1f ms"
                                   |
                                   v
              uvc_display_flush() -> Cy_GFXSS_TransferPartialFrame() (仅活动区)
                                   |
                                   v
[LCD 512x800 RGB565] 显示 YUYV 解码后的图像 + 框/标签
```

数据流形态（一次推理的 buffer 走向）：

```
USB HS ISO 端点 (HyperRAM .m33_m55_shared_hyperram)
    -- CherryUSB 内部 DMA + LLI 拷贝 -->
frame_pool[].frame_buf (.m33_m55_shared_hyperram, 640*480*2, 共 4 帧)
    -- memcpy 到 worker 缓冲 (DTCM/堆) -->
g_uvc_ai_app.worker_frame_buf (153600 B, 异步路径)
    -- uvc_ai_yuyv_to_rgb888_320x320_u8 转换为 RGB888u8 -->
g_model_input_u8[307200] (.cy_ml_input_data -> gfx_mem 区域)
    -- IMAI_compute -->
g_model_output[40] (.cy_dtcm)
    -- 解析填充 -->
uvc_ai_result_t (g_uvc_ai_app.latest_result, .bss/DTCM)
    -- 拷贝到栈上 result_snapshot -->
uvc_ai_app_overlay_cb 在 lcd_fb (HyperRAM, .cy_uvc_rgb565_data / .m33_m55_shared_hyperram) 上画框
    -- Cy_GFXSS -->
LCD panel
```

日志输出路径（不依赖 LCD 的诊断信息）：

```
USB_LOG_INFO/WRN/ERR (libraries/components/CherryUSB-1.6.0/common/usb_log.h)
    -> 默认输出到 RT-Thread console (uart2, 115200)
    -> 串口 MSH/FinSH
```

## 4. 关键源码文件

> 适配 RT-AK 时重点关注 "是否适合 RT-AK 适配" 一列为 "是" 的文件。

| 文件路径 | 作用 | 关键函数/符号 | 是否适合 RT-AK 适配 |
| --- | --- | --- | --- |
| `applications/main.c` | RT-Thread 入口主函数，调用 CherryUSB 主机初始化。 | `main()`、`usbh_initialize(0, USBHS_BASE, NULL)` | 是（数据流入口）。 |
| `applications/uvc_ai_app.c` | **AI 应用层**：把 UVC 帧桥接到 AI runtime；提供 overlay 回调。 | `uvc_ai_app_start` / `uvc_ai_app_process_frame` / `uvc_ai_app_stop` / `uvc_ai_app_overlay_cb` / `uvc_ai_app_enforce_mode` / `uvc_ai_app_worker_thread_entry` | **是**。这是 RT-AK 后端的首要替换目标（worker 线程、buffer 拷贝、结果回传到 LCD）。 |
| `applications/uvc_ai_app.h` | `uvc_ai_app_*` 的对外头。 | 同上声明 | 是。 |
| `applications/uvc_ai_ethosu_rtos.c` | 把 mtb-ml 默认的 RTOS 抽象层（mutex / semaphore）重定向到 RT-Thread。 | `ethosu_mutex_*` / `ethosu_semaphore_*` | 是（Ethos-U55 NPU 的 RTOS 适配层需要 RT-AK 重新实现）。 |
| `libraries/Common/deepcraft_ai/src/uvc_ai.c` | **AI 预处理 / 推理调用 / 后处理**。 | `uvc_ai_init` / `uvc_ai_deinit` / `uvc_ai_process_yuyv` / `uvc_ai_prepare_yuv_lut` / `uvc_ai_yuyv_to_rgb888_320x320_u8` / `uvc_ai_sync_model_blob_from_flash` / `uvc_ai_reset_result` | **是**。直接可作为 RT-AK `backend_run` 的参考实现；YUV->RGB888 查表逻辑可作为 "后端无关预处理"。 |
| `libraries/Common/deepcraft_ai/include/uvc_ai.h` | `uvc_ai_*` 对外头。 | `uvc_ai_init/deinit/process_yuyv/reset_result`、`uvc_ai_config_t`、`uvc_ai_result_t` | 是（用于直接抽出 `backend_init` / `backend_run` / `backend_get_output` 抽象）。 |
| `libraries/Common/deepcraft_ai/model/model.c` | ImagiNet Compiler 5.7 编译产物，**包含 TFLite flatbuffer 参数、arena、state、work buffer**。 | `IMAI_init` / `IMAI_compute` / `IMAI_finalize` / `IMAI_api` / `IMAI_mtb_models_*` | 是（模型 loader 与权重数据都来自这里；RT-AK 适配时**只需保证这些符号被链接到新后端**）。 |
| `libraries/Common/deepcraft_ai/model/model.h` | 模型元数据宏：input shape `(320,320,3)` uint8、output shape `(8,5)` float、Memory 用量、IMAI API 声明。 | `IMAI_DATAIN_*` / `IMAI_DATAOUT_*` / `IMAI_MODEL_ID` | 是（用于 RT-AK 自动推导 input/output 形状）。 |
| `libraries/Common/deepcraft_ai/SConscript` | 把 AI runtime、模型、TFLM 静态库、Ethos-U55 PDL 加入编译。 | `DefineGroup('DeepcraftAi', ...)` | 是（构建侧配置参考；新后端可以保留结构）。 |
| `libraries/Common/deepcraft_ai/third_party/ml-middleware/source/COMPONENT_ML_TFLM/mtb_ml_model.cpp` | Infineon 对 TFLM 的封装，把 `IMAI_*` 桥接到 `tflite::MicroInterpreter`。 | `IMAI_init` / `IMAI_compute` / `IMAI_finalize` | 是（rt-ak backend 内部可以复用或者整段替换）。 |
| `libraries/Common/deepcraft_ai/third_party/ml-middleware/source/COMPONENT_U55/mtb_ml_ethosu.c` | Ethos-U55 NPU 启动/驱动绑定。 | `mtb_ml_set_cache_mgmt_type` / NPU 频率 | 是（与 `uvc_ai_ethosu_rtos.c` 配套）。 |
| `libraries/Common/deepcraft_ai/third_party/ml-tflite-micro/.../libtensorflow-microlite.a` | 预编译 TFLM（含 Ethos-U55 委托）。 | （静态库，符号表见 `rtthread.map`） | 是（底层后端；新 RT-AK 实现可以直接链接或者替换为 RT-AK Ethos-U 后端）。 |
| `libraries/Common/board/ports/usb/usbh_uvc_app.c` | CherryUSB UVC 主机层：FPS 线程、帧消费线程、MSH 命令。 | `usbh_video_run` / `usbh_video_stop` / `uvc_frame_thread_entry` / `cmd_usbh_uvc_start` / `cmd_usbh_uvc_stop` / `uvc_ai_app_*` 桩函数 | 是（保留为 RT-AK "输入源"；可以把 `uvc_ai_app_*` 桥接到 RT-AK `backend_run`）。 |
| `libraries/Common/board/ports/usb/usbh_uvc_stream.h` | CherryUSB UVC 流 API 头（`usbh_video_stream_*`）。 | `usbh_video_stream_create/start/stop/enqueue/dequeue` | 否（属于平台 runtime 抽象）。 |
| `libraries/Common/board/ports/usb/usbh_uvc_display.c` | 摄像头画面到 LCD 的渲染：YUYV/MJPEG 解码、缩放、overlay 回调、GFXSS flush。 | `uvc_display_init` / `uvc_display_frame` / `uvc_display_set_overlay_callback` / `uvc_mjpeg_decode` | 是（overlay hook 是结果回传点；保留即可）。 |
| `libraries/Common/board/ports/usb/usbh_uvc_display_hook.h` | `uvc_display_overlay_info_t` 描述子（framebuffer/lcd_w/lcd_h/src/dst 几何）。 | `uvc_display_set_overlay_callback` | 是。 |
| `libraries/Common/board/ports/usb/tjpgd.c/.h` | TJpgDec，MJPEG 解码。 | `jd_prepare` / `jd_decomp` | 否（平台 runtime）。 |
| `libraries/Common/board/ports/usb/libusbh_uvc.a` | CherryUSB UVC 主机栈预编译（Infineon 已 patch）。 | `usbh_uvc_stream.o` 内的 IMAI 桩函数 | 否（平台 runtime）。 |
| `libraries/Common/board/ports/SConscript` | 板级公共驱动聚合。 | `DefineGroup('Common', ...)` | 否。 |
| `libraries/Common/board/ports/audio/`, `display_panels/`, `fal/`, `filesystem/`, `lvgl/` | 板级音频/LCD/FAL/FS/LVGL 端口。 | — | 否。 |
| `board/board.c` / `board/board.h` | 板级 init：电源、bsp、`INIT_BOARD_EXPORT(en_gpio)`。 | `cy_bsp_all_init` / `_start` / `en_gpio` / `poweroff` | 否。 |
| `board/SConscript` | 把 PDL 的 `mtb-device-support-pse8xxgp` 头目录和关键宏加入全局 CPPDEFINES（`COMPONENT_CM55`、`COMPONENT_U55`、`COMPONENT_ML_TFLM` 等）。 | `DefineGroup('Drivers', ...)` | 否。 |
| `board/linker_scripts/link.ld` | 简化的 BSP 链接脚本入口。 | — | 否。 |
| `libs/.../COMPONENT_CM55/.../pse84_ns_cm55.ld` | **真正的链接脚本**。决定 memory map 与所有 `.cy_*` 段。 | `.cy_ml_model_data` / `.cy_ml_input_data` / `.cy_socmem_data` / `.cy_ml_arena_data` / `.cy_uvc_stream_data` | 是（RT-AK 后端如果要换 buffer 区/链接段，需要看这里）。 |
| `libraries/components/CherryUSB-1.6.0/class/video/usbh_video.c` | CherryUSB UVC 主机类驱动源码。 | `usbh_video_run` 回调注册 | 否。 |
| `libraries/components/CherryUSB-1.6.0/SConscript` | CherryUSB 的 SCons 入口。 | — | 否。 |
| `libraries/components/CherryUSB-1.6.0/Kconfig.rtt` | CherryUSB Kconfig（用于 `RT_CHERRYUSB_HOST_VIDEO` 等）。 | `RT_CHERRYUSB_HOST_VIDEO` | 否。 |
| `SConstruct` / `SConscript` | SCons 总入口，调用 `PrepareBuilding` 拉起 RT-Thread 标准构建链。 | `PrepareBuilding`、`DoBuilding` | 否。 |
| `Kconfig` | 项目级 Kconfig（仅作入口）。 | `source "$RTT_DIR/Kconfig"` 等 | 否。 |
| `rtconfig.h` | 当前生效的 RT-Thread 配置宏。 | `RT_USING_CHERRYUSB`、`RT_CHERRYUSB_HOST_VIDEO`、`BSP_USING_DEEPCRAFT_AI`、`SOC_SERIES_IFX_PSOCE84`、`BSP_USING_LCD`、`COMPONENT_MTB_DISPLAY_tl043wvv02` | 否（参考）。 |
| `libraries/M55_Config/Kconfig` | 板级 Kconfig 入口，含 `BSP_USING_DEEPCRAFT_AI`。 | `BSP_USING_DEEPCRAFT_AI` | 否。 |

## 5. DeepCraft / M55 AI Runtime 接口

> 这一节列出**所有**与 AI runtime 直接相关的导出函数、结构体、宏，便于 RT-AK 抽象。

### 5.1 模型层（`libraries/Common/deepcraft_ai/model/model.h` / `model.c`，由 ImagiNet Compiler 5.7 生成）

- **函数**
  - `int  IMAI_init(void);` — 初始化模型内部 arena/state，返回 `IMAI_RET_SUCCESS(0)` / `IMAI_RET_NODATA(-1)` / `IMAI_RET_ERROR(-2)` / `IMAI_RET_STREAMEND(-3)`。
  - `void IMAI_compute(const uint8_t *restrict datain, float *restrict dataout);` — 一次推理同步调用，**不返回耗时**。
  - `void IMAI_finalize(void);` — 释放资源，关闭 stream。
  - `IMAI_api_def *IMAI_api(void);` — 返回模型元数据：函数列表、参数形状、类别标签。
  - `void IMAI_mtb_models_profile_log();` / `void IMAI_mtb_models_print_info();` — 调试用。
- **常量 / 宏**
  - `IMAI_DATAIN_RANK=3`、`IMAI_DATAIN_SHAPE=((int[]){3,320,320})`、`IMAI_DATAIN_COUNT=307200`、`IMAI_DATAIN_TYPE=uint8_t`、`IMAI_DATAIN_TYPE_ID=IMAGINET_TYPES_UINT8`、`IMAI_DATAIN_SHIFT=0`、`IMAI_DATAIN_OFFSET=0`、`IMAI_DATAIN_SCALE=1`。
  - `IMAI_DATAOUT_RANK=2`、`IMAI_DATAOUT_SHAPE=((int[]){5,8})`、`IMAI_DATAOUT_COUNT=40`、`IMAI_DATAOUT_TYPE=float`、`IMAI_DATAOUT_TYPE_ID=IMAGINET_TYPES_FLOAT32`。
  - `IMAI_KEY_MAX=8`、`IMAI_RET_SUCCESS=0`、`IMAI_RET_NODATA=-1`、`IMAI_RET_ERROR=-2`、`IMAI_RET_STREAMEND=-3`。
  - `IMAI_MODEL_ID={0x06,0x1e,...,0x81}`（16 字节 GUID），`MODEL_NAME=OBJECT_DETECT`。
  - 模型内存（头注释）：Buffers 357600 B、State 891920 B、Readonly 1722352 B。
  - 内部数组 `_K3[]`（参数 blob，~1.6 MB 权重）放在 `.cy_socmem_data`（由 SConscript `CY_ML_MODEL_MEM=.cy_socmem_data` 决定），`_state[891920]` 也在 `.cy_socmem_data`，`_buffer[357600]` 在 `.cy_socmem_data`。
  - 顶层 `IMAI_mtb_models[IMAI_MAX_MTB_MODELS]`、计数 `IMAI_mtb_models_count`（用于 mtb-ml 框架的多模型注册）。
- **类型**
  - `IMAI_param_attrib`：`UNDEFINED/INPUT/OUTPUT/REFERENCE/HANDLE`。
  - `IMAI_func_attrib`：`NONE/CAN_FAIL/PUBLIC/INIT/DESTRUCTOR`。
  - `IMAI_api_type`：`UNDEFINED/FUNCTION/QUEUE/QUEUE_TIME/USER_DEFINED`。
  - `IMAI_shape_dim { char* name; int size; label_text_t* labels; }`。
  - `IMAI_param_def { name, attrib, rank, shape, count, type_id, frequency, shift, scale, offset }`。
  - `IMAI_func_def { name, description, fn_ptr, attrib, param_count, param_list }`。
  - `IMAI_mem_usage { size, peak_usage }`。
  - `IMAI_api_def { api_ver, id[16], api_type, prefix, buffer_mem, static_mem, readonly_mem, func_count, func_list }` — 这是 RT-AK `model_register` 时最需要读取的元数据。

### 5.2 板级 AI 抽象层（`libraries/Common/deepcraft_ai/src/uvc_ai.c` + `include/uvc_ai.h`）

- **函数**
  - `int  uvc_ai_init(const uvc_ai_config_t *config);` — 同步 YUV LUT、刷新模型 blob、关闭 UNALIGN_TRP、调 `IMAI_init`、设置 `MTB_ML_ETHOSU_CACHE_MGMT_OUTER_LAYERS`、清 0 底部 padding 行。
  - `void uvc_ai_deinit(void);` — 调 `IMAI_finalize`，恢复 `SCB->CCR`。
  - `int  uvc_ai_process_yuyv(const uint8_t *yuyv, uint32_t yuyv_size, uvc_ai_result_t *result);` — 一帧完整推理：YUV->RGB888 预处理 + `IMAI_compute` + 后处理解析；填充 `result`；每 3 秒打印一次统计。
  - `void uvc_ai_reset_result(uvc_ai_result_t *result);` — 把 result 清零。
  - 内部：`uvc_ai_prepare_yuv_lut` / `uvc_ai_yuyv_to_rgb888_320x320_u8` / `uvc_ai_sync_model_blob_from_flash` / `uvc_ai_get_best_class`。
- **结构体**
  - `uvc_ai_config_t { uint8_t initialized; uint16_t src_width; uint16_t src_height; }` — AI 初始化配置。
  - `uvc_ai_result_t { uint8_t valid; uint8_t count; float inference_ms; int16_t bbox_int16[UVC_AI_MAX_PREDICTIONS*4]; float conf[UVC_AI_MAX_PREDICTIONS]; uint8_t class_id[UVC_AI_MAX_PREDICTIONS]; union { char label[UVC_AI_MAX_PREDICTIONS][UVC_AI_MAX_CLASS_LEN]; char class_string[UVC_AI_MAX_PREDICTIONS][UVC_AI_MAX_CLASS_LEN]; }; }` — AI 输出。
- **常量**
  - `UVC_AI_CAMERA_WIDTH=320` / `UVC_AI_CAMERA_HEIGHT=240` / `UVC_AI_IMAGE_WIDTH=320` / `UVC_AI_IMAGE_HEIGHT=320`（图像输入 320x240 + 80 行黑边 pad 到 320x320）。
  - `UVC_AI_NUM_CLASSES=3` / `UVC_AI_MAX_CLASS_LEN=10` / `UVC_AI_MAX_PREDICTIONS=5` / `UVC_AI_FRAMES_TO_SKIP=4`。
  - 内部段属性宏：`UVC_AI_ITCM_SECTION`（`.cy_itcm`，热路径），`UVC_AI_DTCM_SECTION`（`.cy_dtcm`），`UVC_AI_ML_INPUT_SECTION`（`.cy_ml_input_data`），`UVC_AI_ALIGN_16`。

### 5.3 应用层（`applications/uvc_ai_app.c` / `uvc_ai_app.h`）

- **函数**
  - `void uvc_ai_app_enforce_mode(uint8_t *fmt, uint16_t *width, uint16_t *height);` — 把用户输入强制改回 YUYV/320x240。
  - `int  uvc_ai_app_start(uint16_t src_width, uint16_t src_height);` — 调 `uvc_ai_init`、分配 worker 缓冲/信号量/线程（DTCM stack 64KB，优先级 8）、注册 overlay 回调。
  - `void uvc_ai_app_process_frame(const struct usbh_videoframe *frame);` — 喂帧入口（仅取 YUYV、按 `UVC_AI_FRAMES_TO_SKIP` 抽帧、同步或异步派发）。
  - `void uvc_ai_app_stop(void);` — 回收 worker 线程、释放缓冲、`uvc_ai_deinit`。
  - `static void uvc_ai_app_overlay_cb(...)` — overlay 回调（由 `uvc_display_set_overlay_callback` 注册到 LCD 渲染层）。
- **结构体 / 状态**
  - `uvc_ai_app_ctx_t`（内部）：`started/ai_ready/worker_running/worker_busy/frame_counter/src_width/src_height/worker_thread/worker_sem/worker_frame_buf/latest_result`。
  - 全局 `g_uvc_ai_app`、`g_uvc_ai_worker_stack[65536]`、静态 TCB `g_uvc_ai_worker_tcb`。
  - 5x7 ASCII 字体表 `g_uvc_font5x7[]`、类色 `g_uvc_ai_class_colors[3]`、文字色、模型耗时底色。

### 5.4 Ethos-U55 RTOS 绑定（`applications/uvc_ai_ethosu_rtos.c`）

- `ethosu_mutex_create/destroy/lock/unlock`
- `ethosu_semaphore_create/destroy/take/give`
- 由 `libraries/Common/deepcraft_ai/third_party/ml-tflite-micro/.../libtensorflow-microlite.a` 内部 `ethosu.o` 调用，**这是 RT-AK 后端必须实现的 OS 抽象**。

### 5.5 mtb-ml 接口（`libraries/Common/deepcraft_ai/third_party/ml-middleware/`）

- `IMAI_*` API 是 mtb-ml 在 `mtb_ml_model.cpp` 中实现的入口，里面把 TFLite model + TFLM MicroInterpreter + Ethos-U delegate 全部组装好。
- 全局 `mtb_ml_npu_clk_freq`、`mtb_ml_cpu_clk_freq`、`mtb_ml_npu_cycles`（Ethos-U55 PMU 计数器）由 mtb-ml 提供。
- `mtb_ml_set_cache_mgmt_type(MTB_ML_ETHOSU_CACHE_MGMT_OUTER_LAYERS)` 在 `uvc_ai_init()` 末尾被调用，影响 CMSIS-DSP/Helium 缓存一致性策略。

### 5.6 内存段分配（`libs/.../COMPONENT_CM55/.../pse84_ns_cm55.ld`）

| 段 | 区域 | 用途 |
| --- | --- | --- |
| `.app_code_main` | `m55_nvm` (0x60580000, 8 MB) | 主代码、rodata、init 表。 |
| `.app_code_itcm` | `m55_code_INTERNAL` (0x00000000, 256 KB) | `.cy_itcm`、CMSIS-DSP 关键函数。 |
| `.app_code_socmem` | `m55_code_secondary` (0x26000000, 384 KB) | `.cy_socmem_code`。 |
| `.data` | `m55_data_INTERNAL` (0x20000000, 256 KB) | 已初始化数据。 |
| `.cy_dtcm` | 跟随 `.data` | DTCM 内的零散缓冲。 |
| `.cy_socmem_data` | `m55_data_secondary` (0x26060000, 3 MB+) | 模型的 `_K3[]`、`_state[891920]`、`_buffer[357600]`、NPU arena。 |
| `.cy_ml_model_data` | `m55_data_secondary`（`m55_data_secondary_sel`） | 备用，预留作为大模型 blob 容器。 |
| `.cy_ml_input_data` | `gfx_mem` (0x263B0000, 1.3 MB) | `g_model_input_u8[307200]`。 |
| `.cy_ml_arena_data` | `m33_m55_shared_hyperram` (0x64400000, 12 MB) | NPU 运行期 arena（HyperRAM）。 |
| `.cy_ml_arena_fast_data` | `m55_data_secondary` (0x26060000) | NPU 内部快速 arena（SoCMEM）。 |
| `.cy_ml_postproc_data` | `m33_m55_shared` (0x26370000, 256 KB) | 后处理缓存。 |
| `.cy_uvc_stream_data` | `m33_m55_shared_hyperram` | UVC 流 buffer（被 `usbh_uvc_stream.o` 单独接管）。 |
| `.m33_m55_shared_hyperram` | `m33_m55_shared_hyperram` | 大帧缓冲 `frame_buffer[4][640*480*2]`。 |
| `.cy_uvc_rgb565_data` | `m33_m55_shared` | 320x240 RGB565 stage buffer。 |
| `.cy_gpu_buf` | `gfx_mem` | GPU buffer。 |
| `.heap` | `m55_data_secondary` | RT-Thread 堆（`__end__` 在 SoCMEM 末尾）。 |

> 这张表是 RT-AK 后端 buffer 规划的"硬约束"：模型参数必须能放进 `m55_data_secondary`（~3 MB）或者 `m33_m55_shared_hyperram`（12 MB）。

## 6. 未来映射到 RT-AK 的接口建议

> RT-AK 约定的常用抽象：`backend_init / backend_run / backend_get_input / backend_get_output / backend_config / model_register`。
> 下表把 Edgi 当前实现里能 1:1 / 容易 1:1 映射过去的位置整理出来。

| 当前 Edgi 函数/模块 | 未来 RT-AK 后端接口 | 说明 |
| --- | --- | --- |
| `IMAI_init()` / `IMAI_finalize()` (model.c) | `int backend_init(const rt_ai_model_desc_t *desc)` / `int backend_deinit(void)` | 加载模型权重（已在 `.cy_socmem_data`） + 初始化 TFLM MicroInterpreter + 注册 Ethos-U55 delegate。`rt_ai_model_desc_t` 用 `IMAI_api()` 填入（input/output shape、type、label）。 |
| `IMAI_compute(datain_u8, dataout_f32)` (model.c) | `int backend_run(rt_ai_tensor_t *in, rt_ai_tensor_t *out)` | 等价于一次推理同步调用；可加 `backend_run_async` 变体。`mtb_ml_npu_cycles` 可填到 `desc->run_time_ms`。 |
| `IMAI_api()` (model.c) | `int model_register(rt_ai_model_desc_t *desc)` | 唯一权威的元数据来源：rank/shape/label/type_id。RT-AK 可以 `model.c` 编译进 `model_*.o`，再 `model_register` 一次。 |
| `uvc_ai_init(config)` | `backend_init` 上层封装 + `backend_config`（设置分辨率/输入格式/线程） | 内部的 YUV LUT、UNALIGN_TRP 关闭、`MTB_ML_ETHOSU_CACHE_MGMT_OUTER_LAYERS` 设置应当下沉到 backend init。 |
| `uvc_ai_process_yuyv(yuyv, size, &result)` | `backend_get_input(buf, len)` + `backend_run` + `backend_get_output(&result)` | 拆分后：①`backend_get_input` 暴露的 input buffer 是 `g_model_input_u8`（已分配在 `.cy_ml_input_data`），业务方把预处理后的 RGB888u8 写入；②`backend_run` 触发 `IMAI_compute`；③`backend_get_output` 拿 `uvc_ai_result_t` 兼容结构。 |
| `uvc_ai_deinit()` | `backend_deinit` | 内部调 `IMAI_finalize`，恢复 CCR。 |
| `uvc_ai_reset_result()` | `backend_get_output` 的初始化分支 | RT-AK 推荐把 reset 折进 `backend_get_output`。 |
| `uvc_ai_app_start(w,h)` | `backend_init` + 启动 worker 线程 | worker 线程（`uvc_aiwk`）由 RT-AK 统一管理（`backend_set_worker_prio/stack`）。 |
| `uvc_ai_app_process_frame(frame)` | `backend_run` 调用方 | 业务方（USB 帧消费线程）每帧调一次，或通过 ringbuffer 喂给 worker。 |
| `uvc_ai_app_overlay_cb()` | `backend_get_output` + 用户回调 | RT-AK 应当允许 `backend_set_output_cb(cb, ctx)`，由后端推理完成后主动 push。 |
| `uvc_ai_app_enforce_mode(fmt, w, h)` | `backend_config` 的 input_constraints 字段 | 320x240 / YUYV 约束可由 RT-AK 描述符表达。 |
| `ethosu_mutex_*` / `ethosu_semaphore_*` (uvc_ai_ethosu_rtos.c) | RT-AK 平台层的 RTOS shim | RT-AK 应当自带一份 Ethos-U RTOS 抽象；当前实现可作为参考，但 RT-AK 自己的 `rt_ai_backend_t->os_*` 会替代。 |
| `mtb_ml_set_cache_mgmt_type(MTB_ML_ETHOSU_CACHE_MGMT_OUTER_LAYERS)` | `backend_init` 中由 RT-AK 决定 | RT-AK 平台初始化时一次性设置，避免每模型重复。 |
| `mtb_ml_npu_cycles` / `mtb_ml_npu_clk_freq` | RT-AK `backend_get_profile` | 把 NPU 周期换算成 ms 暴露给上层。 |
| `libraries/Common/board/ports/usb/usbh_uvc_app.c` 的 `uvc_frame_thread_entry` | RT-AK 输入端（"生产者"） | 保留作为 RT-AK 的输入适配；只需把 `uvc_ai_app_process_frame(frame)` 替换为 `rt_ai_backend_run(...)`。 |
| `libraries/Common/board/ports/usb/usbh_uvc_display.c` 的 `uvc_display_set_overlay_callback` | RT-AK 输出端（"消费者"） | 保留作为 RT-AK 的输出 sink；只把 overlay callback 内部对 `g_uvc_ai_app.latest_result` 的访问替换为 `rt_ai_backend_get_output`。 |
| `libraries/Common/deepcraft_ai/SConscript` | RT-AK 平台插件的 SConscript | `DefineGroup('DeepcraftAi', ...)` 改为 `DefineGroup('RT-AK-Edgi', ...)`，include path 复用 `tflm_root`、`ethosu_root`、`ml_middleware`。 |
| `BSP_USING_DEEPCRAFT_AI` Kconfig | RT-AK 平台 Kconfig（`RT_AI_USING_EDGI`） | 模型声明依旧走 `Kconfig`/env，让用户选模型。 |
| `board/board.c` 的 `en_gpio` | RT-AK 板级 `INIT_BOARD_EXPORT` 钩子 | RT-AK 后端可以通过 `INIT_BOARD_EXPORT` 自行注册硬件初始化（如 NPU 时钟）。 |

**最小可用 RT-AK 插件骨架（伪代码）**：

```c
// rt_ai_edgi.c
int rt_ai_edgi_init(void) {
    // 1. uvc_ai_sync_model_blob_from_flash()  (uvc_ai.c)
    // 2. SCB->CCR 关闭 UNALIGN_TRP
    // 3. IMAI_init()
    // 4. mtb_ml_set_cache_mgmt_type(MTB_ML_ETHOSU_CACHE_MGMT_OUTER_LAYERS)
    // 5. 预清 0 底部 80 行 padding (g_model_input_u8)
}

int rt_ai_edgi_run(uint8_t *in_u8_320x320x3, float *out_5x8) {
    IMAI_compute(in_u8_320x320x3, out_5x8);
}

const rt_ai_model_desc_t *rt_ai_edgi_model(void) {
    // 用 IMAI_api() 填充：input (uint8 [3,320,320])、output (float [5,8])
}
```

> 这段只是设计草图，**不**进入本次提交。

## 7. 当前还不清楚的问题

需要进一步确认（或向 Infineon/Imagimob/导师）的问题：

1. **模型来源与替换流程**
   - `model.c` 是 ImagiNet Compiler 5.7.3938+5213730ae03159abbdafc49774c1243781f8a3db 生成的；原始 `.tflite` 在哪里？DEEPCRAFT Studio 还是 ImagiNet 工具链？
   - 替换模型时是否仍然要保证 `IMAI_init / IMAI_compute / IMAI_finalize` 三个符号 + 模型 ID 兼容？README 提到"保持导出接口兼容"，但具体能否输入不同 shape 的模型？
2. **模型精度与归一化**
   - `_K3[]` 顶部包含 `0x24, 0x334c4654` 头（`TFL3`），确认是 TFLM flatbuffer 还是其他格式？当前预处理是直接 0~255 RGB888，未做 `IMAGE_MEAN / IMAGE_STD` 归一化，是因为模型内部已经包含？需要看 Imagimob 的训练 pipeline。
   - `IMAI_DATAIN_SHIFT / OFFSET / SCALE` 当前都是 0/0/1，是否所有 Imagimob 模型都不需要预处理？替换模型时怎么适配？
3. **输入输出形状细节**
   - `IMAI_DATAOUT_SHAPE` 是 `(5,8)`，列 5 = `[cx, cy, w, h, det_flag, score0, score1, score2]`（实际是 8 列，见 `uvc_ai.c` 的 `output_columns = 8`、`score_count = output_columns - 5 = 3`、`detection_flag_index = 7`）。为什么 `model.h` 写的 `5`？是否文档错误？`(5,8)` 跟 `(8,5)` 的语义差异需要确认。
   - `IMAI_DATAIN_SHAPE` 写成 `(3, 320, 320)`，但实际内存布局是 `uint8_t[320*240*3 + 80*320*3]`：顶 320x240 RGB888 + 80 行黑边 pad。生成器是不是按 HWC 写的 `3,320,320`？RT-AK 后端要不要把它当 `1x3x320x320` 而不是 `1x320x320x3`？
4. **buffer 大小与对齐**
   - `_state[891920]` / `_buffer[357600]` / `_K3[]` 都在 `.cy_socmem_data`（`m55_data_secondary`），加起来超过 3 MB 吗？RT-AK 后端如果换 CMS 运行（比如把模型放 HyperRAM），需要重新算 section。
   - `g_model_input_u8[307200]` 在 `gfx_mem`，跟 GFXSS framebuffer 同一区域，是否有冲突风险？当前 LCD 只用 512x800x2 = 800 KB，`gfx_mem` 1.3 MB 还有余量。
5. **NPU 委托与 cache 策略**
   - 是否真的用到了 Ethos-U55？`mtb_ml_set_cache_mgmt_type(MTB_ML_ETHOSU_CACHE_MGMT_OUTER_LAYERS)` 看起来是开的，但是否有 fallback 到 CPU 的可能？
   - `__UNALIGNED_UINT32_READ` 在 Cortex-M55 上是 MVE 指令？关闭 UNALIGN_TRP 之后是否所有路径都对齐？RT-AK 后端如果换 CMS 不能简单复制这个 workaround。
6. **Ethos-U55 RTOS 抽象**
   - `applications/uvc_ai_ethosu_rtos.c` 中把 mtb-ml 默认 OS 抽象覆盖成 RT-Thread mutex/semaphore。RT-AK 自己的 Ethos 后端是否需要同样一套？需要确认 NPU 中断是否在 RT-Thread 上跑。
7. **多模型支持**
   - `IMAI_MAX_MTB_MODELS=4`，`IMAI_mtb_models[]` 数组已留出。当前项目只注册一个模型，但 RT-AK 多模型场景下需要正确填充 `IMAI_mtb_models_count`。
8. **MSH 与运行时控制**
   - 当前只通过 `usbh_uvc_start / usbh_uvc_stop` 控制 AI 的启停，**没有运行时切模型 / 切分辨率的 MSH 命令**。RT-AK 是否要新增 `rt_ai_list / rt_ai_run <model> <input>` 等命令？
9. **JPEG / MJPEG 路径**
   - 推理路径只看 YUYV；MJPEG 路径在 `usbh_uvc_display.c` 解码到 RGB565 后渲染，**不会进 AI**。RT-AK 适配时如果想支持 MJPEG 直通，需要扩展 `uvc_ai_process_yuyv` 或加新的 `uvc_ai_process_mjpeg`。
10. **overlay / 显示侧可移植性**
    - overlay 回调直接读写 `lcd_fb` (HyperRAM)，通过 `usbh_uvc_display.c` 的 `uvc_display_set_overlay_callback` 注册。RT-AK 后端如果跑在没有 LCD 的板子上，是否要拆掉 `uvc_ai_app_overlay_cb` 的硬依赖？目前 `uvc_ai_app_start` 末尾**强制**注册 overlay，回调里会读 `info->framebuffer`，在没有 LCD 时会拿到 `RT_NULL` 早返回。
11. **代码版本与升级**
    - 当前 CherryUSB 用了 `libusbh_uvc.a`（预编译）；`RT_CHERRYUSB_HOST_BUILD_FROM_SOURCE` 默认是关的。如果未来 CherryUSB 升级或换主控芯片，UVC 路径上的 `IMAI_mtb_models_print_info / IMAI_init` 桩函数会跟着 lib 走，需要重新确认 ABI。
12. **RT-AK 集成位置**
    - 是把 `libraries/Common/deepcraft_ai/` 整个改造成 RT-AK 插件（保留 IMAI），还是把 `applications/uvc_ai_app.c` + `libraries/Common/deepcraft_ai/src/uvc_ai.c` 抽成 RT-AK 平台后端 + 业务 demo？这个决定关系到 `model.c` 是否要参与 RT-AK 编译。

> 上述 12 条需要在和导师/Infineon 确认之前先冻结，不要在没确认的情况下改源码。
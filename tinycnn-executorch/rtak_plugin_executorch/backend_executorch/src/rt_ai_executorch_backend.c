#include "rt_ai_executorch_backend.h"

#include <rtthread.h>
#include <stdlib.h>

#ifdef RT_USING_FINSH
#include <finsh.h>
#endif

#ifndef RT_AI_EXECUTORCH_DEBUG_LOG
#define RT_AI_EXECUTORCH_DEBUG_LOG 0
#endif

#if RT_AI_EXECUTORCH_DEBUG_LOG
#define RT_AI_TINYCNN_DEBUG_LOG_IF(enabled, ...) \
    do                                      \
    {                                       \
        if (enabled)                        \
        {                                   \
            rt_kprintf(__VA_ARGS__);        \
        }                                   \
    } while (0)
#else
#define RT_AI_TINYCNN_DEBUG_LOG_IF(enabled, ...) \
    do                                      \
    {                                       \
        (void)(enabled);                    \
    } while (0)
#endif

#if defined(RT_AI_EXECUTORCH_MODEL_TINYCNN) && defined(RT_AI_EXECUTORCH_LOAD_EMBEDDED)
#include "rt_ai_tinycnn_model_data.h"
#endif

static const rt_ai_executorch_config_t *g_config;
static rt_ai_executorch_config_t g_resolved_config;

#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
int rt_ai_executorch_runtime_init(const rt_ai_executorch_config_t *config);
void *rt_ai_executorch_runtime_get_input(size_t *size_bytes);
int rt_ai_executorch_runtime_fill_input_ones(void);
int rt_ai_executorch_runtime_run(void);
const void *rt_ai_executorch_runtime_get_output(size_t *size_bytes);
int rt_ai_executorch_runtime_dump_output(size_t max_elems);
void rt_ai_executorch_runtime_set_log_enabled(int enabled);
int rt_ai_executorch_runtime_deinit(void);
#endif

#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
static int rt_ai_executorch_resolve_config(const rt_ai_executorch_config_t *config)
{
    if (config != 0)
    {
        g_resolved_config = *config;
    }
    else
    {
        g_resolved_config.model_name = 0;
        g_resolved_config.pte_data = 0;
        g_resolved_config.pte_size = 0;
    }

#if defined(RT_AI_EXECUTORCH_MODEL_TINYCNN) && defined(RT_AI_EXECUTORCH_LOAD_EMBEDDED)
    if (g_resolved_config.model_name == 0)
    {
        g_resolved_config.model_name = "tinycnn";
    }
    if (g_resolved_config.pte_data == 0 || g_resolved_config.pte_size == 0)
    {
        g_resolved_config.pte_data = rt_ai_tinycnn_model_data;
        g_resolved_config.pte_size = (size_t)rt_ai_tinycnn_model_data_len;
    }
#endif

    if (g_resolved_config.pte_data == 0 || g_resolved_config.pte_size == 0)
    {
        rt_kprintf("[executorch] missing PTE data; pass mapped QSPI data or enable embedded model data\n");
        return RT_AI_EXECUTORCH_EINVAL;
    }

    g_config = &g_resolved_config;
    return RT_AI_EXECUTORCH_OK;
}
#endif

#ifdef RT_USING_FINSH
#define RT_AI_TINYCNN_EXPECTED_PTE_SIZE 31696u
#define RT_AI_TINYCNN_EXPECTED_PTE_FNV1A32 0xDC0BDB6Eu

static int rt_ai_executorch_pte_magic_ok(const uint8_t *data, size_t size)
{
    return data != 0 && size >= 8 &&
           data[4] == 'E' && data[5] == 'T' && data[6] == '1' && data[7] == '2';
}

static uint32_t rt_ai_executorch_fnv1a32(const uint8_t *data, size_t size)
{
    uint32_t hash = 2166136261u;
    size_t i;

    for (i = 0; i < size; ++i)
    {
        hash ^= data[i];
        hash *= 16777619u;
    }

    return hash;
}
#endif

int rt_ai_executorch_init(const rt_ai_executorch_config_t *config)
{
    g_config = config;
#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    int status = rt_ai_executorch_resolve_config(config);
    if (status != RT_AI_EXECUTORCH_OK)
    {
        return status;
    }
    return rt_ai_executorch_runtime_init(g_config);
#else
    (void)g_config;
    (void)g_resolved_config;
    return RT_AI_EXECUTORCH_ENOSYS;
#endif
}

void *rt_ai_executorch_get_input(size_t *size_bytes)
{
#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    return rt_ai_executorch_runtime_get_input(size_bytes);
#else
    if (size_bytes != 0)
    {
        *size_bytes = 0;
    }
    return 0;
#endif
}

int rt_ai_executorch_run(void)
{
#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    return rt_ai_executorch_runtime_run();
#else
    return RT_AI_EXECUTORCH_ENOSYS;
#endif
}

const void *rt_ai_executorch_get_output(size_t *size_bytes)
{
#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    return rt_ai_executorch_runtime_get_output(size_bytes);
#else
    if (size_bytes != 0)
    {
        *size_bytes = 0;
    }
    return 0;
#endif
}

int rt_ai_executorch_deinit(void)
{
#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    int status = rt_ai_executorch_runtime_deinit();
    g_config = 0;
    return status;
#else
    g_config = 0;
    return RT_AI_EXECUTORCH_OK;
#endif
}

#ifdef RT_USING_FINSH
#ifndef RT_AI_EXECUTORCH_RUNTIME_READY
static void tinycnn_print_output_head(const uint8_t *data, size_t size)
{
    size_t i;
    size_t count = size < 16u ? size : 16u;

    rt_kprintf("[TinyCNN] output head bytes=");
    for (i = 0; i < count; ++i)
    {
        rt_kprintf("%02x%s", data[i], (i + 1u == count) ? "" : " ");
    }
    rt_kprintf("\n");
}
#endif

static int tinycnn_output_top1_float4(const void *output, size_t output_size)
{
    const float *values;
    int top1;
    int i;

    if (output == 0 || output_size < (4u * sizeof(float)))
    {
        return -1;
    }

    values = (const float *)output;
    top1 = 0;
    for (i = 1; i < 4; ++i)
    {
        if (values[i] > values[top1])
        {
            top1 = i;
        }
    }

    return top1;
}

static int tinycnn_run_once(int dump_output,
                            int log_enabled,
                            rt_uint32_t *execute_ms,
                            int *top1_out)
{
    int status;
    int deinit_status;
    void *input;
    const void *output;
    size_t input_size = 0;
    size_t output_size = 0;
    rt_uint32_t tick_start;
    rt_uint32_t tick_end;
    rt_uint32_t elapsed_ms;
    int top1;

    if (execute_ms != 0)
    {
        *execute_ms = 0;
    }
    if (top1_out != 0)
    {
        *top1_out = -1;
    }

#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    rt_ai_executorch_runtime_set_log_enabled(log_enabled);
#endif

    if (log_enabled)
    {
        rt_kprintf("[TinyCNN] inference start\n");
    }

    status = rt_ai_executorch_init(0);
    if (status != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] init failed: %d\n", status);
        return status;
    }

    input = rt_ai_executorch_get_input(&input_size);
    RT_AI_TINYCNN_DEBUG_LOG_IF(log_enabled,
                               "[TinyCNN] input addr=0x%08x size=%u\n",
                               (unsigned int)(uintptr_t)input,
                               (unsigned int)input_size);
    if (input == 0 || input_size == 0)
    {
        rt_kprintf("[TinyCNN] input binding failed\n");
        (void)rt_ai_executorch_deinit();
        return RT_AI_EXECUTORCH_EINVAL;
    }

#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    status = rt_ai_executorch_runtime_fill_input_ones();
    if (status != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] input fill failed: %d\n", status);
        (void)rt_ai_executorch_deinit();
        return status;
    }
#else
    rt_kprintf("[TinyCNN] RT_AI_EXECUTORCH_RUNTIME_READY is disabled\n");
    (void)rt_ai_executorch_deinit();
    return RT_AI_EXECUTORCH_ENOSYS;
#endif

    tick_start = rt_tick_get_millisecond();
    status = rt_ai_executorch_run();
    tick_end = rt_tick_get_millisecond();
    elapsed_ms = tick_end - tick_start;
    if (execute_ms != 0)
    {
        *execute_ms = elapsed_ms;
    }

    if (status != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] run failed: %d\n", status);
        (void)rt_ai_executorch_deinit();
        return status;
    }

    output = rt_ai_executorch_get_output(&output_size);
    RT_AI_TINYCNN_DEBUG_LOG_IF(log_enabled,
                               "[TinyCNN] output addr=0x%08x size=%u\n",
                               (unsigned int)(uintptr_t)output,
                               (unsigned int)output_size);
    if (output == 0 || output_size == 0)
    {
        rt_kprintf("[TinyCNN] output binding failed\n");
        (void)rt_ai_executorch_deinit();
        return RT_AI_EXECUTORCH_EINVAL;
    }

    top1 = tinycnn_output_top1_float4(output, output_size);
    if (top1_out != 0)
    {
        *top1_out = top1;
    }

#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    if (dump_output)
    {
        rt_ai_executorch_runtime_dump_output(8u);
    }
#else
    if (dump_output)
    {
        tinycnn_print_output_head((const uint8_t *)output, output_size);
    }
#endif

    deinit_status = rt_ai_executorch_deinit();
    if (deinit_status != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] deinit failed: %d\n", deinit_status);
        return deinit_status;
    }

    if (log_enabled)
    {
        rt_kprintf("[TinyCNN] inference PASS execute_ms=%u top1=%d\n",
                   (unsigned int)elapsed_ms,
                   top1);
    }
    return RT_AI_EXECUTORCH_OK;
}

static int tinycnn_run(int argc, char **argv)
{
    (void)argc;
    (void)argv;

    return tinycnn_run_once(1, 1, 0, 0);
}
MSH_CMD_EXPORT(tinycnn_run, run TinyCNN ExecuTorch inference once);

static int tinycnn_parse_loop_count(int argc, char **argv)
{
    int count = 10;

    if (argc >= 2 && argv[1] != 0)
    {
        count = atoi(argv[1]);
    }

    if (count <= 0)
    {
        count = 1;
    }
    if (count > 1000)
    {
        count = 1000;
    }

    return count;
}

static int tinycnn_run_loop(int argc, char **argv)
{
    int count = tinycnn_parse_loop_count(argc, argv);
    int pass = 0;
    int fail = 0;
    int last_status = RT_AI_EXECUTORCH_OK;
    int expected_top1 = -1;
    rt_uint32_t min_ms = 0xffffffffu;
    rt_uint32_t max_ms = 0;
    rt_uint64_t sum_ms = 0;
    int i;

    rt_kprintf("[TinyCNN] loop start count=%d\n", count);

    for (i = 0; i < count; ++i)
    {
        rt_uint32_t execute_ms = 0;
        int top1 = -1;
        int status;

        status = tinycnn_run_once(0, 0, &execute_ms, &top1);
        if (status == RT_AI_EXECUTORCH_OK)
        {
            if (expected_top1 < 0)
            {
                expected_top1 = top1;
            }
            if (execute_ms < min_ms)
            {
                min_ms = execute_ms;
            }
            if (execute_ms > max_ms)
            {
                max_ms = execute_ms;
            }
            sum_ms += execute_ms;
            pass++;
        }
        else
        {
            fail++;
            last_status = status;
        }

        rt_kprintf("[TinyCNN] loop %d/%d status=%d execute_ms=%u top1=%d\n",
                   i + 1,
                   count,
                   status,
                   (unsigned int)execute_ms,
                   top1);

        if (status != RT_AI_EXECUTORCH_OK)
        {
            break;
        }
        if (top1 != expected_top1)
        {
            rt_kprintf("[TinyCNN] loop top1 changed: expected=%d got=%d\n",
                       expected_top1,
                       top1);
            fail++;
            last_status = RT_AI_EXECUTORCH_EIO;
            break;
        }
    }

    if (pass == 0)
    {
        min_ms = 0;
    }

    rt_kprintf("[TinyCNN] loop summary count=%d pass=%d fail=%d min_ms=%u max_ms=%u avg_ms=%u top1=%d\n",
               count,
               pass,
               fail,
               (unsigned int)min_ms,
               (unsigned int)max_ms,
               pass > 0 ? (unsigned int)(sum_ms / (rt_uint64_t)pass) : 0u,
               expected_top1);

    return (fail == 0 && pass == count) ? RT_AI_EXECUTORCH_OK : last_status;
}
MSH_CMD_EXPORT(tinycnn_run_loop, run TinyCNN ExecuTorch inference loop);

static int tinycnn_artifact_check(int argc, char **argv)
{
    const uint8_t *data = 0;
    size_t size = 0;
    uint8_t head[8] = {0};
    uint32_t fnv1a32;
    unsigned int i;
    int aligned16;
    int magic_ok;
    int size_ok;
    int fnv_ok;

    (void)argc;
    (void)argv;

#if defined(RT_AI_EXECUTORCH_MODEL_TINYCNN) && defined(RT_AI_EXECUTORCH_LOAD_EMBEDDED)
    data = rt_ai_tinycnn_model_data;
    size = (size_t)rt_ai_tinycnn_model_data_len;
#else
    if (g_config != 0 && g_config->pte_data != 0 && g_config->pte_size != 0)
    {
        data = g_config->pte_data;
        size = g_config->pte_size;
    }
#endif

    if (data == 0 || size == 0)
    {
        rt_kprintf("[tinycnn] no PTE data is available in embedded config\n");
        rt_kprintf("[tinycnn] qspi mode must pass mapped PTE data through rt_ai_executorch_init()\n");
        return RT_AI_EXECUTORCH_EINVAL;
    }

    for (i = 0; i < sizeof(head) && i < size; ++i)
    {
        head[i] = data[i];
    }

    fnv1a32 = rt_ai_executorch_fnv1a32(data, size);
    aligned16 = (((uintptr_t)data & 0x0fu) == 0u);
    magic_ok = rt_ai_executorch_pte_magic_ok(data, size);
    size_ok = (size == RT_AI_TINYCNN_EXPECTED_PTE_SIZE);
    fnv_ok = (fnv1a32 == RT_AI_TINYCNN_EXPECTED_PTE_FNV1A32);

    rt_kprintf("[tinycnn] pte_addr=0x%08x\n", (unsigned int)(uintptr_t)data);
    rt_kprintf("[tinycnn] pte_size=%u expected=%u %s\n",
               (unsigned int)size,
               (unsigned int)RT_AI_TINYCNN_EXPECTED_PTE_SIZE,
               size_ok ? "OK" : "FAIL");
    rt_kprintf("[tinycnn] pte_head=%02x %02x %02x %02x %02x %02x %02x %02x magic=%s\n",
               head[0], head[1], head[2], head[3], head[4], head[5], head[6], head[7],
               magic_ok ? "ET12" : "FAIL");
    rt_kprintf("[tinycnn] aligned16=%s\n", aligned16 ? "OK" : "FAIL");
    rt_kprintf("[tinycnn] fnv1a32=0x%08x expected=0x%08x %s\n",
               fnv1a32,
               (unsigned int)RT_AI_TINYCNN_EXPECTED_PTE_FNV1A32,
               fnv_ok ? "OK" : "FAIL");
    rt_kprintf("[tinycnn] artifact_check=%s\n",
               (size_ok && magic_ok && aligned16 && fnv_ok) ? "PASS" : "FAIL");

    return (size_ok && magic_ok && aligned16 && fnv_ok) ? RT_AI_EXECUTORCH_OK : RT_AI_EXECUTORCH_EINVAL;
}
MSH_CMD_EXPORT(tinycnn_artifact_check, verify TinyCNN ExecuTorch PTE artifact);
#endif


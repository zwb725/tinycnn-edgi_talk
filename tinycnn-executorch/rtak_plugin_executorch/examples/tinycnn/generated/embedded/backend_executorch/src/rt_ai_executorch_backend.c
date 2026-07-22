#include "rt_ai_executorch_backend.h"

#include <rtthread.h>

#ifdef RT_USING_FINSH
#include <finsh.h>
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

static int tinycnn_run(int argc, char **argv)
{
    int status;
    void *input;
    const void *output;
    size_t input_size = 0;
    size_t output_size = 0;

    (void)argc;
    (void)argv;

    rt_kprintf("[TinyCNN] inference start\n");

    status = rt_ai_executorch_init(0);
    if (status != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] init failed: %d\n", status);
        return status;
    }

    input = rt_ai_executorch_get_input(&input_size);
    rt_kprintf("[TinyCNN] input addr=0x%08x size=%u\n",
               (unsigned int)(uintptr_t)input,
               (unsigned int)input_size);
    if (input == 0 || input_size == 0)
    {
        rt_kprintf("[TinyCNN] input binding failed\n");
        rt_ai_executorch_deinit();
        return RT_AI_EXECUTORCH_EINVAL;
    }

#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    status = rt_ai_executorch_runtime_fill_input_ones();
    if (status != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] input fill failed: %d\n", status);
        rt_ai_executorch_deinit();
        return status;
    }
#else
    rt_kprintf("[TinyCNN] RT_AI_EXECUTORCH_RUNTIME_READY is disabled\n");
    rt_ai_executorch_deinit();
    return RT_AI_EXECUTORCH_ENOSYS;
#endif

    status = rt_ai_executorch_run();
    if (status != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] run failed: %d\n", status);
        rt_ai_executorch_deinit();
        return status;
    }

    output = rt_ai_executorch_get_output(&output_size);
    rt_kprintf("[TinyCNN] output addr=0x%08x size=%u\n",
               (unsigned int)(uintptr_t)output,
               (unsigned int)output_size);
    if (output == 0 || output_size == 0)
    {
        rt_kprintf("[TinyCNN] output binding failed\n");
        rt_ai_executorch_deinit();
        return RT_AI_EXECUTORCH_EINVAL;
    }

#ifdef RT_AI_EXECUTORCH_RUNTIME_READY
    rt_ai_executorch_runtime_dump_output(8u);
#else
    tinycnn_print_output_head((const uint8_t *)output, output_size);
#endif

    rt_ai_executorch_deinit();
    rt_kprintf("[TinyCNN] inference PASS\n");
    return RT_AI_EXECUTORCH_OK;
}
MSH_CMD_EXPORT(tinycnn_run, run TinyCNN ExecuTorch inference once);

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


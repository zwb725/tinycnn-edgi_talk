#include <rtconfig.h>
#include <rtthread.h>

#include <stddef.h>
#include <stdint.h>

#include "rt_ai_executorch_backend.h"
#include "rt_ai_tinycnn_model_data.h"

#if defined(RT_AI_USE_EDGI) || defined(USE_IMAI_GESTURE)
#error "TinyCNN ExecuTorch and DeepCraft / IMAI must not own Ethos-U55 at the same time"
#endif

#if defined(RT_AI_EXECUTORCH_RUNTIME_READY)
#error "RT_AI_EXECUTORCH_RUNTIME_READY is set, but no real E84 ExecuTorch runtime port is present"
#endif

#define TINYCNN_PTE_EXPECTED_SIZE       (31696U)
#define TINYCNN_PTE_EXPECTED_FNV1A32    (0xDC0BDB6EU)
#define TINYCNN_INPUT_BYTES             (1U * 3U * 96U * 96U * 4U)
#define TINYCNN_OUTPUT_BYTES            (1U * 4U * 4U)

static int tinycnn_pte_header_is_valid(void)
{
    return rt_ai_tinycnn_model_data_len >= 8U &&
           rt_ai_tinycnn_model_data[4] == (uint8_t)'E' &&
           rt_ai_tinycnn_model_data[5] == (uint8_t)'T' &&
           rt_ai_tinycnn_model_data[6] == (uint8_t)'1' &&
           rt_ai_tinycnn_model_data[7] == (uint8_t)'2';
}

static uint32_t tinycnn_pte_fnv1a32(const uint8_t *data, uint32_t size)
{
    uint32_t hash = 2166136261U;
    uint32_t i;

    for (i = 0; i < size; ++i)
    {
        hash ^= data[i];
        hash *= 16777619U;
    }

    return hash;
}

static int tinycnn_validate_artifact(void)
{
    uint32_t pte_hash;

    rt_kprintf("[TinyCNN] PTE addr=0x%08x\r\n",
               (unsigned int)(uintptr_t)rt_ai_tinycnn_model_data);
    rt_kprintf("[TinyCNN] PTE size=%u\r\n",
               (unsigned int)rt_ai_tinycnn_model_data_len);
    rt_kprintf("[TinyCNN] PTE expected length=%u\r\n",
               (unsigned int)TINYCNN_PTE_EXPECTED_SIZE);

    if (rt_ai_tinycnn_model_data_len != TINYCNN_PTE_EXPECTED_SIZE)
    {
        rt_kprintf("[TinyCNN] PTE length check FAIL\r\n");
        return -RT_ERROR;
    }

    if (!tinycnn_pte_header_is_valid())
    {
        rt_kprintf("[TinyCNN] PTE ET12 header check FAIL\r\n");
        return -RT_ERROR;
    }

    pte_hash = tinycnn_pte_fnv1a32(rt_ai_tinycnn_model_data,
                                   (uint32_t)rt_ai_tinycnn_model_data_len);
    rt_kprintf("[TinyCNN] PTE fnv1a32=0x%08x\r\n", (unsigned int)pte_hash);
    rt_kprintf("[TinyCNN] PTE expected fnv1a32=0x%08x\r\n",
               (unsigned int)TINYCNN_PTE_EXPECTED_FNV1A32);

    if (pte_hash != TINYCNN_PTE_EXPECTED_FNV1A32)
    {
        rt_kprintf("[TinyCNN] PTE hash check FAIL\r\n");
        return -RT_ERROR;
    }

    rt_kprintf("[TinyCNN] PTE length/header/hash check PASS\r\n");
    return RT_EOK;
}

static int tinycnn_board_test(int argc, char **argv)
{
    int ret;

    RT_UNUSED(argc);
    RT_UNUSED(argv);

    rt_kprintf("[TinyCNN] board test start\r\n");
    ret = tinycnn_validate_artifact();
    if (ret != RT_EOK)
    {
        return ret;
    }

    rt_kprintf("[TinyCNN] input=[1,3,96,96], float32\r\n");
    rt_kprintf("[TinyCNN] output=[1,4], float32\r\n");
    rt_kprintf("[TinyCNN] ExecuTorch target runtime is not available in this BSP\r\n");
    rt_kprintf("[TinyCNN] Program/Method/Allocator/Delegate not executed\r\n");
    rt_kprintf("[TinyCNN] waiting for runtime porting\r\n");

    return RT_AI_EXECUTORCH_ENOSYS;
}
MSH_CMD_EXPORT(tinycnn_board_test, probe TinyCNN ExecuTorch embedded PTE without running inference);

static int tinycnn_artifact_check(int argc, char **argv)
{
    RT_UNUSED(argc);
    RT_UNUSED(argv);

    rt_kprintf("[TinyCNN] artifact check start\r\n");
    return tinycnn_validate_artifact();
}
MSH_CMD_EXPORT(tinycnn_artifact_check, check TinyCNN ExecuTorch embedded PTE artifact);

static int tinycnn_runtime_probe(int argc, char **argv)
{
    rt_ai_executorch_config_t config;
    size_t input_size = 0;
    size_t output_size = 0;
    void *input = RT_NULL;
    const void *output = RT_NULL;
    int ret;

    RT_UNUSED(argc);
    RT_UNUSED(argv);

    rt_kprintf("[TinyCNN] runtime probe start\r\n");
    ret = tinycnn_validate_artifact();
    if (ret != RT_EOK)
    {
        rt_kprintf("[TinyCNN] runtime probe blocked: artifact invalid\r\n");
        return ret;
    }

    config.model_name = "tinycnn";
    config.pte_data = rt_ai_tinycnn_model_data;
    config.pte_size = (size_t)rt_ai_tinycnn_model_data_len;

    rt_kprintf("[TinyCNN] backend interface=rt_ai_executorch\r\n");
    rt_kprintf("[TinyCNN] model=%s\r\n", config.model_name);
    rt_kprintf("[TinyCNN] expected input bytes=%u\r\n", (unsigned int)TINYCNN_INPUT_BYTES);
    rt_kprintf("[TinyCNN] expected output bytes=%u\r\n", (unsigned int)TINYCNN_OUTPUT_BYTES);

    ret = rt_ai_executorch_init(&config);
    rt_kprintf("[TinyCNN] rt_ai_executorch_init=%d\r\n", ret);

    if (ret == RT_AI_EXECUTORCH_ENOSYS)
    {
        rt_kprintf("[TinyCNN] runtime status=NOT_PORTED\r\n");
        rt_kprintf("[TinyCNN] missing Program/Method/Allocator/Ethos-U delegate/tensor binding\r\n");
        rt_ai_executorch_deinit();
        return ret;
    }

    if (ret != RT_AI_EXECUTORCH_OK)
    {
        rt_kprintf("[TinyCNN] runtime status=INIT_FAIL\r\n");
        rt_ai_executorch_deinit();
        return ret;
    }

    input = rt_ai_executorch_get_input(&input_size);
    output = rt_ai_executorch_get_output(&output_size);

    rt_kprintf("[TinyCNN] input ptr=0x%08x size=%u\r\n",
               (unsigned int)(uintptr_t)input,
               (unsigned int)input_size);
    rt_kprintf("[TinyCNN] output ptr=0x%08x size=%u\r\n",
               (unsigned int)(uintptr_t)output,
               (unsigned int)output_size);
    rt_kprintf("[TinyCNN] runtime status=INIT_PASS_RUN_NOT_EXECUTED\r\n");

    rt_ai_executorch_deinit();
    return RT_EOK;
}
MSH_CMD_EXPORT(tinycnn_runtime_probe, probe TinyCNN ExecuTorch runtime integration boundary);

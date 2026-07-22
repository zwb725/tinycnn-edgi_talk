/*
 * Minimal Edgi RT-AK standard API validation demo.
 *
 * This demo verifies:
 * - rt_ai_register()
 * - rt_ai_find()
 * - rt_ai_init()
 * - rt_ai_input()
 * - rt_ai_run()
 * - rt_ai_output()
 * - backend_edgi -> IMAI_compute
 *
 * It intentionally does not use:
 * - UVC camera
 * - LCD overlay
 * - model-specific postprocess
 */

#include <rtthread.h>
#include <stdint.h>

#include "rt_ai.h"
#include "rt_ai_edgi_active_model.h"

#define RT_AI_EDGI_DEMO_THREAD_STACK_SIZE  (65536U)
#define RT_AI_EDGI_DEMO_THREAD_PRIORITY    (20)
#define RT_AI_EDGI_DEMO_THREAD_TICK        (10)

static rt_uint8_t g_rt_ai_edgi_demo_stack[RT_AI_EDGI_DEMO_THREAD_STACK_SIZE];
static struct rt_thread g_rt_ai_edgi_demo_thread;
static struct rt_semaphore g_rt_ai_edgi_demo_sem;
static rt_bool_t g_rt_ai_edgi_demo_thread_started = RT_FALSE;
static rt_bool_t g_rt_ai_edgi_demo_running = RT_FALSE;

static void rt_ai_edgi_fill_test_input(uint8_t *input, uint32_t size)
{
    uint32_t i;

    if (input == RT_NULL)
    {
        return;
    }

    for (i = 0; i < size; i++)
    {
        input[i] = (uint8_t)(i & 0xFFU);
    }
}

static void rt_ai_edgi_print_output_as_hex(const float *output, uint32_t count)
{
    uint32_t i;

    if (output == RT_NULL)
    {
        rt_kprintf("output is NULL\r\n");
        return;
    }

    for (i = 0; i < count; i++)
    {
        union
        {
            float f;
            uint32_t u32;
        } v;

        v.f = output[i];

        /*
         * Avoid depending on float printf support.
         */
        rt_kprintf("out[%02d] = 0x%08x\r\n", i, v.u32);
    }
}

static void rt_ai_edgi_minimal_demo_run_once(void)
{
    int ret;
    rt_ai_t model;
    uint8_t *input;
    float *output;

    rt_kprintf("RT-AK Edgi standard API demo start\r\n");

    model = rt_ai_find(RT_AI_EDGI_ACTIVE_MODEL_NAME);
    if (model == RT_NULL)
    {
        rt_kprintf("rt_ai_find failed: %s\r\n", RT_AI_EDGI_ACTIVE_MODEL_NAME);
        goto out;
    }

    rt_kprintf("rt_ai_find success: %s\r\n", RT_AI_EDGI_ACTIVE_MODEL_NAME);

    ret = rt_ai_init(model, RT_NULL);
    if (ret != RT_AI_OK)
    {
        rt_kprintf("rt_ai_init failed: %d\r\n", ret);
        goto out;
    }

    rt_kprintf("rt_ai_init success\r\n");

    input = (uint8_t *)rt_ai_input(model, 0);
    if (input == RT_NULL)
    {
        rt_kprintf("rt_ai_input failed\r\n");
        goto out;
    }

    rt_kprintf("rt_ai_input success: %p\r\n", input);

    rt_ai_edgi_fill_test_input(input, RT_AI_EDGI_ACTIVE_INPUT_BYTES);

    ret = rt_ai_run(model, RT_NULL, RT_NULL);
    if (ret != RT_AI_OK)
    {
        rt_kprintf("rt_ai_run failed: %d\r\n", ret);
        goto out;
    }

    rt_kprintf("rt_ai_run success\r\n");

    output = (float *)rt_ai_output(model, 0);
    if (output == RT_NULL)
    {
        rt_kprintf("rt_ai_output failed\r\n");
        goto out;
    }

    rt_kprintf("rt_ai_output success: %p\r\n", output);

    rt_ai_edgi_print_output_as_hex(output, RT_AI_EDGI_ACTIVE_OUTPUT_COUNT);

    rt_kprintf("RT-AK Edgi standard API demo end\r\n");

out:
    return;
}

static void rt_ai_edgi_minimal_demo_thread_entry(void *parameter)
{
    RT_UNUSED(parameter);

    while (1)
    {
        if (rt_sem_take(&g_rt_ai_edgi_demo_sem, RT_WAITING_FOREVER) != RT_EOK)
        {
            continue;
        }

        rt_ai_edgi_minimal_demo_run_once();
        g_rt_ai_edgi_demo_running = RT_FALSE;
    }
}

static rt_err_t rt_ai_edgi_minimal_demo_ensure_thread(void)
{
    rt_err_t ret;

    if (g_rt_ai_edgi_demo_thread_started)
    {
        return RT_EOK;
    }

    ret = rt_sem_init(&g_rt_ai_edgi_demo_sem, "edgi_sem", 0, RT_IPC_FLAG_FIFO);
    if (ret != RT_EOK)
    {
        rt_kprintf("RT-AK Edgi demo sem init failed: %d\r\n", ret);
        return ret;
    }

    ret = rt_thread_init(&g_rt_ai_edgi_demo_thread,
                         "edgi_demo",
                         rt_ai_edgi_minimal_demo_thread_entry,
                         RT_NULL,
                         g_rt_ai_edgi_demo_stack,
                         sizeof(g_rt_ai_edgi_demo_stack),
                         RT_AI_EDGI_DEMO_THREAD_PRIORITY,
                         RT_AI_EDGI_DEMO_THREAD_TICK);
    if (ret != RT_EOK)
    {
        rt_sem_detach(&g_rt_ai_edgi_demo_sem);
        rt_kprintf("RT-AK Edgi demo thread init failed: %d\r\n", ret);
        return ret;
    }

    ret = rt_thread_startup(&g_rt_ai_edgi_demo_thread);
    if (ret != RT_EOK)
    {
        rt_thread_detach(&g_rt_ai_edgi_demo_thread);
        rt_sem_detach(&g_rt_ai_edgi_demo_sem);
        rt_kprintf("RT-AK Edgi demo thread startup failed: %d\r\n", ret);
        return ret;
    }

    g_rt_ai_edgi_demo_thread_started = RT_TRUE;
    return RT_EOK;
}

static int rt_ai_edgi_minimal_demo(int argc, char **argv)
{
    rt_err_t ret;

    RT_UNUSED(argc);
    RT_UNUSED(argv);

    if (g_rt_ai_edgi_demo_running)
    {
        rt_kprintf("RT-AK Edgi minimal demo is already running\r\n");
        return -RT_EBUSY;
    }

    ret = rt_ai_edgi_minimal_demo_ensure_thread();
    if (ret != RT_EOK)
    {
        return ret;
    }

    g_rt_ai_edgi_demo_running = RT_TRUE;
    ret = rt_sem_release(&g_rt_ai_edgi_demo_sem);
    if (ret != RT_EOK)
    {
        g_rt_ai_edgi_demo_running = RT_FALSE;
        rt_kprintf("RT-AK Edgi demo sem release failed: %d\r\n", ret);
        return ret;
    }

    rt_kprintf("RT-AK Edgi minimal demo scheduled\r\n");
    return RT_EOK;
}
MSH_CMD_EXPORT(rt_ai_edgi_minimal_demo, run Edgi model through standard RT-AK API);

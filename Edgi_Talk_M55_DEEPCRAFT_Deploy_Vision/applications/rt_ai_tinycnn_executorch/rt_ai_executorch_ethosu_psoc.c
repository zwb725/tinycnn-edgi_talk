#include "rt_ai_executorch_backend.h"

#include <rtconfig.h>
#include <rtthread.h>

#include <cy_pdl.h>
#include <ethosu_driver.h>
#include <system_edge.h>

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#ifndef RT_USING_SEMAPHORE
#error "ExecuTorch Ethos-U platform port requires RT_USING_SEMAPHORE"
#endif

#ifndef RT_AI_EXECUTORCH_ETHOSU_IRQ_PRIORITY
#define RT_AI_EXECUTORCH_ETHOSU_IRQ_PRIORITY (5u)
#endif

#ifndef RT_AI_EXECUTORCH_ETHOSU_WAIT_TIMEOUT_MS
#define RT_AI_EXECUTORCH_ETHOSU_WAIT_TIMEOUT_MS (5000u)
#endif

#ifndef RT_AI_EXECUTORCH_ETHOSU_CACHE_RANGE
#define RT_AI_EXECUTORCH_ETHOSU_CACHE_RANGE 0
#endif

#ifndef RT_AI_EXECUTORCH_ETHOSU_CACHE_LINE_SIZE
#define RT_AI_EXECUTORCH_ETHOSU_CACHE_LINE_SIZE 32u
#endif

#ifndef RT_AI_EXECUTORCH_DEBUG_LOG
#define RT_AI_EXECUTORCH_DEBUG_LOG 0
#endif

#if RT_AI_EXECUTORCH_DEBUG_LOG
extern int rt_ai_executorch_runtime_log_enabled(void) __attribute__((weak));
static bool rt_ai_executorch_ethosu_log_enabled(void)
{
    return rt_ai_executorch_runtime_log_enabled == 0 ||
           rt_ai_executorch_runtime_log_enabled() != 0;
}
#define RT_AI_EXECUTORCH_ETHOSU_DEBUG_LOG(...)       \
    do                                               \
    {                                                \
        if (rt_ai_executorch_ethosu_log_enabled())   \
        {                                            \
            rt_kprintf(__VA_ARGS__);                 \
        }                                            \
    } while (0)
#else
#define RT_AI_EXECUTORCH_ETHOSU_DEBUG_LOG(...)       \
    do                                               \
    {                                                \
    } while (0)
#endif

#ifndef ETHOSU_SEMAPHORE_WAIT_FOREVER
#define ETHOSU_SEMAPHORE_WAIT_FOREVER UINT64_MAX
#endif

static struct ethosu_driver g_executorch_ethosu_driver;
static cy_stc_sysint_t g_executorch_ethosu_irq_cfg;
static rt_uint32_t g_executorch_ethosu_ipc_index;
static bool g_executorch_ethosu_initialized;

static void rt_ai_executorch_ethosu_make_name(const char *prefix,
                                              char *name,
                                              rt_size_t size)
{
    rt_base_t level;
    rt_uint32_t index;

    level = rt_hw_interrupt_disable();
    index = g_executorch_ethosu_ipc_index++;
    rt_hw_interrupt_enable(level);

    rt_snprintf(name, size, "%s%u", prefix, (unsigned int)(index % 1000U));
}

static rt_int32_t rt_ai_executorch_ethosu_timeout_to_ticks(uint64_t timeout)
{
    uint64_t ticks;

    if (timeout == ETHOSU_SEMAPHORE_WAIT_FOREVER)
    {
        timeout = RT_AI_EXECUTORCH_ETHOSU_WAIT_TIMEOUT_MS;
    }

    if (timeout == 0U)
    {
        return RT_WAITING_NO;
    }

    ticks = (timeout * (uint64_t)RT_TICK_PER_SECOND + 999ULL) / 1000ULL;
    if (ticks == 0U)
    {
        ticks = 1U;
    }

    if (ticks > 0x7fffffffULL)
    {
        return RT_WAITING_FOREVER;
    }

    return (rt_int32_t)ticks;
}

void *ethosu_mutex_create(void)
{
    char name[RT_NAME_MAX];

    rt_ai_executorch_ethosu_make_name("emu", name, sizeof(name));
    return (void *)rt_mutex_create(name, RT_IPC_FLAG_PRIO);
}

void ethosu_mutex_destroy(void *mutex)
{
    if (mutex != RT_NULL)
    {
        (void)rt_mutex_delete((rt_mutex_t)mutex);
    }
}

int ethosu_mutex_lock(void *mutex)
{
    if (mutex == RT_NULL)
    {
        return -1;
    }

    return (rt_mutex_take((rt_mutex_t)mutex, RT_WAITING_FOREVER) == RT_EOK) ? 0 : -1;
}

int ethosu_mutex_unlock(void *mutex)
{
    if (mutex == RT_NULL)
    {
        return -1;
    }

    return (rt_mutex_release((rt_mutex_t)mutex) == RT_EOK) ? 0 : -1;
}

void *ethosu_semaphore_create(void)
{
    char name[RT_NAME_MAX];

    rt_ai_executorch_ethosu_make_name("ese", name, sizeof(name));
    return (void *)rt_sem_create(name, 0, RT_IPC_FLAG_PRIO);
}

void ethosu_semaphore_destroy(void *sem)
{
    if (sem != RT_NULL)
    {
        (void)rt_sem_delete((rt_sem_t)sem);
    }
}

int ethosu_semaphore_take(void *sem, uint64_t timeout)
{
    rt_int32_t wait_ticks;

    if (sem == RT_NULL)
    {
        return -1;
    }

    wait_ticks = rt_ai_executorch_ethosu_timeout_to_ticks(timeout);
    return (rt_sem_take((rt_sem_t)sem, wait_ticks) == RT_EOK) ? 0 : -1;
}

int ethosu_semaphore_give(void *sem)
{
    rt_err_t ret;

    if (sem == RT_NULL)
    {
        return -1;
    }

    ret = rt_sem_release((rt_sem_t)sem);
    if ((ret == RT_EOK) || (ret == -RT_EFULL))
    {
        return 0;
    }

    return -1;
}

static void rt_ai_executorch_ethosu_clean_dcache_whole(void)
{
#if (__DCACHE_PRESENT == 1U)
    if ((SCB->CCR & SCB_CCR_DC_Msk) != 0U)
    {
        SCB_CleanDCache();
    }
#endif
}

static void rt_ai_executorch_ethosu_invalidate_dcache_whole(void)
{
#if (__DCACHE_PRESENT == 1U)
    if ((SCB->CCR & SCB_CCR_DC_Msk) != 0U)
    {
        SCB_CleanInvalidateDCache();
    }
#endif
}

#if RT_AI_EXECUTORCH_ETHOSU_CACHE_RANGE
static int rt_ai_executorch_ethosu_apply_dcache_ranges(const uint64_t *base_addr,
                                                       const size_t *base_addr_size,
                                                       int num_base_addr,
                                                       bool invalidate)
{
#if (__DCACHE_PRESENT == 1U)
    uintptr_t line_mask;
    int i;

    if ((SCB->CCR & SCB_CCR_DC_Msk) == 0U)
    {
        return 1;
    }

    if (RT_AI_EXECUTORCH_ETHOSU_CACHE_LINE_SIZE == 0u ||
        (RT_AI_EXECUTORCH_ETHOSU_CACHE_LINE_SIZE & (RT_AI_EXECUTORCH_ETHOSU_CACHE_LINE_SIZE - 1u)) != 0u)
    {
        return 0;
    }

    line_mask = (uintptr_t)RT_AI_EXECUTORCH_ETHOSU_CACHE_LINE_SIZE - 1u;

    if (num_base_addr < 0 || (num_base_addr > 0 && (base_addr == RT_NULL || base_addr_size == RT_NULL)))
    {
        return 0;
    }

    for (i = 0; i < num_base_addr; ++i)
    {
        uintptr_t start;
        uintptr_t end;
        uintptr_t aligned_start;
        uintptr_t aligned_end;
        uintptr_t aligned_size;

        if (base_addr_size[i] == 0u)
        {
            continue;
        }
        if (base_addr[i] > (uint64_t)UINTPTR_MAX)
        {
            return 0;
        }

        start = (uintptr_t)base_addr[i];
        if ((uintptr_t)base_addr_size[i] > (UINTPTR_MAX - start))
        {
            return 0;
        }

        end = start + (uintptr_t)base_addr_size[i];
        if (end > (UINTPTR_MAX - line_mask))
        {
            return 0;
        }

        aligned_start = start & ~line_mask;
        aligned_end = (end + line_mask) & ~line_mask;
        if (aligned_end <= aligned_start)
        {
            return 0;
        }

        aligned_size = aligned_end - aligned_start;
        if (aligned_size > (uintptr_t)INT32_MAX)
        {
            return 0;
        }

        if (invalidate)
        {
            SCB_InvalidateDCache_by_Addr((uint32_t *)aligned_start, (int32_t)aligned_size);
        }
        else
        {
            SCB_CleanDCache_by_Addr((uint32_t *)aligned_start, (int32_t)aligned_size);
        }
    }

    return 1;
#else
    RT_UNUSED(base_addr);
    RT_UNUSED(base_addr_size);
    RT_UNUSED(num_base_addr);
    RT_UNUSED(invalidate);
    return 1;
#endif
}
#endif

void ethosu_flush_dcache(const uint64_t *base_addr,
                         const size_t *base_addr_size,
                         int num_base_addr)
{
#if RT_AI_EXECUTORCH_ETHOSU_CACHE_RANGE
    if (!rt_ai_executorch_ethosu_apply_dcache_ranges(base_addr, base_addr_size, num_base_addr, false))
    {
        rt_ai_executorch_ethosu_clean_dcache_whole();
    }
#else
    RT_UNUSED(base_addr);
    RT_UNUSED(base_addr_size);
    RT_UNUSED(num_base_addr);
    rt_ai_executorch_ethosu_clean_dcache_whole();
#endif
}

void ethosu_invalidate_dcache(const uint64_t *base_addr,
                              const size_t *base_addr_size,
                              int num_base_addr)
{
#if RT_AI_EXECUTORCH_ETHOSU_CACHE_RANGE
    if (!rt_ai_executorch_ethosu_apply_dcache_ranges(base_addr, base_addr_size, num_base_addr, true))
    {
        rt_ai_executorch_ethosu_invalidate_dcache_whole();
    }
#else
    RT_UNUSED(base_addr);
    RT_UNUSED(base_addr_size);
    RT_UNUSED(num_base_addr);
    rt_ai_executorch_ethosu_invalidate_dcache_whole();
#endif
}

static void rt_ai_executorch_ethosu_irq_handler(void)
{
    if (g_executorch_ethosu_initialized)
    {
        ethosu_irq_handler(&g_executorch_ethosu_driver);
    }
}

int rt_ai_executorch_ethosu_platform_init(void)
{
    cy_en_sysint_status_t irq_status;
    int driver_status;

    if (g_executorch_ethosu_initialized)
    {
        return RT_AI_EXECUTORCH_OK;
    }

    memset(&g_executorch_ethosu_driver, 0, sizeof(g_executorch_ethosu_driver));
    memset(&g_executorch_ethosu_irq_cfg, 0, sizeof(g_executorch_ethosu_irq_cfg));

    RT_AI_EXECUTORCH_ETHOSU_DEBUG_LOG("[executorch] Ethos-U platform init start irq=%d base=0x%08x\n",
                                      (int)mxu55_interrupt_npu_IRQn,
                                      (unsigned int)U550_BASE);

    g_executorch_ethosu_irq_cfg.intrSrc = mxu55_interrupt_npu_IRQn;
    g_executorch_ethosu_irq_cfg.intrPriority = RT_AI_EXECUTORCH_ETHOSU_IRQ_PRIORITY;

    irq_status = Cy_SysInt_Init(&g_executorch_ethosu_irq_cfg,
                                rt_ai_executorch_ethosu_irq_handler);
    if (irq_status != CY_SYSINT_SUCCESS)
    {
        rt_kprintf("[executorch] Ethos-U IRQ init failed: 0x%08x\n",
                   (unsigned int)irq_status);
        return RT_AI_EXECUTORCH_EIO;
    }

    NVIC_ClearPendingIRQ(g_executorch_ethosu_irq_cfg.intrSrc);
    NVIC_EnableIRQ(g_executorch_ethosu_irq_cfg.intrSrc);

    Cy_SysEnableU55(true);

    driver_status = ethosu_init(&g_executorch_ethosu_driver,
                                (void *const)U550_BASE,
                                NULL,
                                0,
                                0,
                                1);
    if (driver_status != 0)
    {
        NVIC_DisableIRQ(g_executorch_ethosu_irq_cfg.intrSrc);
        Cy_SysEnableU55(false);
        rt_kprintf("[executorch] ethosu_init failed: %d\n", driver_status);
        return RT_AI_EXECUTORCH_EIO;
    }

    g_executorch_ethosu_initialized = true;
    RT_AI_EXECUTORCH_ETHOSU_DEBUG_LOG("[executorch] Ethos-U platform init ok irq=%d base=0x%08x\n",
                                      (int)g_executorch_ethosu_irq_cfg.intrSrc,
                                      (unsigned int)U550_BASE);
    return RT_AI_EXECUTORCH_OK;
}

int rt_ai_executorch_ethosu_platform_deinit(void)
{
    if (!g_executorch_ethosu_initialized)
    {
        return RT_AI_EXECUTORCH_OK;
    }

    NVIC_DisableIRQ(g_executorch_ethosu_irq_cfg.intrSrc);
    (void)ethosu_soft_reset(&g_executorch_ethosu_driver);
    ethosu_deinit(&g_executorch_ethosu_driver);
    Cy_SysEnableU55(false);

    g_executorch_ethosu_initialized = false;
    memset(&g_executorch_ethosu_driver, 0, sizeof(g_executorch_ethosu_driver));
    RT_AI_EXECUTORCH_ETHOSU_DEBUG_LOG("[executorch] Ethos-U platform deinit ok\n");
    return RT_AI_EXECUTORCH_OK;
}
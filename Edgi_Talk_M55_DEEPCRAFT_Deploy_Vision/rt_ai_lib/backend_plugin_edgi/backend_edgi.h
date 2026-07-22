#ifndef __BACKEND_EDGI_H__
#define __BACKEND_EDGI_H__


#include <stdint.h>
#include <rtthread.h>

#ifdef __cplusplus
extern "C" {
#endif

#define BACKEND_EDGI_OK                  (0)
#define BACKEND_EDGI_ERROR              (-1)
#define BACKEND_EDGI_ERROR_NULL         (-2)
#define BACKEND_EDGI_ERROR_NOT_INIT     (-3)
#define BACKEND_EDGI_ERROR_BAD_INDEX    (-4)

#define RT_AI_EDGI_CMD_DEINIT           (0x100)

#ifndef BACKEND_EDGI_INPUT_SIZE
#define BACKEND_EDGI_INPUT_SIZE         (320U * 320U * 3U)
#endif

#ifndef BACKEND_EDGI_OUTPUT_SIZE
#define BACKEND_EDGI_OUTPUT_SIZE        (40U)
#endif

typedef struct backend_edgi_config
{
    const char *model_name;
    uint32_t input_size;
    uint32_t output_size;
    void *user_data;
} backend_edgi_config_t;


/* Low-level DeepCraft / Imagimob wrapper */
int backend_edgi_init(const backend_edgi_config_t *config);
int backend_edgi_run(const void *input, void *output);
int backend_edgi_deinit(void);
void *backend_edgi_get_input(uint32_t index);
void *backend_edgi_get_output(uint32_t index);
int backend_edgi_is_initialized(void);
int backend_edgi_get_last_error(void);

#ifdef RT_AI_USE_EDGI

#include "rt_ai.h"
#include "rt_ai_common.h"

typedef struct edgi_ai
{
    struct rt_ai parent;
    backend_edgi_config_t config;
} edgi_ai_t;

#define EDGI_AI_T(h)    ((edgi_ai_t *)(h))

/* RT-AK backend constructor, used by rt_ai_register() */
int backend_edgi(void *edgi_handle);

#endif /* RT_AI_USE_EDGI */


#ifdef __cplusplus
}
#endif

#endif /* __BACKEND_EDGI_H__ */

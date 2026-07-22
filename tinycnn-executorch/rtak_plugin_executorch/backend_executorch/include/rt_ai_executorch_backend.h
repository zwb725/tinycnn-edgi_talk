#ifndef RT_AI_EXECUTORCH_BACKEND_H_
#define RT_AI_EXECUTORCH_BACKEND_H_

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define RT_AI_EXECUTORCH_OK 0
#define RT_AI_EXECUTORCH_EINVAL (-22)
#define RT_AI_EXECUTORCH_ENOSYS (-38)
#define RT_AI_EXECUTORCH_ENOMEM (-12)
#define RT_AI_EXECUTORCH_EIO (-5)

typedef struct rt_ai_executorch_config
{
    const char *model_name;
    const uint8_t *pte_data;
    size_t pte_size;
} rt_ai_executorch_config_t;

int rt_ai_executorch_init(const rt_ai_executorch_config_t *config);
void *rt_ai_executorch_get_input(size_t *size_bytes);
int rt_ai_executorch_run(void);
const void *rt_ai_executorch_get_output(size_t *size_bytes);
int rt_ai_executorch_deinit(void);

#ifdef __cplusplus
}
#endif

#endif /* RT_AI_EXECUTORCH_BACKEND_H_ */

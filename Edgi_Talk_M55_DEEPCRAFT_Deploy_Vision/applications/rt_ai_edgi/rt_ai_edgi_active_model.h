#ifndef __RT_AI_EDGI_ACTIVE_MODEL_H__
#define __RT_AI_EDGI_ACTIVE_MODEL_H__

#include <rtconfig.h>
#include "rt_ai.h"

#ifndef RT_AI_EDGI_HAS_RT_AI_INPUT_DECL
rt_ai_buffer_t *rt_ai_input(rt_ai_t ai, rt_ai_uint32_t index);
#endif

#if defined(RT_AI_EDGI_MODEL_OBJECT_DETECT)

#include "rt_ai_object_detect_model.h"

#define RT_AI_EDGI_ACTIVE_MODEL_NAME \
    RT_AI_OBJECT_DETECT_MODEL_NAME

#define RT_AI_EDGI_ACTIVE_INPUT_COUNT \
    RT_AI_OBJECT_DETECT_IN_1_SIZE

#define RT_AI_EDGI_ACTIVE_INPUT_BYTES \
    RT_AI_OBJECT_DETECT_IN_1_SIZE_BYTES

#define RT_AI_EDGI_ACTIVE_OUTPUT_COUNT \
    RT_AI_OBJECT_DETECT_OUT_1_SIZE

#define RT_AI_EDGI_ACTIVE_OUTPUT_BYTES \
    RT_AI_OBJECT_DETECT_OUT_1_SIZE_BYTES

#define RT_AI_EDGI_ACTIVE_INPUT_DTYPE \
    RT_AI_OBJECT_DETECT_INPUT_DTYPE

#define RT_AI_EDGI_ACTIVE_OUTPUT_DTYPE \
    RT_AI_OBJECT_DETECT_OUTPUT_DTYPE

#else

#error "No Edgi AI model selected"

#endif

#endif /* __RT_AI_EDGI_ACTIVE_MODEL_H__ */

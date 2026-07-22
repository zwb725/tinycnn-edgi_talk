#ifndef __RT_AI_EDGI_DEMO_CONFIG_H__
#define __RT_AI_EDGI_DEMO_CONFIG_H__

#include "rt_ai_object_detect_model.h"

#define RT_AI_EDGI_DEMO_MODEL_NAME                RT_AI_OBJECT_DETECT_MODEL_NAME

#define RT_AI_EDGI_INPUT_W                        320
#define RT_AI_EDGI_INPUT_H                        320
#define RT_AI_EDGI_INPUT_C                        3
#define RT_AI_EDGI_INPUT_SIZE                     RT_AI_OBJECT_DETECT_INPUT_SIZE
#define RT_AI_EDGI_OUTPUT_SIZE                    RT_AI_OBJECT_DETECT_OUTPUT_SIZE

#define RT_AI_EDGI_PREPROCESS_YUYV_RGB888_320     1
#define RT_AI_EDGI_POSTPROCESS_OBJECT_DETECT_RPS  1

#endif /* __RT_AI_EDGI_DEMO_CONFIG_H__ */

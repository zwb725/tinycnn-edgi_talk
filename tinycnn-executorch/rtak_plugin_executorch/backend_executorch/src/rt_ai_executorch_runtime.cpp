#include "rt_ai_executorch_backend.h"

#include <rtthread.h>

#include <executorch/extension/data_loader/buffer_data_loader.h>
#include <executorch/runtime/core/error.h>
#include <executorch/runtime/core/evalue.h>
#include <executorch/runtime/core/hierarchical_allocator.h>
#include <executorch/runtime/core/memory_allocator.h>
#include <executorch/runtime/core/span.h>
#include <executorch/runtime/executor/memory_manager.h>
#include <executorch/runtime/executor/method.h>
#include <executorch/runtime/executor/method_meta.h>
#include <executorch/runtime/executor/program.h>
#include <executorch/runtime/platform/platform.h>
#include <executorch/runtime/platform/runtime.h>
#include <rtthread.h>
#include <cstring>
#include <new>
#include <utility>

extern "C" executorch::runtime::Error
executorch_delegate_EthosUBackend_registered(void);

extern "C" int rt_ai_executorch_ethosu_platform_init(void)
    __attribute__((weak));
extern "C" int rt_ai_executorch_ethosu_platform_deinit(void)
    __attribute__((weak));

#ifndef RT_AI_EXECUTORCH_METHOD_POOL_SIZE
#define RT_AI_EXECUTORCH_METHOD_POOL_SIZE (512u * 1024u)
#endif

#ifndef RT_AI_EXECUTORCH_TEMP_POOL_SIZE
#define RT_AI_EXECUTORCH_TEMP_POOL_SIZE (512u * 1024u)
#endif

#ifndef RT_AI_EXECUTORCH_MAX_PLANNED_BUFFERS
#define RT_AI_EXECUTORCH_MAX_PLANNED_BUFFERS 8u
#endif

#ifndef RT_AI_EXECUTORCH_MAX_IO_TENSORS
#define RT_AI_EXECUTORCH_MAX_IO_TENSORS 4u
#endif

#if defined(__GNUC__)
#define RT_AI_EXECUTORCH_ALIGNED16 __attribute__((aligned(16)))
#define RT_AI_EXECUTORCH_ARENA_ATTR __attribute__((aligned(16), section(".cy_ml_arena_data")))
#else
#define RT_AI_EXECUTORCH_ALIGNED16
#define RT_AI_EXECUTORCH_ARENA_ATTR
#endif

namespace {

using executorch::aten::Tensor;
using executorch::extension::BufferDataLoader;
using executorch::runtime::Error;
using executorch::runtime::EValue;
using executorch::runtime::HierarchicalAllocator;
using executorch::runtime::MemoryAllocator;
using executorch::runtime::MemoryManager;
using executorch::runtime::Method;
using executorch::runtime::MethodMeta;
using executorch::runtime::Program;
using executorch::runtime::Result;
using executorch::runtime::Span;

static uint8_t g_method_pool[RT_AI_EXECUTORCH_METHOD_POOL_SIZE]
    RT_AI_EXECUTORCH_ARENA_ATTR;
static uint8_t g_temp_pool[RT_AI_EXECUTORCH_TEMP_POOL_SIZE]
    RT_AI_EXECUTORCH_ARENA_ATTR;

template <typename T>
class RuntimeSlot {
 public:
  RuntimeSlot() = default;
  RuntimeSlot(const RuntimeSlot&) = delete;
  RuntimeSlot& operator=(const RuntimeSlot&) = delete;

  template <typename... Args>
  T& emplace(Args&&... args) {
    destroy();
    new (storage_) T(std::forward<Args>(args)...);
    constructed_ = true;
    return get();
  }

  void destroy() {
    if (constructed_) {
      get().~T();
      constructed_ = false;
    }
  }

  bool has_value() const {
    return constructed_;
  }

  T& get() {
    return *reinterpret_cast<T*>(storage_);
  }

  const T& get() const {
    return *reinterpret_cast<const T*>(storage_);
  }

  T* ptr() {
    return &get();
  }

 private:
  alignas(T) unsigned char storage_[sizeof(T)];
  bool constructed_ = false;
};

struct RuntimeContext {
  bool initialized = false;
  const char* model_name = nullptr;
  const char* method_name = nullptr;
  const uint8_t* pte_data = nullptr;
  size_t pte_size = 0;

  RuntimeSlot<BufferDataLoader> loader;
  RuntimeSlot<Program> program;
  RuntimeSlot<MemoryAllocator> method_allocator;
  RuntimeSlot<MemoryAllocator> temp_allocator;
  RuntimeSlot<HierarchicalAllocator> planned_memory;
  RuntimeSlot<MemoryManager> memory_manager;
  RuntimeSlot<Method> method;

  Span<uint8_t> planned_spans[RT_AI_EXECUTORCH_MAX_PLANNED_BUFFERS];
  size_t planned_span_count = 0;

  EValue input_evalues[RT_AI_EXECUTORCH_MAX_IO_TENSORS];
  EValue output_evalues[RT_AI_EXECUTORCH_MAX_IO_TENSORS];
  size_t input_count = 0;
  size_t output_count = 0;

  void* input_data = nullptr;
  size_t input_size = 0;
  const void* output_data = nullptr;
  size_t output_size = 0;

  void clear_evalues() {
    for (size_t i = 0; i < RT_AI_EXECUTORCH_MAX_IO_TENSORS; ++i) {
      input_evalues[i] = EValue();
      output_evalues[i] = EValue();
    }
  }

  void reset() {
    initialized = false;
    clear_evalues();
    method.destroy();
    memory_manager.destroy();
    planned_memory.destroy();
    temp_allocator.destroy();
    method_allocator.destroy();
    program.destroy();
    loader.destroy();

    model_name = nullptr;
    method_name = nullptr;
    pte_data = nullptr;
    pte_size = 0;
    planned_span_count = 0;
    input_count = 0;
    output_count = 0;
    input_data = nullptr;
    input_size = 0;
    output_data = nullptr;
    output_size = 0;
  }
};

RuntimeContext g_ctx;
bool g_log_enabled = true;

#define RT_AI_EXECUTORCH_INFO_LOG(...) \
  do {                                 \
    if (g_log_enabled) {               \
      rt_kprintf(__VA_ARGS__);         \
    }                                  \
  } while (0)

#ifndef RT_AI_EXECUTORCH_DEBUG_LOG
#define RT_AI_EXECUTORCH_DEBUG_LOG 0
#endif

#if RT_AI_EXECUTORCH_DEBUG_LOG
#define RT_AI_EXECUTORCH_DEBUG_LOGF(...) \
  do {                                  \
    if (g_log_enabled) {                \
      rt_kprintf(__VA_ARGS__);          \
    }                                   \
  } while (0)
#else
#define RT_AI_EXECUTORCH_DEBUG_LOGF(...) \
  do {                                  \
  } while (0)
#endif

int map_error(Error error) {
  switch (error) {
    case Error::Ok:
      return RT_AI_EXECUTORCH_OK;
    case Error::MemoryAllocationFailed:
    case Error::DelegateMemoryAllocationFailed:
    case Error::OutOfResources:
      return RT_AI_EXECUTORCH_ENOMEM;
    case Error::NotImplemented:
    case Error::NotSupported:
      return RT_AI_EXECUTORCH_ENOSYS;
    case Error::InvalidArgument:
    case Error::InvalidState:
    case Error::InvalidType:
    case Error::InvalidProgram:
      return RT_AI_EXECUTORCH_EINVAL;
    default:
      return RT_AI_EXECUTORCH_EIO;
  }
}

void log_et_error(const char* stage, Error error) {
  rt_kprintf(
      "[executorch] %s failed: %s (0x%08x)\n",
      stage,
      executorch::runtime::to_string(error),
      static_cast<unsigned int>(error));
}

Error register_ethosu_delegate() {
  return executorch_delegate_EthosUBackend_registered();
}

int bind_input_tensor() {
  g_ctx.input_count = g_ctx.method.get().inputs_size();
  if (g_ctx.input_count == 0 ||
      g_ctx.input_count > RT_AI_EXECUTORCH_MAX_IO_TENSORS) {
    rt_kprintf(
        "[executorch] unsupported input count: %lu\n",
        static_cast<unsigned long>(g_ctx.input_count));
    return RT_AI_EXECUTORCH_EINVAL;
  }

#if defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#endif
  Error status = g_ctx.method.get().get_inputs(
      g_ctx.input_evalues, g_ctx.input_count);
#if defined(__GNUC__)
#pragma GCC diagnostic pop
#endif
  if (status != Error::Ok) {
    log_et_error("get_inputs", status);
    return map_error(status);
  }

  if (!g_ctx.input_evalues[0].isTensor()) {
    rt_kprintf("[executorch] input 0 is not a tensor\n");
    return RT_AI_EXECUTORCH_EINVAL;
  }

  Tensor& tensor = g_ctx.input_evalues[0].toTensor();
  g_ctx.input_data = tensor.mutable_data_ptr();
  g_ctx.input_size = tensor.nbytes();
  if (g_ctx.input_data == nullptr || g_ctx.input_size == 0) {
    rt_kprintf("[executorch] input 0 has no writable buffer\n");
    return RT_AI_EXECUTORCH_EINVAL;
  }

  RT_AI_EXECUTORCH_DEBUG_LOGF(
      "[executorch] input0=%p bytes=%lu\n",
      g_ctx.input_data,
      static_cast<unsigned long>(g_ctx.input_size));
  return RT_AI_EXECUTORCH_OK;
}

template <typename T>
int fill_input_tensor_with_one(Tensor& tensor) {
  const auto signed_numel = tensor.numel();
  if (signed_numel < 0) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  T* data = tensor.mutable_data_ptr<T>();
  if (data == nullptr) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  const size_t numel = static_cast<size_t>(signed_numel);
  for (size_t i = 0; i < numel; ++i) {
    data[i] = static_cast<T>(1);
  }
  return RT_AI_EXECUTORCH_OK;
}

template <>
int fill_input_tensor_with_one<bool>(Tensor& tensor) {
  const auto signed_numel = tensor.numel();
  if (signed_numel < 0) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  bool* data = tensor.mutable_data_ptr<bool>();
  if (data == nullptr) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  const size_t numel = static_cast<size_t>(signed_numel);
  for (size_t i = 0; i < numel; ++i) {
    data[i] = true;
  }
  return RT_AI_EXECUTORCH_OK;
}

int fill_input0_with_ones() {
  if (!g_ctx.initialized || !g_ctx.input_evalues[0].isTensor()) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  Tensor& tensor = g_ctx.input_evalues[0].toTensor();
  int status = RT_AI_EXECUTORCH_EINVAL;
  switch (tensor.scalar_type()) {
    case executorch::aten::ScalarType::Byte:
      status = fill_input_tensor_with_one<uint8_t>(tensor);
      break;
    case executorch::aten::ScalarType::Char:
      status = fill_input_tensor_with_one<int8_t>(tensor);
      break;
    case executorch::aten::ScalarType::Short:
      status = fill_input_tensor_with_one<int16_t>(tensor);
      break;
    case executorch::aten::ScalarType::Int:
      status = fill_input_tensor_with_one<int32_t>(tensor);
      break;
    case executorch::aten::ScalarType::Long:
      status = fill_input_tensor_with_one<int64_t>(tensor);
      break;
    case executorch::aten::ScalarType::Float:
      status = fill_input_tensor_with_one<float>(tensor);
      break;
    case executorch::aten::ScalarType::Double:
      status = fill_input_tensor_with_one<double>(tensor);
      break;
    case executorch::aten::ScalarType::Bool:
      status = fill_input_tensor_with_one<bool>(tensor);
      break;
    default:
      rt_kprintf(
          "[executorch] unsupported input scalar type id=%d\n",
          static_cast<int>(tensor.scalar_type()));
      return RT_AI_EXECUTORCH_EINVAL;
  }

  if (status == RT_AI_EXECUTORCH_OK) {
    RT_AI_EXECUTORCH_DEBUG_LOGF(
        "[executorch] input0 filled with ones scalar_type=%d bytes=%lu\n",
        static_cast<int>(tensor.scalar_type()),
        static_cast<unsigned long>(tensor.nbytes()));
  }
  return status;
}

void print_output_head_bytes(const void* data, size_t size) {
  const uint8_t* bytes = static_cast<const uint8_t*>(data);
  const size_t count = size < 16u ? size : 16u;

  rt_kprintf("[executorch] output0 head bytes=");
  for (size_t i = 0; i < count; ++i) {
    rt_kprintf("%02x%s", bytes[i], (i + 1u == count) ? "" : " ");
  }
  rt_kprintf("\n");
}

int dump_output0(size_t max_elems) {
  if (!g_ctx.initialized || !g_ctx.output_evalues[0].isTensor()) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  const Tensor& tensor = g_ctx.output_evalues[0].toTensor();
  const void* data = tensor.const_data_ptr();
  if (data == nullptr) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  const auto signed_numel = tensor.numel();
  if (signed_numel < 0) {
    return RT_AI_EXECUTORCH_EINVAL;
  }
  const size_t numel = static_cast<size_t>(signed_numel);
  const size_t count = numel < max_elems ? numel : max_elems;

  RT_AI_EXECUTORCH_INFO_LOG(
      "[executorch] output0 scalar_type=%d numel=%lu bytes=%lu\n",
      static_cast<int>(tensor.scalar_type()),
      static_cast<unsigned long>(numel),
      static_cast<unsigned long>(tensor.nbytes()));

  if (tensor.scalar_type() == executorch::aten::ScalarType::Float) {
    const float* values = tensor.const_data_ptr<float>();
    size_t top1 = 0;
    for (size_t i = 1; i < numel; ++i) {
      if (values[i] > values[top1]) {
        top1 = i;
      }
    }
    RT_AI_EXECUTORCH_INFO_LOG("[executorch] output0 float top1=%u\n", (unsigned int)top1);
    for (size_t i = 0; i < count; ++i) {
      uint32_t bits = 0;
      std::memcpy(&bits, &values[i], sizeof(bits));
      RT_AI_EXECUTORCH_DEBUG_LOGF(
          "[executorch] output0[%u] float_bits=0x%08x\n",
          (unsigned int)i,
          (unsigned int)bits);
    }
  } else {
    print_output_head_bytes(data, tensor.nbytes());
  }

  return RT_AI_EXECUTORCH_OK;
}

int bind_output_tensor() {
  g_ctx.output_count = g_ctx.method.get().outputs_size();
  if (g_ctx.output_count == 0 ||
      g_ctx.output_count > RT_AI_EXECUTORCH_MAX_IO_TENSORS) {
    rt_kprintf(
        "[executorch] unsupported output count: %lu\n",
        static_cast<unsigned long>(g_ctx.output_count));
    return RT_AI_EXECUTORCH_EINVAL;
  }

  Error status = g_ctx.method.get().get_outputs(
      g_ctx.output_evalues, g_ctx.output_count);
  if (status != Error::Ok) {
    log_et_error("get_outputs", status);
    return map_error(status);
  }

  if (!g_ctx.output_evalues[0].isTensor()) {
    rt_kprintf("[executorch] output 0 is not a tensor\n");
    return RT_AI_EXECUTORCH_EINVAL;
  }

  const Tensor& tensor = g_ctx.output_evalues[0].toTensor();
  g_ctx.output_data = tensor.const_data_ptr();
  g_ctx.output_size = tensor.nbytes();
  if (g_ctx.output_data == nullptr || g_ctx.output_size == 0) {
    rt_kprintf("[executorch] output 0 has no readable buffer\n");
    return RT_AI_EXECUTORCH_EINVAL;
  }

  RT_AI_EXECUTORCH_DEBUG_LOGF(
      "[executorch] output0=%p bytes=%lu\n",
      g_ctx.output_data,
      static_cast<unsigned long>(g_ctx.output_size));
  return RT_AI_EXECUTORCH_OK;
}

} // namespace

extern "C" et_timestamp_t et_pal_current_ticks(void) {
  return static_cast<et_timestamp_t>(rt_tick_get_millisecond());
}

extern "C" et_tick_ratio_t et_pal_ticks_to_ns_multiplier(void) {
  return {1000000ULL, 1ULL};
}

extern "C" void et_pal_emit_log_message(
    et_timestamp_t timestamp,
    et_pal_log_level_t level,
    const char* filename,
    const char* function,
    size_t line,
    const char* message,
    size_t length) {
  (void)timestamp;
  (void)function;

#if RT_AI_EXECUTORCH_DEBUG_LOG
  if ((level == et_pal_log_level_t::kDebug ||
       level == et_pal_log_level_t::kInfo) &&
      !g_log_enabled) {
    return;
  }
#else
  if (level == et_pal_log_level_t::kDebug ||
      level == et_pal_log_level_t::kInfo) {
    return;
  }
#endif

  char buffer[161];
  const size_t copy_length = length < (sizeof(buffer) - 1u)
      ? length
      : (sizeof(buffer) - 1u);
  for (size_t i = 0; i < copy_length; ++i) {
    buffer[i] = message != nullptr ? message[i] : '\0';
  }
  buffer[copy_length] = '\0';

  rt_kprintf(
      "[executorch] %c %s:%u %s\n",
      static_cast<char>(level),
      filename != nullptr ? filename : "?",
      static_cast<unsigned int>(line),
      buffer);
}

extern "C" void rt_ai_executorch_runtime_set_log_enabled(int enabled) {
  g_log_enabled = enabled != 0;
}

extern "C" int rt_ai_executorch_runtime_log_enabled(void) {
  return g_log_enabled ? 1 : 0;
}

extern "C" int rt_ai_executorch_runtime_init(
    const rt_ai_executorch_config_t* config) {
  if (config == nullptr || config->pte_data == nullptr || config->pte_size == 0) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

  auto reset_and_return = [](int status) -> int {
    g_ctx.reset();
    if (rt_ai_executorch_ethosu_platform_deinit != nullptr) {
      (void)rt_ai_executorch_ethosu_platform_deinit();
    }
    return status;
  };

  g_ctx.reset();

  if (rt_ai_executorch_ethosu_platform_init != nullptr) {
    int platform_status = rt_ai_executorch_ethosu_platform_init();
    if (platform_status != RT_AI_EXECUTORCH_OK) {
      rt_kprintf(
          "[executorch] Ethos-U platform init failed: %d\n",
          platform_status);
      return reset_and_return(platform_status);
    }
  }
  g_ctx.model_name =
      config->model_name != nullptr ? config->model_name : "executorch";
  g_ctx.pte_data = config->pte_data;
  g_ctx.pte_size = config->pte_size;

  executorch::runtime::runtime_init();
  RT_AI_EXECUTORCH_INFO_LOG(
      "[executorch] runtime_init model=%s pte=%p bytes=%lu\n",
      g_ctx.model_name,
      static_cast<const void*>(g_ctx.pte_data),
      static_cast<unsigned long>(g_ctx.pte_size));

  Error delegate_status = register_ethosu_delegate();
  if (delegate_status != Error::Ok &&
      delegate_status != Error::RegistrationAlreadyRegistered) {
    log_et_error("Ethos-U delegate registration", delegate_status);
    return reset_and_return(map_error(delegate_status));
  }

  g_ctx.loader.emplace(g_ctx.pte_data, g_ctx.pte_size);

  {
    Result<Program> program_result = Program::load(g_ctx.loader.ptr());
    if (!program_result.ok()) {
      log_et_error("Program::load", program_result.error());
      return reset_and_return(map_error(program_result.error()));
    }
    g_ctx.program.emplace(std::move(program_result.get()));
  }

  if (g_ctx.program.get().num_methods() == 0) {
    rt_kprintf("[executorch] Program has no methods\n");
    return reset_and_return(RT_AI_EXECUTORCH_EINVAL);
  }

  {
    Result<const char*> method_name_result =
        g_ctx.program.get().get_method_name(0);
    if (!method_name_result.ok()) {
      log_et_error("get_method_name", method_name_result.error());
      return reset_and_return(map_error(method_name_result.error()));
    }
    g_ctx.method_name = method_name_result.get();
  }

  RT_AI_EXECUTORCH_INFO_LOG("[executorch] method=%s\n", g_ctx.method_name);

  Result<MethodMeta> method_meta_result =
      g_ctx.program.get().method_meta(g_ctx.method_name);
  if (!method_meta_result.ok()) {
    log_et_error("method_meta", method_meta_result.error());
    return reset_and_return(map_error(method_meta_result.error()));
  }

  g_ctx.method_allocator.emplace(
      static_cast<uint32_t>(RT_AI_EXECUTORCH_METHOD_POOL_SIZE), g_method_pool);
  g_ctx.temp_allocator.emplace(
      static_cast<uint32_t>(RT_AI_EXECUTORCH_TEMP_POOL_SIZE), g_temp_pool);

  g_ctx.planned_span_count = method_meta_result->num_memory_planned_buffers();
  if (g_ctx.planned_span_count > RT_AI_EXECUTORCH_MAX_PLANNED_BUFFERS) {
    rt_kprintf(
        "[executorch] planned buffer count %lu exceeds RT_AI_EXECUTORCH_MAX_PLANNED_BUFFERS=%u\n",
        static_cast<unsigned long>(g_ctx.planned_span_count),
        (unsigned int)RT_AI_EXECUTORCH_MAX_PLANNED_BUFFERS);
    return reset_and_return(RT_AI_EXECUTORCH_EINVAL);
  }

  for (size_t id = 0; id < g_ctx.planned_span_count; ++id) {
    auto buffer_size_result =
        method_meta_result->memory_planned_buffer_size(id);
    if (!buffer_size_result.ok()) {
      log_et_error("memory_planned_buffer_size", buffer_size_result.error());
      return reset_and_return(map_error(buffer_size_result.error()));
    }

    const auto signed_buffer_size = buffer_size_result.get();
    if (signed_buffer_size < 0) {
      rt_kprintf(
          "[executorch] planned buffer %lu has invalid negative size %ld\n",
          static_cast<unsigned long>(id),
          static_cast<long>(signed_buffer_size));
      return reset_and_return(RT_AI_EXECUTORCH_EINVAL);
    }

    const size_t buffer_size = static_cast<size_t>(signed_buffer_size);
    uint8_t* buffer = static_cast<uint8_t*>(
        g_ctx.method_allocator.get().allocate(buffer_size, 16u));
    if (buffer == nullptr) {
      rt_kprintf(
          "[executorch] failed to allocate planned buffer %lu bytes=%lu\n",
          static_cast<unsigned long>(id),
          static_cast<unsigned long>(buffer_size));
      return reset_and_return(RT_AI_EXECUTORCH_ENOMEM);
    }
    g_ctx.planned_spans[id] = Span<uint8_t>(buffer, buffer_size);
  }

  g_ctx.planned_memory.emplace(Span<Span<uint8_t>>(
      g_ctx.planned_spans, g_ctx.planned_span_count));
  g_ctx.memory_manager.emplace(
      g_ctx.method_allocator.ptr(),
      g_ctx.planned_memory.ptr(),
      g_ctx.temp_allocator.ptr());

  {
    Result<Method> method_result = g_ctx.program.get().load_method(
        g_ctx.method_name, g_ctx.memory_manager.ptr());
    if (!method_result.ok()) {
      log_et_error("load_method", method_result.error());
      return reset_and_return(map_error(method_result.error()));
    }
    g_ctx.method.emplace(std::move(method_result.get()));
  }

  int result = bind_input_tensor();
  if (result != RT_AI_EXECUTORCH_OK) {
    return reset_and_return(result);
  }
  result = bind_output_tensor();
  if (result != RT_AI_EXECUTORCH_OK) {
    return reset_and_return(result);
  }

  g_ctx.initialized = true;
  RT_AI_EXECUTORCH_DEBUG_LOGF(
      "[executorch] init complete planned_buffers=%lu method_pool=%u temp_pool=%u\n",
      static_cast<unsigned long>(g_ctx.planned_span_count),
      (unsigned int)RT_AI_EXECUTORCH_METHOD_POOL_SIZE,
      (unsigned int)RT_AI_EXECUTORCH_TEMP_POOL_SIZE);
  return RT_AI_EXECUTORCH_OK;
}

extern "C" void* rt_ai_executorch_runtime_get_input(size_t* size_bytes) {
  if (size_bytes != nullptr) {
    *size_bytes = g_ctx.initialized ? g_ctx.input_size : 0;
  }
  return g_ctx.initialized ? g_ctx.input_data : nullptr;
}

extern "C" int rt_ai_executorch_runtime_fill_input_ones(void) {
  return fill_input0_with_ones();
}

extern "C" int rt_ai_executorch_runtime_run(void) {
  if (!g_ctx.initialized || !g_ctx.method.has_value()) {
    return RT_AI_EXECUTORCH_EINVAL;
  }

#if RT_AI_EXECUTORCH_DEBUG_LOG
  {
    const size_t n_in = g_ctx.method.get().inputs_size();
    const size_t n_out = g_ctx.method.get().outputs_size();
    RT_AI_EXECUTORCH_DEBUG_LOGF(
        "[executorch] execute start n_in=%u n_out=%u\n",
        static_cast<unsigned int>(n_in),
        static_cast<unsigned int>(n_out));
  }
#endif
  RT_AI_EXECUTORCH_DEBUG_LOGF("[executorch] pre-call tick=%lu\n", (unsigned long)rt_tick_get_millisecond());
  Error status = g_ctx.method.get().execute();
  RT_AI_EXECUTORCH_DEBUG_LOGF("[executorch] post-call tick=%lu status=%d\n",
                              (unsigned long)rt_tick_get_millisecond(), (int)status);
  g_ctx.temp_allocator.get().reset();
  RT_AI_EXECUTORCH_INFO_LOG(
      "[executorch] execute done status=%d\n",
      static_cast<int>(status));
  if (status != Error::Ok) {
    log_et_error("Method::execute", status);
    return map_error(status);
  }

  return bind_output_tensor();
}

extern "C" const void* rt_ai_executorch_runtime_get_output(size_t* size_bytes) {
  if (size_bytes != nullptr) {
    *size_bytes = g_ctx.initialized ? g_ctx.output_size : 0;
  }
  return g_ctx.initialized ? g_ctx.output_data : nullptr;
}

extern "C" int rt_ai_executorch_runtime_dump_output(size_t max_elems) {
  return dump_output0(max_elems);
}

extern "C" int rt_ai_executorch_runtime_deinit(void) {
  g_ctx.reset();
  if (rt_ai_executorch_ethosu_platform_deinit != nullptr) {
    return rt_ai_executorch_ethosu_platform_deinit();
  }
  return RT_AI_EXECUTORCH_OK;
}



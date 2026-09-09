// SPDX-License-Identifier: Apache-2.0
// Explicit FP32 raw-decay extension of the frozen FlashRWKV StateTune kernel.
#include "common/wkv7/recurrent_common_fp32io16.h"

PYBIND11_MODULE(TORCH_EXTENSION_NAME, module) {
  module.def("forward", &recurrent_common_fp32io16_from_decay_logits_forward);
  module.def("backward", &recurrent_common_fp32io16_from_decay_logits_backward);
}

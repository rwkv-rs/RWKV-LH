# EXE-G2-V3-RL training status

- State: pre-registered; authoritative remote data contract passed.
- Initialization: native zero.
- Device: remote physical GPU0.
- Dataset: 2000 request-last V3 target-suffix rows.
- Checkpoints: steps 250 through 2000 at interval 250; all retained.
- Product vLLM on remote port 18070 remains running; only the temporary G1
  candidate on 18075 was stopped to release GPU0 memory.

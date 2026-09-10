# E5 设计线：持续进程会话（设计与可行性，未实施）

## 目标能力

跨动作保留开发服务器、REPL、交互式进程和长任务：`start_session` / `send_to_session` / `read_session_output` / `stop_session` 四个动作。

## 与现状的核心矛盾

当前每次命令动作独立新建 bwrap，且 `--die-with-parent --unshare-all`（rwkv_lh/harness.py 沙箱命令行）使整个 PID namespace 随动作进程退出被拆除——`background_lifetime` 探针（ENGINEERING_REMAINING_AUDIT_R1_20260910）证实孙进程在动作返回瞬间即死。schema `timeout` 上限 120 秒也是按"单命令"设计的。

## 可行性结论（已验证）

`persistent_session_probe/PROBE.json`：由 Harness 进程持有的**单个长驻 bwrap**（stdin/stdout 管道交互）在两次相隔 2 秒的独立交互之间保持存活，会话内文件状态跨交互保留，stdin 关闭后干净退出。前提成立：不需要逃逸 `--die-with-parent`，而是把"每动作一个 bwrap"改为"每会话一个 bwrap、每动作一次交互"。

## 设计要点

1. **所有权**：session-supervisor 是 Harness 内的对象，持有 `subprocess.Popen` 的 bwrap 进程 + 非阻塞输出缓冲线程；会话随 Controller 进程结束（--die-with-parent 语义保持，进程逃逸仍然不可能）。
2. **动作合同**：
   - `start_session(argv, cwd, env)` → session_id；side_effect=True（进程是真实副作用）。
   - `send_to_session(session_id, input)` → 写 stdin；幂等 False。
   - `read_session_output(session_id, from_byte)` → 增量读缓冲（复用 command_streams 的 byte-cursor 形态）；read_only=True。
   - `stop_session(session_id)` → SIGTERM→SIGKILL 阶梯；幂等 True。
3. **timeout 语义**：120 秒上限适用于**单次交互**（一次 send/read 的等待），不适用于会话生命周期；会话生命周期由显式 stop 或运行终止控制。
4. **证据完整性**：会话输出进入与 run_command 相同的 `command_streams` SHA-256 记录；工作区写入范围由每次 read 时的快照 diff 判定（复用 controller `_workspace_change_metadata`）。
5. **崩溃恢复**：session 是不可恢复资源——进程丢失后 `recover` 一律报告 `interrupted`，绝不重放（与非幂等动作现有纪律一致）。

## 边界

- 不作为 Selector 首轮训练门槛（owner 决定）。
- 实施排在传输修复轮之后单独立轮；本文档只冻结设计与可行性证据。

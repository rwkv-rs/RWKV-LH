# INVALID

第一次运行得到 29/30，暴露 LH-M04 fixture 仍输出 Round39 批量 Goal 协议；修正 fixture 后误复用了同一 output 目录，SQLite run id 冲突使第二次结果变为 2/30。

该目录不参与任何架构指标。有效结果只取重新创建的 `../lh_control_30/`。

# Round11 基础设施中断记录

## 事件

2026-08-12 16:01:22 CST，WSL 因用户网络/转发更新重启。第一次 Round11 运行器与
GPU3 SSH forward 同时被停止；当时已有 54/90 份完整 audit，另有 8 个未完成工作区。

这不是模型或 Controller 失败。该目录原样保留为：

`data/experiments/Round11_interrupted_network_20260812T160122/`

- 完整 audit：54。
- 快照 results SHA-256：
  `86bbfbdd10447d2f710077b3aa501b83541172095f4871a43880611841a237ab`。
- 该快照不参与 Round11 得分、择优、标准答案比较或上传门。

## 恢复与重跑

- 从 systemd journal 恢复原 GPU3 映射：本地 `127.0.0.1:29613` 到远端 localhost
  `18073`。
- runtime smoke 重新确认模型仍为
  `rwkv7-g1i-13.3b-20260805-ctx16384`。
- 用同一协议、代码、模型、sampling、并发 8 和 200 transitions，从 1/90 开始全量重跑。
- 重跑改由独立 systemd user service 托管，避免 Codex 对话连接再次终止实验。
- 新 `data/experiments/Round11/` 的 90/90 audit 是唯一正式计分集。


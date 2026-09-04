# INVALID：旧 multiprocessing worker 与新运行重叠

日期：2026-08-23

本目录不计分，不得用于 Round161 门槛或训练数据。

第一次无效 canary 的主 runner 被终止后，4 个 `multiprocessing.spawn` worker 和一个
resource tracker 被 WSL init 收养并继续运行。旧目录改名后，这些 worker 又创建了原输出
路径；第二次 runner 随后也写入相同路径，造成两个代码批次和两个进程池重叠。

发现后已按只读 `ps` 解析出的精确 PID 终止旧、新两组 runner/worker/resource tracker，
并确认无相关进程残留。本目录原样改名保存。

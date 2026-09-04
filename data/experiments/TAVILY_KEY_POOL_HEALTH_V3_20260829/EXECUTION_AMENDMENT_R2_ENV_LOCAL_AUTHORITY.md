# V3 R2 `.env.local` 权威输入执行修正

登记时间：2026-08-29；发生在 R2 任一外部调用之前。

R1 按预注册探测逻辑运行，但发现调用进程继承了旧的 17-key `TAVILY_API_KEYS`。`load_local_env()` 正确遵循“进程环境优先、不覆盖”的产品规则，因此 R1 实际验证 17/17 usable，无法回答本轮预注册的“`.env.local` 当前 29-key 全池”问题。R1 目录和结果原样保留，不纳入 29-key 完整池结论。

R2 只修正输入权限：启动审计子进程时删除继承的 `TAVILY_API_KEY` 与 `TAVILY_API_KEYS`，随后仍由同一个冻结加载器从 ignored `.env.local` 读取。探测 endpoint、query、顺序、一次调用、超时、分类、零明文凭据和门槛均不改变。R2 使用新目录，绝不覆盖 R1。


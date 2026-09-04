# RWKV7 G1J 权重准备记录

## 目标

将以下公开权重先下载到 WSL 本地、完成整文件校验，再上传到服务器 NAS，并在 NAS 上再次完成整文件校验：

- `rwkv7-g1j-1.5b-20260831-ctx16384.pth`
- `rwkv7-g1j-2.9b-20260831-ctx16384.pth`
- `rwkv7-g1j-7.2b-20260831-ctx16384.pth`
- `rwkv7-g1j-13.3b-20260831-ctx16384.pth`

官方仓库：`https://huggingface.co/BlinkDL/rwkv7-g1`

## 官方元数据

| 文件 | 字节数 | Hugging Face LFS SHA-256 |
| --- | ---: | --- |
| `rwkv7-g1j-1.5b-20260831-ctx16384.pth` | 3,055,444,605 | `c43176881caf85fe22ad654ab02e7519260d560f3d20420ab590adb0c823860f` |
| `rwkv7-g1j-2.9b-20260831-ctx16384.pth` | 5,896,273,469 | `966f3420f833532aae3fb1fd6326533b08d43d23b7b03eaa2f0694a30b64a239` |
| `rwkv7-g1j-7.2b-20260831-ctx16384.pth` | 14,400,007,869 | `e3091a579c23ea7ebce9a0ad1ecfbda27082eeecd64d7f0474016e626df8f9c3` |
| `rwkv7-g1j-13.3b-20260831-ctx16384.pth` | 26,540,868,485 | `559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65` |

## 下载与上传流程

1. 在 WSL 项目 `temp/` 下使用带完成标记的 Range 分段下载，未完成分段不会进入最终校验。
2. 对本地完整文件执行 SHA-256，必须与 Hugging Face LFS 哈希一致。
3. 使用可续传的 `rsync --partial --append-verify` 上传到 NAS 的 `.uploading` 临时路径。
4. 对 NAS `.uploading` 文件再次执行完整 SHA-256。
5. 哈希一致后原子改为正式文件名；删除分段标记、临时文件和 WSL 本地副本。

13.3B 下载期间，WSL 代理发生 TLS 故障。最终使用 `hf-mirror.com` 只获取 Hugging Face 官方 CDN 的临时签名，实际权重数据由 `us.aws.cdn.hf.co` 直连下载。

## 最终结果

NAS 目录：`/mnt/nas-model/g1j/`

| NAS 文件 | 字节数 | 本地 SHA-256 | NAS SHA-256 | 状态 |
| --- | ---: | --- | --- | --- |
| `/mnt/nas-model/g1j/rwkv7-g1j-1.5b-20260831-ctx16384.pth` | 3,055,444,605 | 与官方一致 | 与官方一致 | 已发布 |
| `/mnt/nas-model/g1j/rwkv7-g1j-2.9b-20260831-ctx16384.pth` | 5,896,273,469 | 与官方一致 | 与官方一致 | 已发布 |
| `/mnt/nas-model/g1j/rwkv7-g1j-7.2b-20260831-ctx16384.pth` | 14,400,007,869 | 与官方一致 | 与官方一致 | 已发布 |
| `/mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth` | 26,540,868,485 | 与官方一致 | 与官方一致 | 已发布 |

- NAS 临时 `.partial` / `.uploading` 文件：0
- NAS 分段标记目录：0
- WSL 本地临时权重：已删除
- 服务器根盘模型副本：未创建
- G1J 四档权重总字节数：49,892,594,428
- NAS 校验后剩余空间：约 6.4 TB

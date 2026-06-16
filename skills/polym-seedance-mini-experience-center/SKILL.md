---
name: polym-seedance-mini-experience-center
description: >-
  Generate videos with Seedance 2.0 Mini (dreamina-seedance-2-0-mini-260615),
  which has NO public OpenAPI and only runs through the BytePlus console
  experience-center BFF. Use when the user wants to batch-generate Seedance Mini
  videos from a script/terminal instead of clicking the web playground —
  text-to-video, image/video/audio reference (I2V/R2V), first/last frame, or
  human-portrait references. All reference materials (including faces) go through
  the 素材库 (Assets API), exactly like the seedance-2-0 skill. Trigger on:
  "seedance mini", "dreamina mini", "mini 批量生成", "用 mini 出视频",
  "experience center 批量", or any request to drive the Mini model outside the web UI.
---

# Seedance 2.0 Mini — Experience Center

Mini (`dreamina-seedance-2-0-mini-260615`) **没有公开 OpenAPI**，只能走 BytePlus
控制台「体验中心」的 BFF 接口。本 skill 把整条链路封装成本地 CLI / Python 库，
让你脱离网页批量提交。**所有图片/视频/音频参考（含人像）统一走素材库（Assets API）**。

> 这条路线是逆向 + 端到端验证过的：T2V、非人像 I2V、**人像 I2V 都能出片**。
> 详见 [[reference_seedance_mini_console_bff_api]]（auto-memory）。

## 三种认证 / 凭证

| 凭证 | 用途 | 来源 | 是否必须 |
|------|------|------|---------|
| **Cookie + csrfToken** | mini BFF 提交/查询 | 本机 Chrome（已登录 console.byteplus.com） | 必须 |
| **AK/SK** | 素材库 Assets API 上传 | 自动复用 `~/.claude/skills/seedance-2-0/ark_ak_sk.json`，或 onboard 时手动给 | 传素材才需要（纯 T2V 不需要） |

**关键设计：凭证只在 onboarding 时读一次 Chrome cookie（Mac 上触发一次 keychain 授权），
之后全部读本地缓存 `~/.seedance_mini/creds.json`，绝不重复弹 keychain。**

## Onboarding（首次必做，只授权一次）

```bash
cd <skill>/scripts

# 读一次 Chrome cookie（会弹一次 macOS keychain 授权，点"始终允许"）+ 自动复用 seedance-2-0 的 AK/SK
python3 creds.py onboard

# 若没有 seedance-2-0 的 AK/SK，手动提供（上传素材库才需要）：
python3 creds.py onboard --ak AKLT... --sk ...

python3 creds.py status      # 查看缓存（不碰 keychain）
```

凭证失效（调用报 `InvalidCSRFToken`，cookie 一般几天过期）时：

```bash
python3 creds.py refresh     # 重新读 Chrome（再授权一次 keychain），保留 AK/SK
```

前置条件：
- Python 依赖：`pip install browser-cookie3 requests`（macOS 上 `pip3 install ... --break-system-packages`）。
- 本机 Chrome 已登录 <https://console.byteplus.com/ark/>。
- 首次用素材库前，需在控制台「素材库」签署数字资产承诺函（一次性）。
- AK/SK：若已装 `seedance-2-0` skill 会自动复用其 `ark_ak_sk.json`；否则在 onboard 时用 `--ak/--sk` 手动提供（仅上传素材库需要，纯 T2V 不需要）。

## ⚠️ 安全须知

`~/.seedance_mini/creds.json` 是**明文**存储完整登录 cookie（约 67 个）+ AK/SK，
权限收紧到 `600`（仅本人可读）。这是为了避免每次调用都弹 macOS keychain 的有意取舍，
但请注意：

- **不要把 `~/.seedance_mini/` 纳入 Time Machine / 云同步 / git**。
- 这等于把"登录态 + AK/SK 两个凭证"放在同一个明文文件，泄漏即双失。
- 撤销方式：控制台登出（使 cookie 失效）+ 轮换 AK/SK。
- cookie 一般几天过期，过期后 `python3 creds.py refresh` 重取。

## 用法

### CLI

```bash
cd <skill>/scripts

# 纯文字 T2V（不需要 AK/SK）
python3 mini.py gen "金色麦田夕阳下随风起伏，镜头横移" --duration 5 --wait

# 图片参考 I2V —— 本地图自动走素材库（人像也支持！）
python3 mini.py gen "[image1] 人物轻轻转头微笑，镜头缓缓推近" \
  --image /path/to/face.jpg --wait

# 首尾帧
python3 mini.py gen "镜头从清晨推到日落" --first f0.jpg --last f1.jpg --wait

# 仅上传素材，拿 asset_id
python3 mini.py upload /path/to/ref.jpg --type Image

# 查询 / 列表
python3 mini.py get cgt-xxxxx
python3 mini.py list
```

### Python 库（批量任务推荐）

```python
import sys; sys.path.insert(0, "<skill>/scripts")
import creds, mini

s = creds.bff_session()                       # 一个 session 复用
face = mini.upload_asset("face.jpg", session=s)         # 人像 → 素材库 asset
bottle = mini.upload_asset("bottle.jpg", session=s)

ids = mini.generate(
    "[image1] 人物看向 [image2] 香水瓶，镜头缓缓推进",
    image_assets=[face, bottle], duration=5, count=2, session=s,
)
for r in mini.wait_for_tasks(ids):
    print(r["Status"]["Phase"], r.get("VideoUrl"))
```

## 素材库统一上传流程（本地文件 → 可引用 asset）

`upload_asset()` 内部做了 4 步（已验证）：
1. `GetBatchPreSignedUrl` + PUT：本地文件 → 临时 TOS，拿 7天签名 URL（mini BFF, cookie）
2. `CreateAsset`：用该 URL 注册进素材库（Assets API, AK/SK）→ `asset_id`
3. 轮询 `GetAsset` 到 `Active`
4. 提交时引用：`ReferenceImages=[{AssetId, AssetUri:"asset://<id>"}]`（**最简结构，缺一不可**）

人像必须走素材库才能过审：裸 presigned 直传的人像会被
`InputImageSensitiveContentDetected.PrivacyInformation` 拦；走 Assets API 注册的
资产是「可信来源」，已验证人像 I2V 能出片。

## 提示词规则（沿用 seedance-2-0）

- 多参考素材用 `[image1]`/`[video1]`/`[audio1]` 标注（与 `image_assets=` 等参数顺序对应）。
- 人像参考最好拆分（脸部特写 / 三视图 / 服装分开传多个 asset），见
  [seedance-2-0 assets.md](../seedance-2-0/references/assets.md) 的 best practice。
- 需要导演级提示词优化（6-component / 时长计算 / 多镜头）时，读
  [seedance-2-0 的 prompt-guidance / duration-calculus](../seedance-2-0/references/)。
  本 skill 只负责"Mini 的提交通道"，提示词工艺复用 seedance-2-0。

## BFF 接口速查（modelark-api.console.byteplus.com/.../2024-01-29）

| 功能 | Action | 备注 |
|------|--------|------|
| 上传(第一步) | `GetBatchPreSignedUrl` | `{Biz:"experience_video", TosPathArray:[name]}` → PutUrl + 7天读 Url |
| 提交 | `CreateVideoGenTask` | 见 mini.py payload；图片参考 `ReferenceImages:[{AssetId,AssetUri}]` |
| 查询 | `GetVideoGenTask` | `{Id}` → Status.Phase / VideoUrl |
| 列表 | `ListVideoGenTasks` | `{PageSize}` → Items |

⚠️ 海外版**没有** `UploadArkTosFile` / `CheckTosService` / `ListActiveAIGCAssetGroup`
等接口（直接 404）——素材列表/管理走 Assets API（`assets.py`），不要走 BFF。

## 文件

- `scripts/creds.py` — 凭证管理（onboard/refresh/status + 本地缓存 + BFF session 构建）
- `scripts/mini.py` — Mini BFF 客户端 + 素材库上传 + 高层 `upload_asset`/`generate`/`wait_for_tasks`
- `scripts/assets.py` — Assets API SigV4 客户端（从 seedance-2-0 复制，纯 stdlib）

"""
Seedance Mini 客户端 — Experience Center (console BFF)
=====================================================

Mini 模型 (`dreamina-seedance-2-0-mini-260615`) 没有公开 OpenAPI，
本客户端复刻控制台 playground 的 BFF 调用，已端到端验证：
  - 凭证      : creds.py（本地缓存，不重复 keychain）
  - 素材上传  : 所有图片/视频/音频参考都走【素材库 Assets API】（支持人像，过审）
  - 提交/查询 : mini BFF (cookie 认证)

素材库统一流程（本地文件 → 可引用的 asset）：
  1. presigned PUT 把本地文件传到临时 TOS，拿 7天签名 URL（mini BFF, cookie）
  2. CreateAsset 用该 URL 注册进素材库（Assets API, AK/SK）→ asset_id
  3. 轮询到 Active
  4. 提交时引用： ReferenceImages=[{AssetId, AssetUri:"asset://<id>"}]

依赖: pip install browser-cookie3 requests --break-system-packages
"""

from __future__ import annotations

import time
import random
import mimetypes
from pathlib import Path

import requests

# 让 `import creds` / `from assets` 在任意 cwd 下都能解析（不只是 scripts/ 目录）
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))

import creds as _creds
from assets import create_asset, wait_for_active, get_or_create_group

BFF = "https://modelark-api.console.byteplus.com/ark/bff/api/ap-southeast-1/2024-01-29"
MODEL_NAME = "dreamina-seedance-2-0-mini"
# ⚠️ 模型版本是快照 id。若提交开始报 model-not-found，去控制台体验中心看 Mini 的新版本号并更新这里。
MODEL_VERSION = "260615"
ENDPOINT_ID = f"{MODEL_NAME}-{MODEL_VERSION}"
DEFAULT_GROUP = "seedance-mini-experience-center"
# 终态枚举：实测真实返回 "Completed"（cgt-20260616132326-kwjtc 出片验证）；
# Succeeded/Failed 作为保险一并纳入。
_DONE = ("Completed", "Succeeded", "Failed")


# ── BFF 调用 ──────────────────────────────────────────────────────────────────

def _bff(session: requests.Session, action: str, payload: dict) -> dict:
    r = session.post(f"{BFF}/{action}", json=payload)
    r.raise_for_status()
    d = r.json()
    err = d.get("ResponseMetadata", {}).get("Error")
    if err:
        msg = err.get("Message", "")
        if "CSRF" in str(err.get("Code", "")) or "CSRF" in msg:
            raise RuntimeError(f"{action}: {err.get('Code')} — cookie 可能过期，请运行 "
                               f"`python creds.py refresh`")
        raise RuntimeError(f"{action} failed: {err.get('Code')} - {msg}")
    return d["Result"]


# ── 素材库上传（所有参考素材的唯一入口）────────────────────────────────────────

def upload_asset(local_path: str, *, asset_type: str = "Image",
                 group: str = DEFAULT_GROUP,
                 moderation_skip: bool = False,
                 session: requests.Session | None = None) -> str:
    """
    本地文件 → 素材库 asset_id（图片/视频/音频通用，人像也走这里）。

    Args:
        local_path: 本地文件路径
        asset_type: "Image" | "Video" | "Audio"
        group:      素材库分组名（幂等，不会重复建）
        moderation_skip: 跳过内容预审（仅用于你有授权的内容，如自有素材）
    Returns:
        asset_id（已 Active，可直接用于 generate）
    """
    s = session or _creds.bff_session()
    ak, sk, region = _creds.get_aksk()
    path = Path(local_path)

    # 1) presigned PUT → 临时 TOS，拿 7天签名 URL
    fname = f"{int(time.time()*1000)}_{path.name}"
    info = _bff(s, "GetBatchPreSignedUrl", {"Biz": "experience_video", "TosPathArray": [fname]})
    pre = info["PreSignedUrls"][0]
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    with open(path, "rb") as f:
        requests.put(pre["PutUrl"], data=f.read(), headers={"Content-Type": mime},
                     timeout=(10, 300)).raise_for_status()

    # 2) CreateAsset 注册进素材库（Assets API 用签名 URL 拉取）
    gid = get_or_create_group(group, description="Seedance Mini experience-center assets",
                              ak=ak, sk=sk, region=region)
    aid = create_asset(group_id=gid, url=pre["Url"], asset_type=asset_type, name=path.stem,
                       moderation_strategy="Skip" if moderation_skip else None,
                       ak=ak, sk=sk, region=region)

    # 3) 轮询到 Active
    wait_for_active(aid, interval_seconds=3, timeout_seconds=120, ak=ak, sk=sk, region=region)
    return aid


def _ref(asset_id: str) -> dict:
    """asset_id → mini BFF 的参考素材结构（最简：AssetId + AssetUri）。"""
    return {"AssetId": asset_id, "AssetUri": f"asset://{asset_id}"}


# ── 提交任务 ──────────────────────────────────────────────────────────────────

def generate(
    prompt: str,
    *,
    image_assets: list[str] | None = None,   # asset_id 列表（upload_asset 返回），参考图
    video_assets: list[str] | None = None,   # asset_id 列表，参考视频
    audio_assets: list[str] | None = None,   # asset_id 列表，参考音频
    first_frame_asset: str | None = None,    # asset_id，首帧
    last_frame_asset: str | None = None,     # asset_id，尾帧
    ratio: str = "adaptive",
    duration: int = 5,
    resolution: str = "720p",
    generate_audio: bool = False,
    seed: int = -1,
    count: int = 1,
    session: requests.Session | None = None,
) -> list[str]:
    """
    提交 Seedance Mini 生成任务。所有素材都用 asset_id（upload_asset 返回）。
    prompt 用 [image1]/[video1]/[audio1] 标注引用（与参数顺序对应）。
    Returns: task_id 列表（长度 = count）
    """
    s = session or _creds.bff_session()
    group_id = f"4-{int(time.time()*1000)}"
    task_ids = []

    for _ in range(count):
        p: dict = {
            "Name": MODEL_NAME, "Prompt": prompt,
            "TaskType": "BasicMode", "VideoTaskType": "reference_media",
            "ModelName": MODEL_NAME, "ModelVersion": MODEL_VERSION,
            "Ratio": ratio, "Resolution": resolution, "GroupId": group_id,
            "Duration": duration, "Seed": seed if seed >= 0 else random.randint(0, 2**31),
            "EndpointID": ENDPOINT_ID, "Watermark": False, "GenerationTimeout": 48,
            "GenerateAudio": generate_audio, "DurationMode": "duration",
            "RichTextTemplatePrompt": prompt,
        }
        if image_assets:
            p["ReferenceImages"] = [_ref(a) for a in image_assets]
        if video_assets:
            p["ReferenceVideos"] = [_ref(a) for a in video_assets]
        if audio_assets:
            p["ReferenceAudios"] = [_ref(a) for a in audio_assets]
        if first_frame_asset:
            p["FirstFrameImageTosLocation"] = _ref(first_frame_asset)
        if last_frame_asset:
            p["LastFrameImageTosLocation"] = _ref(last_frame_asset)

        try:
            res = _bff(s, "CreateVideoGenTask", p)
        except Exception as e:
            # 批量中途失败：不丢已提交的 task_id，附在错误信息里抛出
            raise RuntimeError(
                f"第 {len(task_ids)+1}/{count} 条提交失败: {e}. "
                f"已提交: {task_ids}"
            ) from e
        task_ids.append(res["Id"])
    return task_ids


# ── 查询 ──────────────────────────────────────────────────────────────────────

def get_task(task_id: str, *, session: requests.Session | None = None) -> dict:
    """Result.Status.Phase ∈ {Queuing,Running,Completed,Failed}; Result.VideoUrl 完成时有值。"""
    s = session or _creds.bff_session()
    return _bff(s, "GetVideoGenTask", {"Id": task_id})


def wait_for_tasks(task_ids: list[str], poll_interval: int = 8, timeout: int = 600) -> list[dict]:
    s = _creds.bff_session()
    results, pending = {}, set(task_ids)
    deadline = time.time() + timeout
    while pending and time.time() < deadline:
        for tid in list(pending):
            r = get_task(tid, session=s)
            ph = r.get("Status", {}).get("Phase", "")
            print(f"  [{tid}] {ph}")
            if ph in _DONE:
                results[tid] = r; pending.discard(tid)
        if pending:
            time.sleep(poll_interval)
    for tid in pending:
        results[tid] = {"Id": tid, "Status": {"Phase": "Timeout"}, "VideoUrl": "", "Error": "Timeout"}
    return [results[tid] for tid in task_ids]


def list_tasks(page_size: int = 20, *, session: requests.Session | None = None) -> list[dict]:
    s = session or _creds.bff_session()
    return _bff(s, "ListVideoGenTasks", {"PageSize": page_size}).get("Items", [])


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json

    p = argparse.ArgumentParser(description="Seedance Mini Experience Center CLI")
    sub = p.add_subparsers(dest="cmd")

    pa = sub.add_parser("upload", help="上传素材到素材库，打印 asset_id")
    pa.add_argument("file"); pa.add_argument("--type", default="Image", choices=["Image", "Video", "Audio"])
    pa.add_argument("--group", default=DEFAULT_GROUP); pa.add_argument("--skip-moderation", action="store_true")

    pg = sub.add_parser("gen", help="提交生成任务")
    pg.add_argument("prompt")
    pg.add_argument("--image", action="append", default=[], help="参考图本地路径（可多次；自动走素材库）")
    pg.add_argument("--first", help="首帧图本地路径")
    pg.add_argument("--last", help="尾帧图本地路径")
    pg.add_argument("--ratio", default="adaptive"); pg.add_argument("--duration", type=int, default=5)
    pg.add_argument("--count", type=int, default=1); pg.add_argument("--wait", action="store_true")

    pq = sub.add_parser("get", help="查询任务"); pq.add_argument("task_id")
    sub.add_parser("list", help="列出最近任务")

    a = p.parse_args()

    if a.cmd == "upload":
        print(upload_asset(a.file, asset_type=a.type, group=a.group, moderation_skip=a.skip_moderation))

    elif a.cmd == "gen":
        s = _creds.bff_session()
        imgs = [upload_asset(x, session=s) for x in a.image]
        ff = upload_asset(a.first, session=s) if a.first else None
        lf = upload_asset(a.last, session=s) if a.last else None
        ids = generate(a.prompt, image_assets=imgs or None, first_frame_asset=ff, last_frame_asset=lf,
                       ratio=a.ratio, duration=a.duration, count=a.count, session=s)
        print("Task IDs:", ids)
        if a.wait:
            for r in wait_for_tasks(ids):
                print(f"\n[{r['Id']}] {r['Status']['Phase']}")
                if r.get("VideoUrl"): print("  VideoUrl:", r["VideoUrl"])
                err = r.get("Error") or r.get("Status", {}).get("Message")
                if err: print("  Error:", err)

    elif a.cmd == "get":
        print(json.dumps(get_task(a.task_id), indent=2, ensure_ascii=False))

    elif a.cmd == "list":
        for t in list_tasks():
            print(f"{t.get('Id')}  {t.get('Status', {}).get('Phase')}")

    else:
        p.print_help()

"""
凭证管理 — Seedance Mini Experience Center
==========================================

核心目标：**只在 onboarding 时读一次 Chrome cookie**（Mac 上会触发一次 keychain 授权），
之后所有调用都读本地缓存文件，绝不重复碰 keychain。

缓存文件： ~/.seedance_mini/creds.json  (chmod 600)
  {
    "cookies":     [{"name","value","domain","path"}, ...],   # .byteplus.com 全量 cookie
    "csrf_token":  "...",                                       # mini BFF 的 CSRF token
    "ak": "...", "sk": "...", "region": "ap-southeast-1",       # Assets API 上传用 (可选)
    "saved_at":    <unix ts>
  }

凭证来源：
  - cookies + csrf_token : 从本机 Chrome 读取（需已登录 console.byteplus.com）
  - ak / sk              : onboarding 参数，或自动从 seedance-2-0 skill 的 ark_ak_sk.json 复制

CLI:
  python creds.py onboard           # 首次配置（读 Chrome cookie + AK/SK），存本地
  python creds.py onboard --ak X --sk Y
  python creds.py refresh           # cookie 过期后重新读 Chrome（再授权一次 keychain）
  python creds.py status            # 查看缓存状态，不碰 keychain
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

CRED_DIR = Path.home() / ".seedance_mini"
CRED_FILE = CRED_DIR / "creds.json"
DEFAULT_REGION = "ap-southeast-1"

# 自动复用 seedance-2-0 skill 的 AK/SK（如果存在）
_SEEDANCE2_AKSK = Path.home() / ".claude/skills/seedance-2-0/ark_ak_sk.json"


# ── 读 Chrome cookie（唯一会碰 keychain 的地方）────────────────────────────────

def _read_chrome_cookies() -> tuple[list[dict], str]:
    """从本机 Chrome 读 .byteplus.com 的 cookie + csrfToken。触发一次 keychain。"""
    import browser_cookie3  # 延迟 import，status 命令无需它
    jar = browser_cookie3.chrome(domain_name=".byteplus.com")
    cookies = [{"name": c.name, "value": c.value, "domain": c.domain, "path": c.path}
               for c in jar]
    csrf = next((c["value"] for c in cookies if c["name"] == "csrfToken"), None)
    if not csrf:
        raise RuntimeError(
            "未在 Chrome 找到 csrfToken cookie。请先在 Chrome 登录 "
            "https://console.byteplus.com 的 BytePlus 控制台，再重试。"
        )
    return cookies, csrf


# ── onboarding / refresh / load ───────────────────────────────────────────────

def _resolve_aksk(ak: str | None, sk: str | None, region: str | None) -> tuple:
    """AK/SK 解析：显式参数 > env > seedance-2-0 的 ark_ak_sk.json。"""
    ak = ak or os.environ.get("ARK_AK")
    sk = sk or os.environ.get("ARK_SK")
    region = region or os.environ.get("ARK_REGION") or DEFAULT_REGION
    if (not ak or not sk) and _SEEDANCE2_AKSK.exists():
        d = json.loads(_SEEDANCE2_AKSK.read_text())
        ak = ak or d.get("ak")
        sk = sk or d.get("sk")
        region = d.get("region") or region
    return ak, sk, region


def onboard(ak: str | None = None, sk: str | None = None,
            region: str | None = None) -> dict:
    """首次配置：读 Chrome cookie + 解析 AK/SK，存本地缓存。"""
    cookies, csrf = _read_chrome_cookies()
    ak, sk, region = _resolve_aksk(ak, sk, region)

    CRED_DIR.mkdir(mode=0o700, exist_ok=True)
    CRED_DIR.chmod(0o700)   # mkdir 的 mode 对已存在目录无效，显式收紧
    data = {
        "cookies": cookies,
        "csrf_token": csrf,
        "ak": ak, "sk": sk, "region": region,
        "saved_at": int(time.time()),
    }
    CRED_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    CRED_FILE.chmod(0o600)
    return data


def refresh() -> dict:
    """cookie 过期后重新读 Chrome（保留已有 AK/SK）。再触发一次 keychain。"""
    existing = _load_raw() if CRED_FILE.exists() else {}
    cookies, csrf = _read_chrome_cookies()
    existing.update({"cookies": cookies, "csrf_token": csrf, "saved_at": int(time.time())})
    if "region" not in existing:
        existing["region"] = DEFAULT_REGION
    CRED_DIR.mkdir(mode=0o700, exist_ok=True)
    CRED_DIR.chmod(0o700)   # mkdir 的 mode 对已存在目录无效，显式收紧
    CRED_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
    CRED_FILE.chmod(0o600)
    return existing


def _load_raw() -> dict:
    if not CRED_FILE.exists():
        raise RuntimeError(
            f"未找到凭证缓存 {CRED_FILE}。请先运行：python creds.py onboard"
        )
    try:
        d = json.loads(CRED_FILE.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(
            f"凭证缓存 {CRED_FILE} 损坏（{e}）。请重新运行：python creds.py onboard"
        ) from e
    if not d.get("cookies") or not d.get("csrf_token"):
        raise RuntimeError(
            f"凭证缓存 {CRED_FILE} 不完整（缺 cookies/csrf）。请运行：python creds.py refresh"
        )
    return d


def load() -> dict:
    """读本地缓存凭证。**不碰 keychain。**"""
    return _load_raw()


def get_aksk() -> tuple[str, str, str]:
    """返回 (ak, sk, region)，供 assets.py 使用。"""
    d = _load_raw()
    if not d.get("ak") or not d.get("sk"):
        raise RuntimeError(
            "缓存里没有 AK/SK（上传素材库需要）。运行："
            "python creds.py onboard --ak <AK> --sk <SK>"
        )
    return d["ak"], d["sk"], d.get("region", DEFAULT_REGION)


# ── 构建 mini BFF 的 requests.Session（从本地缓存，不碰 keychain）──────────────

def bff_session() -> requests.Session:
    """用本地缓存的 cookie + csrf 构建 mini BFF session。"""
    d = _load_raw()
    s = requests.Session()
    for c in d["cookies"]:
        s.cookies.set(c["name"], c["value"], domain=c.get("domain"), path=c.get("path", "/"))
    csrf = d["csrf_token"]
    s.headers.update({
        "content-type": "application/json",
        "x-csrf-token": csrf,
        "x-tt-csrf-token": csrf,
        "referer": "https://console.byteplus.com/",
        "origin": "https://console.byteplus.com",
    })
    return s


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Seedance Mini 凭证管理")
    sub = p.add_subparsers(dest="cmd")

    po = sub.add_parser("onboard", help="首次配置（读 Chrome cookie + AK/SK）")
    po.add_argument("--ak"); po.add_argument("--sk"); po.add_argument("--region")

    sub.add_parser("refresh", help="cookie 过期后重新读 Chrome")
    sub.add_parser("status", help="查看缓存状态（不碰 keychain）")

    a = p.parse_args()

    if a.cmd == "onboard":
        d = onboard(ak=a.ak, sk=a.sk, region=a.region)
        print(f"✅ 已保存到 {CRED_FILE}")
        print(f"   cookies: {len(d['cookies'])} 个  |  csrf: {'有' if d['csrf_token'] else '无'}"
              f"  |  AK/SK: {'有' if d.get('ak') and d.get('sk') else '无(只能T2V/无素材)'}")

    elif a.cmd == "refresh":
        d = refresh()
        print(f"✅ cookie 已刷新（{len(d['cookies'])} 个）")

    elif a.cmd == "status":
        if not CRED_FILE.exists():
            print(f"❌ 未配置。运行: python creds.py onboard"); raise SystemExit(1)
        d = _load_raw()
        age_h = (int(time.time()) - d.get("saved_at", 0)) / 3600
        print(f"凭证文件: {CRED_FILE}")
        print(f"  cookies : {len(d.get('cookies', []))} 个")
        print(f"  csrf    : {'有' if d.get('csrf_token') else '无'}")
        print(f"  AK/SK   : {'有' if d.get('ak') and d.get('sk') else '无 (无法上传素材，只能纯文字)'}")
        print(f"  region  : {d.get('region')}")
        print(f"  保存于  : {age_h:.1f} 小时前")
        if age_h > 24:
            print("  ⚠️  cookie 可能已过期，若调用报 InvalidCSRFToken 请: python creds.py refresh")

    else:
        p.print_help()

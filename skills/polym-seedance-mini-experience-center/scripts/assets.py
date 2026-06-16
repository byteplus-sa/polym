"""BytePlus / Volcano-Engine Assets API client (pure stdlib).

⚠️ VENDORED COPY of ~/.claude/skills/seedance-2-0/scripts/assets.py (copied 2026-06-16).
   保持自包含是有意的。若 seedance-2-0 那份修了 SigV4 签名/端点/审核字段，记得手动 re-sync 这份。

Implements the Assets API surface for managing trusted digital portrait assets
that bypass input image moderation in the Seedance 2.0 video generation API.

Authentication: Volcano-Engine SigV4 (HMAC-SHA256) using AK/SK — NOT the
Bearer token used for the video generation API.

Endpoint: https://ark.ap-southeast-1.byteplusapi.com
Service: ark   Version: 2024-01-01   Region: ap-southeast-1

Key functions:
    load_ak_sk()           — resolve AK / SK from env or ark_ak_sk.json
    create_asset_group()   — POST /?Action=CreateAssetGroup
    create_asset()         — POST /?Action=CreateAsset (async; returns asset_id in Processing)
    get_asset()            — POST /?Action=GetAsset
    list_assets()          — POST /?Action=ListAssets
    list_asset_groups()    — POST /?Action=ListAssetGroups
    update_asset()         — POST /?Action=UpdateAsset
    delete_asset()         — POST /?Action=DeleteAsset

High-level helpers:
    upload_and_wait(group_id, url, asset_type, ...) -> asset_id
        Single-call: CreateAsset → poll GetAsset until Active → return id

Reference: see ../references/assets.md
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, parse, request


LOGGER = logging.getLogger(__name__)


# --- Constants ------------------------------------------------------------------

DEFAULT_HOST = "ark.ap-southeast-1.byteplusapi.com"
DEFAULT_REGION = "ap-southeast-1"
DEFAULT_SERVICE = "ark"
DEFAULT_VERSION = "2024-01-01"
DEFAULT_PROJECT = "default"

ALGORITHM = "HMAC-SHA256"

# Asset status enum
ASSET_PROCESSING = "Processing"
ASSET_ACTIVE = "Active"
ASSET_FAILED = "Failed"
ASSET_TERMINAL = {ASSET_ACTIVE, ASSET_FAILED}

# Asset / group types
GROUP_TYPE_AIGC = "AIGC"
ASSET_TYPE_IMAGE = "Image"
ASSET_TYPE_VIDEO = "Video"
ASSET_TYPE_AUDIO = "Audio"

# Content pre-filter review strategy (CreateAsset `Moderation.Strategy`)
MODERATION_DEFAULT = "Default"  # content pre-filter review is ON (server default)
MODERATION_SKIP = "Skip"        # skip most non-baseline content security review policies


# --- AK/SK resolution -----------------------------------------------------------

def load_ak_sk(
    ak: str | None = None,
    sk: str | None = None,
    region: str | None = None,
) -> tuple[str, str, str]:
    """Resolve (ak, sk, region) from explicit args, env vars, or ark_ak_sk.json.

    Lookup order per credential:
        1. Explicit argument
        2. ARK_AK / ARK_SK / ARK_REGION env vars
        3. ark_ak_sk.json next to the skill root: {"ak":"...","sk":"...","region":"..."}

    Region defaults to "ap-southeast-1" if not configured.

    Raises:
        RuntimeError if ak or sk cannot be resolved.
    """
    if ak and sk:
        return ak.strip(), sk.strip(), (region or DEFAULT_REGION).strip()

    env_ak = os.getenv("ARK_AK")
    env_sk = os.getenv("ARK_SK")
    env_region = os.getenv("ARK_REGION")
    if env_ak and env_sk:
        return (
            env_ak.strip(),
            env_sk.strip(),
            (region or env_region or DEFAULT_REGION).strip(),
        )

    skill_dir = Path(__file__).resolve().parent.parent
    cred_file = skill_dir / "ark_ak_sk.json"
    if cred_file.exists():
        try:
            data = json.loads(cred_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"{cred_file} is not valid JSON: {exc}"
            ) from exc
        file_ak = data.get("ak") or data.get("AK")
        file_sk = data.get("sk") or data.get("SK")
        file_region = data.get("region") or data.get("Region")
        if file_ak and file_sk:
            return (
                str(file_ak).strip(),
                str(file_sk).strip(),
                (region or file_region or DEFAULT_REGION).strip(),
            )

    raise RuntimeError(
        "ARK AK/SK not found. Provide one of:\n"
        "  - ak= / sk= arguments\n"
        "  - ARK_AK + ARK_SK environment variables\n"
        f"  - {cred_file} with {{\"ak\":\"...\",\"sk\":\"...\",\"region\":\"ap-southeast-1\"}}"
    )


# --- SigV4 signing (Volcano-Engine flavor) --------------------------------------

def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hmac_sha256(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _canonical_query_string(params: dict[str, str]) -> str:
    """Canonicalize query string per SigV4 spec (sorted, percent-encoded)."""
    items = []
    for k in sorted(params.keys()):
        ek = parse.quote(k, safe="-_.~")
        ev = parse.quote(str(params[k]), safe="-_.~")
        items.append(f"{ek}={ev}")
    return "&".join(items)


def _canonical_headers(headers: dict[str, str]) -> tuple[str, str]:
    """Return (canonical_headers_block, signed_headers_list)."""
    lower = {k.lower(): str(v).strip() for k, v in headers.items()}
    keys = sorted(lower.keys())
    canon = "".join(f"{k}:{lower[k]}\n" for k in keys)
    signed = ";".join(keys)
    return canon, signed


def _canonical_request(
    method: str,
    canonical_uri: str,
    query: dict[str, str],
    headers: dict[str, str],
    payload: bytes,
) -> tuple[str, str]:
    canon_headers, signed_headers = _canonical_headers(headers)
    body_hash = _sha256_hex(payload)
    canon = "\n".join([
        method.upper(),
        canonical_uri or "/",
        _canonical_query_string(query),
        canon_headers,
        signed_headers,
        body_hash,
    ])
    return canon, signed_headers


def _string_to_sign(amz_date: str, credential_scope: str, canonical_request: str) -> str:
    return "\n".join([
        ALGORITHM,
        amz_date,
        credential_scope,
        _sha256_hex(canonical_request.encode("utf-8")),
    ])


def _derive_signing_key(sk: str, date: str, region: str, service: str) -> bytes:
    """Volcano-Engine signing key derivation (NB: no AWS4 prefix)."""
    k_date = _hmac_sha256(sk.encode("utf-8"), date)
    k_region = _hmac_sha256(k_date, region)
    k_service = _hmac_sha256(k_region, service)
    k_signing = _hmac_sha256(k_service, "request")
    return k_signing


def _sign(
    method: str,
    canonical_uri: str,
    query: dict[str, str],
    headers: dict[str, str],
    payload: bytes,
    *,
    ak: str,
    sk: str,
    region: str,
    service: str,
    amz_date: str,
) -> str:
    """Compute the Authorization header value."""
    date = amz_date[:8]  # YYYYMMDD
    canon_req, signed_headers = _canonical_request(
        method, canonical_uri, query, headers, payload
    )
    credential_scope = f"{date}/{region}/{service}/request"
    sts = _string_to_sign(amz_date, credential_scope, canon_req)
    signing_key = _derive_signing_key(sk, date, region, service)
    signature = hmac.new(
        signing_key, sts.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return (
        f"{ALGORITHM} "
        f"Credential={ak}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, "
        f"Signature={signature}"
    )


# --- Low-level call -------------------------------------------------------------

def _call(
    action: str,
    payload: dict | None = None,
    *,
    ak: str | None = None,
    sk: str | None = None,
    region: str | None = None,
    host: str = DEFAULT_HOST,
    service: str = DEFAULT_SERVICE,
    version: str = DEFAULT_VERSION,
    timeout: int = 30,
) -> dict[str, Any]:
    """Sign and POST a single Action call.

    Returns the parsed JSON response body. Raises RuntimeError on HTTP error.
    """
    resolved_ak, resolved_sk, resolved_region = load_ak_sk(ak, sk, region)

    body = json.dumps(payload or {}, separators=(",", ":")).encode("utf-8")
    now = _dt.datetime.now(_dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    short_date = amz_date[:8]

    query = {"Action": action, "Version": version}
    headers = {
        "Host": host,
        "X-Date": amz_date,
        "Content-Type": "application/json",
        "X-Content-Sha256": _sha256_hex(body),
    }

    auth_header = _sign(
        "POST",
        "/",
        query,
        headers,
        body,
        ak=resolved_ak,
        sk=resolved_sk,
        region=resolved_region,
        service=service,
        amz_date=amz_date,
    )
    headers["Authorization"] = auth_header

    url = f"https://{host}/?{_canonical_query_string(query)}"
    req = request.Request(url, data=body, headers=headers, method="POST")

    try:
        with request.urlopen(req, timeout=timeout) as resp:
            response_body = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(
            f"{action} failed [HTTP {exc.code}]: {err_body}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"{action} failed: {exc}") from exc

    if not response_body:
        return {}
    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{action} returned non-JSON body: {response_body[:200]}"
        ) from exc

    # Surface API-level errors
    meta = parsed.get("ResponseMetadata") or {}
    if isinstance(meta, dict) and meta.get("Error"):
        err = meta["Error"]
        raise RuntimeError(
            f"{action} returned API error: "
            f"{err.get('Code')} - {err.get('Message')} "
            f"(request_id={meta.get('RequestId')})"
        )
    return parsed


# --- Asset Group operations -----------------------------------------------------

def create_asset_group(
    name: str,
    *,
    description: str = "",
    group_type: str = GROUP_TYPE_AIGC,
    project_name: str = DEFAULT_PROJECT,
    **kw: Any,
) -> str:
    """Create an asset group. Returns the new group_id.

    Raises RuntimeError if the authorization letter has not been signed
    (one-time setup in BytePlus Console).
    """
    payload = {
        "Name": name,
        "Description": description,
        "GroupType": group_type,
        "ProjectName": project_name,
    }
    resp = _call("CreateAssetGroup", payload, **kw)
    result = resp.get("Result") or {}
    gid = result.get("Id")
    if not gid:
        raise RuntimeError(f"CreateAssetGroup response missing Result.Id: {resp}")
    return gid


def list_asset_groups(
    *,
    name: str | None = None,
    group_ids: list[str] | None = None,
    group_type: str = GROUP_TYPE_AIGC,
    page_number: int = 1,
    page_size: int = 100,
    project_name: str = DEFAULT_PROJECT,
    sort_by: str = "CreateTime",
    sort_order: str = "Desc",
    **kw: Any,
) -> dict[str, Any]:
    """List asset groups. Returns the parsed Result block (Items, TotalCount, ...)."""
    filt: dict[str, Any] = {"GroupType": group_type}
    if name:
        filt["Name"] = name
    if group_ids:
        filt["GroupIds"] = group_ids
    payload = {
        "Filter": filt,
        "PageNumber": page_number,
        "PageSize": page_size,
        "SortBy": sort_by,
        "SortOrder": sort_order,
        "ProjectName": project_name,
    }
    return (_call("ListAssetGroups", payload, **kw).get("Result") or {})


def get_asset_group(group_id: str, **kw: Any) -> dict[str, Any]:
    return (_call("GetAssetGroup", {"Id": group_id}, **kw).get("Result") or {})


def update_asset_group(
    group_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    **kw: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"Id": group_id}
    if name is not None:
        payload["Name"] = name
    if description is not None:
        payload["Description"] = description
    return (_call("UpdateAssetGroup", payload, **kw).get("Result") or {})


# --- Asset operations -----------------------------------------------------------

def create_asset(
    group_id: str,
    url: str,
    *,
    asset_type: str = ASSET_TYPE_IMAGE,
    name: str = "",
    project_name: str = DEFAULT_PROJECT,
    moderation_strategy: str | None = None,
    **kw: Any,
) -> str:
    """Create an asset. Returns asset_id (initial status = Processing).

    The `url` MUST be publicly fetchable by ModelArk (no Lark-internal links,
    no auth, no data: URIs).

    `moderation_strategy` maps to the CreateAsset `Moderation.Strategy` field:
      - None / "Default" → content pre-filter review is ON (server default).
      - "Skip" (MODERATION_SKIP) → skip most non-baseline content security
        review policies for this asset. Use only for content you are
        authorized to use; baseline policies still apply.

    To use the asset for generation, you must first wait until status = Active.
    Use `upload_and_wait()` to do create + poll in one call.
    """
    payload = {
        "GroupId": group_id,
        "URL": url,
        "AssetType": asset_type,
        "Name": name,
        "ProjectName": project_name,
    }
    if moderation_strategy is not None:
        payload["Moderation"] = {"Strategy": moderation_strategy}
    resp = _call("CreateAsset", payload, **kw)
    result = resp.get("Result") or {}
    aid = result.get("Id") or result.get("AssetId")
    if not aid:
        raise RuntimeError(f"CreateAsset response missing Result.Id: {resp}")
    return aid


def get_asset(asset_id: str, **kw: Any) -> dict[str, Any]:
    """Retrieve a single asset's info. Returns the Result block."""
    return (_call("GetAsset", {"Id": asset_id}, **kw).get("Result") or {})


def list_assets(
    group_ids: list[str] | None = None,
    *,
    statuses: list[str] | None = None,
    name: str | None = None,
    group_type: str = GROUP_TYPE_AIGC,
    page_number: int = 1,
    page_size: int = 100,
    project_name: str = DEFAULT_PROJECT,
    sort_by: str = "CreateTime",
    sort_order: str = "Desc",
    **kw: Any,
) -> dict[str, Any]:
    filt: dict[str, Any] = {"GroupType": group_type}
    if group_ids:
        filt["GroupIds"] = group_ids
    if statuses:
        filt["Statuses"] = statuses
    if name:
        filt["Name"] = name
    payload = {
        "Filter": filt,
        "PageNumber": page_number,
        "PageSize": page_size,
        "SortBy": sort_by,
        "SortOrder": sort_order,
        "ProjectName": project_name,
    }
    return (_call("ListAssets", payload, **kw).get("Result") or {})


def update_asset(
    asset_id: str,
    *,
    name: str | None = None,
    **kw: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"Id": asset_id}
    if name is not None:
        payload["Name"] = name
    return (_call("UpdateAsset", payload, **kw).get("Result") or {})


def delete_asset(asset_id: str, **kw: Any) -> dict[str, Any]:
    return (_call("DeleteAsset", {"Id": asset_id}, **kw).get("Result") or {})


# --- High-level orchestration ---------------------------------------------------

def wait_for_active(
    asset_id: str,
    *,
    interval_seconds: float = 3.0,
    timeout_seconds: float = 120.0,
    **kw: Any,
) -> dict[str, Any]:
    """Poll GetAsset until status is Active or Failed (or timeout).

    Returns the final asset Result dict on Active.
    Raises RuntimeError on Failed or timeout.
    """
    deadline = time.monotonic() + timeout_seconds
    last: dict[str, Any] = {}
    while True:
        if time.monotonic() > deadline:
            raise RuntimeError(
                f"Asset {asset_id} polling timed out after {timeout_seconds}s "
                f"(last status: {last.get('Status')})"
            )
        last = get_asset(asset_id, **kw)
        status = last.get("Status")
        if status == ASSET_ACTIVE:
            return last
        if status == ASSET_FAILED:
            err = last.get("Error") or {}
            raise RuntimeError(
                f"Asset {asset_id} failed: "
                f"{err.get('Code')} - {err.get('Message')}"
            )
        # Processing or unknown — keep polling
        time.sleep(interval_seconds)


def upload_and_wait(
    group_id: str,
    url: str,
    *,
    asset_type: str = ASSET_TYPE_IMAGE,
    name: str = "",
    project_name: str = DEFAULT_PROJECT,
    moderation_strategy: str | None = None,
    interval_seconds: float = 3.0,
    timeout_seconds: float = 120.0,
    **kw: Any,
) -> str:
    """Create an asset and wait until Active, returning the asset_id.

    This is the most common use: hand it a publicly-fetchable URL and get
    back an `asset-...` id ready to use as `asset://<id>` in generation.

    Pass `moderation_strategy="Skip"` (MODERATION_SKIP) to skip the content
    pre-filter review for this asset (see create_asset). Default leaves review on.

    For convenience: returns just the asset_id string. Call get_asset() for
    the full payload.
    """
    asset_id = create_asset(
        group_id,
        url,
        asset_type=asset_type,
        name=name,
        project_name=project_name,
        moderation_strategy=moderation_strategy,
        **kw,
    )
    LOGGER.info("CreateAsset ok: id=%s status=Processing", asset_id)
    info = wait_for_active(
        asset_id,
        interval_seconds=interval_seconds,
        timeout_seconds=timeout_seconds,
        **kw,
    )
    LOGGER.info("Asset Active: id=%s url=%s", asset_id, info.get("URL"))
    return asset_id


def get_or_create_group(
    name: str,
    *,
    description: str = "",
    project_name: str = DEFAULT_PROJECT,
    group_type: str = GROUP_TYPE_AIGC,
    **kw: Any,
) -> str:
    """Find an existing group by exact name match, or create one.

    Convenient idempotent setup: pin a logical project to a stable group name.
    """
    listing = list_asset_groups(
        name=name,
        group_type=group_type,
        project_name=project_name,
        **kw,
    )
    for item in listing.get("Items") or []:
        # Exact match — ListAssetGroups uses fuzzy matching on Filter.name,
        # so we still verify equality.
        if (item.get("Name") or "") == name:
            return item.get("Id") or ""
    return create_asset_group(
        name,
        description=description,
        group_type=group_type,
        project_name=project_name,
        **kw,
    )


def asset_url(asset_id: str) -> str:
    """Convert an asset_id into the asset:// URL form used by the generation API."""
    if asset_id.startswith("asset://"):
        return asset_id
    return f"asset://{asset_id}"


__all__ = [
    "ASSET_ACTIVE",
    "ASSET_FAILED",
    "ASSET_PROCESSING",
    "ASSET_TYPE_AUDIO",
    "ASSET_TYPE_IMAGE",
    "ASSET_TYPE_VIDEO",
    "GROUP_TYPE_AIGC",
    "MODERATION_DEFAULT",
    "MODERATION_SKIP",
    "asset_url",
    "create_asset",
    "create_asset_group",
    "delete_asset",
    "get_asset",
    "get_asset_group",
    "get_or_create_group",
    "list_asset_groups",
    "list_assets",
    "load_ak_sk",
    "update_asset",
    "update_asset_group",
    "upload_and_wait",
    "wait_for_active",
]

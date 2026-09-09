"""
GenBox v2 - 多模型生图生视频服务
FastAPI 主入口
"""
import os
import sys
import platform
import re
import base64
import binascii
import math
import hmac
import hashlib
import threading
import asyncio
import io
import json as _json
import time
import uuid
import secrets
import webbrowser
import warnings
import uvicorn
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, List, Optional
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from genbox_version import __version__


def _configure_console_encoding() -> None:
    """Keep packaged Windows startup output from failing on Unicode text."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError):
                pass


_configure_console_encoding()

# ──────────────────────────────────────────────────────────────
# PyInstaller 路径兼容
# ──────────────────────────────────────────────────────────────
def get_base_path() -> Path:
    """获取基础路径（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return Path(sys._MEIPASS)
    else:
        # 源码运行
        return Path(__file__).parent

BASE_PATH = get_base_path()

# 确保工作目录正确
if getattr(sys, 'frozen', False):
    os.chdir(Path(sys.executable).parent)

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictFloat, StrictInt, model_validator
from pydantic_core import PydanticCustomError
from PIL import Image

from config import (
    cfg_mgr, BASE_DIR, GALLERY_DIR, STORAGE_DIR, PrecisionEditProfile, ProviderConfig, ProvidersConfig,
    PRECISION_GPT_IMAGE_2_FLEXIBLE_SIZE_POLICY,
    documented_precision_model_size_presets,
    gpt_image_2_size_error,
    is_prod_mode, get_admin_key, verify_admin_key, generate_admin_key, reset_admin_key,
    normalize_precision_capability_size, precision_capability_size_declaration,
    resolve_precision_model_capability, verify_ssl_enabled,
)
from providers import (
    DEFAULT_PRECISION_RESIZE_GUIDANCE,
    GeneratedImageValidationError,
    ImageResult,
    ProviderResponseValidationError,
    _decode_generated_image_base64,
    _endpoint_failure_summary,
    _parse_provider_json_response,
    _provider_error_text,
    _save_image,
    _stream_bounded_provider_response,
    enhance_prompt_with_llm,
    enhance_prompt_with_llm_detailed,
    fetch_models_from_upstream,
    generate_multi,
    precision_model_uses_gpt_image_2_size_contract,
    resolve_provider_precision_model_capability,
    translate_upstream_error,
)

# ── 远程 chatgpt2api 兼容部署同步 ──
from sync.models import RemoteImageRecord, SyncCandidate, SyncDeployment
from sync.client import ChatGPT2APIClient, sha256_bytes
from sync.manifest import SyncManifest, LocalImageIndex
from sync.ingest import (
    PUSH_CONTRACT_VERSION,
    authenticate_push_source,
    push_max_image_bytes,
    validate_source_sha256,
    validate_image_payload,
    validate_remote_path,
)
import sync.store as sync_store
from extensions.models import (
    ExtensionBatchTargetsRequest, ExtensionDeployRequest, ExtensionDiscoveryRequest,
    ExtensionDeliveryClaimRequest, ExtensionHostKeyConfirmRequest, ExtensionHostKeyPairingCancelRequest,
    ExtensionHostKeyPairingCompleteRequest, ExtensionHostKeyPairingStartRequest, ExtensionHostKeyProbeRequest, ExtensionKeyResetRequest,
    ExtensionHostKeyResetRequest,
    ExtensionTaskResumeRequest,
    ExtensionPlanRequest, ExtensionTestRequest, PushKeyLocalSaveConfirmationRequest, PushKeyLocalSaveRequest,
    PushSourceProvisionRequest, PushSourceRotateRequest, PushSourceGrantDeleteRequest,
    ImageIntegrationCheckRequest,
    ManagedCredential, ManagedCredentialUpsertRequest, VaultPasswordRequest,
    ManagedImageUpdatePlanRequest, ManagedImageUpdateApplyRequest, SSHCredential,
    is_canonical_host_key_trust, is_immutable_image_reference, validate_deployment_image,
)
from extensions.orchestrator import (
    DeploymentAttemptConflictError, DeploymentNoTaskError, SSHAuthenticationError, SSHConnectionError,
    deployment_plans, extension_tasks, public_instance_access, public_instance_handle, reset_managed_admin_key,
    update_managed_image,
    probe_host_key,
    test_connection as test_extension_connection,
)
from extensions.discovery import discover_environment
from extensions.read_only_discovery_plan import (
    DiscoveryPlanValidationError,
    ValidatedDiscoveryPlan,
    validate_read_only_discovery_plan,
)
from extensions.capabilities import validate_deployment_capability
from extensions.image_capabilities import check_image_integration
import extensions.store as extensions_store
from extensions.store import (
    build_host_key_pairing_helper,
    parse_host_key_pairing_response,
    target_identity_digest,
    host_key_pairings,
)
from extensions.credential_vault import credential_vault
from extensions.catalog import public_catalog
from extensions.models import NetworkConnectRequest
from extensions.network_adapters import network_tasks
from extensions.local_tailscale import begin_login, enable_genbox_serve, local_install_tasks, local_status
from sync.push_sources import create_source as create_push_source
from sync.push_sources import deletion_granted as push_source_deletion_granted
from sync.push_sources import list_sources as list_push_sources
from sync.push_sources import revoke_source as revoke_push_source
from sync.push_sources import revoke_target_sources as revoke_target_push_sources
from sync.push_sources import rotate_source as rotate_push_source
from sync.push_sources import set_source_grant_delete as set_push_source_grant_delete
from sync.push_sources import source_key_belongs_to_instance
from image_tools.cutout_onnx import (
    ADAPTER_ID as CUTOUT_ADAPTER_ID,
    MODEL_MANIFEST as CUTOUT_MODEL_MANIFEST,
    MODEL_RELATIVE_PATH as CUTOUT_MODEL_RELATIVE_PATH,
    CutoutAdapterError,
    CutoutONNXAdapter,
)
from image_tools.cutout_model_manager import (
    MODEL_INSTALL_CONTRACT as CUTOUT_MODEL_INSTALL_CONTRACT,
    MODEL_SOURCE_ID as CUTOUT_MODEL_SOURCE_ID,
    MODEL_SOURCE_PAGE as CUTOUT_MODEL_SOURCE_PAGE,
    CutoutModelManager,
    CutoutModelManagerError,
)
from image_tools.cutout_registry import create_default_registry
from image_tools.cutout_refine import (
    CUTOUT_REFINE_CONTRACT,
    CUTOUT_SELECTION_MASK_CONTRACT,
    MAX_FEATHER_RADIUS,
    CutoutRefineError,
    refine_cutout_alpha,
    save_refined_png_atomic,
)
from image_tools.cutout_modnet_import import (
    ModNetImportError,
    ModNetModelImportManager,
)
from image_tools.cutout_modnet import MODNET_ADAPTER_ID, ModNetONNXAdapter


# ──────────────────────────────────────────────────────────────
# SSRF 防护：私有 IP 黑名单
# ──────────────────────────────────────────────────────────────
import ipaddress
import socket as _socket

_BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # localhost
    ipaddress.ip_network("10.0.0.0/8"),       # 私有 A 类
    ipaddress.ip_network("172.16.0.0/12"),    # 私有 B 类
    ipaddress.ip_network("192.168.0.0/16"),   # 私有 C 类
    ipaddress.ip_network("169.254.0.0/16"),   # 链路本地
    ipaddress.ip_network("::1/128"),          # IPv6 localhost
    ipaddress.ip_network("fc00::/7"),         # IPv6 私有
    ipaddress.ip_network("fe80::/10"),        # IPv6 链路本地
]

def _is_url_safe(url: str) -> tuple:
    """检查 URL 是否指向私有/内网 IP。返回 (safe, error_msg)"""
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False, "无效的 URL"
        # 解析域名到 IP
        try:
            ip_str = _socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            for net in _BLOCKED_IP_RANGES:
                if ip in net:
                    return False, f"目标 IP {ip_str} 属于保留地址范围"
        except _socket.gaierror:
            return False, f"无法解析域名: {hostname}"
        return True, None
    except Exception as e:
        return False, f"URL 解析失败: {str(e)[:50]}"


# ──────────────────────────────────────────────────────────────
# Pydantic 模型
# ──────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    providers: List[str] = []          # Provider ID 列表（空=全部启用）
    enhance_prompt: bool = False
    llm_provider_id: Optional[str] = None  # 指定用于优化提示词的 LLM Provider
    size: Optional[str] = None
    quality: Optional[str] = None
    mode: str = "t2i"                # t2i | i2i | inpaint | precision_edit
    image_data: Optional[str] = None  # base64 图片数据 (i2i 模式)
    image_data_list: List[str] = []   # 多张参考图；image_data 保留兼容旧客户端
    mask_data: Optional[str] = None    # 局部重绘遮罩（白色=编辑）
    mask_contract: Optional[str] = None
    annotation_image_data: Optional[str] = None  # 精准改图批注叠加图
    annotation_contract: Optional[str] = None
    annotations: List[dict] = []       # 箭头、矩形、文字的归一化坐标
    precision_strategy: str = "standard"  # fine | standard | fast
    precision_selection_mode: str = "annotation"  # annotation | local
    precision_selection_feather: StrictInt | StrictFloat = 0  # local selection guidance only, 0-64px
    precision_size_mode: str = "preserve"  # preserve | resize；精准改图不复用文生图尺寸
    precision_target_size: Optional[str] = None
    precision_resize_prompt: Optional[str] = None
    precision_output_size_policy: str = "strict"  # strict | fit_crop；仅 precision resize
    strength: float = 0.55            # 变换强度 (i2i 模式)
    continuous: bool = False          # 连续生图模式（保持一致性）
    system_prompt: Optional[str] = None  # 系统提示词（专业模式）
    continuous_id: Optional[str] = None  # 连续生图会话 ID（用于保持一致性）
    quantities: dict = {}              # {provider_id: 数量(int)}，如 {"gpt-image": 2, "gemini": 1}
    # ── Per-provider 设置 ──
    provider_settings: dict = {}       # {provider_id: {quality, size, ...}}
    exact_ratio_crop: bool = False      # 用户显式允许对近似画布做居中裁切
    # ── 尺寸自适应：小图生成 + 本地放大 ──
    upscale_to: Optional[str] = None
    upscale_method: str = "lanczos3"
    upscale_ratio: str = "original"  # 宽高比：1:1, 16:9, 21:9, 4:3, 3:2, 9:16, 3:4, original

    @model_validator(mode="before")
    @classmethod
    def reject_unknown_precision_fields(cls, value):
        """Reject likely precision aliases without changing other mode compatibility."""
        if not isinstance(value, dict) or value.get("mode") != "precision_edit":
            return value

        known_fields = set(cls.model_fields)
        precision_boundary_aliases = {
            "imagedatalist",
            "maskcontract",
            "maskdata",
            "upscaleratio",
            "upscaleto",
        }
        for raw_name in value:
            if not isinstance(raw_name, str) or raw_name in known_fields:
                continue
            normalized = re.sub(r"[^a-z0-9]", "", raw_name.lower())
            if (
                normalized.startswith("annotation")
                or normalized.startswith("precision")
                or normalized in precision_boundary_aliases
            ):
                raise PydanticCustomError(
                    "precision_unknown_field",
                    "precision_edit contains unsupported precision fields",
                )
        return value


class CutoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: str
    image_data: str
    adapter: Optional[str] = None
    algorithm: Optional[str] = None


class CutoutModelActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: str
    source_id: str
    confirmed: StrictBool


class CutoutRefineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract: str
    image_data: str
    selection_mask_data: Optional[str] = None
    selection_mask_contract: Optional[str] = None
    feather_radius: StrictInt | StrictFloat = 0
    restore_mode: bool = False
    restore_source_image_data: Optional[str] = None
    restore_min_alpha: StrictInt | StrictFloat = 255
    parent_version_id: Optional[str] = None


GENERATION_MODES = frozenset({"t2i", "i2i", "inpaint", "precision_edit"})
INPAINT_MASK_CONTRACT = "genbox-edit-white-v1"
PRECISION_ANNOTATION_CONTRACT_V1 = "genbox-annotation-v1"
PRECISION_ANNOTATION_CONTRACT_V2 = "genbox-annotation-v2"
PRECISION_ANNOTATION_CONTRACT_V3 = "genbox-annotation-v3"
PRECISION_ANNOTATION_CONTRACT = PRECISION_ANNOTATION_CONTRACT_V1
PRECISION_ANNOTATION_CONTRACTS = frozenset({
    PRECISION_ANNOTATION_CONTRACT_V1,
    PRECISION_ANNOTATION_CONTRACT_V2,
    PRECISION_ANNOTATION_CONTRACT_V3,
})
PRECISION_EDIT_CAPABILITY = "precision_edit"
PRECISION_ANNOTATION_TYPES = frozenset({"arrow", "rectangle", "ellipse", "brush", "text"})
PRECISION_STRATEGIES = frozenset({"fine", "standard", "fast"})
PRECISION_SELECTION_MODES = frozenset({"annotation", "local"})
PRECISION_SELECTION_TYPES = frozenset({"rectangle", "ellipse", "brush"})
MAX_PRECISION_SELECTION_FEATHER = 64
MAX_PRECISION_ANNOTATIONS = 100
MAX_PRECISION_BRUSH_POINTS = 1024
MAX_PRECISION_BRUSH_POINTS_TOTAL = 4096
MAX_PRECISION_ANNOTATION_TEXT = 500
MAX_PRECISION_ANNOTATION_TEXT_TOTAL = 4000
MAX_PRECISION_PROMPT_TEXT = 2000
MAX_PRECISION_RESIZE_PROMPT_TEXT = 500
PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE = "gpt-image-2"
MAX_PRECISION_OUTPUT_PIXELS = int(
    os.getenv("GENBOX_PRECISION_MAX_OUTPUT_PIXELS", str(64 * 1024 * 1024))
)
MAX_PRECISION_SUPPORTED_SIZES = 64
CUTOUT_CONTRACT = "genbox-cutout-v1"
# The adapter is declared locally, but capability is advertised only after the
# fixed model manifest and CPU-only ONNX session have both been validated.
CUTOUT_MODEL_PATH = BASE_DIR / CUTOUT_MODEL_RELATIVE_PATH
CUTOUT_ADAPTER = CutoutONNXAdapter(model_path=CUTOUT_MODEL_PATH)
CUTOUT_MODEL_MANAGER = CutoutModelManager(CUTOUT_ADAPTER)
# MODNet is an explicit, user-supplied experimental checkpoint.  Keep its
# importer isolated from the U²-Net installer and default registry.
MODNET_IMPORT_MANAGER = ModNetModelImportManager(base_path=BASE_DIR)
# Keep model installation tied to the existing U2Net adapter while routing
# execution through the fail-closed multi-algorithm registry.
CUTOUT_REGISTRY = create_default_registry(CUTOUT_ADAPTER)


def _refresh_modnet_registry(manager: ModNetModelImportManager) -> dict[str, Any]:
    """Replace the MODNet placeholder only after a full runtime probe passes."""
    status = manager.status()
    manifest = manager.manifest()
    if not status.get("installed") or not status.get("valid") or manifest is None:
        return {"available": False, "executable": False, "state": "needs_model"}
    adapter = ModNetONNXAdapter(
        model_path=manager.model_path,
        base_path=manager.base_path,
        model_manifest={**manifest, "filename": status.get("filename") or manifest["filename"]},
        license_confirmed=bool(status.get("license_confirmed")),
        license_source=status.get("license_source"),
    )
    capability = dict(adapter.capabilities())
    if capability.get("available") is not True or capability.get("executable") is not True:
        return capability
    runtime_adapter_id = str(getattr(adapter, "adapter_id", "")).strip()
    if not runtime_adapter_id:
        return capability
    registered_ids = set(CUTOUT_REGISTRY.ids())
    # The first successful probe replaces the descriptive placeholder with the
    # runtime adapter id. Later capability checks must replace that runtime
    # entry in place instead of trying to replace a placeholder that no longer
    # exists.
    replace_id = (
        runtime_adapter_id
        if runtime_adapter_id in registered_ids
        else "modnet-photographic-portrait"
    )
    if replace_id not in registered_ids:
        return capability
    CUTOUT_REGISTRY.replace(
        replace_id,
        adapter,
        verified=True,
        algorithm=capability.get("algorithm") or "MODNet photographic portrait matting ONNX",
        algorithm_aliases=("modnet", "modnet portrait", "modnet photographic portrait matting"),
    )
    return capability
GENERATION_ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
MAX_GENERATION_INPUT_BYTES = int(
    os.getenv("GENBOX_GENERATE_MAX_IMAGE_BYTES", str(25 * 1024 * 1024))
)
MAX_GENERATION_INPUT_PIXELS = int(
    os.getenv("GENBOX_GENERATE_MAX_IMAGE_PIXELS", "25000000")
)
_GENERATION_IMAGE_VALIDATION_LOCK = threading.RLock()
_GENERATION_IMAGE_FORMAT_MIME_TYPES = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}
_GALLERY_FILE_EXTENSIONS = frozenset({".png"})
_VIDEO_FILE_EXTENSIONS = frozenset({".mp4", ".webm", ".mov"})
_VIDEO_THUMB_EXTENSIONS = frozenset({".jpg"})
_VIDEO_MEDIA_TYPES = {
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
}
MAX_BYTE_RANGE_DIGITS = 20


def _gallery_file_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="图片不存在")


def _video_file_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="视频文件不存在")


def _thumbnail_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="缩略图不存在")


def _resolve_confined_media_file(
    root: Path,
    filename: object,
    *,
    allowed_extensions: frozenset[str],
    not_found,
    must_exist: bool = True,
) -> Path:
    raw_name = str(filename or "")
    probe = raw_name
    for _ in range(5):
        posix = PurePosixPath(probe)
        windows = PureWindowsPath(probe)
        if (
            not probe
            or probe in {".", ".."}
            or "/" in probe
            or "\\" in probe
            or ":" in probe
            or posix.is_absolute()
            or windows.is_absolute()
            or bool(windows.drive)
            or len(posix.parts) != 1
            or len(windows.parts) != 1
            or posix.suffix.lower() not in allowed_extensions
        ):
            raise not_found()
        decoded = unquote(probe)
        if decoded == probe:
            break
        probe = decoded
    else:
        raise not_found()

    try:
        confined_root = Path(root).resolve(strict=True)
        unresolved = confined_root / raw_name
        if not confined_root.is_dir() or unresolved.is_symlink():
            raise ValueError("unsafe media path")
        candidate = unresolved.resolve(strict=must_exist)
        candidate.relative_to(confined_root)
    except (OSError, RuntimeError, ValueError):
        raise not_found() from None
    if candidate.parent != confined_root or candidate.name != raw_name:
        raise not_found()
    if must_exist and not candidate.is_file():
        raise not_found()
    if not must_exist and candidate.exists() and not candidate.is_file():
        raise not_found()
    return candidate


def _resolve_gallery_file(filename: object) -> Path:
    return _resolve_confined_media_file(
        GALLERY_DIR,
        filename,
        allowed_extensions=_GALLERY_FILE_EXTENSIONS,
        not_found=_gallery_file_not_found,
    )


def _resolve_video_file(filename: object, *, must_exist: bool = True) -> Path:
    return _resolve_confined_media_file(
        VIDEO_DIR,
        filename,
        allowed_extensions=_VIDEO_FILE_EXTENSIONS,
        not_found=_video_file_not_found,
        must_exist=must_exist,
    )


def _resolve_video_thumbnail_file(filename: object, *, must_exist: bool = True) -> Path:
    return _resolve_confined_media_file(
        VIDEO_THUMBS_DIR,
        filename,
        allowed_extensions=_VIDEO_THUMB_EXTENSIONS,
        not_found=_thumbnail_not_found,
        must_exist=must_exist,
    )


def _read_gallery_image_payload(path: Path) -> tuple[bytes, str, str]:
    """Read and verify gallery bytes, deriving MIME from decoded content."""
    try:
        payload = path.read_bytes()
        prompt_text = ""
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(payload)) as image:
                image_format = str(image.format or "").upper()
                prompt_text = str((image.info or {}).get("Prompt") or "")
                image.verify()
            with Image.open(io.BytesIO(payload)) as image:
                image.load()
    except Exception:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "gallery_image_invalid",
                "message": "gallery image is not readable",
            },
        ) from None

    mime_type = _GENERATION_IMAGE_FORMAT_MIME_TYPES.get(image_format, "")
    if mime_type not in GENERATION_ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "gallery_image_mime_unsupported",
                "message": "gallery image uses an unsupported MIME type",
            },
        )
    return payload, mime_type, prompt_text


def _load_gallery_image_payload(filename: object) -> tuple[Path, bytes, str, str]:
    path = _resolve_gallery_file(filename)
    payload, mime_type, prompt_text = _read_gallery_image_payload(path)
    return path, payload, mime_type, prompt_text


def _load_thumbnail_image_payload(filename: object) -> tuple[bytes, str]:
    try:
        _path, payload, mime_type, _prompt = _load_gallery_image_payload(filename)
        return payload, mime_type
    except HTTPException as exc:
        if exc.status_code != 404:
            raise

    try:
        video_path = _resolve_video_file(filename, must_exist=False)
        thumb_name = video_path.stem + "_thumb.jpg"
        planned_thumb = _resolve_video_thumbnail_file(thumb_name, must_exist=False)
    except HTTPException:
        raise _thumbnail_not_found() from None

    if planned_thumb.exists():
        thumb_path = _resolve_video_thumbnail_file(thumb_name)
    else:
        try:
            video_path = _resolve_video_file(filename)
        except HTTPException:
            raise _thumbnail_not_found() from None
        if _generate_video_thumbnail(video_path) is None:
            raise _thumbnail_not_found()
        try:
            thumb_path = _resolve_video_thumbnail_file(thumb_name)
        except HTTPException:
            raise _thumbnail_not_found() from None

    payload, mime_type, _prompt = _read_gallery_image_payload(thumb_path)
    return payload, mime_type


def _parse_byte_range_spec(range_spec: str) -> Optional[tuple[Optional[int], Optional[int]]]:
    match = re.fullmatch(r"(\d*)-(\d*)", str(range_spec or "").strip())
    if not match:
        return None

    start_text, end_text = match.groups()
    if not start_text and not end_text:
        return None
    if max(len(start_text), len(end_text)) > MAX_BYTE_RANGE_DIGITS:
        return None
    try:
        start_value = int(start_text) if start_text else None
        end_value = int(end_text) if end_text else None
    except (ValueError, OverflowError):
        return None
    if start_value is not None and end_value is not None and end_value < start_value:
        return None
    return start_value, end_value


def _resolve_byte_range_spec(range_spec: str, total: int) -> Optional[tuple[int, int]]:
    parsed = _parse_byte_range_spec(range_spec)
    if parsed is None or total <= 0:
        return None

    start_value, end_value = parsed
    if start_value is not None:
        start = start_value
        if start >= total:
            return None
        if end_value is not None:
            end = end_value
            end = min(end, total - 1)
        else:
            end = total - 1
        return start, end

    if end_value is None:
        return None
    suffix_length = end_value
    if suffix_length <= 0:
        return None
    return max(total - suffix_length, 0), total - 1


def _parse_single_byte_range(range_header: str, total: int) -> Optional[tuple[int, int]]:
    normalized = str(range_header or "").strip()
    unit, separator, range_spec = normalized.partition("=")
    if separator != "=" or unit.lower() != "bytes":
        return None
    return _resolve_byte_range_spec(range_spec, total)


def _is_valid_multiple_byte_range(range_header: str, total: int) -> bool:
    normalized = str(range_header or "").strip()
    unit, separator, range_set = normalized.partition("=")
    if separator != "=" or unit.lower() != "bytes":
        return False

    parts = range_set.split(",")
    if len(parts) < 2:
        return False
    normalized_parts = [part.strip() for part in parts]
    if any(not part or _parse_byte_range_spec(part) is None for part in normalized_parts):
        return False
    return any(_resolve_byte_range_spec(part, total) is not None for part in normalized_parts)


def _memory_media_response(request: Request, payload: bytes, media_type: str) -> Response:
    total = len(payload)
    headers = {"Accept-Ranges": "bytes"}
    range_header = request.headers.get("range") if request.method.upper() == "GET" else None
    ignore_multiple_ranges = _is_valid_multiple_byte_range(range_header, total)
    if range_header is None or ignore_multiple_ranges:
        headers["Content-Length"] = str(total)
        return Response(
            content=b"" if request.method.upper() == "HEAD" else payload,
            media_type=media_type,
            headers=headers,
        )

    byte_range = _parse_single_byte_range(range_header, total)
    if byte_range is None:
        headers.update({
            "Content-Range": f"bytes */{total}",
            "Content-Length": "0",
        })
        return Response(
            content=b"",
            status_code=416,
            media_type=media_type,
            headers=headers,
        )

    start, end = byte_range
    partial = payload[start : end + 1]
    headers.update({
        "Content-Range": f"bytes {start}-{end}/{total}",
        "Content-Length": str(len(partial)),
    })
    return Response(
        content=partial,
        status_code=206,
        media_type=media_type,
        headers=headers,
    )


def _generation_contract_error(code: str, message: str, *, status_code: int = 422, **extra) -> HTTPException:
    """Return a stable, secret-free error payload for generation input violations."""
    detail = {"code": code, "message": message}
    detail.update(extra)
    return HTTPException(status_code=status_code, detail=detail)


def _has_generation_value(value: object) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _normalize_generation_mime_type(value: str) -> str:
    mime_type = str(value or "").strip().lower()
    return "image/jpeg" if mime_type == "image/jpg" else mime_type


def _validate_generation_image_data(
    value: object,
    field_name: str,
    *,
    required_mime_type: Optional[str] = None,
) -> dict:
    """Decode and inspect one browser image payload before a task is created."""
    if not isinstance(value, str) or not value.strip():
        raise _generation_contract_error(
            "image_data_required",
            f"{field_name} must contain a base64 image payload",
            field=field_name,
        )

    original_value = value.strip()
    encoded = original_value
    declared_mime_type = ""
    if original_value.lower().startswith("data:"):
        header, separator, encoded = original_value.partition(",")
        if not separator:
            raise _generation_contract_error(
                "invalid_image_data_url",
                f"{field_name} must be a base64 data URL",
                field=field_name,
            )
        match = re.fullmatch(
            r"data:([A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+);base64",
            header,
            flags=re.IGNORECASE,
        )
        if not match:
            raise _generation_contract_error(
                "invalid_image_data_url",
                f"{field_name} must be a base64 data URL",
                field=field_name,
            )
        declared_mime_type = _normalize_generation_mime_type(match.group(1))
        if declared_mime_type not in GENERATION_ALLOWED_IMAGE_MIME_TYPES:
            raise _generation_contract_error(
                "unsupported_image_mime",
                f"{field_name} uses an unsupported image MIME type",
                field=field_name,
            )

    max_encoded_length = ((MAX_GENERATION_INPUT_BYTES + 2) // 3) * 4
    if len(encoded) > max_encoded_length:
        raise _generation_contract_error(
            "image_too_large",
            f"{field_name} exceeds the configured byte limit",
            field=field_name,
            max_bytes=MAX_GENERATION_INPUT_BYTES,
        )
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError, TypeError):
        raise _generation_contract_error(
            "invalid_image_base64",
            f"{field_name} is not valid base64",
            field=field_name,
        ) from None
    if not payload:
        raise _generation_contract_error(
            "invalid_image_base64",
            f"{field_name} decoded to an empty image",
            field=field_name,
        )
    if len(payload) > MAX_GENERATION_INPUT_BYTES:
        raise _generation_contract_error(
            "image_too_large",
            f"{field_name} exceeds the configured byte limit",
            field=field_name,
            max_bytes=MAX_GENERATION_INPUT_BYTES,
        )

    try:
        # Pillow warning filters are process-global. Serialize the warning
        # promotion so concurrent browser inputs cannot bypass the bomb guard.
        with _GENERATION_IMAGE_VALIDATION_LOCK:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(payload)) as image:
                    width, height = image.size
                    image_format = str(image.format or "").upper()
                    if width <= 0 or height <= 0 or width * height > MAX_GENERATION_INPUT_PIXELS:
                        raise _generation_contract_error(
                            "image_pixels_exceeded",
                            f"{field_name} exceeds the configured pixel limit",
                            field=field_name,
                            max_pixels=MAX_GENERATION_INPUT_PIXELS,
                        )
                    image.verify()
                with Image.open(io.BytesIO(payload)) as image:
                    image.load()
    except HTTPException:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise _generation_contract_error(
            "image_decompression_bomb",
            f"{field_name} was rejected by the decompression-bomb guard",
            field=field_name,
        ) from None
    except Exception:
        raise _generation_contract_error(
            "invalid_image_payload",
            f"{field_name} is not a readable image",
            field=field_name,
        ) from None

    actual_mime_type = _GENERATION_IMAGE_FORMAT_MIME_TYPES.get(image_format, "")
    if actual_mime_type not in GENERATION_ALLOWED_IMAGE_MIME_TYPES:
        raise _generation_contract_error(
            "unsupported_image_mime",
            f"{field_name} uses an unsupported image MIME type",
            field=field_name,
        )
    if declared_mime_type and declared_mime_type != actual_mime_type:
        raise _generation_contract_error(
            "image_mime_mismatch",
            f"{field_name} MIME type does not match its image payload",
            field=field_name,
        )
    if required_mime_type and actual_mime_type != required_mime_type:
        raise _generation_contract_error(
            "unsupported_image_mime",
            f"{field_name} must use {required_mime_type}",
            field=field_name,
        )
    return {
        "value": original_value,
        "mime_type": actual_mime_type,
        "width": width,
        "height": height,
    }


def _precision_annotation_string_is_safe(value: str) -> bool:
    """Reject annotation text that could be interpreted as executable content or a resource."""
    if not value.isprintable():
        return False
    if re.search(r"(?i)(?:https?|ftp|file|data|javascript):|www\.", value):
        return False
    if "<" in value or ">" in value:
        return False
    return not re.search(
        r"(?:^|\s)(?:[A-Za-z]:[\\/]|\\\\|\.\.[\\/]|/(?:[\w.-]+/)+[\w.-]+)",
        value,
    )


def _precision_coordinate(annotation: dict, field_name: str, index: int) -> float:
    value = annotation.get(field_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _generation_contract_error(
            "precision_annotation_coordinate_invalid",
            f"annotations[{index}].{field_name} must be a normalized number",
            field=f"annotations[{index}].{field_name}",
        )
    normalized = float(value)
    if not math.isfinite(normalized) or normalized < 0.0 or normalized > 1.0:
        raise _generation_contract_error(
            "precision_annotation_coordinate_invalid",
            f"annotations[{index}].{field_name} must be between 0 and 1",
            field=f"annotations[{index}].{field_name}",
        )
    return normalized


def _validate_precision_annotations(value: object, contract: str) -> List[dict]:
    if not isinstance(value, list) or not value:
        raise _generation_contract_error(
            "precision_annotations_required",
            "precision_edit requires at least one structured annotation",
            field="annotations",
        )
    if len(value) > MAX_PRECISION_ANNOTATIONS:
        raise _generation_contract_error(
            "precision_annotations_exceeded",
            "precision_edit contains too many annotations",
            field="annotations",
            max_annotations=MAX_PRECISION_ANNOTATIONS,
        )

    is_v2 = contract == PRECISION_ANNOTATION_CONTRACT_V2
    is_v3 = contract == PRECISION_ANNOTATION_CONTRACT_V3
    is_structured = is_v2 or is_v3
    if contract == PRECISION_ANNOTATION_CONTRACT_V1:
        allowed_fields = {
            "arrow": frozenset({"type", "x1", "y1", "x2", "y2"}),
            "rectangle": frozenset({"type", "x", "y", "width", "height"}),
            "text": frozenset({"type", "x", "y", "text"}),
        }
    elif is_v2:
        allowed_fields = {
            "arrow": frozenset({"type", "label", "instruction", "x1", "y1", "x2", "y2"}),
            "rectangle": frozenset({"type", "label", "instruction", "x", "y", "width", "height"}),
            "text": frozenset({"type", "label", "text", "instruction", "x", "y"}),
        }
    elif is_v3:
        allowed_fields = {
            "arrow": frozenset({"type", "label", "instruction", "x1", "y1", "x2", "y2"}),
            "rectangle": frozenset({"type", "label", "instruction", "x", "y", "width", "height"}),
            "ellipse": frozenset({"type", "label", "instruction", "x", "y", "width", "height"}),
            "brush": frozenset({"type", "label", "instruction", "points"}),
            "text": frozenset({"type", "label", "text", "instruction", "x", "y"}),
        }
    else:
        raise _generation_contract_error(
            "precision_annotation_contract_unsupported",
            "precision_edit annotation contract is unsupported",
            mode="precision_edit",
        )
    coordinate_fields = {
        "arrow": ("x1", "y1", "x2", "y2"),
        "rectangle": ("x", "y", "width", "height"),
        "ellipse": ("x", "y", "width", "height"),
        "brush": (),
        "text": ("x", "y"),
    }
    normalized_annotations: List[dict] = []
    total_text_length = 0
    seen_labels: set[int] = set()
    total_brush_points = 0

    for index, raw_annotation in enumerate(value):
        if not isinstance(raw_annotation, dict):
            raise _generation_contract_error(
                "precision_annotation_invalid",
                f"annotations[{index}] must be an object",
                field=f"annotations[{index}]",
            )
        annotation_type = raw_annotation.get("type")
        if annotation_type not in allowed_fields:
            raise _generation_contract_error(
                "precision_annotation_type_unsupported",
                f"annotations[{index}].type is unsupported for {contract}",
                field=f"annotations[{index}].type",
            )
        actual_fields = set(raw_annotation)
        permitted_fields = allowed_fields[annotation_type]
        if is_structured and annotation_type == "text":
            required_fields = permitted_fields - {"instruction"}
        else:
            required_fields = permitted_fields
        unknown_fields = sorted(actual_fields - permitted_fields)
        missing_fields = sorted(required_fields - actual_fields)
        if unknown_fields or missing_fields:
            raise _generation_contract_error(
                "precision_annotation_fields_unsupported",
                f"annotations[{index}] contains missing or unsupported fields",
                field=f"annotations[{index}]",
                unsupported_fields=unknown_fields,
                missing_fields=missing_fields,
            )

        normalized = {"type": annotation_type}
        if is_structured:
            label = raw_annotation.get("label")
            if isinstance(label, bool) or not isinstance(label, int) or label <= 0:
                raise _generation_contract_error(
                    "precision_annotation_label_invalid",
                    f"annotations[{index}].label must be a positive integer",
                    field=f"annotations[{index}].label",
                )
            if label in seen_labels:
                raise _generation_contract_error(
                    "precision_annotation_label_duplicate",
                    f"annotations[{index}].label must be unique",
                    field=f"annotations[{index}].label",
                )
            seen_labels.add(label)
            normalized["label"] = label
        for field_name in coordinate_fields[annotation_type]:
            normalized[field_name] = _precision_coordinate(raw_annotation, field_name, index)

        if annotation_type == "arrow":
            if normalized["x1"] == normalized["x2"] and normalized["y1"] == normalized["y2"]:
                raise _generation_contract_error(
                    "precision_annotation_geometry_invalid",
                    f"annotations[{index}] arrow must have distinct endpoints",
                    field=f"annotations[{index}]",
                )
        elif annotation_type in {"rectangle", "ellipse"}:
            if normalized["width"] <= 0.0 or normalized["height"] <= 0.0:
                raise _generation_contract_error(
                    "precision_annotation_geometry_invalid",
                    f"annotations[{index}] {annotation_type} must have positive width and height",
                    field=f"annotations[{index}]",
                )
            if normalized["x"] + normalized["width"] > 1.0 or normalized["y"] + normalized["height"] > 1.0:
                raise _generation_contract_error(
                    "precision_annotation_geometry_invalid",
                    f"annotations[{index}] {annotation_type} must stay within the normalized canvas",
                    field=f"annotations[{index}]",
                )
        elif annotation_type == "brush":
            points = raw_annotation.get("points")
            if not isinstance(points, list) or len(points) < 2 or len(points) > MAX_PRECISION_BRUSH_POINTS:
                raise _generation_contract_error(
                    "precision_annotation_geometry_invalid",
                    f"annotations[{index}].points must contain 2 to {MAX_PRECISION_BRUSH_POINTS} points",
                    field=f"annotations[{index}].points",
                )
            normalized_points = []
            for point_index, point in enumerate(points):
                if not isinstance(point, dict) or set(point) != {"x", "y"}:
                    raise _generation_contract_error(
                        "precision_annotation_geometry_invalid",
                        f"annotations[{index}].points[{point_index}] must contain only x and y",
                        field=f"annotations[{index}].points[{point_index}]",
                    )
                normalized_points.append({
                    "x": _precision_coordinate(point, "x", index),
                    "y": _precision_coordinate(point, "y", index),
                })
            if all(point == normalized_points[0] for point in normalized_points[1:]):
                raise _generation_contract_error(
                    "precision_annotation_geometry_invalid",
                    f"annotations[{index}].points must describe a non-empty path",
                    field=f"annotations[{index}].points",
                )
            total_brush_points += len(normalized_points)
            if total_brush_points > MAX_PRECISION_BRUSH_POINTS_TOTAL:
                raise _generation_contract_error(
                    "precision_annotation_geometry_exceeded",
                    "precision_edit brush paths exceed the total point limit",
                    field="annotations",
                    max_total_points=MAX_PRECISION_BRUSH_POINTS_TOTAL,
                )
            normalized["points"] = normalized_points
        if annotation_type == "text":
            text = raw_annotation.get("text")
            if not isinstance(text, str) or not text.strip():
                raise _generation_contract_error(
                    "precision_annotation_text_required",
                    f"annotations[{index}].text must contain annotation text",
                    field=f"annotations[{index}].text",
                )
            text = text.strip()
            if len(text) > MAX_PRECISION_ANNOTATION_TEXT:
                raise _generation_contract_error(
                    "precision_annotation_text_exceeded",
                    f"annotations[{index}].text is too long",
                    field=f"annotations[{index}].text",
                    max_length=MAX_PRECISION_ANNOTATION_TEXT,
                )
            if not _precision_annotation_string_is_safe(text):
                raise _generation_contract_error(
                    "precision_annotation_text_unsafe",
                    f"annotations[{index}].text cannot contain URLs, HTML, or filesystem paths",
                    field=f"annotations[{index}].text",
                )
            total_text_length += len(text)
            if total_text_length > MAX_PRECISION_ANNOTATION_TEXT_TOTAL:
                raise _generation_contract_error(
                    "precision_annotation_text_exceeded",
                    "precision_edit annotation text exceeds the total length limit",
                    field="annotations",
                    max_total_length=MAX_PRECISION_ANNOTATION_TEXT_TOTAL,
                )
            normalized["text"] = text
        if is_structured:
            instruction = raw_annotation.get("instruction")
            instruction_required = annotation_type in {"arrow", "rectangle", "ellipse", "brush"}
            if instruction_required and (not isinstance(instruction, str) or not instruction.strip()):
                raise _generation_contract_error(
                    "precision_annotation_instruction_required",
                    f"annotations[{index}].instruction must contain an edit instruction",
                    field=f"annotations[{index}].instruction",
                )
            if instruction is not None:
                if not isinstance(instruction, str) or not instruction.strip():
                    raise _generation_contract_error(
                        "precision_annotation_instruction_required",
                        f"annotations[{index}].instruction must be omitted or non-empty",
                        field=f"annotations[{index}].instruction",
                    )
                instruction = instruction.strip()
                if len(instruction) > MAX_PRECISION_ANNOTATION_TEXT:
                    raise _generation_contract_error(
                        "precision_annotation_instruction_exceeded",
                        f"annotations[{index}].instruction is too long",
                        field=f"annotations[{index}].instruction",
                        max_length=MAX_PRECISION_ANNOTATION_TEXT,
                    )
                if not _precision_annotation_string_is_safe(instruction):
                    raise _generation_contract_error(
                        "precision_annotation_instruction_unsafe",
                        f"annotations[{index}].instruction contains unsafe characters or resource references",
                        field=f"annotations[{index}].instruction",
                    )
                total_text_length += len(instruction)
                if total_text_length > MAX_PRECISION_ANNOTATION_TEXT_TOTAL:
                    raise _generation_contract_error(
                        "precision_annotation_text_exceeded",
                        "precision_edit annotation text exceeds the total length limit",
                        field="annotations",
                        max_total_length=MAX_PRECISION_ANNOTATION_TEXT_TOTAL,
                    )
                normalized["instruction"] = instruction
        normalized_annotations.append(normalized)
    if is_structured:
        normalized_annotations.sort(key=lambda item: item["label"])
    return normalized_annotations


def _validate_generation_request_inputs(req: GenerateRequest) -> dict:
    """Enforce the generation input matrix before allocating a task ID."""
    mode = req.mode if isinstance(req.mode, str) else ""
    if mode not in GENERATION_MODES:
        raise _generation_contract_error(
            "invalid_mode",
            "mode must be one of: t2i, i2i, inpaint, precision_edit",
            field="mode",
        )

    precision_strategy_supplied = "precision_strategy" in req.model_fields_set
    precision_selection_mode_supplied = "precision_selection_mode" in req.model_fields_set
    precision_selection_feather_supplied = "precision_selection_feather" in req.model_fields_set
    output_size_policy_supplied = "precision_output_size_policy" in req.model_fields_set
    if mode != "precision_edit" and output_size_policy_supplied and not any((
        precision_strategy_supplied,
        precision_selection_mode_supplied,
        precision_selection_feather_supplied,
    )):
        raise _generation_contract_error(
            "precision_output_size_policy_not_allowed",
            "precision_output_size_policy is accepted only for precision_edit resize",
            field="precision_output_size_policy",
        )
    if mode != "precision_edit" and any((
        precision_strategy_supplied,
        precision_selection_mode_supplied,
        precision_selection_feather_supplied,
    )):
        raise _generation_contract_error(
            "precision_fields_not_allowed",
            "precision strategy and selection fields are accepted only for precision_edit",
            mode=mode,
        )

    has_image_list = bool(req.image_data_list)
    has_mask_fields = _has_generation_value(req.mask_data) or _has_generation_value(req.mask_contract)
    has_annotation_fields = (
        _has_generation_value(req.annotation_image_data)
        or _has_generation_value(req.annotation_contract)
        or bool(req.annotations)
    )
    if mode == "t2i":
        if _has_generation_value(req.image_data) or has_image_list:
            raise _generation_contract_error(
                "image_input_not_allowed",
                "t2i does not accept image_data or image_data_list",
                mode=mode,
            )
        if has_mask_fields:
            raise _generation_contract_error(
                "mask_input_not_allowed",
                "t2i does not accept mask data",
                mode=mode,
            )
        if has_annotation_fields:
            raise _generation_contract_error(
                "annotation_input_not_allowed",
                "t2i does not accept precision annotation data",
                mode=mode,
            )
        return {"mode": mode, "images": []}

    if mode == "i2i":
        if has_mask_fields:
            raise _generation_contract_error(
                "mask_input_not_allowed",
                "i2i does not accept mask data",
                mode=mode,
            )
        if has_annotation_fields:
            raise _generation_contract_error(
                "annotation_input_not_allowed",
                "i2i does not accept precision annotation data",
                mode=mode,
            )
        legacy_image = (
            _validate_generation_image_data(req.image_data, "image_data")
            if _has_generation_value(req.image_data)
            else None
        )
        images = [
            _validate_generation_image_data(item, f"image_data_list[{index}]")
            for index, item in enumerate(req.image_data_list or [])
        ]
        if legacy_image and images and legacy_image["value"] != images[0]["value"]:
            raise _generation_contract_error(
                "i2i_base_image_conflict",
                "image_data must match the first image_data_list item when both are supplied",
                mode=mode,
            )
        if not images and legacy_image:
            images = [legacy_image]
        if not images:
            raise _generation_contract_error(
                "i2i_image_required",
                "i2i requires at least one reference image",
                mode=mode,
            )
        return {"mode": mode, "images": images}

    if mode == "precision_edit":
        if "image_data_list" in req.model_fields_set:
            raise _generation_contract_error(
                "precision_edit_image_data_list_not_allowed",
                "precision_edit accepts exactly one base image through image_data",
                mode=mode,
            )
        if has_mask_fields:
            raise _generation_contract_error(
                "mask_input_not_allowed",
                "precision_edit does not accept inpaint mask data",
                mode=mode,
            )
        precision_prompt = req.prompt.strip()
        if len(precision_prompt) > MAX_PRECISION_PROMPT_TEXT:
            raise _generation_contract_error(
                "precision_edit_prompt_exceeded",
                "precision_edit prompt is too long",
                field="prompt",
                max_length=MAX_PRECISION_PROMPT_TEXT,
            )
        if precision_prompt and not _precision_annotation_string_is_safe(precision_prompt):
            raise _generation_contract_error(
                "precision_edit_prompt_unsafe",
                "precision_edit prompt cannot contain URLs, HTML, or filesystem paths",
                field="prompt",
            )
        precision_strategy = str(req.precision_strategy or "standard").strip().lower()
        if precision_strategy not in PRECISION_STRATEGIES:
            raise _generation_contract_error(
                "precision_strategy_invalid",
                "precision_strategy must be fine, standard, or fast",
                field="precision_strategy",
                allowed_strategies=sorted(PRECISION_STRATEGIES),
            )
        precision_selection_mode = str(req.precision_selection_mode or "annotation").strip().lower()
        if precision_selection_mode not in PRECISION_SELECTION_MODES:
            raise _generation_contract_error(
                "precision_selection_mode_invalid",
                "precision_selection_mode must be annotation or local",
                field="precision_selection_mode",
                allowed_modes=sorted(PRECISION_SELECTION_MODES),
            )
        if isinstance(req.precision_selection_feather, bool) or not math.isfinite(float(req.precision_selection_feather)):
            raise _generation_contract_error(
                "precision_selection_feather_invalid",
                "precision_selection_feather must be a finite number between 0 and 64",
                field="precision_selection_feather",
            )
        precision_selection_feather = float(req.precision_selection_feather)
        if not 0 <= precision_selection_feather <= MAX_PRECISION_SELECTION_FEATHER:
            raise _generation_contract_error(
                "precision_selection_feather_invalid",
                "precision_selection_feather must be between 0 and 64",
                field="precision_selection_feather",
                max_feather=MAX_PRECISION_SELECTION_FEATHER,
            )
        if precision_selection_mode != "local" and precision_selection_feather_supplied:
            raise _generation_contract_error(
                "precision_selection_feather_not_allowed",
                "precision_selection_feather is accepted only for local selection mode",
                field="precision_selection_feather",
            )
        size_mode = str(req.precision_size_mode or "preserve").strip().lower()
        if size_mode not in {"preserve", "resize"}:
            raise _generation_contract_error(
                "precision_size_mode_invalid",
                "precision_size_mode must be preserve or resize",
                field="precision_size_mode",
            )
        output_size_policy = str(req.precision_output_size_policy or "")
        if output_size_policy not in {"strict", "fit_crop"}:
            raise _generation_contract_error(
                "precision_output_size_policy_invalid",
                "precision_output_size_policy must be strict or fit_crop",
                field="precision_output_size_policy",
                allowed_policies=["strict", "fit_crop"],
            )
        if size_mode != "resize" and output_size_policy_supplied:
            raise _generation_contract_error(
                "precision_output_size_policy_not_allowed",
                "precision_output_size_policy is accepted only for precision_edit resize",
                field="precision_output_size_policy",
            )
        annotation_field_names = {
            "annotation_image_data",
            "annotation_contract",
            "annotations",
        }
        supplied_annotation_fields = annotation_field_names.intersection(req.model_fields_set)
        precision_canvas_only = not supplied_annotation_fields
        if supplied_annotation_fields and supplied_annotation_fields != annotation_field_names:
            raise _generation_contract_error(
                "precision_resize_annotation_fields_conflict",
                "precision annotation fields must be supplied as one complete annotated-edit envelope",
                field="annotations",
            )
        if precision_canvas_only and size_mode != "resize":
            raise _generation_contract_error(
                "precision_canvas_only_resize_required",
                "precision_edit without annotations requires precision_size_mode=resize",
                field="precision_size_mode",
            )
        if precision_canvas_only and precision_selection_mode == "local":
            raise _generation_contract_error(
                "precision_local_selection_requires_annotations",
                "local selection mode requires rectangle, ellipse, or brush annotations",
                field="precision_selection_mode",
            )
        resize_prompt = str(req.precision_resize_prompt or "").strip()
        if req.upscale_to is not None or req.upscale_ratio != "original":
            raise _generation_contract_error(
                "precision_upscale_not_allowed",
                "precision_edit does not accept generic post-generation upscaling",
                field="upscale_to",
            )
        if len(resize_prompt) > MAX_PRECISION_RESIZE_PROMPT_TEXT:
            raise _generation_contract_error(
                "precision_resize_prompt_exceeded",
                "precision_resize_prompt is too long",
                field="precision_resize_prompt",
                max_length=MAX_PRECISION_RESIZE_PROMPT_TEXT,
            )
        if resize_prompt and not _precision_annotation_string_is_safe(resize_prompt):
            raise _generation_contract_error(
                "precision_resize_prompt_unsafe",
                "precision_resize_prompt cannot contain URLs, HTML, or filesystem paths",
                field="precision_resize_prompt",
            )
        target_size = str(req.precision_target_size or "")
        if size_mode == "preserve":
            generic_size = str(req.size or "").strip().lower()
            if generic_size not in {"", "auto"} or target_size or resize_prompt:
                raise _generation_contract_error(
                    "precision_preserve_size_conflict",
                    "preserve mode does not accept generation or resize dimensions",
                    field="precision_size_mode",
                )
        else:
            normalized_target_size = _normalize_precision_size(target_size)
            if not normalized_target_size:
                raise _generation_contract_error(
                    "precision_target_size_invalid",
                    "resize mode requires precision_target_size as WIDTHxHEIGHT",
                    field="precision_target_size",
                )
            target_size = normalized_target_size
            resize_prompt = resize_prompt or DEFAULT_PRECISION_RESIZE_GUIDANCE
        base_image = _validate_generation_image_data(req.image_data, "image_data")
        if precision_canvas_only:
            return {
                "mode": mode,
                "images": [base_image],
                "precision_canvas_only": True,
                "precision_strategy": precision_strategy,
                "precision_selection_mode": precision_selection_mode,
                "precision_size_mode": size_mode,
                "precision_target_size": target_size,
                "precision_resize_prompt": resize_prompt,
                "precision_output_size_policy": output_size_policy,
            }
        annotation_contract = str(req.annotation_contract or "").strip()
        if annotation_contract not in PRECISION_ANNOTATION_CONTRACTS:
            raise _generation_contract_error(
                "precision_annotation_contract_unsupported",
                "precision_edit requires a supported annotation_contract",
                mode=mode,
                supported_contracts=sorted(PRECISION_ANNOTATION_CONTRACTS),
            )
        annotation_image = _validate_generation_image_data(
            req.annotation_image_data,
            "annotation_image_data",
            required_mime_type="image/png",
        )
        if (base_image["width"], base_image["height"]) != (
            annotation_image["width"],
            annotation_image["height"],
        ):
            raise _generation_contract_error(
                "precision_annotation_image_size_mismatch",
                "image_data and annotation_image_data dimensions must match",
                mode=mode,
            )
        annotations = _validate_precision_annotations(req.annotations, annotation_contract)
        if precision_selection_mode == "local" and not any(
            item["type"] in PRECISION_SELECTION_TYPES for item in annotations
        ):
            raise _generation_contract_error(
                "precision_local_selection_required",
                "local selection mode requires at least one rectangle, ellipse, or brush annotation",
                field="annotations",
            )
        if annotation_contract == PRECISION_ANNOTATION_CONTRACT_V2:
            annotations.sort(key=lambda item: item["label"])
        return {
            "mode": mode,
            "images": [base_image],
            "annotation_image": annotation_image,
            "annotation_contract": annotation_contract,
            "annotations": annotations,
            "precision_canvas_only": False,
            "precision_strategy": precision_strategy,
            "precision_selection_mode": precision_selection_mode,
            "precision_selection_feather": precision_selection_feather,
            "precision_size_mode": size_mode,
            "precision_target_size": target_size or None,
            "precision_resize_prompt": resize_prompt or None,
            **(
                {"precision_output_size_policy": output_size_policy}
                if size_mode == "resize"
                else {}
            ),
        }

    if has_annotation_fields:
        raise _generation_contract_error(
            "annotation_input_not_allowed",
            "inpaint does not accept precision annotation data",
            mode=mode,
        )
    if has_image_list:
        raise _generation_contract_error(
            "inpaint_image_data_list_not_allowed",
            "inpaint accepts exactly one base image through image_data",
            mode=mode,
        )
    base_image = _validate_generation_image_data(req.image_data, "image_data")
    if not _has_generation_value(req.mask_data):
        raise _generation_contract_error(
            "inpaint_mask_required",
            "inpaint requires mask_data",
            mode=mode,
        )
    if req.mask_contract != INPAINT_MASK_CONTRACT:
        raise _generation_contract_error(
            "inpaint_mask_contract_unsupported",
            f"inpaint requires mask_contract={INPAINT_MASK_CONTRACT}",
            mode=mode,
        )
    mask_image = _validate_generation_image_data(
        req.mask_data,
        "mask_data",
        required_mime_type="image/png",
    )
    if (base_image["width"], base_image["height"]) != (mask_image["width"], mask_image["height"]):
        raise _generation_contract_error(
            "inpaint_image_mask_size_mismatch",
            "image_data and mask_data dimensions must match",
            mode=mode,
        )
    return {"mode": mode, "images": [base_image], "mask": mask_image}


def _validate_inpaint_provider_authorization(provider_ids: List[str], all_providers: dict) -> None:
    """Allow inpaint only for a deliberately configured OpenAI mask adapter."""
    unsupported = []
    for provider_id in provider_ids:
        provider = all_providers.get(provider_id)
        if provider is None:
            unsupported.append({"id": provider_id, "reason": "provider_not_found"})
            continue
        if getattr(provider, "type", "") != "image" or not getattr(provider, "enabled", False):
            unsupported.append({"id": provider_id, "reason": "provider_not_enabled"})
            continue
        endpoint_type = str(getattr(provider, "endpoint_type", "auto") or "auto").strip().lower()
        if endpoint_type != "openai":
            unsupported.append({"id": provider_id, "reason": "explicit_openai_required"})
            continue
        capabilities = getattr(provider, "capabilities", None)
        if not isinstance(capabilities, dict) or capabilities.get("inpaint_mask") is not True:
            unsupported.append({"id": provider_id, "reason": "inpaint_mask_capability_required"})
    if unsupported:
        raise _generation_contract_error(
            "inpaint_provider_unsupported",
            "inpaint requires an enabled image provider with endpoint_type=openai and capabilities.inpaint_mask=true",
            providers=unsupported,
        )


def _provider_precision_model_capability(provider, selected_model: str) -> bool:
    capabilities = getattr(provider, "capabilities", None)
    if not isinstance(capabilities, dict) or capabilities.get(PRECISION_EDIT_CAPABILITY) is not True:
        return False
    resolution = _provider_precision_model_resolution(provider, selected_model)
    return resolution.structure_valid and resolution.precision_edit_confirmed


def _provider_precision_model_resolution(provider, selected_model: str):
    return resolve_provider_precision_model_capability(
        provider,
        selected_model,
    )


def _normalize_precision_size(value: object) -> Optional[str]:
    return normalize_precision_capability_size(
        value,
        max_output_pixels=MAX_PRECISION_OUTPUT_PIXELS,
    )


def _precision_declared_sizes(model_capabilities: object) -> set[str]:
    """Return only valid, explicitly declared WIDTHxHEIGHT dimensions."""
    _present, valid, sizes, _reason = precision_capability_size_declaration(
        model_capabilities,
        max_output_pixels=MAX_PRECISION_OUTPUT_PIXELS,
    )
    return set(sizes) if valid else set()


def _precision_declared_size_list(model_capabilities: object) -> List[str]:
    """Return valid declared sizes in stable first-seen order."""
    _present, valid, sizes, _reason = precision_capability_size_declaration(
        model_capabilities,
        max_output_pixels=MAX_PRECISION_OUTPUT_PIXELS,
    )
    return list(sizes) if valid else []


def _precision_model_declared_sizes(provider, selected_model: str) -> set[str]:
    resolution = _provider_precision_model_resolution(provider, selected_model)
    if not resolution.structure_valid or not resolution.size_declaration_valid:
        return set()
    return set(resolution.supported_sizes)


def _precision_model_allows_flexible_sizes(provider, selected_model: str) -> bool:
    """Allow the GPT Image 2 envelope only after an explicit persisted opt-in."""
    resolution = _provider_precision_model_resolution(provider, selected_model)
    return bool(
        resolution.structure_valid
        and resolution.precision_edit_confirmed
        and resolution.size_declaration_valid
        and resolution.flexible_sizes
    )


def _validate_precision_edit_size_authorization(
    provider_ids: List[str],
    all_providers: dict,
    provider_settings: dict,
    generation_input: dict,
) -> None:
    if generation_input.get("precision_size_mode") != "resize":
        return
    target = generation_input.get("precision_target_size")
    output_size_policy = str(
        generation_input.get("precision_output_size_policy") or "strict"
    )
    settings = provider_settings if isinstance(provider_settings, dict) else {}
    unsupported = []
    for provider_id in provider_ids:
        provider = all_providers.get(provider_id)
        setting = settings.get(provider_id) if isinstance(settings.get(provider_id), dict) else {}
        model = str(setting.get("model") or "").strip()
        flexible_sizes = _precision_model_allows_flexible_sizes(provider, model) if provider else False
        protocol_model = bool(
            provider
            and precision_model_uses_gpt_image_2_size_contract(provider, model)
        ) or flexible_sizes
        if protocol_model:
            protocol_error = gpt_image_2_size_error(target)
            if protocol_error:
                unsupported.append({
                    "id": provider_id,
                    "model": model,
                    "reason": protocol_error[0],
                    "target_size": target,
                })
                continue
        sizes = _precision_model_declared_sizes(provider, model) if provider else set()
        if flexible_sizes:
            # The policy itself is an explicit operator confirmation that this
            # OpenAI-compatible model accepts the documented GPT Image 2
            # dimension envelope. The protocol validation above remains the
            # hard boundary; this is not an unrestricted arbitrary-size grant.
            continue
        if not sizes:
            unsupported.append({
                "id": provider_id,
                "model": model,
                "reason": "precision_edit_size_capability_unknown",
            })
        elif output_size_policy == "strict" and target not in sizes:
            unsupported.append({
                "id": provider_id,
                "model": model,
                "reason": "precision_edit_target_size_not_declared",
                "target_size": target,
            })
    if unsupported:
        raise _generation_contract_error(
            "precision_edit_size_unsupported",
            "resize requires the selected model to explicitly declare the requested size",
            providers=unsupported,
            target_size=target,
        )


def _validate_precision_edit_provider_authorization(
    provider_ids: List[str],
    all_providers: dict,
    provider_settings: dict,
) -> None:
    """Require an explicit model-level annotation-edit capability and transport."""
    unsupported = []
    settings = provider_settings if isinstance(provider_settings, dict) else {}
    for provider_id in provider_ids:
        provider = all_providers.get(provider_id)
        if provider is None:
            unsupported.append({"id": provider_id, "reason": "provider_not_found"})
            continue
        if getattr(provider, "type", "") != "image" or not getattr(provider, "enabled", False):
            unsupported.append({"id": provider_id, "reason": "provider_not_enabled"})
            continue
        endpoint_type = str(getattr(provider, "endpoint_type", "auto") or "auto").strip().lower()
        if endpoint_type != "openai":
            unsupported.append({"id": provider_id, "reason": "explicit_openai_required"})
            continue
        provider_setting = settings.get(provider_id, {})
        if not isinstance(provider_setting, dict):
            provider_setting = {}
        selected_model = str(provider_setting.get("model") or "").strip()
        if not selected_model:
            unsupported.append({
                "id": provider_id,
                "model": "",
                "reason": "precision_edit_explicit_model_required",
            })
            continue
        if not _provider_precision_model_capability(provider, selected_model):
            unsupported.append({
                "id": provider_id,
                "model": selected_model,
                "reason": "precision_edit_model_capability_required",
            })
    if unsupported:
        raise _generation_contract_error(
            "precision_edit_provider_unsupported",
            "precision_edit requires an explicitly verified OpenAI image-edit model",
            providers=unsupported,
        )


def _normalize_generation_quantity(value: object) -> int:
    """Keep a malformed or stale quantity from silently multiplying work."""
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return 1
    return max(1, min(10, quantity))


class GenerateResponse(BaseModel):
    generation_id: str
    results: dict
    enhanced_prompt: Optional[str] = None
    elapsed_seconds: Optional[float] = None  # 本次生图总耗时（秒）


class GalleryItem(BaseModel):
    id: str
    model: str
    prompt: str
    local_path: str
    created_at: str
    thumbnail: str


class EndpointReq(BaseModel):
    """端点请求体"""
    url: str = ""
    key: str = ""
    enabled: bool = True
    name: str = ""


class ProviderCreateReq(BaseModel):
    """创建/更新 Provider 的请求体"""
    id: str
    name: str
    type: str                          # "image" | "llm" | "video"
    api_key: str = ""
    api_keys: List[str] = []           # 多账号轮询
    base_url: str = ""
    endpoints: List[EndpointReq] = []  # 多端点
    model: str = ""
    models: List[str] = []
    size: str = ""
    quality: str = ""
    enabled: bool = True
    color: str = "#0ea5e9"
    display_name: str = ""
    capabilities: Dict[str, bool] = {}  # 能力声明: {"t2i": True, "i2i": True}
    precision_edit_profile: Optional[PrecisionEditProfile] = None
    skip_proxy: bool = False            # 跳过全局代理（直连）
    endpoint_type: str = "auto"         # 端点协议类型
    extra: dict = {}


class PrecisionCapabilityReq(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    enabled: bool
    confirmed: bool = False
    size: Optional[str] = None
    flexible_sizes: Optional[bool] = None
    compatibility_profile: Optional[str] = None


def _is_masked_secret(value: str) -> bool:
    """识别 API 响应中的脱敏占位符，避免把它当成真实凭证保存。"""
    return "****" in str(value or "")


def _merge_provider_secrets(existing: ProviderConfig, req: ProviderCreateReq) -> dict:
    """保留未在表单中重新输入的已存凭证。"""
    payload = req.model_dump()
    if not req.api_key or _is_masked_secret(req.api_key):
        payload["api_key"] = existing.api_key if not _is_masked_secret(existing.api_key) else ""
    if not req.api_keys or any(_is_masked_secret(key) for key in req.api_keys):
        payload["api_keys"] = [key for key in (existing.api_keys or []) if not _is_masked_secret(key)]

    incoming_endpoints = payload.get("endpoints") or []
    existing_endpoints = existing.endpoints or []
    if incoming_endpoints and existing_endpoints:
        for index, endpoint in enumerate(incoming_endpoints):
            if index >= len(existing_endpoints):
                break
            if not endpoint.key or _is_masked_secret(endpoint.key):
                endpoint.key = (
                    existing_endpoints[index].key
                    if not _is_masked_secret(existing_endpoints[index].key)
                    else ""
                )
    elif not incoming_endpoints:
        payload["endpoints"] = list(existing_endpoints)
    if "precision_edit_profile" not in req.model_fields_set:
        payload["precision_edit_profile"] = existing.precision_edit_profile
    incoming_extra = payload.get("extra")
    existing_extra = existing.extra if isinstance(existing.extra, dict) else {}
    if isinstance(incoming_extra, dict) and "model_capabilities" not in incoming_extra:
        existing_model_capabilities = existing_extra.get("model_capabilities")
        if isinstance(existing_model_capabilities, dict):
            incoming_extra = dict(incoming_extra)
            incoming_extra["model_capabilities"] = existing_model_capabilities
            payload["extra"] = incoming_extra
    return payload


# ──────────────────────────────────────────────────────────────
# FastAPI 实例
# ──────────────────────────────────────────────────────────────
app = FastAPI(title="GenBox", version=__version__)
app_start_time = time.time()
app_runtime_id = uuid.uuid4().hex[:12]
GENBOX_PORT = int(os.getenv("GENBOX_PORT", "8891"))
GENBOX_LOCAL_URL = f"http://localhost:{GENBOX_PORT}"
GENBOX_LOOPBACK_URL = f"http://127.0.0.1:{GENBOX_PORT}"

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", f"{GENBOX_LOCAL_URL},{GENBOX_LOOPBACK_URL}").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_response(_request: Request, exc: RequestValidationError):
    """Do not echo invalid request bodies, which may contain credentials."""
    return JSONResponse(
        status_code=422,
        content={
            "detail": [
                {"type": item.get("type", "validation_error"), "loc": item.get("loc", ()), "msg": item.get("msg", "输入无效")}
                for item in exc.errors()
            ]
        },
    )

# ──────────────────────────────────────────────────────────────
# 安全 Headers 中间件
# ──────────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Content Security Policy：限制脚本来源，防止 XSS
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    if is_prod_mode():
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def csrf_protection(request: Request, call_next):
    """CSRF 防护：校验 Origin/Referer 头"""
    if request.method in ("POST", "PUT", "DELETE"):
        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")
        source = origin or referer
        if source:
            source_authority = urlsplit(source).netloc.lower()
            request_authority = request.headers.get("host", "").lower()
            configured = set(ALLOWED_ORIGINS)
            configured.update({
                GENBOX_LOCAL_URL, GENBOX_LOOPBACK_URL,
                "http://localhost:8890", "http://127.0.0.1:8890",
            })
            allowed_authorities = {
                urlsplit(value.strip()).netloc.lower()
                for value in configured if urlsplit(value.strip()).netloc
            }
            if not source_authority or (
                source_authority != request_authority
                and source_authority not in allowed_authorities
            ):
                return JSONResponse(
                    status_code=403,
                    content={"error": "CSRF 验证失败", "code": "CSRF_REJECTED"},
                )
    return await call_next(request)

# ──────────────────────────────────────────────────────────────
# 速率限制（简单内存实现）
# ──────────────────────────────────────────────────────────────
from collections import defaultdict
_rate_limit_store: dict = defaultdict(list)
RATE_LIMIT_GENERATE = int(os.getenv("RATE_LIMIT_GENERATE", "10"))  # 每分钟最多10次生图
RATE_LIMIT_API = int(os.getenv("RATE_LIMIT_API", "60"))  # 每分钟最多60次API调用

def _check_rate_limit(client_ip: str, endpoint_type: str = "api") -> bool:
    """检查速率限制，返回 True 表示允许"""
    now = time.time()
    limit = RATE_LIMIT_GENERATE if endpoint_type == "generate" else RATE_LIMIT_API
    key = f"{client_ip}:{endpoint_type}"
    _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < 60]
    if len(_rate_limit_store[key]) >= limit:
        return False
    _rate_limit_store[key].append(now)
    return True

# ──────────────────────────────────────────────────────────────
# 内存存储
# ──────────────────────────────────────────────────────────────
generation_history: dict = {}
generation_counter = 0
HISTORY_FILE = STORAGE_DIR / "history.jsonl"
PRECISION_WORKFLOW_SCHEMA = "genbox-precision-workflow-v1"
PRECISION_WORKFLOW_ID_RE = re.compile(r"^pw_[a-f0-9]{32}$")
PRECISION_VERSION_ID_RE = re.compile(r"^pv_[a-f0-9]{24}$")

# 连续生图会话状态（内存存储）
continuous_sessions: dict = {}  # {session_id: {"images": [...], "prompts": [...], "context": "..."}}

# ──────────────────────────────────────────────────────────────
# 生图任务队列（带并发控制，防风控）
# ──────────────────────────────────────────────────────────────
image_tasks: dict = {}        # {gen_id: {status, progress, providers: {pid: {status, log, result}}, ...}}
image_task_handles: dict = {}
image_gen_semaphore = None    # 延迟初始化（FastAPI lifespan）
MAX_CONCURRENT_GENERATIONS = 16  # 最大并发生图数，可调
BACKGROUND_GENERATION_ERROR_MAX_LENGTH = 2400


def _background_generation_error_text(value: object, provider: ProviderConfig) -> str:
    """Sanitize a provider failure before task, log, history, or API exposure."""
    error_text = _provider_error_text(value, provider).strip()
    if not error_text:
        error_text = type(value).__name__ if isinstance(value, BaseException) else "Provider generation failed"
    return error_text[:BACKGROUND_GENERATION_ERROR_MAX_LENGTH]


def _cleanup_image_task_handle(gen_id: str, handle=None):
    current = image_task_handles.get(gen_id)
    if current is not None and (handle is None or current is handle):
        image_task_handles.pop(gen_id, None)


def _image_state_progress(state: dict) -> int:
    """Keep terminal failure/cancellation distinct from completed work."""
    try:
        progress = round(float(state.get("progress", 0)))
    except (TypeError, ValueError):
        progress = 0
    progress = max(0, min(100, progress))
    if state.get("status") in ("failed", "cancelled"):
        return min(99, progress)
    return progress


def _image_task_progress(states: dict, overall_status: str) -> int:
    if not states:
        return 0
    progress = round(sum(_image_state_progress(state) for state in states.values()) / len(states))
    if overall_status in ("failed", "cancelled"):
        return min(99, progress)
    return progress


def _image_task_elapsed(task: dict) -> float:
    """Return the terminal snapshot duration, or the current duration while running."""
    stored = task.get("elapsed_seconds")
    if stored is not None:
        try:
            return round(max(0.0, float(stored)), 1)
        except (TypeError, ValueError):
            pass
    start_time = task.get("start_time")
    if not start_time:
        return 0.0
    return round(max(0.0, time.time() - start_time), 1)


def _image_task_status(current_status: str, states: dict) -> str:
    """Derive one truthful public status without hiding partial successes."""
    child_statuses = [state.get("status") for state in states.values()]
    if current_status == "cancelled" or "cancelled" in child_statuses:
        return "cancelled"
    if not child_statuses:
        return current_status
    if all(status in ("completed", "failed") for status in child_statuses):
        return "completed" if "completed" in child_statuses else "failed"
    return current_status


def _refresh_image_task_state(task: dict) -> str:
    """Normalize child progress and publish the status derived from it."""
    states = task.get("provider_states", {})
    for state in states.values():
        state["progress"] = _image_state_progress(state)
    status = _image_task_status(task.get("status", "queued"), states)
    task["status"] = status
    task["progress"] = _image_task_progress(states, status)
    return status


def _mark_image_task_cancelled(gen_id: str):
    task = image_tasks.get(gen_id)
    if not task:
        return None
    status = _refresh_image_task_state(task)
    if status in ("completed", "failed", "cancelled"):
        return status
    states = task.get("provider_states", {})
    if not any(state.get("status") in ("queued", "generating") for state in states.values()):
        return status
    task["status"] = "cancelled"
    for state in states.values():
        if state.get("status") in ("queued", "generating"):
            state["status"] = "cancelled"
            state["progress"] = _image_state_progress(state)
            log = state.setdefault("log", [])
            if not log or "已停止" not in log[-1]:
                log.append(f"[{time.strftime('%H:%M:%S')}] ■ 已停止")
    task["progress"] = _image_task_progress(task.get("provider_states", {}), task["status"])
    task["elapsed_seconds"] = _image_task_elapsed(task)
    return task["status"]


def _load_history():
    """启动时从 history.jsonl 加载历史记录到内存"""
    global generation_counter
    if not HISTORY_FILE.exists():
        return
    with open(HISTORY_FILE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entry = _json.loads(line)
                gen_id = entry.get("generation_id", "")
                if gen_id:
                    generation_history[gen_id] = entry
                    # 更新计数器以避免 ID 冲突
                    import re
                    m = re.match(r'gen_(\d+)', gen_id)
                    if m:
                        num = int(m.group(1))
                        if num > generation_counter:
                            generation_counter = num
            except Exception:
                pass


def _save_history_entry(entry: dict):
    """追加一条历史记录到 history.jsonl"""
    with open(HISTORY_FILE, "a", encoding="utf-8") as fh:
        fh.write(_json.dumps(entry, ensure_ascii=False) + "\n")


def _precision_data_url_sha256(value: object) -> str:
    """Hash a validated image data URL without retaining its bytes."""
    raw = str(value or "")
    encoded = raw.split(",", 1)[1] if "," in raw else raw
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError, TypeError):
        return ""
    return hashlib.sha256(payload).hexdigest() if payload else ""


def _precision_history_metadata(entry: object) -> dict:
    if not isinstance(entry, dict):
        return {}
    metadata = entry.get("precision_workflow")
    if not isinstance(metadata, dict) or metadata.get("schema") != PRECISION_WORKFLOW_SCHEMA:
        return {}
    workflow_id = str(metadata.get("workflow_id") or "")
    if not PRECISION_WORKFLOW_ID_RE.fullmatch(workflow_id):
        return {}
    return metadata


def _precision_legacy_workflow_id(generation_id: object) -> str:
    digest = hashlib.sha256(f"legacy:{generation_id}".encode("utf-8")).hexdigest()
    return f"pw_{digest[:32]}"


def _precision_version_id(generation_id: object, result_key: object) -> str:
    digest = hashlib.sha256(
        f"{generation_id}:{result_key}".encode("utf-8")
    ).hexdigest()
    return f"pv_{digest[:24]}"


def _precision_history_gallery_file(local_path: object) -> Optional[Path]:
    raw = str(local_path or "")
    if not raw:
        return None
    filename = PureWindowsPath(raw).name if "\\" in raw else PurePosixPath(raw).name
    try:
        return _resolve_gallery_file(filename)
    except HTTPException:
        return None


def _precision_gallery_file_sha256(path: Optional[Path]) -> str:
    if path is None:
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _precision_result_artifact(entry: dict, result_key: str, result: dict) -> dict:
    metadata = _precision_history_metadata(entry)
    outputs = metadata.get("outputs") if isinstance(metadata.get("outputs"), dict) else {}
    stored = outputs.get(result_key) if isinstance(outputs.get(result_key), dict) else {}
    sha256 = str(stored.get("sha256") or "")
    path = _precision_history_gallery_file(result.get("local_path"))
    if path is None and isinstance(stored.get("filename"), str):
        path = _precision_history_gallery_file(stored["filename"])
    if path is None and re.fullmatch(r"[a-f0-9]{64}", sha256):
        recovered_filename = _precision_find_gallery_source(sha256)
        if recovered_filename:
            path = _precision_history_gallery_file(recovered_filename)
    if not re.fullmatch(r"[a-f0-9]{64}", sha256):
        sha256 = _precision_gallery_file_sha256(path)

    width = stored.get("width")
    height = stored.get("height")
    if not isinstance(width, int) or not isinstance(height, int) or width <= 0 or height <= 0:
        width = height = None
        if path is not None:
            try:
                with Image.open(path) as image:
                    width, height = image.size
            except Exception:
                width = height = None
    return {
        "sha256": sha256,
        "filename": path.name if path is not None else None,
        "available": path is not None,
        "width": width,
        "height": height,
    }


def _precision_success_results(entry: dict):
    results = entry.get("results")
    if not isinstance(results, dict):
        return
    for result_key in sorted(results):
        result = results.get(result_key)
        if isinstance(result, dict) and result.get("success"):
            yield str(result_key), result


def _precision_find_parent_result(source_sha256: str) -> Optional[tuple[str, str, dict]]:
    matches = []
    for generation_id, entry in list(generation_history.items()):
        if not isinstance(entry, dict) or entry.get("mode") != "precision_edit":
            continue
        for result_key, result in _precision_success_results(entry):
            artifact = _precision_result_artifact(entry, result_key, result)
            if artifact["sha256"] == source_sha256:
                matches.append((str(entry.get("created_at") or ""), str(generation_id), result_key, artifact))
    if not matches:
        return None
    _created_at, generation_id, result_key, artifact = max(matches)
    return generation_id, result_key, artifact


def _precision_existing_workflow_id(parent_generation_id: str) -> str:
    parent = generation_history.get(parent_generation_id)
    parent_metadata = _precision_history_metadata(parent)
    if parent_metadata:
        return str(parent_metadata["workflow_id"])
    for entry in list(generation_history.values()):
        metadata = _precision_history_metadata(entry)
        if str(metadata.get("parent_generation_id") or "") == parent_generation_id:
            return str(metadata["workflow_id"])
    return _precision_legacy_workflow_id(parent_generation_id)


def _precision_find_gallery_source(source_sha256: str) -> Optional[str]:
    try:
        candidates = sorted(GALLERY_DIR.glob("*.png"), reverse=True)
    except OSError:
        return None
    for candidate in candidates:
        try:
            path = _resolve_gallery_file(candidate.name)
        except HTTPException:
            continue
        if _precision_gallery_file_sha256(path) == source_sha256:
            return path.name
    return None


def _precision_workflow_annotation_snapshot(generation_input: dict) -> Optional[dict]:
    """Persist only the validated, structured edit record needed for restore."""
    if not isinstance(generation_input, dict) or generation_input.get("precision_canvas_only"):
        return None
    contract = str(generation_input.get("annotation_contract") or "")
    annotations = generation_input.get("annotations")
    if contract not in PRECISION_ANNOTATION_CONTRACTS or not isinstance(annotations, list):
        return None
    # Validation already normalized this input. JSON round-tripping prevents a
    # later task mutation from changing the durable history snapshot.
    return {
        "annotation_contract": contract,
        "annotations": _json.loads(_json.dumps(annotations, ensure_ascii=True)),
        "precision_strategy": str(generation_input.get("precision_strategy") or "standard"),
        "precision_selection_mode": str(generation_input.get("precision_selection_mode") or "annotation"),
        "precision_selection_feather": generation_input.get("precision_selection_feather", 0),
    }


def _precision_project_annotation_snapshot(metadata: dict) -> Optional[dict]:
    """Fail closed when an on-disk history record has an invalid snapshot."""
    raw = metadata.get("annotation_snapshot") if isinstance(metadata, dict) else None
    if not isinstance(raw, dict):
        return None
    contract = str(raw.get("annotation_contract") or "")
    if contract not in PRECISION_ANNOTATION_CONTRACTS:
        return None
    try:
        annotations = _validate_precision_annotations(raw.get("annotations"), contract)
    except HTTPException:
        return None
    strategy = str(raw.get("precision_strategy") or "standard")
    selection_mode = str(raw.get("precision_selection_mode") or "annotation")
    feather = raw.get("precision_selection_feather", 0)
    if strategy not in PRECISION_STRATEGIES or selection_mode not in PRECISION_SELECTION_MODES:
        return None
    if isinstance(feather, bool) or not isinstance(feather, (int, float)):
        return None
    feather = float(feather)
    if not math.isfinite(feather) or feather < 0 or feather > MAX_PRECISION_SELECTION_FEATHER:
        return None
    return {
        "annotation_contract": contract,
        "annotations": annotations,
        "precision_strategy": strategy,
        "precision_selection_mode": selection_mode,
        "precision_selection_feather": feather,
    }


def _prepare_precision_workflow_metadata(generation_input: dict) -> dict:
    image = generation_input["images"][0]
    source_sha256 = _precision_data_url_sha256(image.get("value"))
    parent = _precision_find_parent_result(source_sha256) if source_sha256 else None
    if parent:
        parent_generation_id, parent_result_key, parent_artifact = parent
        workflow_id = _precision_existing_workflow_id(parent_generation_id)
        input_filename = parent_artifact.get("filename")
    else:
        parent_generation_id = None
        parent_result_key = None
        workflow_id = f"pw_{uuid.uuid4().hex}"
        input_filename = _precision_find_gallery_source(source_sha256) if source_sha256 else None
    return {
        "schema": PRECISION_WORKFLOW_SCHEMA,
        "workflow_id": workflow_id,
        "source_sha256": source_sha256,
        "source_width": image.get("width"),
        "source_height": image.get("height"),
        "input_gallery_filename": input_filename,
        "parent_generation_id": parent_generation_id,
        "parent_result_key": parent_result_key,
        "outputs": {},
        "annotation_snapshot": _precision_workflow_annotation_snapshot(generation_input),
    }


def _finalize_precision_workflow_metadata(task: dict) -> dict:
    metadata = dict(task.get("precision_workflow") or {})
    outputs = {}
    entry_view = {"precision_workflow": metadata}
    for result_key, result in _precision_success_results(task):
        artifact = _precision_result_artifact(entry_view, result_key, result)
        outputs[result_key] = {
            "sha256": artifact["sha256"],
            "filename": artifact["filename"],
            "width": artifact["width"],
            "height": artifact["height"],
        }
    metadata["outputs"] = outputs
    return metadata


def _precision_normalize_timestamp(value: object) -> str:
    if not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")
        except (OSError, OverflowError, ValueError):
            return ""
    text = str(value or "").strip()
    if not text or len(text) > 64:
        return ""
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return parsed.isoformat(timespec="seconds")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _precision_entry_timestamp(entry: dict, result: Optional[dict] = None) -> str:
    if isinstance(result, dict):
        finished_at = _precision_normalize_timestamp(result.get("finished_at"))
        if finished_at:
            return finished_at
    return _precision_normalize_timestamp(entry.get("created_at"))


def _precision_source_artifact(metadata: dict) -> dict:
    filename = metadata.get("input_gallery_filename")
    path = None
    if isinstance(filename, str) and filename:
        try:
            path = _resolve_gallery_file(filename)
        except HTTPException:
            path = None
    width = metadata.get("source_width")
    height = metadata.get("source_height")
    return {
        "filename": path.name if path is not None else None,
        "available": path is not None,
        "width": width if isinstance(width, int) and width > 0 else None,
        "height": height if isinstance(height, int) and height > 0 else None,
    }


def _precision_workflow_projection_data(*, include_annotation_snapshots: bool = False) -> tuple[List[dict], dict]:
    entries = {
        str(generation_id): entry
        for generation_id, entry in list(generation_history.items())
        if isinstance(entry, dict) and entry.get("mode") == "precision_edit"
    }
    assignments = {}
    for generation_id, entry in entries.items():
        metadata = _precision_history_metadata(entry)
        if metadata:
            assignments[generation_id] = str(metadata["workflow_id"])
    changed = True
    while changed:
        changed = False
        for generation_id, entry in entries.items():
            metadata = _precision_history_metadata(entry)
            parent_generation_id = str(metadata.get("parent_generation_id") or "")
            workflow_id = assignments.get(generation_id)
            if workflow_id and parent_generation_id in entries and parent_generation_id not in assignments:
                assignments[parent_generation_id] = workflow_id
                changed = True
    for generation_id in entries:
        assignments.setdefault(generation_id, _precision_legacy_workflow_id(generation_id))

    grouped = defaultdict(list)
    for generation_id, entry in entries.items():
        grouped[assignments[generation_id]].append((generation_id, entry))

    projections = []
    file_index = {}
    for workflow_id, workflow_entries in grouped.items():
        workflow_entries.sort(key=lambda item: _precision_entry_timestamp(item[1]))
        generation_ids = {generation_id for generation_id, _entry in workflow_entries}
        _root_generation_id, root_entry = next(
            (
                (generation_id, entry)
                for generation_id, entry in workflow_entries
                if str(_precision_history_metadata(entry).get("parent_generation_id") or "") not in generation_ids
            ),
            workflow_entries[0],
        )
        root_metadata = _precision_history_metadata(root_entry)
        source_artifact = _precision_source_artifact(root_metadata)
        source_created_at = _precision_entry_timestamp(root_entry)
        source_version = {
            "version_id": "original",
            "parent_version_id": None,
            "kind": "source",
            "created_at": source_created_at,
            "available": source_artifact["available"],
            "width": source_artifact["width"],
            "height": source_artifact["height"],
            "thumbnail": None,
            "image_url": None,
        }
        if source_artifact["available"]:
            source_version["thumbnail"] = f"/api/precision/workflows/{workflow_id}/versions/original/thumb"
            source_version["image_url"] = f"/api/precision/workflows/{workflow_id}/versions/original/image"
            file_index[(workflow_id, "original")] = source_artifact["filename"]

        versions = []
        result_version_ids = {}
        for generation_id, entry in workflow_entries:
            for result_key, _result in _precision_success_results(entry):
                result_version_ids[(generation_id, result_key)] = _precision_version_id(generation_id, result_key)
        for generation_id, entry in workflow_entries:
            metadata = _precision_history_metadata(entry)
            parent_generation_id = str(metadata.get("parent_generation_id") or "")
            parent_result_key = str(metadata.get("parent_result_key") or "")
            parent_version_id = result_version_ids.get((parent_generation_id, parent_result_key), "original")
            for result_key, result in _precision_success_results(entry):
                artifact = _precision_result_artifact(entry, result_key, result)
                version_id = result_version_ids[(generation_id, result_key)]
                version = {
                    "version_id": version_id,
                    "parent_version_id": parent_version_id,
                    "kind": "result",
                    "created_at": _precision_entry_timestamp(entry, result),
                    "available": artifact["available"],
                    "width": artifact["width"],
                    "height": artifact["height"],
                    "thumbnail": None,
                    "image_url": None,
                }
                if include_annotation_snapshots:
                    snapshot = _precision_project_annotation_snapshot(metadata)
                    if snapshot is not None:
                        version["annotation_snapshot"] = snapshot
                if artifact["available"]:
                    version["thumbnail"] = f"/api/precision/workflows/{workflow_id}/versions/{version_id}/thumb"
                    version["image_url"] = f"/api/precision/workflows/{workflow_id}/versions/{version_id}/image"
                    file_index[(workflow_id, version_id)] = artifact["filename"]
                versions.append(version)

        if not versions:
            continue
        versions.sort(key=lambda item: (item["created_at"], item["version_id"]))
        all_versions = [source_version, *versions]
        dated = [item["created_at"] for item in all_versions if item["created_at"]]
        available_versions = [item for item in versions if item["available"]]
        latest_available = available_versions[-1] if available_versions else None
        latest_size = None
        if latest_available and latest_available["width"] and latest_available["height"]:
            latest_size = f"{latest_available['width']}x{latest_available['height']}"
        restore = ({
            "workflow_id": workflow_id,
            "version_id": latest_available["version_id"],
            "image_url": latest_available["image_url"],
        } if latest_available else None)
        if include_annotation_snapshots and restore is not None:
            snapshot = latest_available.get("annotation_snapshot")
            if snapshot is not None:
                restore["annotation_snapshot"] = snapshot
                restore["base_version_id"] = latest_available["parent_version_id"]
        projections.append({
            "workflow_id": workflow_id,
            "created_at": min(dated) if dated else "",
            "updated_at": max(dated) if dated else "",
            "edit_count": len(versions),
            "thumbnail": latest_available["thumbnail"] if latest_available else None,
            "summary": {
                "edit_count": len(versions),
                "available_version_count": len(available_versions),
                "source_available": source_artifact["available"],
                "latest_size": latest_size,
            },
            "versions": all_versions,
            "restore": restore,
        })
    projections.sort(key=lambda item: (item["updated_at"], item["workflow_id"]), reverse=True)
    return projections, file_index


def _precision_filter_date(value: str, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"code": "precision_workflow_date_invalid", "field": field},
        ) from None
    return text


def _precision_validate_workflow_id(workflow_id: str) -> str:
    value = str(workflow_id or "")
    if not PRECISION_WORKFLOW_ID_RE.fullmatch(value):
        raise HTTPException(status_code=404, detail="工作流不存在")
    return value


# 启动时加载历史
_load_history()


# ──────────────────────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────────────────────

def _get_video_duration(video_path) -> float:
    """使用 ffprobe 获取视频时长"""
    import subprocess
    import json
    
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", 
               "-show_format", str(video_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
        if result.returncode == 0:
            info = json.loads(result.stdout)
            duration = info.get("format", {}).get("duration")
            if duration:
                return round(float(duration), 1)
    except:
        pass
    return None


def _scan_gallery(limit: int = 100) -> List[dict]:
    """扫描图库和视频库，从 PNG 元数据中读取 prompt"""
    items = []
    
    # 扫描图片
    for f in sorted(GALLERY_DIR.glob("*.png"), reverse=True)[:limit]:
        parts = f.stem.split("_")
        model_name = parts[0] if parts else "unknown"
        created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
        
        # 从 PNG 元数据中读取 prompt
        prompt_text = ""
        source = "cloud" if f.stem.startswith("remote_") else "local"
        tags = ["cloud-sync"] if source == "cloud" else []
        source_path = ""
        source_deployment = ""
        source_created_at = ""
        try:
            from PIL import Image
            with Image.open(f) as img:
                if img.info and "Prompt" in img.info:
                    prompt_text = img.info["Prompt"]
                if img.info and img.info.get("Model"):
                    model_name = img.info["Model"]
                if img.info and img.info.get("Source"):
                    source = img.info["Source"]
                if img.info and img.info.get("Tags"):
                    tags = [tag.strip() for tag in img.info["Tags"].split(",") if tag.strip()]
                if img.info:
                    source_path = str(img.info.get("SourcePath") or "")
                    source_deployment = str(img.info.get("SourceDeployment") or "")
                    source_created_at = str(img.info.get("CreatedAt") or "")
        except Exception as e:
            pass
        
        # 如果元数据中没有，从历史记录中查找
        if not prompt_text:
            fname = f.name
            for h in generation_history.values():
                if h.get("results"):
                    for pid, res in h["results"].items():
                        if res.get("success") and res.get("local_path"):
                            local_path = res["local_path"]
                            if fname in local_path or f.stem in local_path:
                                prompt_text = h.get("prompt", "")
                                break
                    if prompt_text:
                        break
        
        items.append({
            "id": f.stem,
            "type": "image",
            "model": model_name,
            "prompt": prompt_text,
            "local_path": str(f),
            "created_at": created,
            "thumbnail": f"/api/gallery/thumb/{f.name}",
            "file_size": f.stat().st_size,
            "source": source,
            "tags": tags,
            "source_path": source_path,
            "source_deployment": source_deployment,
            "source_created_at": source_created_at,
        })
    
    # 扫描视频
    VIDEO_DIR = STORAGE_DIR / "videos"
    if VIDEO_DIR.exists():
        for f in sorted(VIDEO_DIR.glob("*.mp4"), reverse=True)[:limit]:
            parts = f.stem.split("_")
            provider_name = parts[0] if parts else "unknown"
            created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime))
            
            # 从视频历史记录中查找 prompt
            prompt_text = ""
            if 'video_tasks' in globals():
                for task_id, task in list(video_tasks.items()):
                    if task.get("local_path") and f.stem in task["local_path"]:
                        prompt_text = task.get("prompt", "")
                        provider_name = task.get("provider_id", provider_name)
                        break
            
            items.append({
                "id": f.stem,
                "type": "video",
                "model": provider_name,
                "prompt": prompt_text,
                "local_path": str(f),
                "created_at": created,
                "thumbnail": f"/api/gallery/thumb/{f.name}",  # 视频缩略图用首帧
                "video_url": f"/api/video/file/{f.name}",
                    "duration": _get_video_duration(f),
                "file_size": f.stat().st_size,
            })
    
    # 按创建时间倒序排列
    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items[:limit]


# ══════════════════════════════════════════════════════════════
# API 路由
# ══════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return FileResponse(str(BASE_PATH / "static" / "index.html"))


@app.get("/api/status")
async def status():
    """检查各 Provider 配置状态"""
    result = {}
    for p in cfg_mgr.config.providers:
        result[p.id] = {
            "configured": bool(p.api_key),
            "enabled": p.enabled,
            "type": p.type,
            "name": p.name,
            "model": p.model,
        }
    return result


@app.get("/api/runtime/status")
async def runtime_status():
    """Return a non-secret identity used to detect stale browser/runtime mixes."""
    configured_mode = os.getenv("APP_MODE", "prod").strip().lower()
    if configured_mode != "dev":
        raise HTTPException(status_code=404, detail="Not found")
    payload = {
        "service": "genbox",
        "version": __version__,
        "mode": "dev",
        "port": GENBOX_PORT,
        "started_at": int(app_start_time),
        "runtime_id": app_runtime_id,
        "runtime_head": os.getenv("GENBOX_RUNTIME_HEAD", "").strip(),
        "runtime_source": os.getenv("GENBOX_RUNTIME_SOURCE", "").strip(),
    }
    return JSONResponse(payload, headers={"Cache-Control": "no-store"})


def _public_precision_size_catalog(provider: ProviderConfig) -> List[dict]:
    """Project strict-size choices without converting documentation into support.

    ``documented_presets`` is descriptive data for the model-size menu.  The
    only values a caller may enable for a strict provider request are copied
    into ``strict_selectable_sizes`` from the selected provider's explicit,
    validated ``supported_sizes`` record.
    """
    extra = provider.extra if isinstance(provider.extra, dict) else {}
    model_capabilities = extra.get("model_capabilities")
    capability_models = list(model_capabilities) if isinstance(model_capabilities, dict) else []
    model_ids = []
    for candidate in list(provider.models or []) + [provider.model] + capability_models:
        model_id = str(candidate or "").strip()
        if model_id and model_id not in model_ids:
            model_ids.append(model_id)

    catalog = []
    for model_id in model_ids:
        resolution = _provider_precision_model_resolution(provider, model_id)
        canonical_model = resolution.canonical_model if resolution.structure_valid else ""
        provider_ready = bool(
            getattr(provider, "type", "") == "image"
            and getattr(provider, "enabled", False)
            and str(getattr(provider, "endpoint_type", "auto") or "auto").strip().lower() == "openai"
            and isinstance(getattr(provider, "capabilities", None), dict)
            and provider.capabilities.get("precision_edit") is True
        )
        declared_sizes = (
            list(resolution.supported_sizes)
            if provider_ready
            and resolution.structure_valid
            and resolution.precision_edit_confirmed
            and resolution.size_declaration_valid
            else []
        )
        capability_record = resolution.capability if isinstance(resolution.capability, dict) else {}
        protocol = str(getattr(provider, "endpoint_type", "auto") or "auto").strip().lower()
        if protocol not in {"openai", "gemini", "qwen", "volc_ark", "volc_ark_plan"}:
            protocol = "unknown"
        if provider_ready and resolution.structure_valid and resolution.precision_edit_confirmed:
            # The current backend contract implements source-preserving edit and
            # resize. More specific semantics (mask/inpaint/outpaint) must be
            # explicitly declared by a future provider adapter.
            operations = capability_record.get("operations")
            if not isinstance(operations, list) or not all(
                isinstance(item, str) and item in {"edit", "inpaint", "outpaint", "resize"}
                for item in operations
            ):
                operations = ["edit", "resize"]
            input_contract = (
                "image_plus_annotation"
                if not capability_record.get("input_contract")
                else str(capability_record["input_contract"])
            )
            evidence = "explicit_provider_capability"
            status = "ready"
        else:
            operations = []
            input_contract = "unknown"
            evidence = "unverified"
            status = "unknown"
        native_size = "exact_list" if declared_sizes else "unknown"
        catalog.append({
            "model": model_id,
            "canonical_model": canonical_model,
            "documented_presets": list(documented_precision_model_size_presets(canonical_model)),
            "declared_sizes": declared_sizes,
            "strict_selectable_sizes": list(declared_sizes),
            "precision_capability": {
                "status": status,
                "provider": str(getattr(provider, "id", "") or ""),
                "model": model_id,
                "canonical_model": canonical_model,
                "protocol": protocol,
                "operations": operations,
                "input_contract": input_contract,
                "output_contract": "image_result" if status == "ready" else "unknown",
                "native_size": native_size,
                "size_policy": (
                    ["native_strict", "provider_native_then_local_fit", "local_only"]
                    if status == "ready"
                    else ["local_only"]
                ),
                "evidence": evidence,
                "dispatch_authorized": bool(status == "ready" and declared_sizes),
            },
        })
    return catalog


@app.get("/api/providers")
async def list_providers():
    """获取所有 Provider 配置（API Key 脱敏）"""
    from providers.key_pool import key_pool_manager
    providers_data = []
    for p in cfg_mgr.config.providers:
        d = p.model_dump(exclude={"api_key", "api_keys", "endpoints"})
        # Endpoint-only providers are valid runtime configurations too. Keep
        # this readiness flag aligned with the transport's active-endpoint logic.
        d["has_key"] = bool(p.get_effective_keys() or p.get_active_endpoints())
        d["has_keys"] = len(p.get_effective_keys()) > 1
        d["key_count"] = len(p.get_effective_keys())
        extra = p.extra if isinstance(p.extra, dict) else {}
        d["model_capabilities"] = extra.get("model_capabilities", {})
        d["precision_size_catalog"] = _public_precision_size_catalog(p)
        # API Key 脱敏
        keys = p.get_effective_keys()
        if keys:
            d["api_key_masked"] = keys[0][:4] + "****" + keys[0][-4:] if len(keys[0]) > 8 else "****"
            pool = key_pool_manager.get_or_create(p.id, keys)
            d["keypool"] = {
                "total_keys": pool.size,
                "available_keys": pool.available_count,
                "keys": pool.get_status(),
            }
        # 端点脱敏
        d["endpoints"] = []
        for ep in (p.endpoints or []):
            ep_dict = {"name": ep.name, "url": ep.url, "model": getattr(ep, "model", ""), "enabled": ep.enabled}
            if ep.key:
                ep_dict["key_masked"] = ep.key[:4] + "****" + ep.key[-4:] if len(ep.key) > 8 else "****"
            d["endpoints"].append(ep_dict)
        providers_data.append(d)
    return {"providers": providers_data}


@app.get("/api/providers/{provider_id}")
async def get_provider(provider_id: str):
    """获取单个 Provider 详细配置（API Key 脱敏）"""
    for p in cfg_mgr.config.providers:
        if p.id == provider_id:
            d = p.model_dump(exclude={"api_key", "api_keys"})
            d["has_key"] = bool(p.get_effective_keys() or p.get_active_endpoints())
            d["precision_size_catalog"] = _public_precision_size_catalog(p)
            keys = p.get_effective_keys()
            if keys:
                d["api_key_masked"] = keys[0][:4] + "****" + keys[0][-4:] if len(keys[0]) > 8 else "****"
            d["endpoints"] = []
            for ep in (p.endpoints or []):
                ep_dict = {"name": ep.name, "url": ep.url, "model": getattr(ep, "model", ""), "enabled": ep.enabled}
                if ep.key:
                    ep_dict["key_masked"] = ep.key[:4] + "****" + ep.key[-4:] if len(ep.key) > 8 else "****"
                d["endpoints"].append(ep_dict)
            return d
    raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' 不存在")


@app.post("/api/providers")
async def create_provider(req: ProviderCreateReq):
    """新增或更新 Provider"""
    cfg = cfg_mgr.config

    # 检查 ID 是否已存在
    existing_idx = None
    for i, p in enumerate(cfg.providers):
        if p.id == req.id:
            existing_idx = i
            break

    if existing_idx is not None:
        new_p = ProviderConfig(**_merge_provider_secrets(cfg.providers[existing_idx], req))
    else:
        new_p = ProviderConfig(**req.model_dump())

    if existing_idx is not None:
        cfg.providers[existing_idx] = new_p
    else:
        cfg.providers.append(new_p)

    cfg_mgr.save(cfg)
    _write_log("provider", f"Provider '{req.id}' 已保存", {"type": req.type})
    return {"ok": True, "message": f"Provider '{req.id}' 已保存", "id": req.id}


@app.post("/api/providers/{provider_id}/precision-capability")
async def set_precision_capability(provider_id: str, req: PrecisionCapabilityReq):
    """Persist an explicit, per-model user confirmation for precision editing."""
    model = str(req.model or "").strip()
    size_requested = "size" in req.model_fields_set
    flexible_sizes_requested = "flexible_sizes" in req.model_fields_set
    compatibility_profile = req.compatibility_profile
    if compatibility_profile is not None and compatibility_profile != PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "precision_compatibility_profile_invalid",
                "message": "Compatibility profile is not supported",
            },
        )
    if compatibility_profile is not None and (size_requested or flexible_sizes_requested or not req.enabled):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "precision_compatibility_request_invalid",
                "message": "Compatibility profile is accepted only when enabling a model capability",
            },
        )
    normalized_size = None
    if size_requested:
        normalized_size = _normalize_precision_size(req.size)
        if not normalized_size:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "precision_size_invalid",
                    "message": "Size must be a supported WIDTHxHEIGHT value",
                },
            )
    if flexible_sizes_requested and not req.enabled:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "precision_flexible_size_request_invalid",
                "message": "Flexible-size policy can be changed only while precision editing remains enabled",
            },
        )
    provider = next((p for p in cfg_mgr.config.providers if p.id == provider_id), None)
    if provider is None:
        raise HTTPException(status_code=404, detail={"code": "provider_not_found", "message": "Provider not found"})
    known_models = {str(item).strip() for item in (provider.models or [provider.model]) if str(item).strip()}
    if not model or model not in known_models:
        raise HTTPException(status_code=400, detail={"code": "precision_model_invalid", "message": "Model must belong to the selected provider"})
    if (req.enabled or size_requested or flexible_sizes_requested or compatibility_profile is not None) and not req.confirmed:
        raise HTTPException(status_code=400, detail={"code": "precision_confirmation_required", "message": "Explicit user confirmation is required"})
    capabilities = dict(provider.capabilities or {})
    extra = dict(provider.extra or {})
    model_capabilities = dict(extra.get("model_capabilities") or {})
    selected = dict(model_capabilities.get(model) or {})
    resolution = resolve_precision_model_capability(
        model_capabilities,
        model,
        max_output_pixels=MAX_PRECISION_OUTPUT_PIXELS,
    )
    selected_is_alias = any(field in selected for field in ("alias_of", "canonical_model"))
    if selected_is_alias and not resolution.structure_valid:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "precision_model_alias_invalid",
                "message": "Model alias metadata must resolve to one direct canonical model",
            },
        )
    capability_model = resolution.canonical_model if resolution.structure_valid else model
    capability_record = dict(resolution.capability or selected)

    if size_requested or flexible_sizes_requested:
        if getattr(provider, "type", "") != "image":
            raise HTTPException(status_code=400, detail={"code": "precision_provider_not_image", "message": "Provider must be an image provider"})
        if not getattr(provider, "enabled", False):
            raise HTTPException(status_code=400, detail={"code": "precision_provider_not_enabled", "message": "Provider must be enabled"})
        if not (provider.get_effective_keys() or provider.get_active_endpoints()):
            raise HTTPException(status_code=400, detail={"code": "precision_provider_key_required", "message": "Provider must have a configured key"})
        endpoint_type = str(getattr(provider, "endpoint_type", "auto") or "auto").strip().lower()
        if endpoint_type != "openai":
            raise HTTPException(status_code=400, detail={"code": "precision_provider_openai_required", "message": "Provider must use the OpenAI-compatible image transport"})
        if not _provider_precision_model_capability(provider, model):
            raise HTTPException(status_code=400, detail={"code": "precision_model_precision_edit_required", "message": "Model must already have explicit precision_edit capability"})

        # gpt-image-2 has a stricter upstream size envelope than the generic
        # WIDTHxHEIGHT capability contract.  Apply it to both the canonical
        # model and explicitly reviewed aliases that resolve to that model.
        if size_requested and req.enabled and resolution.structure_valid and capability_model == PRECISION_GPT_IMAGE_2_COMPATIBILITY_PROFILE:
            protocol_error = gpt_image_2_size_error(normalized_size)
            if protocol_error:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "precision_size_invalid",
                        "message": protocol_error[1],
                        "reason_code": protocol_error[0],
                    },
                )

        supported_sizes = list(resolution.supported_sizes) if resolution.size_declaration_valid else []
        if size_requested:
            if req.enabled:
                if normalized_size not in supported_sizes:
                    if len(supported_sizes) >= MAX_PRECISION_SUPPORTED_SIZES:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "code": "precision_size_limit_exceeded",
                                "message": "Model supported size list is full",
                                "max_sizes": MAX_PRECISION_SUPPORTED_SIZES,
                            },
                        )
                    supported_sizes.append(normalized_size)
            else:
                supported_sizes = [item for item in supported_sizes if item != normalized_size]

            for legacy_field in ("supportedSizes", "sizes", "dimensions"):
                capability_record.pop(legacy_field, None)
            capability_record["supported_sizes"] = supported_sizes
        if flexible_sizes_requested:
            if req.flexible_sizes:
                if not supported_sizes or any(gpt_image_2_size_error(size) for size in supported_sizes):
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "code": "precision_flexible_size_profile_required",
                            "message": "Flexible sizes require a confirmed GPT Image 2-compatible declared size",
                        },
                    )
                capability_record["size_policy"] = PRECISION_GPT_IMAGE_2_FLEXIBLE_SIZE_POLICY
            else:
                capability_record.pop("size_policy", None)
        model_capabilities[capability_model] = capability_record
    elif req.enabled and compatibility_profile is not None:
        canonical_resolution = resolve_precision_model_capability(
            model_capabilities,
            compatibility_profile,
            max_output_pixels=MAX_PRECISION_OUTPUT_PIXELS,
        )
        if (
            model == compatibility_profile
            or not canonical_resolution.structure_valid
            or not canonical_resolution.precision_edit_confirmed
            or not canonical_resolution.size_declaration_valid
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "precision_compatibility_target_unavailable",
                    "message": "The selected compatibility profile requires an explicit canonical capability and supported sizes",
                },
            )
        selected_record = dict(selected)
        for field_name in (
            "precision_edit",
            "supported_sizes",
            "supportedSizes",
            "sizes",
            "dimensions",
            "alias_of",
            "canonical_model",
        ):
            selected_record.pop(field_name, None)
        selected_record["alias_of"] = compatibility_profile
        model_capabilities[model] = selected_record
        capabilities[PRECISION_EDIT_CAPABILITY] = True
        provider.endpoint_type = "openai"
        provider.precision_edit_profile = (
            PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
        )
        capability_model = model
        capability_record = selected_record
    elif req.enabled:
        for alias_field in ("alias_of", "canonical_model"):
            capability_record.pop(alias_field, None)
        capabilities[PRECISION_EDIT_CAPABILITY] = True
        capability_record[PRECISION_EDIT_CAPABILITY] = True
        provider.endpoint_type = "openai"
        if provider.precision_edit_profile is None:
            provider.precision_edit_profile = (
                PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE
            )
    else:
        capability_model = model
        capability_record = dict(selected)
        capability_record.pop(PRECISION_EDIT_CAPABILITY, None)
        capability_record.pop("alias_of", None)
        capability_record.pop("canonical_model", None)
    model_capabilities[capability_model] = capability_record
    extra["model_capabilities"] = model_capabilities
    provider.capabilities = capabilities
    provider.extra = extra
    cfg_mgr.save(cfg_mgr.config)
    _write_log("provider", "精准改图模型能力已更新", {"provider_id": provider_id, "model": model, "enabled": req.enabled})
    if size_requested or flexible_sizes_requested:
        result = {
            "ok": True,
            "provider_id": provider_id,
            "model": model,
            "enabled": req.enabled,
            "size": normalized_size,
            "supported_sizes": supported_sizes,
        }
        if flexible_sizes_requested:
            result["flexible_sizes"] = bool(req.flexible_sizes)
        return result
    result = {"ok": True, "provider_id": provider_id, "model": model, "enabled": req.enabled}
    if compatibility_profile is not None:
        result["compatibility_profile"] = compatibility_profile
    return result


@app.delete("/api/providers/{provider_id}")
async def delete_provider(provider_id: str):
    """删除 Provider"""
    cfg = cfg_mgr.config
    original_len = len(cfg.providers)
    cfg.providers = [p for p in cfg.providers if p.id != provider_id]

    if len(cfg.providers) == original_len:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' 不存在")

    cfg_mgr.save(cfg)
    _write_log("provider", f"已删除 Provider: {provider_id}")
    return {"ok": True, "message": f"Provider '{provider_id}' 已删除"}


@app.put("/api/providers/reorder")
async def reorder_providers(order: List[str]):
    """调整 Provider 排序"""
    cfg = cfg_mgr.config
    id_map = {p.id: p for p in cfg.providers}
    reordered = []
    for oid in order:
        if oid in id_map:
            reordered.append(id_map[oid])
            del id_map[oid]
    # 剩余的追加到末尾
    reordered.extend(id_map.values())
    cfg.providers = reordered
    cfg_mgr.save(cfg)
    return {"ok": True}


@app.post("/api/providers/reload")
async def reload_providers():
    """从文件重新加载配置"""
    cfg_mgr.reload()
    return {"ok": True, "message": "配置已重新加载"}


@app.get("/api/setup/status")
async def setup_status():
    """Return the stable, non-secret setup and provider readiness contract."""
    configured_mode = os.getenv("APP_MODE", "prod").strip().lower()
    app_mode = "dev" if configured_mode == "dev" else "prod"
    providers = [
        provider
        for provider in cfg_mgr.config.providers
        if provider.type in ("image", "video")
    ]

    def _provider_has_key(provider) -> bool:
        if str(getattr(provider, "api_key", "") or "").strip():
            return True
        if any(str(key).strip() for key in (getattr(provider, "api_keys", []) or [])):
            return True
        return any(
            bool(str(getattr(endpoint, "key", "") or "").strip())
            for endpoint in (getattr(provider, "endpoints", []) or [])
        )

    has_configured_provider = any(_provider_has_key(provider) for provider in providers)
    has_enabled_provider = any(bool(provider.enabled) for provider in providers)
    return {
        "app_mode": app_mode,
        "auth_required": app_mode == "prod",
        "needs_provider_setup": not has_configured_provider,
        "has_configured_provider": has_configured_provider,
        "has_enabled_provider": has_enabled_provider,
        "provider_count": len(providers),
    }


@app.get("/api/providers/test/{provider_id}")
async def test_provider(provider_id: str):
    """测试 Provider 连通性：多端点时逐个测试，返回每个端点的结果"""
    import time as _time
    import httpx as _httpx

    for p in cfg_mgr.config.providers:
        if p.id == provider_id:
            endpoints = p.get_active_endpoints()
            if not endpoints:
                return {"success": False, "error": "无可用端点", "endpoints": []}

            ep_results = []
            for ep in endpoints:
                ep_start = _time.time()
                try:
                    # 轻量连通性检查：GET /models 或简单请求
                    _verify_ssl = verify_ssl_enabled()
                    async with _httpx.AsyncClient(timeout=15.0, verify=_verify_ssl) as client:
                        headers = {"Authorization": f"Bearer {ep.key}"}
                        # 尝试 models 端点
                        r = await client.get(f"{ep.url.rstrip('/')}/models", headers=headers)
                        latency = round((_time.time() - ep_start) * 1000)
                        if r.status_code in (200, 401):
                            ep_results.append({
                                "url": ep.url,
                                "name": ep.name or ep.display_name,
                                "success": True,
                                "latency_ms": latency,
                                "status_code": r.status_code,
                                "error": None
                            })
                        else:
                            ep_results.append({
                                "url": ep.url,
                                "name": ep.name or ep.display_name,
                                "success": False,
                                "latency_ms": latency,
                                "status_code": r.status_code,
                                "error": f"HTTP {r.status_code}"
                            })
                except Exception as e:
                    latency = round((_time.time() - ep_start) * 1000)
                    ep_results.append({
                        "url": ep.url,
                        "name": ep.name or ep.display_name,
                        "success": False,
                        "latency_ms": latency,
                        "status_code": 0,
                        "error": str(e)[:100]
                    })

            any_ok = any(ep["success"] for ep in ep_results)
            return {
                "success": any_ok,
                "endpoints": ep_results,
            }
    raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' 不存在")


@app.get("/api/providers/fetch-models/{provider_id}")
async def fetch_models(provider_id: str):
    """从上游 API 拉取 Provider 的可用模型列表"""
    for p in cfg_mgr.config.providers:
        if p.id == provider_id:
            try:
                models = await fetch_models_from_upstream(p)
                is_fallback = False
                note = ""
                # 火山方舟 Agent Plan：返回的是官方候选名，并非实时拉取
                if (p.endpoint_type or "auto").strip().lower() == "volc_ark_plan":
                    is_fallback = True
                    note = "（Agent Plan 无模型列表 API，以上为官方候选模型，真实可用性需在生成时验证；Small 套餐不支持视频生成）"
                else:
                    # 检查是否是 fallback（通过对比已知 fallback 列表）
                    fallback_signatures = {
                        "gemini": ["gemini-2.0-flash-exp-image-generation", "gemini-1.5-pro", "gemini-1.5-flash"],
                        "qwen": ["qwen3.6-plus", "wanx-v1", "wanx2.1-t2i-turbo"],
                        "openai": ["gpt-image-2", "dall-e-3", "flux-dev", "sd-xl"],
                    }
                    protocol = "gemini" if "gemini" in p.base_url.lower() or "google" in p.base_url.lower() else ("qwen" if "qwen" in p.id else "openai")
                    sig_models = fallback_signatures.get(protocol, [])
                    if protocol == "qwen":
                        is_fallback = len(models) <= 8 and any(m in models for m in sig_models)
                    elif len(models) <= 8 and any(m in models for m in sig_models):
                        is_fallback = True

                # 自动保存到配置中
                p.models = models
                if models and not p.model:
                    p.model = models[0]
                cfg_mgr.save(cfg_mgr.config)
                return {
                    "success": True,
                    "models": models,
                    "count": len(models),
                    "auto_selected": p.model,
                    "is_fallback": is_fallback,
                    "message": note if is_fallback else "",
                    "provider_type": p.type,
                }
            except Exception as e:
                return {
                    "success": False,
                    "detail": f"拉取失败: {_provider_error_text(e, p)}。请确认 URL 支持 GET /v1/models 接口，或手动输入模型名称。",
                    "provider_type": p.type,
                }
    raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' 不存在")


# ──────────────────────────────────────────────────────────────
# 本地图片放大（Pillow Lanczos3）— 支持宽高比
# ──────────────────────────────────────────────────────────────
def _do_local_upscale(local_path: str, target_size: str, method: str = "lanczos3", ratio: str = "original") -> str:
    """将已保存的图片本地放大到目标尺寸，支持宽高比，返回新路径（原图不动）"""
    import io
    from PIL import Image as _PILImage

    # 解析目标最大边
    max_dim = int(target_size)

    # 读取原图
    src = Path(local_path)
    if not src.exists():
        raise FileNotFoundError(f"原图不存在: {local_path}")
    img = _PILImage.open(src)
    orig_w, orig_h = img.size

    # 根据宽高比计算目标尺寸
    if ratio == "original":
        # 保持原图比例，最大边为 target_size
        scale = max_dim / max(orig_w, orig_h)
        target_w = int(orig_w * scale)
        target_h = int(orig_h * scale)
    else:
        # 解析宽高比
        parts = ratio.split(":")
        if len(parts) != 2:
            raise ValueError(f"无效宽高比格式: {ratio}")
        ratio_w, ratio_h = int(parts[0]), int(parts[1])

        # 根据宽高比和最大边计算目标尺寸
        if orig_w / orig_h > ratio_w / ratio_h:
            # 原图更宽，以宽度为基准
            target_w = max_dim
            target_h = int(max_dim * ratio_h / ratio_w)
        else:
            # 原图更高，以高度为基准
            target_h = max_dim
            target_w = int(max_dim * ratio_w / ratio_h)

    # 已满足目标尺寸
    if target_w <= orig_w and target_h <= orig_h:
        return local_path

    resample_map = {"lanczos3": _PILImage.LANCZOS, "bicubic": _PILImage.BICUBIC, "nearest": _PILImage.NEAREST}
    resample = resample_map.get(method, _PILImage.LANCZOS)

    upscaled = img.resize((target_w, target_h), resample)

    # 保存到新文件（保留原图）
    ratio_tag = ratio.replace(":", "x") if ratio != "original" else "orig"
    upscaled_path = src.parent / f"{src.stem}_upscaled_{target_w}x{target_h}_{ratio_tag}{src.suffix}"
    upscaled.save(str(upscaled_path), format="PNG", quality=95)

    # 写入 PNG 元数据（Prompt 等）
    try:
        from PIL import PngImagePlugin
        info = PngImagePlugin.PngInfo()
        info.add_text("UpscaledFrom", str(orig_w) + "x" + str(orig_h))
        info.add_text("UpscaleMethod", method)
        info.add_text("UpscaleRatio", ratio)
        upscaled.save(str(upscaled_path), format="PNG", pnginfo=info)
    except Exception:
        pass

    return str(upscaled_path)


# ──────────────────────────────────────────────────────────────
# 生图核心（异步队列 + 并发控制 + 实时进度）
# ──────────────────────────────────────────────────────────────
def _validate_cutout_model_action(req: CutoutModelActionRequest) -> None:
    if req.contract != CUTOUT_MODEL_INSTALL_CONTRACT:
        raise _generation_contract_error(
            "cutout_model_contract_unsupported",
            f"cutout model installation requires contract={CUTOUT_MODEL_INSTALL_CONTRACT}",
            field="contract",
        )
    if req.source_id != CUTOUT_MODEL_SOURCE_ID:
        raise _generation_contract_error(
            "cutout_model_source_unsupported",
            "cutout model source_id is not supported",
            field="source_id",
        )
    if req.confirmed is not True:
        raise _generation_contract_error(
            "cutout_model_confirmation_required",
            "explicit confirmation is required because checkpoint provenance and commercial authorization are unverified",
            field="confirmed",
            checkpoint_provenance_status="UNVERIFIED",
            commercial_use_status="UNVERIFIED",
        )


def _cutout_model_manager_http_error(exc: CutoutModelManagerError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.to_detail())


def _cutout_model_projection(capability: dict) -> dict:
    try:
        return CUTOUT_MODEL_MANAGER.model_projection_from_capability(capability)
    except Exception:
        return {
            "contract": CUTOUT_MODEL_INSTALL_CONTRACT,
            "source_id": CUTOUT_MODEL_SOURCE_ID,
            "source_page": CUTOUT_MODEL_SOURCE_PAGE,
            "filename": str(CUTOUT_MODEL_MANIFEST["filename"]),
            "installed": False,
            "valid": False,
            "state": "invalid",
            "reason": "cutout_model_status_unavailable",
            "size_bytes": int(CUTOUT_MODEL_MANIFEST["size_bytes"]),
            "sha256": str(CUTOUT_MODEL_MANIFEST["sha256"]),
            "md5": str(CUTOUT_MODEL_MANIFEST["md5"]),
            "download_supported": False,
            "install_supported": False,
            "confirmation_required": True,
            "license": {
                "checkpoint_provenance_status": "UNVERIFIED",
                "commercial_use_status": "UNVERIFIED",
            },
            "active_task": None,
        }


MODNET_IMPORT_HTTP_CONTRACT = "genbox-cutout-modnet-http-v1"


def _parse_modnet_import_manifest(raw_manifest: str) -> dict:
    """Parse the browser-supplied manifest without accepting paths or URLs."""
    if not isinstance(raw_manifest, str) or not raw_manifest.strip():
        raise HTTPException(
            status_code=422,
            detail={
                "code": "modnet_manifest_required",
                "message": "请提供 MODNet 文件清单",
                "contract": MODNET_IMPORT_HTTP_CONTRACT,
            },
        )
    try:
        manifest = _json.loads(raw_manifest)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "modnet_manifest_invalid",
                "message": "MODNet 文件清单必须是 JSON 对象",
                "contract": MODNET_IMPORT_HTTP_CONTRACT,
            },
        ) from None
    if not isinstance(manifest, dict):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "modnet_manifest_invalid",
                "message": "MODNet 文件清单必须是 JSON 对象",
                "contract": MODNET_IMPORT_HTTP_CONTRACT,
            },
        )
    required = {"filename", "size_bytes", "sha256", "md5"}
    if not required.issubset(manifest):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "modnet_manifest_incomplete",
                "message": "MODNet 文件清单缺少必要字段",
                "required": sorted(required),
                "contract": MODNET_IMPORT_HTTP_CONTRACT,
            },
        )
    # Do not allow a manifest to smuggle a server path or a remote source.
    filename = manifest.get("filename")
    if not isinstance(filename, str) or filename != Path(filename).name or "\\" in filename:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "modnet_filename_invalid",
                "message": "MODNet 文件名必须是上传内容中的安全 .onnx 文件名",
                "contract": MODNET_IMPORT_HTTP_CONTRACT,
            },
        )
    return {key: manifest[key] for key in required}


def _modnet_import_http_error(exc: ModNetImportError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code if exc.status_code in {400, 409, 413, 422, 500} else 422,
        detail={
            "code": exc.code,
            "message": exc.message,
            "contract": MODNET_IMPORT_HTTP_CONTRACT,
        },
    )


@app.post("/api/image-tools/cutout/modnet/import", status_code=201)
async def import_modnet_model(
    upload: UploadFile = File(...),
    manifest: str = Form(...),
    license_confirmed: str = Form(...),
    license_source: str = Form(""),
):
    """Import an explicitly authorized MODNet checkpoint from browser bytes."""
    expected = _parse_modnet_import_manifest(manifest)
    if license_confirmed.strip().lower() != "true":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "modnet_license_unconfirmed",
                "message": "请明确确认你拥有该 MODNet 权重的使用许可",
                "contract": MODNET_IMPORT_HTTP_CONTRACT,
            },
        )
    try:
        result = await MODNET_IMPORT_MANAGER.import_upload(
            upload,
            filename=expected["filename"],
            license_confirmed=True,
            license_source=license_source,
            expected=expected,
        )
    except ModNetImportError as exc:
        raise _modnet_import_http_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "modnet_import_failed",
                "message": "MODNet 模型导入失败",
                "contract": MODNET_IMPORT_HTTP_CONTRACT,
            },
        ) from None
    # Importing a checkpoint is not enough to advertise it: rebuild the
    # optional adapter and require a fresh CPU/runtime capability probe.
    try:
        runtime_capability = _refresh_modnet_registry(MODNET_IMPORT_MANAGER)
    except Exception:
        # Import remains successful, but capability advertisement stays
        # fail-closed if registry replacement/probing encounters an issue.
        runtime_capability = {
            "available": False,
            "executable": False,
            "state": "unavailable",
        }
    # Never expose local filesystem paths in a browser response.
    return {
        "ok": True,
        "contract": MODNET_IMPORT_HTTP_CONTRACT,
        "adapter": result.as_dict()["adapter"],
        "filename": result.filename,
        "size_bytes": result.size_bytes,
        "sha256": result.sha256,
        "md5": result.md5,
        "license_confirmed": True,
        "runtime": {
            "available": runtime_capability.get("available") is True,
            "executable": runtime_capability.get("executable") is True,
            "state": runtime_capability.get("state") or "unavailable",
        },
    }


@app.get("/api/image-tools/cutout/model")
async def get_cutout_model_status():
    try:
        return await asyncio.to_thread(CUTOUT_MODEL_MANAGER.model_status)
    except CutoutModelManagerError as exc:
        raise _cutout_model_manager_http_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_model_status_unavailable",
                "message": "抠图模型状态暂时不可用",
                "contract": CUTOUT_MODEL_INSTALL_CONTRACT,
                "source_id": CUTOUT_MODEL_SOURCE_ID,
            },
        ) from None


@app.post("/api/image-tools/cutout/model/download", status_code=202)
async def start_cutout_model_download(req: CutoutModelActionRequest):
    _validate_cutout_model_action(req)
    try:
        task = CUTOUT_MODEL_MANAGER.start_download()
    except CutoutModelManagerError as exc:
        raise _cutout_model_manager_http_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_model_download_start_failed",
                "message": "无法启动抠图模型下载任务",
                "contract": CUTOUT_MODEL_INSTALL_CONTRACT,
                "source_id": CUTOUT_MODEL_SOURCE_ID,
            },
        ) from None
    return {"ok": True, "task": task}


@app.get("/api/image-tools/cutout/model/download/{task_id}")
async def get_cutout_model_download(task_id: str):
    task = CUTOUT_MODEL_MANAGER.get_task(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "cutout_model_download_not_found",
                "message": "抠图模型下载任务不存在",
            },
        )
    return {"task": task}


@app.delete("/api/image-tools/cutout/model/download/{task_id}")
async def cancel_cutout_model_download(task_id: str):
    task = await CUTOUT_MODEL_MANAGER.cancel_download(task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "cutout_model_download_not_found",
                "message": "抠图模型下载任务不存在",
            },
        )
    return {"task": task}


@app.post("/api/image-tools/cutout/model/delete")
async def delete_cutout_model(req: CutoutModelActionRequest):
    _validate_cutout_model_action(req)
    try:
        result = await asyncio.to_thread(CUTOUT_MODEL_MANAGER.delete_model)
    except CutoutModelManagerError as exc:
        raise _cutout_model_manager_http_error(exc) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_model_delete_failed",
                "message": "抠图模型删除失败",
                "contract": CUTOUT_MODEL_INSTALL_CONTRACT,
                "source_id": CUTOUT_MODEL_SOURCE_ID,
            },
        ) from None
    return {"ok": True, **result}


@app.get("/api/image-tools/cutout/capabilities")
async def get_cutout_capabilities():
    # Pick up an already-imported, explicitly licensed optional MODNet
    # checkpoint without requiring a process restart.  The refresh remains
    # fail-closed: invalid manifests, missing dependencies, or a failed CPU
    # probe leave the default U2-Net capability unchanged.
    try:
        modnet_status = MODNET_IMPORT_MANAGER.status()
        if modnet_status.get("installed") and modnet_status.get("valid"):
            _refresh_modnet_registry(MODNET_IMPORT_MANAGER)
    except Exception:
        pass
    try:
        capability = CUTOUT_REGISTRY.probe()
    except Exception:
        capability = {
            "code": "cutout_capability_invalid",
            "message": "本地抠图能力状态无效",
            "contract": CUTOUT_CONTRACT,
            "available": False,
            "executable": False,
            "adapters": [],
            "state": "unavailable",
            "adapter_capabilities": [],
        }
    if not isinstance(capability, dict):
        capability = {
            "contract": CUTOUT_CONTRACT,
            "available": False,
            "executable": False,
            "adapters": [],
            "code": "cutout_capability_invalid",
            "message": "本地抠图能力状态无效",
            "state": "unavailable",
            "adapter_capabilities": [],
        }
    capability.setdefault("contract", CUTOUT_CONTRACT)
    capability.setdefault("available", False)
    capability.setdefault("executable", False)
    capability.setdefault("adapters", [])
    capability.setdefault("adapter_capabilities", [])
    capability["model"] = _cutout_model_projection(capability)
    capability["can_download"] = capability["model"].get("download_supported") is True
    if capability.get("available") is not True or capability.get("executable") is not True:
        # Keep the historical 503 fail-closed status while returning the
        # reason (missing model/dependency/session) for a guided UI.
        raise HTTPException(status_code=503, detail=capability)
    return capability


@app.post("/api/image-tools/cutout")
async def cutout_image(req: CutoutRequest):
    if req.contract != CUTOUT_CONTRACT:
        raise _generation_contract_error(
            "cutout_contract_unsupported",
            f"cutout requires contract={CUTOUT_CONTRACT}",
            field="contract",
        )
    try:
        result = await CUTOUT_REGISTRY.process_async(
            req.image_data,
            adapter=req.adapter,
            algorithm=req.algorithm,
        )
    except CutoutAdapterError as exc:
        adapter_id = str(exc.details.get("adapter") or req.adapter or CUTOUT_ADAPTER_ID)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_detail(adapter_id=adapter_id),
        ) from None
    except Exception:
        # Do not expose runtime/provider internals or write a partial result.
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_failed",
                "message": "本地抠图失败，未保存结果",
                "contract": CUTOUT_CONTRACT,
                "available": True,
                "executable": True,
                "adapters": [],
                "cancel_supported": False,
            },
        ) from None

    if not isinstance(result, dict) or not result.get("image_bytes"):
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_output_invalid",
                "message": "本地抠图未返回有效结果，未保存结果",
                "contract": CUTOUT_CONTRACT,
                "available": True,
                "executable": True,
                "adapters": [],
            },
        )

    result_adapter_id = str(result.get("adapter") or "")
    result_adapter = CUTOUT_REGISTRY.get(result_adapter_id)
    if result_adapter is None:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_output_invalid",
                "message": "本地抠图未返回有效适配器，未保存结果",
                "contract": CUTOUT_CONTRACT,
                "available": True,
                "executable": True,
                "adapters": [],
            },
        )

    expected_size = None
    if result.get("width") is not None and result.get("height") is not None:
        try:
            expected_size = (int(result["width"]), int(result["height"]))
        except (TypeError, ValueError):
            expected_size = None
    try:
        local_path = result_adapter.save_atomic(
            result["image_bytes"],
            GALLERY_DIR,
            expected_size=expected_size,
        )
    except CutoutAdapterError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.to_detail(adapter_id=result_adapter_id),
        ) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_persistence_failed",
                "message": "抠图结果保存失败，未返回不完整文件",
                "contract": CUTOUT_CONTRACT,
                "available": True,
                "executable": True,
                "adapters": [result_adapter_id],
            },
        ) from None

    encoded = base64.b64encode(bytes(result["image_bytes"])).decode("ascii")
    width_value = result.get("width")
    height_value = result.get("height")
    if width_value is None and expected_size:
        width_value = expected_size[0]
    if height_value is None and expected_size:
        height_value = expected_size[1]
    width = int(width_value or 0)
    height = int(height_value or 0)
    try:
        executable_adapters = list(CUTOUT_REGISTRY.probe().get("adapters") or [])
    except Exception:
        executable_adapters = [result_adapter_id]
    if result_adapter_id not in executable_adapters:
        executable_adapters.insert(0, result_adapter_id)

    response = {
        "contract": CUTOUT_CONTRACT,
        "success": True,
        "status": "completed",
        "source_preserved": True,
        "transparent": True,
        "preview_background": "checkerboard",
        "available": True,
        "executable": True,
        "adapters": executable_adapters,
        "adapter": result_adapter_id,
        "image_data": "data:image/png;base64," + encoded,
        "filename": Path(local_path).name,
        "gallery_url": f"/api/gallery/image/{quote(Path(local_path).name)}",
        "width": width,
        "height": height,
        "elapsed_seconds": float(result.get("elapsed_seconds") or 0.0),
        "cancel_supported": False,
    }
    if result.get("fallback_from"):
        response["fallback_from"] = str(result["fallback_from"])
    return response


@app.post("/api/image-tools/cutout/refine")
async def refine_cutout_image(req: CutoutRefineRequest):
    if req.contract != CUTOUT_REFINE_CONTRACT:
        raise _generation_contract_error(
            "cutout_refine_contract_unsupported",
            f"cutout refinement requires contract={CUTOUT_REFINE_CONTRACT}",
            field="contract",
        )

    selection_field_names = {
        "selection_mask_data",
        "selection_mask_contract",
    }
    supplied_selection_fields = selection_field_names.intersection(req.model_fields_set)
    if supplied_selection_fields and supplied_selection_fields != selection_field_names:
        raise _generation_contract_error(
            "cutout_refine_selection_fields_conflict",
            "selection mask data and contract must be supplied together",
            field="selection_mask_data",
        )
    if supplied_selection_fields and req.selection_mask_contract != CUTOUT_SELECTION_MASK_CONTRACT:
        raise _generation_contract_error(
            "cutout_refine_selection_contract_unsupported",
            f"selection mask requires contract={CUTOUT_SELECTION_MASK_CONTRACT}",
            field="selection_mask_contract",
        )
    if supplied_selection_fields and (
        not isinstance(req.selection_mask_data, str) or not req.selection_mask_data.strip()
    ):
        raise _generation_contract_error(
            "cutout_refine_selection_mask_required",
            "selection_mask_data must contain a PNG payload",
            field="selection_mask_data",
        )
    restore_field_names = {
        "restore_mode",
        "restore_source_image_data",
        "restore_min_alpha",
    }
    supplied_restore_fields = restore_field_names.intersection(req.model_fields_set)
    if supplied_restore_fields and req.restore_mode is not True and supplied_restore_fields - {"restore_mode"}:
        raise _generation_contract_error(
            "cutout_refine_restore_fields_conflict",
            "restore fields require restore_mode=true",
            field="restore_mode",
        )
    if req.restore_mode and not supplied_selection_fields:
        raise _generation_contract_error(
            "cutout_refine_restore_selection_mask_required",
            "restore_mode requires selection_mask_data and selection_mask_contract",
            field="selection_mask_data",
        )
    if req.restore_mode and (
        not isinstance(req.restore_source_image_data, str) or not req.restore_source_image_data.strip()
    ):
        raise _generation_contract_error(
            "cutout_refine_restore_source_required",
            "restore_mode requires restore_source_image_data",
            field="restore_source_image_data",
        )

    feather_radius = float(req.feather_radius)
    if not math.isfinite(feather_radius) or feather_radius < 0 or feather_radius > MAX_FEATHER_RADIUS:
        raise _generation_contract_error(
            "feather_radius_invalid",
            "feather_radius is outside the supported range",
            field="feather_radius",
            minimum=0,
            maximum=MAX_FEATHER_RADIUS,
        )

    parent_version_id = None
    if req.parent_version_id is not None:
        parent_version_id = str(req.parent_version_id).strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", parent_version_id):
            raise _generation_contract_error(
                "cutout_refine_parent_version_invalid",
                "parent_version_id must be a bounded opaque identifier",
                field="parent_version_id",
            )

    selection_mask_data = req.selection_mask_data if supplied_selection_fields else None
    try:
        result = await asyncio.to_thread(
            refine_cutout_alpha,
            req.image_data,
            selection_mask_data,
            feather_radius,
            restore_mode=req.restore_mode,
            restore_source_image_data=req.restore_source_image_data,
            restore_min_alpha=req.restore_min_alpha,
        )
    except CutoutRefineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_refine_failed",
                "message": "本地透明边缘精修失败，未保存结果",
                "contract": CUTOUT_REFINE_CONTRACT,
                "operation": "alpha_refine",
                "local_only": True,
            },
        ) from None

    if not isinstance(result, dict) or not result.get("image_bytes"):
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_refine_output_invalid",
                "message": "本地透明边缘精修未返回有效 PNG，未保存结果",
                "contract": CUTOUT_REFINE_CONTRACT,
                "operation": "alpha_refine",
                "local_only": True,
            },
        )

    try:
        width = int(result["width"])
        height = int(result["height"])
        image_bytes = bytes(result["image_bytes"])
        if width <= 0 or height <= 0 or not image_bytes:
            raise ValueError("invalid refined image result")
    except (KeyError, TypeError, ValueError, OverflowError):
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_refine_output_invalid",
                "message": "本地透明边缘精修未返回有效 PNG，未保存结果",
                "contract": CUTOUT_REFINE_CONTRACT,
                "operation": "alpha_refine",
                "local_only": True,
            },
        ) from None

    try:
        local_path = await asyncio.to_thread(
            save_refined_png_atomic,
            image_bytes,
            GALLERY_DIR,
            expected_size=(width, height),
        )
    except CutoutRefineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.to_detail()) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_refine_persistence_failed",
                "message": "透明边缘精修结果保存失败，未返回不完整文件",
                "contract": CUTOUT_REFINE_CONTRACT,
                "operation": "alpha_refine",
                "local_only": True,
            },
        ) from None

    try:
        filename = Path(local_path).name
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=500,
            detail={
                "code": "cutout_refine_persistence_failed",
                "message": "透明边缘精修结果保存失败，未返回不完整文件",
                "contract": CUTOUT_REFINE_CONTRACT,
                "operation": "alpha_refine",
                "local_only": True,
            },
        ) from None
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return {
        "contract": CUTOUT_REFINE_CONTRACT,
        "success": True,
        "status": "completed",
        "operation": "alpha_refine",
        "local_only": True,
        "source_preserved": True,
        "transparent": True,
        "preview_background": "checkerboard",
        "image_data": "data:image/png;base64," + encoded,
        "filename": filename,
        "gallery_url": f"/api/gallery/image/{quote(filename)}",
        "width": width,
        "height": height,
        "version_id": f"cutout-refine-{uuid.uuid4().hex}",
        "parent_version_id": parent_version_id,
        "restore_mode": bool(result.get("restore_mode")),
        "restore_min_alpha": result.get("restore_min_alpha"),
        "restore_applied": bool(result.get("restore_applied")),
        "selection_applied": bool(result.get("selection_applied")),
        "selection_mask_contract": (
            CUTOUT_SELECTION_MASK_CONTRACT if result.get("selection_applied") else None
        ),
        "feather_radius": float(result.get("feather_radius", feather_radius)),
        "alpha_changed": bool(result.get("alpha_changed")),
        "alpha_extrema": list(result.get("alpha_extrema") or []),
    }


@app.post("/api/generate")
async def generate(req: GenerateRequest, request: Request):
    global generation_counter, image_gen_semaphore
    generation_input = _validate_generation_request_inputs(req)
    mode = generation_input["mode"]

    if image_gen_semaphore is None:
        image_gen_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)

    # 速率限制
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip, "generate"):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    # 确定要调用的 Provider 列表
    if req.providers:
        provider_ids = list(dict.fromkeys(req.providers))
    else:
        provider_ids = [p.id for p in cfg_mgr.get_image_providers()]

    if not provider_ids:
        raise HTTPException(status_code=400, detail="无可用的生图模型，请先在设置中配置")

    all_providers = {p.id: p for p in cfg_mgr.config.providers}
    if mode == "inpaint":
        _validate_inpaint_provider_authorization(provider_ids, all_providers)
    elif mode == "precision_edit":
        _validate_precision_edit_provider_authorization(
            provider_ids,
            all_providers,
            req.provider_settings,
        )
        _validate_precision_edit_size_authorization(
            provider_ids,
            all_providers,
            req.provider_settings,
            generation_input,
        )

    generation_counter += 1
    gen_id = f"gen_{generation_counter:04d}_{uuid.uuid4().hex[:6]}"
    precision_workflow = (
        await asyncio.to_thread(_prepare_precision_workflow_metadata, generation_input)
        if mode == "precision_edit"
        else None
    )

    # LLM 优化提示词（仅对文生图模式）
    original_prompt = req.prompt
    enhanced_by_llm = None
    llm_error_msg = None
    if req.enhance_prompt and mode == "t2i":
        enhanced_by_llm = await enhance_prompt_with_llm(req.prompt, req.llm_provider_id)
        if enhanced_by_llm == req.prompt:
            # LLM 未配置或调用失败（返回了原始 prompt）
            llm_error_msg = "LLM 优化未生效，请检查 Provider 配置"

    # 构建参数
    kwargs = {}
    if req.size: kwargs["size"] = req.size
    if req.quality: kwargs["quality"] = req.quality
    kwargs["exact_ratio_crop"] = req.exact_ratio_crop
    if mode == "i2i":
        image_list = [item["value"] for item in generation_input["images"]]
        kwargs["mode"] = mode
        kwargs["image_data"] = image_list[0]
        kwargs["image_data_list"] = image_list
        kwargs["strength"] = req.strength
    elif mode == "inpaint":
        kwargs.update({
            "mode": mode,
            "image_data": generation_input["images"][0]["value"],
            "mask_data": generation_input["mask"]["value"],
            "mask_contract": INPAINT_MASK_CONTRACT,
            "inpaint_authorized": True,
        })
    elif mode == "precision_edit":
        kwargs.update({
            "mode": mode,
            "image_data": generation_input["images"][0]["value"],
            "precision_canvas_only": generation_input["precision_canvas_only"],
            "precision_strategy": generation_input["precision_strategy"],
            "precision_selection_mode": generation_input["precision_selection_mode"],
            "precision_size_mode": generation_input["precision_size_mode"],
            "precision_target_size": generation_input["precision_target_size"],
            "precision_resize_prompt": generation_input["precision_resize_prompt"],
            "precision_edit_authorized": True,
        })
        if generation_input["precision_selection_mode"] == "local":
            kwargs["precision_selection_feather"] = generation_input["precision_selection_feather"]
        if generation_input["precision_size_mode"] == "resize":
            kwargs["precision_output_size_policy"] = generation_input[
                "precision_output_size_policy"
            ]
        if not generation_input["precision_canvas_only"]:
            kwargs.update({
                "annotation_image_data": generation_input["annotation_image"]["value"],
                "annotation_contract": generation_input["annotation_contract"],
                "annotations": generation_input["annotations"],
            })

    # 构建任务列表 (pid, seq, qty) + per-provider kwargs
    task_list = []
    provider_kwargs_map = {}  # {pid: kwargs} per-provider overrides
    for pid in provider_ids:
        raw_qty = req.quantities.get(pid, 1) if req.quantities else 1
        qty = _normalize_generation_quantity(raw_qty)
        # 为每个 provider 构建独立的 kwargs
        p_kwargs = dict(kwargs)  # 复制全局 kwargs
        p_setting = req.provider_settings.get(pid, {}) if isinstance(req.provider_settings, dict) else {}
        if not isinstance(p_setting, dict):
            p_setting = {}
        if p_setting.get("size"):
            p_kwargs["size"] = p_setting["size"]
        if p_setting.get("quality"):
            p_kwargs["quality"] = p_setting["quality"]
        if mode == "precision_edit":
            p_kwargs["model"] = str(p_setting["model"]).strip()
        provider_kwargs_map[pid] = p_kwargs
        for seq in range(qty):
            if pid in all_providers:
                task_list.append((pid, seq, qty))

    # 初始化任务状态
    provider_states = {}
    for pid, seq, qty in task_list:
        key = f"{pid}_{seq}" if qty > 1 else pid
        prov_obj = all_providers.get(pid)
        provider_states[key] = {
            "status": "queued",
            "progress": 0,
            "model": pid,
            "name": prov_obj.name if prov_obj else pid,
            "color": prov_obj.color if prov_obj else "#5b8def",
            "seq": seq,
            "qty": qty,
            "log": ["[系统] 排队中..."],
            "result": None,
        }

    image_tasks[gen_id] = {
        "status": "queued",
        "progress": 0,
        "mode": mode,
        "prompt": req.prompt,
        "enhanced_prompt": enhanced_by_llm,
        "llm_error": llm_error_msg,
        "providers": provider_ids,
        "provider_states": provider_states,
        "task_list": task_list,
        "task_index": 0,
        "all_providers": {pid: all_providers[pid] for pid in provider_ids if pid in all_providers},
        "kwargs": kwargs,
        "provider_kwargs_map": provider_kwargs_map,  # per-provider 参数覆盖
        "start_time": time.time(),
        "results": {},
        "continuous": req.continuous,
        "continuous_id": req.continuous_id,
        "system_prompt": req.system_prompt,
        "original_prompt": req.prompt,
        "precision_workflow": precision_workflow,
        # ── 尺寸自适应 ──
        "upscale_to": req.upscale_to,
        "upscale_method": req.upscale_method,
        "upscale_ratio": req.upscale_ratio,
    }

    # 后台处理
    image_task_handles[gen_id] = asyncio.create_task(_process_image_gen(gen_id))

    _write_log("generate", f"生图任务已创建: {gen_id}, {len(task_list)} 个子任务", {"gen_id": gen_id, "providers": provider_ids})

    # 返回 provider_states 让前端立即创建占位卡片
    provider_states_out = {}
    for key, st in provider_states.items():
        provider_states_out[key] = {
            "status": st["status"],
            "progress": st["progress"],
            "name": st.get("name", key),
            "log": st["log"][-3:] if st["log"] else [],
        }

    return {"generation_id": gen_id, "status": "queued", "provider_states": provider_states_out}


async def _process_image_gen(gen_id: str):
    try:
        await _process_image_gen_impl(gen_id)
    except asyncio.CancelledError:
        _mark_image_task_cancelled(gen_id)
        return
    finally:
        _cleanup_image_task_handle(gen_id, asyncio.current_task())


async def _process_image_gen_impl(gen_id: str):
    """后台逐个处理生图任务（带并发控制）"""
    global image_gen_semaphore
    task = image_tasks.get(gen_id)
    if not task:
        return

    if task.get("status") == "cancelled":
        return

    task["status"] = "generating"
    task["start_time"] = time.time()

    from providers import generate_for_provider as _gen_one

    async def _run_one(key, pid, seq, p_cfg, prompt, kwargs):
        if task.get("status") == "cancelled":
            return
        t0 = time.time()
        state = task["provider_states"][key]
        state["status"] = "generating"
        state["progress"] = 10
        state["log"].append(f"[{time.strftime('%H:%M:%S')}] ▸ 开始生成 - 模型: {p_cfg.name or pid}")

        # 后台递增进度（10% → 90%）
        async def _tick_progress():
            while state["status"] == "generating":
                await asyncio.sleep(2)
                if state["status"] == "generating":
                    elapsed = time.time() - t0
                    state["progress"] = min(90, 10 + int(elapsed / 60 * 80))

        tick_task = asyncio.create_task(_tick_progress())
        try:
            res = await _gen_one(p_cfg, prompt, **kwargs)
            if task.get("status") == "cancelled":
                state["status"] = "cancelled"
                state["progress"] = 0
                state["log"].append(f"[{time.strftime('%H:%M:%S')}] ■ 已停止")
                return
            t1 = time.time()
            res.elapsed_seconds = round(t1 - t0, 1)
            res.started_at = t0
            res.finished_at = t1

            # ── 尺寸自适应：生成后本地放大 ──
            if res.success and res.local_path and task.get("upscale_to"):
                try:
                    state["log"].append(f"[{time.strftime('%H:%M:%S')}] ⤢ 正在本地放大到 {task['upscale_to']} ({task.get('upscale_ratio', 'original')})...")
                    _upscaled = _do_local_upscale(
                        res.local_path, 
                        task["upscale_to"], 
                        task.get("upscale_method", "lanczos3"),
                        task.get("upscale_ratio", "original")
                    )
                    if _upscaled:
                        res.local_path = _upscaled
                        state["log"].append(f"[{time.strftime('%H:%M:%S')}] ✔ 放大完成")
                except Exception as ue:
                    upscale_error = _background_generation_error_text(ue, p_cfg)
                    state["log"].append(f"[{time.strftime('%H:%M:%S')}] ⚠ 放大失败(保留原图): {upscale_error[:80]}")

            if res.success:
                for warning in getattr(res, "warnings", None) or []:
                    warning_code = str(warning.get("code") or "generation_warning")[:80]
                    warning_message = str(warning.get("message") or "")[:240]
                    state["log"].append(
                        f"[{time.strftime('%H:%M:%S')}] ⚠ {warning_code}: {warning_message}"
                    )
                state["status"] = "completed"
                state["progress"] = 100
                state["log"].append(f"[{time.strftime('%H:%M:%S')}] ✔ 完成 ({res.elapsed_seconds}s)")
            else:
                error_text = _background_generation_error_text(res.error, p_cfg)
                res.error = error_text
                state["status"] = "failed"
                state["progress"] = _image_state_progress(state)
                state["log"].append(f"[{time.strftime('%H:%M:%S')}] ✗ 失败: {error_text[:120]}")
                # 写入详细错误日志到 logs.jsonl
                _write_log("generation_error", f"{pid} 失败: {error_text[:200]}", {
                    "provider_id": pid,
                    "model": (p_cfg.model if p_cfg else pid),
                    "error": error_text[:500],
                    "mode": task.get("mode", "t2i"),
                    "elapsed_seconds": res.elapsed_seconds,
                })

            state["result"] = {
                "success": res.success,
                "local_path": res.local_path,
                "generation_id": res.generation_id,
                "error": res.error,
                "error_code": getattr(res, "error_code", "") or None,
                "error_details": getattr(res, "error_details", None),
                "metadata": getattr(res, "metadata", None),
                "warnings": getattr(res, "warnings", None) or [],
                "model": pid,
                "prompt": prompt,
                "original_prompt": task["original_prompt"],
                "seq": seq,
                "elapsed_seconds": res.elapsed_seconds,
                "started_at": t0,
                "finished_at": t1,
            }
            task["results"][key] = state["result"]
        except Exception as e:
            t1 = time.time()
            error_text = _background_generation_error_text(e, p_cfg)
            state["status"] = "failed"
            state["progress"] = _image_state_progress(state)
            state["log"].append(f"[{time.strftime('%H:%M:%S')}] ✗ 异常: {error_text[:120]}")
            _write_log("generation_error", f"{pid} 异常: {error_text[:200]}", {
                "provider_id": pid,
                "model": (p_cfg.model if p_cfg else pid),
                "error": error_text[:500],
                "mode": task.get("mode", "t2i"),
                "elapsed_seconds": round(t1 - t0, 1),
            })
            state["result"] = {
                "success": False, "local_path": None, "generation_id": None,
                "error": error_text, "model": pid, "prompt": prompt,
                "error_code": None, "error_details": None,
                "metadata": None, "warnings": [],
                "original_prompt": task["original_prompt"], "seq": seq,
                "elapsed_seconds": round(t1 - t0, 1), "started_at": t0, "finished_at": t1,
            }
            task["results"][key] = state["result"]
        finally:
            tick_task.cancel()
            try:
                await tick_task
            except asyncio.CancelledError:
                pass

    # 按 provider 分组，不同 provider 并行执行
    provider_tasks = {}
    for pid, seq, qty in task["task_list"]:
        if pid not in provider_tasks:
            provider_tasks[pid] = []
        provider_tasks[pid].append((pid, seq, qty))

    async def _run_provider_group(pid, items):
        for i, (p, s, q) in enumerate(items):
            if task.get("status") == "cancelled":
                return
            if i > 0:
                await asyncio.sleep(1.5)
            key = f"{p}_{s}" if q > 1 else p
            p_cfg = task["all_providers"].get(p)
            if p_cfg:
                p_kwargs = task.get("provider_kwargs_map", {}).get(p, task["kwargs"])
                await _run_one(key, p, s, p_cfg, task["enhanced_prompt"] or task["prompt"], p_kwargs)

    await asyncio.gather(*[_run_provider_group(pid, items) for pid, items in provider_tasks.items()])

    if task.get("status") == "cancelled":
        return

    # 全部子任务结束；部分成功仍可交付结果，全失败则明确失败。
    elapsed = round(time.time() - task["start_time"], 1)
    task["status"] = _image_task_status(task.get("status", "generating"), task["provider_states"])
    task["progress"] = _image_task_progress(task["provider_states"], task["status"])
    task["elapsed_seconds"] = elapsed

    # 计算分组耗时
    group_timings = {}
    for key, res in task["results"].items():
        pid = res["model"]
        if pid not in group_timings:
            group_timings[pid] = {"total": 0.0, "images": []}
        group_timings[pid]["images"].append({"seq": res["seq"], "elapsed": res["elapsed_seconds"], "success": res["success"]})
    for g in group_timings.values():
        g["total"] = round(sum(img["elapsed"] for img in g["images"]), 1)

    # 连续生图
    if task.get("continuous"):
        cid = task.get("continuous_id") or str(uuid.uuid4())[:8]
        if cid not in continuous_sessions:
            continuous_sessions[cid] = {"images": [], "prompts": [], "context": ""}
        continuous_sessions[cid]["prompts"].append(task["prompt"])
        continuous_sessions[cid]["prompts"] = continuous_sessions[cid]["prompts"][-3:]
        for key, res in task["results"].items():
            if res["success"] and res["local_path"]:
                continuous_sessions[cid]["images"].append(res["local_path"])
        continuous_sessions[cid]["images"] = continuous_sessions[cid]["images"][-12:]
        continuous_sessions[cid]["context"] = " | ".join(continuous_sessions[cid]["prompts"])
        task["continuous_id"] = cid

    # 记录历史
    history_entry = {
        "generation_id": gen_id,
        "prompt": task["prompt"],
        "system_prompt": task.get("system_prompt"),
        "enhanced_prompt": task.get("enhanced_prompt"),
        "mode": task["mode"],
        "providers": task["providers"],
        "results": task["results"],
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "continuous": task.get("continuous"),
        "continuous_id": task.get("continuous_id"),
        "elapsed_seconds": elapsed,
        "group_timings": group_timings,
    }
    if task["mode"] == "precision_edit":
        history_entry["precision_workflow"] = _finalize_precision_workflow_metadata(task)
    generation_history[gen_id] = history_entry
    _save_history_entry(history_entry)

    ok_count = sum(1 for r in task["results"].values() if r.get("success"))
    _write_log("generate", f"生图完成: {ok_count}/{len(task['providers'])} 成功 ({elapsed}s)", {"gen_id": gen_id})


@app.get("/api/generate/status/{gen_id}")
async def get_generate_status(gen_id: str):
    task = image_tasks.get(gen_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 计算整体进度（每个 provider 的真实进度/耗时估算平均值）
    states = task["provider_states"]
    status = _refresh_image_task_state(task)
    progress = task["progress"]

    elapsed = _image_task_elapsed(task)

    # 构建响应（不含 all_providers 大对象）
    provider_states_out = {}
    for k, v in states.items():
        provider_states_out[k] = {
            "status": v["status"],
            "progress": v["progress"],
            "model": v["model"],
            "name": v["name"],
            "color": v["color"],
            "seq": v["seq"],
            "qty": v["qty"],
            "log": v["log"],
            "result": v["result"],
        }

    return {
        "generation_id": gen_id,
        "status": status,
        "progress": progress,
        "elapsed_seconds": elapsed,
        "provider_states": provider_states_out,
        "enhanced_prompt": task.get("enhanced_prompt"),
        "llm_error": task.get("llm_error"),
        "continuous_id": task.get("continuous_id"),
        # Only terminal tasks may deliver provider results. Every terminal
        # outcome keeps its real result/error and timing projection, including
        # failed and cancelled tasks with partial success.
        "results": task["results"] if status in ("completed", "failed", "cancelled") else {},
        "group_timings": {pid: {"total": round(sum(img["elapsed"] for img in imgs), 1), "images": imgs}
                          for pid, imgs in _calc_group_timings(task["results"]).items()}
                          if status in ("completed", "failed", "cancelled") else {},
    }


@app.post("/api/generate/cancel/{gen_id}")
async def cancel_generate(gen_id: str):
    task = image_tasks.get(gen_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    status = _refresh_image_task_state(task)
    if status in ("completed", "failed", "cancelled"):
        return {"ok": True, "status": status}
    status = _mark_image_task_cancelled(gen_id)
    if status != "cancelled":
        return {"ok": True, "status": status}
    handle = image_task_handles.get(gen_id)
    if handle:
        if not handle.done():
            handle.cancel()
        _cleanup_image_task_handle(gen_id, handle)
    _write_log("generate", f"生图任务已取消: {gen_id}", {"gen_id": gen_id})
    return {"ok": True, "status": status}


class LLMOptimizeRequest(BaseModel):
    prompt: str
    llm_provider_id: Optional[str] = None


# ──────────────────────────────────────────────────────────────
# 图片变形 (Variations) — 移植自 4K Image API
# ──────────────────────────────────────────────────────────────
class VariationRequest(BaseModel):
    image_data: str                  # base64 data URL
    provider_id: str = ""            # 空=第一个支持的 provider
    model: str = ""                  # 可选：指定模型
    size: str = "1024x1024"          # 256x256 | 512x512 | 1024x1024
    n: int = Field(default=1, ge=1, le=4)  # 生成数量 1-4


@app.post("/api/images/variations")
async def image_variations(req: VariationRequest):
    """图片变形：基于输入图片生成变体（OpenAI /images/variations 协议）"""
    import httpx as _httpx

    source_image = _validate_generation_image_data(req.image_data, "image_data")
    source_value = source_image["value"]
    source_encoded = (
        source_value.partition(",")[2]
        if source_value.lower().startswith("data:")
        else source_value
    )
    img_bytes = base64.b64decode(source_encoded, validate=True)
    source_mime = source_image["mime_type"]
    source_filename = {
        "image/png": "image.png",
        "image/jpeg": "image.jpg",
        "image/webp": "image.webp",
    }[source_mime]

    # 找到可用 provider
    provider = None
    if req.provider_id:
        for p in cfg_mgr.config.providers:
            if p.id == req.provider_id and p.type == "image":
                provider = p
                break
    else:
        for p in cfg_mgr.get_image_providers():
            provider = p
            break
    if not provider:
        raise HTTPException(status_code=400, detail="无可用的生图 Provider")

    model_id = req.model or provider.model or "gpt-image-2"

    # 支持多端点 failover
    endpoints = provider.get_active_endpoints()
    endpoint_failures = []
    result = None
    last_response_validation = None

    for endpoint_index, ep in enumerate(endpoints, start=1):
        url = f"{ep.url.rstrip('/')}/images/variations"
        headers = {"Authorization": f"Bearer {ep.key}"}
        files = {"image": (source_filename, img_bytes, source_mime)}
        data = {"model": model_id, "n": req.n, "size": req.size, "response_format": "b64_json"}

        try:
            async with _httpx.AsyncClient(
                timeout=180.0,
                verify=verify_ssl_enabled(),
            ) as client:
                resp = await _stream_bounded_provider_response(
                    client,
                    "POST",
                    url,
                    response_image_count=req.n,
                    headers=headers,
                    files=files,
                    data=data,
                )
                if resp.status_code >= 400:
                    response_detail = _provider_error_text(
                        getattr(resp, "text", ""),
                        provider,
                    ).strip()[:240]
                    failure = f"HTTP {resp.status_code}"
                    if response_detail:
                        failure += f": {response_detail}"
                    endpoint_failures.append((endpoint_index, ep, failure))
                    continue  # 尝试下一个端点
                result = _parse_provider_json_response(resp)
                break  # 成功
        except ProviderResponseValidationError as exc:
            last_response_validation = exc
            endpoint_failures.append((endpoint_index, ep, f"{exc.code}: {exc}"))
            continue
        except Exception as exc:
            endpoint_failures.append(
                (
                    endpoint_index,
                    ep,
                    _provider_error_text(exc, provider).strip() or type(exc).__name__,
                )
            )
            continue  # 尝试下一个端点
    else:
        if last_response_validation is not None:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "image_variation_invalid_response",
                    "message": "variation provider returned an invalid response",
                    "validation_code": last_response_validation.code,
                    **last_response_validation.details,
                },
            )
        raise HTTPException(
            status_code=502,
            detail={
                "code": "image_variation_upstream_error",
                "message": "all variation provider endpoints failed",
                "upstream_error": _endpoint_failure_summary(provider, endpoint_failures),
            },
        )

    response_validation_details = {}
    if not isinstance(result, dict):
        response_validation_code = "variation_response_not_object"
    elif not isinstance(result.get("data"), list):
        response_validation_code = "variation_response_data_invalid"
    elif len(result["data"]) != req.n:
        response_validation_code = "variation_response_item_count_mismatch"
        response_validation_details = {
            "requested_count": req.n,
            "actual_count": len(result["data"]),
        }
    else:
        response_validation_code = ""
        for item in result["data"]:
            if not isinstance(item, dict):
                response_validation_code = "variation_response_item_invalid"
                break
            if not isinstance(item.get("b64_json"), str) or not item["b64_json"].strip():
                response_validation_code = "variation_response_image_missing"
                break
    if response_validation_code:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "image_variation_invalid_response",
                "message": "variation provider returned an invalid response",
                "validation_code": response_validation_code,
                **response_validation_details,
            },
        )

    images_out = []
    for item in result["data"]:
        b64_data = item["b64_json"]
        try:
            raw = _decode_generated_image_base64(b64_data)
            local_path = _save_image(raw, provider.id, "variation", "")
        except GeneratedImageValidationError as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "image_variation_invalid_response",
                    "message": "variation provider returned an invalid image",
                    "validation_code": exc.code,
                },
            ) from None
        images_out.append({"b64_json": b64_data, "local_path": local_path, "provider_id": provider.id})

    return {"success": True, "images": images_out, "model": model_id, "provider_id": provider.id}


# ──────────────────────────────────────────────────────────────
# 图片缩放/超分 — 移植自 4K Image API Lanczos3 Processor
# ──────────────────────────────────────────────────────────────
class UpscaleRequest(BaseModel):
    image_data: str                  # base64 data URL
    target_width: int = 2048         # 目标宽度
    target_height: int = 2048        # 目标高度
    method: str = "lanczos3"         # lanczos3 | bicubic | nearest


@app.post("/api/images/upscale")
async def image_upscale(req: UpscaleRequest):
    """本地图片缩放（Lanczos3 / Bicubic / Nearest），无需外部 API"""
    import base64 as _b64
    from PIL import Image as _PILImage
    import io

    # 解析图片
    if "," in req.image_data:
        img_b64 = req.image_data.split(",")[1]
    else:
        img_b64 = req.image_data
    try:
        img_bytes = _b64.b64decode(img_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="图片数据无效")

    try:
        img = _PILImage.open(io.BytesIO(img_bytes))
    except Exception:
        raise HTTPException(status_code=400, detail="无法解析图片格式")

    orig_w, orig_h = img.size

    # 如果目标尺寸比原图小，不缩放（只放大不缩小）
    if req.target_width <= orig_w and req.target_height <= orig_h:
        return {"success": True, "width": orig_w, "height": orig_h, "message": "原图已满足目标尺寸"}

    # 等比缩放到目标尺寸内
    scale = min(req.target_width / orig_w, req.target_height / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    # 选择插值方法
    resample_map = {
        "lanczos3": _PILImage.LANCZOS,
        "bicubic": _PILImage.BICUBIC,
        "nearest": _PILImage.NEAREST,
    }
    resample = resample_map.get(req.method, _PILImage.LANCZOS)

    try:
        upscaled = img.resize((new_w, new_h), resample)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"缩放失败: {str(e)[:100]}")

    # 保存为 PNG
    buf = io.BytesIO()
    upscaled.save(buf, format="PNG", quality=95)
    out_bytes = buf.getvalue()
    out_b64 = _b64.b64encode(out_bytes).decode()

    return {
        "success": True,
        "width": new_w,
        "height": new_h,
        "original_width": orig_w,
        "original_height": orig_h,
        "b64_json": out_b64,
        "message": f"已从 {orig_w}x{orig_h} 放大到 {new_w}x{new_h} ({req.method})",
    }


class LLMOptimizeRequest(BaseModel):
    prompt: str
    llm_provider_id: Optional[str] = None


@app.post("/api/llm/optimize")
async def llm_optimize(req: LLMOptimizeRequest):
    """独立的 LLM 提示词优化端点（不触发图片生成）"""
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="提示词不能为空")
    result = await enhance_prompt_with_llm_detailed(req.prompt, req.llm_provider_id)
    return {
        "original": req.prompt,
        "optimized": result["text"],
        "optimized_by_llm": result["optimized"],
        "error": result["error"],
        "provider": result["provider"],
    }


def _calc_group_timings(results):
    gt = {}
    for key, res in results.items():
        pid = res["model"]
        if pid not in gt:
            gt[pid] = []
        gt[pid].append({"seq": res["seq"], "elapsed": res["elapsed_seconds"], "success": res["success"]})
    return gt


# ──────────────────────────────────────────────────────────────
# 图库 & 历史
# ──────────────────────────────────────────────────────────────
@app.get("/api/gallery")
async def gallery(limit: int = 50):
    items = _scan_gallery(limit)
    return {"items": items, "total": len(items)}


@app.get("/api/gallery/thumb/{filename}")
async def thumbnail(filename: str, request: Request):
    payload, mime_type = await asyncio.to_thread(_load_thumbnail_image_payload, filename)
    return _memory_media_response(request, payload, mime_type)


@app.get("/api/gallery/image/{filename}")
async def gallery_image(filename: str, request: Request):
    _fpath, payload, mime_type, _prompt = await asyncio.to_thread(
        _load_gallery_image_payload,
        filename,
    )
    return _memory_media_response(request, payload, mime_type)


@app.delete("/api/gallery/{item_id}")
async def delete_gallery_item(item_id: str):
    for f in GALLERY_DIR.glob("*.png"):
        if item_id in f.stem:
            f.unlink()
            _write_log("delete", f"删除图片: {f.name}", {"id": item_id})
            return {"deleted": True, "id": item_id}
    raise HTTPException(status_code=404, detail="图片不存在")


@app.post("/api/gallery/batch-delete")
async def batch_delete_gallery(items: List[str] = []):
    """批量删除图库图片和视频（按 stem 列表）"""
    deleted = []
    failed = []
    VIDEO_DIR = STORAGE_DIR / "videos"
    
    for item_id in items:
        found = False
        # 搜索图片
        for f in GALLERY_DIR.glob("*.png"):
            if item_id in f.stem:
                try:
                    f.unlink()
                    deleted.append(item_id)
                except Exception as e:
                    failed.append({"id": item_id, "error": str(e)})
                found = True
                break
        # 搜索视频
        if not found and VIDEO_DIR.exists():
            for f in VIDEO_DIR.glob("*.mp4"):
                if item_id in f.stem:
                    try:
                        f.unlink()
                        # 删除元数据缓存
                        meta_file = f.with_suffix(f.suffix + ".json")
                        if meta_file.exists():
                            meta_file.unlink()
                        deleted.append(item_id)
                    except Exception as e:
                        failed.append({"id": item_id, "error": str(e)})
                    found = True
                    break
        if not found:
            failed.append({"id": item_id, "error": "not found"})
    
    _write_log("delete", f"批量删除: {len(deleted)} 个文件", {"deleted": deleted, "failed": len(failed)})
    return {"deleted": deleted, "failed": failed, "total_deleted": len(deleted)}
@app.get("/api/gallery/video-info/{item_id}")
async def get_video_info(item_id: str):
    """获取视频元数据（时长、尺寸），结果缓存到 .json 文件"""
    import subprocess
    import json as json_lib
    
    VIDEO_DIR = Path(GALLERY_DIR).parent / "videos"
    
    # 查找视频文件
    video_path = None
    for f in VIDEO_DIR.glob("*"):
        if item_id in f.stem and f.suffix in [".mp4", ".webm", ".mov"]:
            video_path = f
            break
    
    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")
    
    info_path = video_path.with_suffix(video_path.suffix + ".json")
    
    # 尝试读取缓存
    if info_path.exists():
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                return json_lib.loads(f.read())
        except:
            pass
    
    # 调用 ffprobe
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=10)
        if result.returncode == 0:
            info = json_lib.loads(result.stdout)
            duration = info.get("format", {}).get("duration")
            if duration:
                duration = round(float(duration), 1)
            
            video_stream = None
            for stream in info.get("streams", []):
                if stream.get("codec_type") == "video":
                    video_stream = stream
                    break
            
            width = video_stream.get("width") if video_stream else None
            height = video_stream.get("height") if video_stream else None
            
            metadata = {
                "duration": duration,
                "width": width,
                "height": height,
                "size_bytes": video_path.stat().st_size,
            }
            
            # 缓存到 JSON
            with open(info_path, "w", encoding="utf-8") as f:
                f.write(json_lib.dumps(metadata, ensure_ascii=False, indent=2))
            
            return metadata
    except Exception as e:
        pass
    
    return {"duration": None, "width": None, "height": None}





@app.post("/api/gallery/batch-download")
async def batch_download_gallery(items: List[str] = []):
    """批量下载图库图片为 ZIP 文件（按 stem 列表）"""
    import zipfile, io
    from fastapi.responses import Response
    
    buf = io.BytesIO()
    files_found = 0
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for item_id in items:
            for f in GALLERY_DIR.glob("*.png"):
                if item_id in f.stem:
                    zf.write(f, f.name)
                    files_found += 1
                    break
    
    if files_found == 0:
        raise HTTPException(status_code=404, detail="No matching images found")
    
    buf.seek(0)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="image_gen_studio_{ts}.zip"'}
    )


@app.post("/api/gallery/rename")
async def rename_gallery_item(body: dict = {}):
    """重命名图库图片（修改文件名）"""
    old_id = body.get("old_id", "")
    new_name = body.get("new_name", "")
    if not old_id or not new_name:
        raise HTTPException(status_code=400, detail="old_id 和 new_name 必填")
    # 安全: 只允许字母数字下划线中文
    import re
    if not re.match(r'^[\w\u4e00-\u9fff]+$', new_name):
        raise HTTPException(status_code=400, detail="名称只允许字母、数字、下划线和中文")
    for f in GALLERY_DIR.glob("*.png"):
        if old_id in f.stem:
            # 保留时间戳后缀: model_20260617_211120_xxx -> newname_20260617_211120_xxx
            parts = f.stem.split('_', 1)
            suffix = "_" + parts[1] if len(parts) > 1 else ""
            new_stem = f"{new_name}{suffix}"
            new_path = GALLERY_DIR / (new_stem + f.suffix)
            if new_path.exists():
                raise HTTPException(status_code=409, detail="目标文件名已存在")
            f.rename(new_path)
            _write_log("gallery", f"重命名图片: {f.name} → {new_path.name}")
            return {"ok": True, "old_id": old_id, "new_id": new_stem, "new_name": new_name}
    raise HTTPException(status_code=404, detail="图片不存在")


@app.get("/api/gallery/image/{filename}/base64")
async def gallery_image_base64(filename: str):
    """返回图片的 base64 数据，用于推送到参考图区域"""
    import base64 as _b64
    _fpath, payload, mime_type, _prompt = await asyncio.to_thread(
        _load_gallery_image_payload,
        filename,
    )
    data = _b64.b64encode(payload).decode()
    return {"filename": filename, "data": f"data:{mime_type};base64,{data}"}


@app.get("/api/precision/workflows")
async def precision_workflows(
    date_from: str = "",
    date_to: str = "",
    workflow_id: str = "",
    limit: int = 50,
):
    """Return a prompt-free, path-free projection of persisted precision edits."""
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=422,
            detail={"code": "precision_workflow_limit_invalid", "field": "limit"},
        )
    normalized_from = _precision_filter_date(date_from, "date_from")
    normalized_to = _precision_filter_date(date_to, "date_to")
    if normalized_from and normalized_to and normalized_from > normalized_to:
        raise HTTPException(
            status_code=422,
            detail={"code": "precision_workflow_date_range_invalid"},
        )
    if workflow_id and not PRECISION_WORKFLOW_ID_RE.fullmatch(workflow_id):
        raise HTTPException(
            status_code=422,
            detail={"code": "precision_workflow_id_invalid", "field": "workflow_id"},
        )

    items, _file_index = await asyncio.to_thread(_precision_workflow_projection_data)
    if workflow_id:
        items = [item for item in items if item["workflow_id"] == workflow_id]
    if normalized_from or normalized_to:
        items = [
            item
            for item in items
            if any(
                (not normalized_from or version["created_at"][:10] >= normalized_from)
                and (not normalized_to or version["created_at"][:10] <= normalized_to)
                for version in item["versions"]
                if version.get("created_at")
            )
        ]
    return {"items": items[:limit], "total": len(items)}


@app.get("/api/precision/workflows/{workflow_id}")
async def precision_workflow(workflow_id: str):
    workflow_id = _precision_validate_workflow_id(workflow_id)
    items, _file_index = await asyncio.to_thread(
        _precision_workflow_projection_data,
        include_annotation_snapshots=True,
    )
    for item in items:
        if item["workflow_id"] == workflow_id:
            return {"workflow": item}
    raise HTTPException(status_code=404, detail="工作流不存在")


def _precision_workflow_version_filename(workflow_id: str, version_id: str) -> str:
    workflow_id = _precision_validate_workflow_id(workflow_id)
    if version_id != "original" and not PRECISION_VERSION_ID_RE.fullmatch(str(version_id or "")):
        raise HTTPException(status_code=404, detail="工作流版本不存在")
    _items, file_index = _precision_workflow_projection_data()
    filename = file_index.get((workflow_id, version_id))
    if not filename:
        raise HTTPException(status_code=404, detail="工作流版本不存在")
    return filename


def _load_precision_workflow_media(filename: str, *, thumbnail: bool) -> tuple[bytes, str]:
    """Re-encode gallery pixels so PNG prompt metadata never crosses this API."""
    _path, payload, _mime_type, _prompt = _load_gallery_image_payload(filename)
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.load()
            image = source.copy()
        try:
            image.info.clear()
            if thumbnail:
                image.thumbnail((320, 320), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue(), "image/png"
        finally:
            image.close()
    except Exception:
        raise HTTPException(
            status_code=415,
            detail={
                "code": "precision_workflow_image_invalid",
                "message": "workflow image is not readable",
            },
        ) from None


@app.get("/api/precision/workflows/{workflow_id}/versions/{version_id}/thumb")
async def precision_workflow_thumbnail(workflow_id: str, version_id: str, request: Request):
    filename = await asyncio.to_thread(
        _precision_workflow_version_filename,
        workflow_id,
        version_id,
    )
    payload, mime_type = await asyncio.to_thread(
        _load_precision_workflow_media,
        filename,
        thumbnail=True,
    )
    return _memory_media_response(request, payload, mime_type)


@app.get("/api/precision/workflows/{workflow_id}/versions/{version_id}/image")
async def precision_workflow_image(workflow_id: str, version_id: str, request: Request):
    filename = await asyncio.to_thread(
        _precision_workflow_version_filename,
        workflow_id,
        version_id,
    )
    payload, mime_type = await asyncio.to_thread(
        _load_precision_workflow_media,
        filename,
        thumbnail=False,
    )
    return _memory_media_response(request, payload, mime_type)


@app.get("/api/history")
async def history(limit: int = 30, search: str = "", provider: str = "", mode: str = "", type: str = ""):
    """查询历史记录，支持图片和视频。type=image|video|'' (全部)"""
    items = []
    
    # 图片历史
    for h in generation_history.values():
        if type and type != "image": continue
        items.append({**h, "type": "image"})
    
    # 视频历史
    if 'video_tasks' in globals():
        for task_id, task in video_tasks.items():
            if type and type != "video": continue
            if task.get("status") in ["completed", "failed", "error", "cancelled"]:
                items.append({
                    "generation_id": task_id,
                    "type": "video",
                    "prompt": task.get("prompt", ""),
                    "providers": [task.get("provider_id", "unknown")],
                    "mode": task.get("mode", "t2vid"),
                    "results": {
                        task.get("provider_id", "video"): {
                            "success": task.get("status") == "completed",
                            "local_path": task.get("local_path"),
                            "video_url": task.get("video_url"),
                        }
                    },
                    "created_at": task.get("created_at", ""),
                    "status": task.get("status"),
                    "error": task.get("error"),
                })
    
    # 搜索: 按提示词关键词
    if search:
        search_lower = search.lower()
        items = [h for h in items if search_lower in (h.get("prompt", "") + h.get("enhanced_prompt", "")).lower()]
    # 筛选: 按Provider
    if provider:
        items = [h for h in items if provider in h.get("providers", [])]
    # 筛选: 按模式
    if mode:
        items = [h for h in items if h.get("mode", "t2i") == mode]
    # 默认按时间倒序
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"items": items[:limit]}


# ──────────────────────────────────────────────────────────────
# 日志系统
# ──────────────────────────────────────────────────────────────
from datetime import datetime

LOG_FILE = STORAGE_DIR / "logs.jsonl"
LOG_CATEGORIES = ["generate", "delete", "provider", "system", "error"]


def _write_log(category: str, message: str, details: dict = None):
    """追加一条日志到 logs.jsonl"""
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "category": category,
        "message": message,
        "details": details or {},
    }
    with open(LOG_FILE, "a", encoding="utf-8") as fh:
        fh.write(_json.dumps(entry, ensure_ascii=False) + "\n")


@app.get("/api/logs")
async def get_logs(category: str = "", limit: int = 100):
    """读取日志，支持分类过滤"""
    entries = []
    if LOG_FILE.exists():
        with open(LOG_FILE, "r", encoding="utf-8") as fh:
            for line in reversed(list(fh)):
                line = line.strip()
                if not line:
                    continue
                try:
                    e = _json.loads(line)
                    if category and e.get("category") != category:
                        continue
                    entries.append(e)
                    if len(entries) >= limit:
                        break
                except:
                    pass
    return {"items": entries, "categories": LOG_CATEGORIES, "total": len(entries)}


@app.delete("/api/logs")
async def clear_logs():
    """清空日志"""
    if LOG_FILE.exists():
        LOG_FILE.write_text("", encoding="utf-8")
    return {"ok": True}


# ──────────────────────────────────────────────────────────────
# 视频生成 API
# ──────────────────────────────────────────────────────────────
VIDEO_DIR = STORAGE_DIR / "videos"
VIDEO_DIR.mkdir(exist_ok=True)
VIDEO_THUMBS_DIR = STORAGE_DIR / "video_thumbs"
VIDEO_THUMBS_DIR.mkdir(exist_ok=True)
VIDEO_HISTORY_FILE = STORAGE_DIR / "video_history.jsonl"


def _generate_video_thumbnail(video_path: Path) -> Path | None:
    """用 ffmpeg 提取视频首帧作为缩略图，返回缩略图路径"""
    thumb_name = video_path.stem + "_thumb.jpg"
    thumb_path = VIDEO_THUMBS_DIR / thumb_name
    if thumb_path.exists():
        return thumb_path
    try:
        import subprocess
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(video_path), "-vframes", "1", "-ss", "0.5",
             "-vf", "scale=480:-1", "-q:v", "3", str(thumb_path)],
            capture_output=True, timeout=15
        )
        if result.returncode == 0 and thumb_path.exists():
            return thumb_path
    except Exception:
        pass
    return None


def _generate_video_thumbnail_async(video_path: Path):
    """后台线程生成视频缩略图"""
    def _worker():
        try:
            _generate_video_thumbnail(video_path)
        except Exception:
            pass
    threading.Thread(target=_worker, daemon=True).start()

# 内存中的视频任务状态
video_tasks: dict = {}  # {task_id: {status, progress, ...}}
video_tasks_lock = threading.Lock()


def _save_video_history_entry(entry: dict):
    """追加一条视频历史记录"""
    with open(VIDEO_HISTORY_FILE, "a", encoding="utf-8") as fh:
        fh.write(_json.dumps(entry, ensure_ascii=False) + "\n")


def _load_video_history():
    """加载视频历史"""
    if not VIDEO_HISTORY_FILE.exists():
        return []
    entries = []
    with open(VIDEO_HISTORY_FILE, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(_json.loads(line))
            except Exception:
                pass
    return entries


class VideoGenerateRequest(BaseModel):
    prompt: str
    provider_id: str = ""  # 空=第一个视频provider
    model: str = ""        # 可选：指定模型（覆盖 Provider 默认）
    mode: str = "ti2vid"   # "ti2vid" | "keyframes"
    image: Optional[list] = None  # 图片URL或base64数组
    image_role: Optional[str] = None  # "first_frame" | "last_frame" | "reference" | "first_last"
    width: int = 1152
    height: int = 768
    num_frames: int = 121  # 8n+1, 默认5秒@24fps
    frame_rate: int = 24
    num_inference_steps: Optional[int] = None
    seed: Optional[int] = None
    negative_prompt: Optional[str] = None


def _detect_video_provider_type(provider):
    """检测视频 Provider 的 API 协议类型: 'agnes' | 'gemini' | 'volcengine' | 'openai'

    优先使用用户显式设置的 endpoint_type；为 auto 时回退到 URL/ID 启发式。
    """
    et = (getattr(provider, 'endpoint_type', None) or 'auto').strip().lower()
    if et in ("volc_ark_plan", "volc_ark", "volcengine"):
        return "volcengine"
    if et == "openai":
        return "openai"
    if et == "gemini":
        return "gemini"
    if et == "agnes":
        return "agnes"

    base = provider.base_url.lower()
    pid = provider.id.lower()
    if "agnes" in pid or "agnes" in base:
        return "agnes"
    if "gemini" in pid or "localhost:38000" in base or "google" in base or "flow2api" in base:
        return "gemini"
    if "volcengine" in pid or "volces.com" in base or "ark.cn-beijing" in base:
        return "volcengine"
    return "openai"


def _build_agnes_payload(req, effective_model):
    """构建 Agnes Video API 请求体（匹配官方文档）"""
    payload = {
        "model": effective_model,
        "prompt": req.prompt,
        "height": req.height,
        "width": req.width,
        "num_frames": req.num_frames,
        "frame_rate": req.frame_rate,
    }
    if req.negative_prompt:
        payload["negative_prompt"] = req.negative_prompt
    if req.seed is not None:
        payload["seed"] = req.seed

    if req.image:
        if len(req.image) == 1:
            # 单图 I2V → image 为字符串
            payload["image"] = req.image[0]
        else:
            # 多图 → 放入 extra_body
            extra = {"image": req.image}
            if req.mode == "keyframes":
                extra["mode"] = "keyframes"
            payload["extra_body"] = extra
    elif req.mode == "keyframes":
        # 无图的关键帧模式（罕见）
        payload["extra_body"] = {"mode": "keyframes"}

    return payload


def _volcengine_task_base(base_url: str) -> str:
    """规范化火山方舟视频任务的基础 URL（返回到 .../tasks 之前的前缀）

    支持用户填写多种形式的 Base URL：
    - https://ark.cn-beijing.volces.com                         → 追加 /api/v3/contents/generations
    - https://ark.cn-beijing.volces.com/api/v3                  → 追加 /contents/generations
    - https://ark.cn-beijing.volces.com/api/plan/v3             → 追加 /contents/generations
    - https://ark.cn-beijing.volces.com/api/plan/v3/contents/generations/tasks → 去掉末尾 /tasks
    返回值不含末尾的 /tasks，方便统一拼接创建/查询路径。
    """
    b = (base_url or "").rstrip("/")
    # 去掉末尾的 /tasks（用户填了完整任务路径）
    if b.endswith("/contents/generations/tasks"):
        return b[:-len("/tasks")]
    # 已经到 /contents/generations
    if b.endswith("/contents/generations"):
        return b
    # 形如 /api/v3 或 /api/plan/v3
    if b.endswith("/v3") or "/v3" in b.split("//")[-1]:
        # 截断到 .../v3
        idx = b.rfind("/v3")
        prefix = b[:idx + len("/v3")]
        return prefix + "/contents/generations"
    # 裸域名或其他：默认使用标准 /api/v3
    return b + "/api/v3/contents/generations"


def _build_volcengine_payload(req, effective_model):
    """构建火山方舟 Agent Plan 视频生成请求体"""
    # 构建 content 数组
    content = []
    
    # 文本提示词
    prompt_text = req.prompt
    # 在提示词中追加参数
    params = []
    if req.width and req.height:
        # 计算宽高比
        from math import gcd
        w, h = req.width, req.height
        g = gcd(w, h)
        ratio = f"{w//g}:{h//g}"
        params.append(f"--ratio {ratio}")
    if req.num_frames and req.frame_rate:
        duration = int(req.num_frames / req.frame_rate)
        params.append(f"--duration {duration}")
    if params:
        prompt_text += " " + " ".join(params)
    
    content.append({
        "type": "text",
        "text": prompt_text
    })
    
    # 图片输入（图生视频）
    if req.image:
        for img_url in req.image:
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url}
            })
    
    payload = {
        "model": effective_model,
        "content": content,
    }
    
    return payload


def _auto_select_gemini_model(req, effective_model):
    """根据是否有图片输入，自动选择正确的 Gemini 视频模型"""
    model_lower = effective_model.lower()
    has_images = bool(req.image)

    is_t2v = "t2v" in model_lower and "i2v" not in model_lower
    is_i2v = "i2v" in model_lower

    # T2V 和 I2V 的朝向命名规则不同:
    #   T2V: veo_3_1_t2v_fast_landscape （_landscape 为后缀）
    #   I2V: veo_3_1_i2v_s_fast_fl       （_fl 即 landscape，内嵌）
    T2V_ORIENTATIONS = ("_landscape", "_portrait", "_square",
                        "_four-three", "_three-four",
                        "_landscape_2k", "_portrait_2k",
                        "_landscape_4k", "_portrait_4k",
                        "_landscape_1080p", "_portrait_1080p")

    def strip_t2v_orient(name, t2v_prefix):
        base = name[len(t2v_prefix):]
        for o in T2V_ORIENTATIONS:
            if base == o or base.endswith(o):
                return base[:len(base)-len(o)]
        return base

    if has_images and is_t2v:
        for t2v_prefix, i2v_prefix in [
            ("veo_3_1_t2v_fast_ultra_real", "veo_3_1_i2v_s_fast_ultra_real"),
            ("veo_3_1_t2v_fast_ultra", "veo_3_1_i2v_s_fast_ultra_fl"),
            ("veo_3_1_t2v_fast", "veo_3_1_i2v_s_fast_fl"),
            ("veo_3_1_t2v", "veo_3_1_i2v_s"),
            ("veo_2_1_fast_d_15_t2v", "veo_2_1_fast_d_15_i2v"),
            ("veo_2_0_t2v", "veo_2_0_i2v"),
        ]:
            if t2v_prefix in model_lower:
                extra = strip_t2v_orient(effective_model, t2v_prefix)
                return i2v_prefix + extra
        return effective_model.replace("t2v", "i2v_s")
    elif not has_images and is_i2v:
        for i2v_prefix, t2v_prefix in [
            ("veo_3_1_i2v_s_fast_ultra_real", "veo_3_1_t2v_fast_ultra_real"),
            ("veo_3_1_i2v_s_fast_ultra_fl", "veo_3_1_t2v_fast_ultra_relaxed"),
            ("veo_3_1_i2v_s_fast_fl", "veo_3_1_t2v_fast"),
            ("veo_3_1_i2v_s_fast_portrait_fl", "veo_3_1_t2v_fast_portrait"),
            ("veo_3_1_i2v_s", "veo_3_1_t2v_lite"),
            ("veo_2_1_fast_d_15_i2v", "veo_2_1_fast_d_15_t2v"),
            ("veo_2_0_i2v", "veo_2_0_t2v"),
        ]:
            if i2v_prefix in model_lower:
                extra = effective_model[len(i2v_prefix):]
                return t2v_prefix + extra
        return effective_model.replace("i2v_s", "t2v").replace("i2v", "t2v")
    return effective_model


def _build_gemini_payload(req, effective_model):
    """构建 Gemini (Flow2API) OpenAI-compatible chat completions 请求体"""
    model_lower = effective_model.lower()
    content = []
    content.append({"type": "text", "text": req.prompt})
    # 只有 I2V 模型才发送图片，T2V 模型不支持图片输入
    if req.image and "i2v" in model_lower:
        for img_data in req.image[:3]:
            if img_data.startswith("data:"):
                content.append({"type": "image_url", "image_url": {"url": img_data}})
            elif img_data.startswith("http"):
                content.append({"type": "image_url", "image_url": {"url": img_data}})
            elif img_data.startswith("/"):
                # 相对路径：读取本地文件并转为 base64
                try:
                    import base64 as _b64
                    file_path = STORAGE_DIR / "gallery" / img_data.split("/")[-1]
                    if file_path.exists():
                        file_data = _b64.b64encode(file_path.read_bytes()).decode()
                        content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + file_data}})
                except Exception:
                    pass
            else:
                content.append({"type": "image_url", "image_url": {"url": "data:image/png;base64," + img_data}})
    return {
        "model": effective_model,
        "messages": [{"role": "user", "content": content}],
        "stream": True,
    }


@app.post("/api/video/generate")
async def video_generate(req: VideoGenerateRequest):
    """创建视频生成任务"""
    import httpx as _httpx
    import threading

    video_providers = cfg_mgr.get_video_providers()
    if not video_providers:
        raise HTTPException(status_code=400, detail="无可用的视频生成模型，请先在设置中配置视频 Provider")

    provider = None
    if req.provider_id:
        for p in video_providers:
            if p.id == req.provider_id:
                provider = p
                break
        if not provider:
            raise HTTPException(status_code=404, detail=f"视频 Provider '{req.provider_id}' 不存在")
    else:
        provider = video_providers[0]

    if not provider.api_key:
        raise HTTPException(status_code=400, detail=f"视频 Provider '{provider.name}' API Key 未配置")

    effective_model = req.model.strip() if req.model else provider.model
    provider_type = _detect_video_provider_type(provider)
    
    # ── 智能参数适配：根据模型约束校验并调整参数 ──
    from providers import get_video_model_spec
    model_spec = get_video_model_spec(effective_model)
    adjustment_log = []
    
    if model_spec:
        # 1. 分辨率适配：如果模型不支持当前分辨率，自动降级到最近可用值
        req_width, req_height = req.width, req.height
        # 简化分辨率匹配：检查是否在支持范围内
        max_supported_p = max([int(r.replace("p", "")) for r in model_spec.resolutions if "p" in r] or [1080])
        if req_width > 1920 or req_height > 1080:
            # 需要降级
            scale = min(1920 / req_width, 1080 / req_height) if req_width > 1920 or req_height > 1080 else 1
            new_w = int(req_width * scale)
            new_h = int(req_height * scale)
            adjustment_log.append(f"分辨率从 {req_width}x{req_height} 降级到 {new_w}x{new_h}")
            req_width, req_height = new_w, new_h
        
        # 2. 时长适配：如果模型不支持当前时长，裁剪到最近可用值
        duration_seconds = req.num_frames / req.frame_rate if req.frame_rate > 0 else 5
        if duration_seconds not in model_spec.duration_options:
            # 找到最接近的可用时长
            closest_duration = min(model_spec.duration_options, key=lambda x: abs(x - duration_seconds))
            if closest_duration != duration_seconds:
                adjustment_log.append(f"时长从 {duration_seconds}s 调整到 {closest_duration}s")
                duration_seconds = closest_duration
        
        # 3. FPS适配
        if req.frame_rate not in model_spec.fps_options:
            closest_fps = min(model_spec.fps_options, key=lambda x: abs(x - req.frame_rate))
            if closest_fps != req.frame_rate:
                adjustment_log.append(f"FPS从 {req.frame_rate} 调整到 {closest_fps}")
                req.frame_rate = closest_fps
        
        # 4. 帧数计算：根据时长和FPS重新计算帧数，并应用帧数规则
        num_frames = int(duration_seconds * req.frame_rate)
        
        # 应用帧数规则
        if model_spec.frame_rule == "8n+1":
            num_frames = max(model_spec.min_frames, min(num_frames, model_spec.max_frames))
            remainder = (num_frames - 1) % 8
            if remainder != 0:
                if remainder <= 4:
                    num_frames = num_frames - remainder
                else:
                    num_frames = num_frames + (8 - remainder)
                num_frames = max(model_spec.min_frames, num_frames)
            adjustment_log.append(f"帧数规则 8n+1: 调整为 {num_frames} 帧")
        elif model_spec.frame_rule == "4n+1":
            num_frames = max(model_spec.min_frames, min(num_frames, model_spec.max_frames))
            remainder = (num_frames - 1) % 4
            if remainder != 0:
                num_frames = num_frames - remainder
                num_frames = max(model_spec.min_frames, num_frames)
            adjustment_log.append(f"帧数规则 4n+1: 调整为 {num_frames} 帧")
        else:
            num_frames = max(9, min(num_frames, 441))
        
        # 5. 推理步数适配
        if req.num_inference_steps and model_spec.inference_steps_range:
            min_steps, max_steps, default_steps = model_spec.inference_steps_range
            if req.num_inference_steps < min_steps:
                adjustment_log.append(f"推理步数从 {req.num_inference_steps} 调整到 {min_steps}")
                req.num_inference_steps = min_steps
            elif req.num_inference_steps > max_steps:
                adjustment_log.append(f"推理步数从 {req.num_inference_steps} 调整到 {max_steps}")
                req.num_inference_steps = max_steps
        
        # 更新请求参数
        req.width = req_width
        req.height = req_height
        req.num_frames = num_frames
    
    provider_type = _detect_video_provider_type(provider)
    # 自动选择正确的模型（T2V vs I2V）
    if provider_type == "gemini":
        effective_model = _auto_select_gemini_model(req, effective_model)
    base_url = provider.base_url.rstrip("/")

    # ── 按 Provider 类型构建请求 ──
    if provider_type == "gemini":
        payload = _build_gemini_payload(req, effective_model)
        api_url = f"{base_url}/chat/completions"
        headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
    elif provider_type == "volcengine":
        payload = _build_volcengine_payload(req, effective_model)
        # Agent Plan / 标准 Ark 均使用 .../contents/generations/tasks 端点
        api_url = f"{_volcengine_task_base(provider.base_url)}/tasks"
        headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}
    else:
        payload = _build_agnes_payload(req, effective_model)
        api_url = f"{base_url}/videos"
        headers = {"Authorization": f"Bearer {provider.api_key}", "Content-Type": "application/json"}

    # ── 调用 API 创建任务 ──
    if provider_type == "gemini":
        video_result_url = ""
        sse_error_msg = ""
        accumulated_content = ""
        done_received = False
        try:
            import json as _json
            import re as _re
            async with _httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream("POST", api_url, headers=headers, json=payload) as resp:
                    resp.raise_for_status()
                    buffer = ""
                    async for chunk in resp.aiter_text():
                        if done_received:
                            break
                        buffer += chunk
                        while "\n" in buffer and not done_received:
                            line, buffer = buffer.split("\n", 1)
                            line = line.strip()
                            if not line or not line.startswith("data:"):
                                continue
                            data_str = line[5:].strip()
                            if data_str == "[DONE]":
                                done_received = True
                                break
                            try:
                                sse_data = _json.loads(data_str)
                                err = sse_data.get("error")
                                if err:
                                    sse_error_msg = translate_upstream_error(err.get("message", str(err)))
                                    done_received = True
                                    break
                                choices = sse_data.get("choices", [])
                                for choice in choices:
                                    delta = choice.get("delta", {})
                                    finish_reason = choice.get("finish_reason")
                                    if finish_reason == "stop":
                                        done_received = True
                                    content_val = delta.get("content", "")
                                    if isinstance(content_val, str):
                                        accumulated_content += content_val
                            except Exception:
                                continue
                    # 在所有 SSE 完成后，从累积的 content 中提取视频 URL
                    if accumulated_content:
                        # Flow2API 返回 <video src='URL' controls> 格式
                        src_match = _re.search(r"src=['\"]([^'\"]+)['\"]", accumulated_content)
                        if src_match:
                            video_result_url = src_match.group(1)
                        else:
                            url_match = _re.search(r"https?://[^\s<>\"']+", accumulated_content)
                            if url_match:
                                video_result_url = url_match.group(0)
        except _httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"视频 API 错误: {translate_upstream_error(e.response.text[:500])}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"视频 API 调用失败: {translate_upstream_error(str(e))}")

        task_id = str(uuid.uuid4())
        video_id = task_id  # Gemini uses task_id as video_id
        if video_result_url:
            initial_status = "completed"
            initial_progress = 100
        elif sse_error_msg:
            initial_status = "failed"
            initial_progress = 0
        else:
            initial_status = "queued"
            initial_progress = 0
    elif provider_type == "volcengine":
        # 火山方舟 Agent Plan: 异步任务模式
        try:
            async with _httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(api_url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except _httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"火山方舟 API 错误: {translate_upstream_error(e.response.text[:500])}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"火山方舟 API 调用失败: {translate_upstream_error(str(e))}")
        
        # 返回格式: {"id": "cgt-xxx", "status": "queued", ...}
        task_id = data.get("id") or str(uuid.uuid4())
        video_id = ""
        video_result_url = ""
        initial_status = data.get("status", "queued")
        initial_progress = 0
    else:
        payload = _build_agnes_payload(req, effective_model)
        api_url = f"{base_url}/videos"
        try:
            async with _httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(api_url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except _httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"视频 API 错误: {translate_upstream_error(e.response.text[:500])}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"视频 API 调用失败: {translate_upstream_error(str(e))}")
        task_id = data.get("task_id") or data.get("id") or str(uuid.uuid4())
        video_id = data.get("video_id", "")
        video_result_url = ""
        initial_status = data.get("status", "queued")
        initial_progress = data.get("progress", 0)

    task_info = {
        "task_id": task_id, "video_id": video_id,
        "provider_id": provider.id, "provider_name": provider.name,
        "prompt": req.prompt, "mode": req.mode,
        "status": initial_status, "progress": initial_progress,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "start_time": time.time(),
        "width": req.width, "height": req.height,
        "num_frames": req.num_frames, "frame_rate": req.frame_rate,
        "video_url": video_result_url if provider_type == "gemini" else None,
        "local_path": None, "error": sse_error_msg if provider_type == "gemini" and sse_error_msg else None,
        "provider_type": provider_type,
    }
    video_tasks[task_id] = task_info

    # ── 如果 Gemini 流式响应直接返回了视频，立即下载并标记完成 ──
    if provider_type == "gemini" and video_result_url:
        def _download_gemini_video(tid, vurl, provider_id, prompt_text):
            import requests as _req
            try:
                if vurl.startswith("http"):
                    vr = _req.get(vurl, timeout=120)
                    if vr.status_code == 200:
                        ts2 = time.strftime("%Y%m%d_%H%M%S")
                        safe_prompt = "".join(c if c.isalnum() else "_" for c in prompt_text[:30])
                        vfilename = f"{provider_id}_{ts2}_{safe_prompt}_{uuid.uuid4().hex[:6]}.mp4"
                        vpath = VIDEO_DIR / vfilename
                        vpath.write_bytes(vr.content)
                        _generate_video_thumbnail_async(vpath)
                        if tid in video_tasks:
                            video_tasks[tid]["local_path"] = str(vpath)
                elif vurl.startswith("data:"):
                    import base64 as _b64
                    b64_str = vurl.split(",", 1)[1] if "," in vurl else vurl
                    vid_bytes = _b64.b64decode(b64_str)
                    ts2 = time.strftime("%Y%m%d_%H%M%S")
                    safe_prompt = "".join(c if c.isalnum() else "_" for c in prompt_text[:30])
                    vfilename = f"{provider_id}_{ts2}_{safe_prompt}_{uuid.uuid4().hex[:6]}.mp4"
                    vpath = VIDEO_DIR / vfilename
                    vpath.write_bytes(vid_bytes)
                    _generate_video_thumbnail_async(vpath)
                    if tid in video_tasks:
                        video_tasks[tid]["local_path"] = str(vpath)
            except Exception as e:
                print(f"[Video] Gemini 视频下载失败: {e}")
            if tid in video_tasks:
                _save_video_history_entry(video_tasks[tid])

        import threading as _threading
        _threading.Thread(target=_download_gemini_video, args=(task_id, video_result_url, provider.id, req.prompt), daemon=True).start()
    elif provider_type == "gemini" and not video_result_url:
        error_detail = sse_error_msg or "Flow2API 未返回视频数据，请检查模型是否支持视频生成"
        task_info["status"] = "failed"
        task_info["error"] = error_detail
        _save_video_history_entry(task_info)
        print(f"[Video] Gemini 视频生成失败: {error_detail} (model={effective_model})")
    elif provider_type == "volcengine":
        # ── 火山方舟: 后台轮询线程 ──
        def _poll_volcengine(tid, base, key, model, prompt_text, provider_id):
            import time as _t
            import requests as _req
            poll_count = 0
            max_polls = 180  # 最多轮询 180 次 (约 15 分钟)
            # 构建轮询 URL（base 已是规范化到 .../contents/generations 的前缀）
            poll_url = f"{base}/tasks/{tid}"
            while poll_count < max_polls:
                _t.sleep(15)  # 火山方舟建议 15 秒轮询间隔
                poll_count += 1
                try:
                    r = _req.get(poll_url, headers={"Authorization": f"Bearer {key}"}, timeout=30)
                    if r.status_code != 200:
                        print(f"[Video] 火山方舟轮询失败: {r.status_code} {r.text[:200]}")
                        continue
                    result = r.json()
                    status = result.get("status", "")
                    # 更新进度
                    if tid in video_tasks:
                        video_tasks[tid]["status"] = status
                        # 简单估算进度
                        if status == "queued":
                            video_tasks[tid]["progress"] = 10
                        elif status == "running":
                            video_tasks[tid]["progress"] = 50
                    
                    if status == "succeeded":
                        # 提取视频 URL
                        content = result.get("content", {})
                        vurl = content.get("video_url", "") if isinstance(content, dict) else ""
                        if tid in video_tasks:
                            video_tasks[tid]["video_url"] = vurl
                            video_tasks[tid]["progress"] = 100
                            video_tasks[tid]["status"] = "completed"
                        # 下载视频
                        if vurl:
                            try:
                                vr = _req.get(vurl, timeout=120)
                                if vr.status_code == 200:
                                    ts2 = time.strftime("%Y%m%d_%H%M%S")
                                    safe_p = "".join(c if c.isalnum() else "_" for c in prompt_text[:30])
                                    vfn = f"{provider_id}_{ts2}_{safe_p}_{uuid.uuid4().hex[:6]}.mp4"
                                    vp = VIDEO_DIR / vfn
                                    vp.write_bytes(vr.content)
                                    _generate_video_thumbnail_async(vp)
                                    if tid in video_tasks:
                                        video_tasks[tid]["local_path"] = str(vp)
                            except Exception as e:
                                print(f"[Video] 火山方舟视频下载失败: {e}")
                        if tid in video_tasks:
                            _save_video_history_entry(video_tasks[tid])
                        return
                    elif status in ("failed", "expired"):
                        error_msg = translate_upstream_error(result.get("error", {}).get("message", "任务失败") if isinstance(result.get("error"), dict) else str(result.get("error", "任务失败")))
                        if tid in video_tasks:
                            video_tasks[tid]["status"] = "failed"
                            video_tasks[tid]["error"] = error_msg
                            _save_video_history_entry(video_tasks[tid])
                        print(f"[Video] 火山方舟视频生成失败: {error_msg} (model={model})")
                        return
                    # queued/running 继续轮询
                except Exception as e:
                    print(f"[Video] 火山方舟轮询异常: {e}")
                    continue
            # 超时
            if tid in video_tasks:
                video_tasks[tid]["status"] = "timeout"
                video_tasks[tid]["error"] = "任务超时（超过 15 分钟）"
                _save_video_history_entry(video_tasks[tid])

        t = threading.Thread(
            target=_poll_volcengine,
            args=(task_id, _volcengine_task_base(provider.base_url), provider.api_key, effective_model, req.prompt, provider.id),
            daemon=True,
        )
        t.start()
    else:
        # ── Agnes: 后台轮询线程 ──
        def _poll_agnes(vid, tid, base, key):
            import requests as _req
            if vid:
                agnes_base = base.replace("/v1", "").rstrip("/")
                r = _req.get(f"{agnes_base}/agnesapi?video_id={vid}",
                             headers={"Authorization": f"Bearer {key}"}, timeout=30)
            else:
                r = _req.get(f"{base}/videos/{tid}",
                             headers={"Authorization": f"Bearer {key}"}, timeout=30)
            if r.status_code != 200:
                return None, False
            result = r.json()
            return result, result.get("status", "") in ("completed", "failed", "error", "cancelled")

        def _poll_task(tid, vid, base, key, model, prompt_text, provider_id, ptype):
            import time as _t
            import requests as _req
            poll_count = 0
            max_polls = 180
            while poll_count < max_polls:
                _t.sleep(5)
                poll_count += 1
                try:
                    result, done = _poll_agnes(vid, tid, base, key)
                    if result is None:
                        continue
                    status = result.get("status", "")
                    progress = result.get("progress", 0)
                    if tid in video_tasks:
                        video_tasks[tid]["status"] = status
                        video_tasks[tid]["progress"] = progress
                    if status == "completed":
                        vurl = (result.get("remixed_from_video_id") or
                                result.get("video_url") or result.get("url", ""))
                        if tid in video_tasks:
                            video_tasks[tid]["video_url"] = vurl
                            video_tasks[tid]["progress"] = 100
                        if vurl and not vurl.startswith("http"):
                            vurl = ""
                        if vurl:
                            try:
                                vr = _req.get(vurl, timeout=120)
                                if vr.status_code == 200:
                                    ts2 = time.strftime("%Y%m%d_%H%M%S")
                                    safe_p = "".join(c if c.isalnum() else "_" for c in prompt_text[:30])
                                    vfn = f"{provider_id}_{ts2}_{safe_p}_{uuid.uuid4().hex[:6]}.mp4"
                                    vp = VIDEO_DIR / vfn
                                    vp.write_bytes(vr.content)
                                    _generate_video_thumbnail_async(vp)
                                    if tid in video_tasks:
                                        video_tasks[tid]["local_path"] = str(vp)
                            except Exception as e:
                                print(f"[Video] 下载失败: {e}")
                        if tid in video_tasks:
                            _save_video_history_entry(video_tasks[tid])
                        return
                    elif status in ("failed", "error", "cancelled"):
                        if tid in video_tasks:
                            video_tasks[tid]["status"] = status
                            video_tasks[tid]["error"] = result.get("error", "任务失败")
                            _save_video_history_entry(video_tasks[tid])
                        return
                except Exception as e:
                    print(f"[Video] 轮询异常: {e}")
                    continue
            if tid in video_tasks:
                video_tasks[tid]["status"] = "timeout"
                video_tasks[tid]["error"] = "任务超时"
                _save_video_history_entry(video_tasks[tid])

        t = threading.Thread(
            target=_poll_task,
            args=(task_id, video_id, base_url, provider.api_key, provider.model, req.prompt, provider.id, provider_type),
            daemon=True,
        )
        t.start()

    return {
        "task_id": task_id, "video_id": video_id,
        "status": task_info["status"],
        "progress": task_info.get("progress", 0),
        "error": task_info.get("error"),
        "video_url": task_info.get("video_url") or None,
    }


@app.get("/api/video/status/{task_id}")
async def video_status(task_id: str):
    """查询视频任务状态"""
    if task_id not in video_tasks:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在")
    info = video_tasks[task_id]
    elapsed = round(time.time() - info.get("start_time", time.time()), 1)
    result = {**info, "elapsed_seconds": elapsed}
    if info.get("local_path"):
        fname = Path(info["local_path"]).name
        result["video_url_local"] = f"/api/video/file/{fname}"
    return result


@app.get("/api/video/file/{filename}")
async def video_file(filename: str):
    """访问本地视频文件"""
    fpath = _resolve_video_file(filename)
    return FileResponse(str(fpath), media_type=_VIDEO_MEDIA_TYPES[fpath.suffix.lower()])


@app.get("/api/video/list")
async def video_list(limit: int = 50):
    """获取视频生成历史"""
    entries = _load_video_history()
    active = [v for v in video_tasks.values() if v.get("status") not in ("completed", "failed", "error", "cancelled", "timeout")]
    all_entries = active + list(reversed(entries[-limit:]))
    return {"items": all_entries, "total": len(all_entries)}


@app.get("/api/video/model-spec/{model_name}")
async def video_model_spec(model_name: str):
    """获取视频模型参数约束
    
    根据模型名称返回该模型支持的参数范围：
    - resolutions: 支持的分辨率档位
    - duration_options: 支持的时长选项(秒)
    - fps_options: 支持的FPS选项
    - frame_rule: 帧数规则 (8n+1, 4n+1, 无限制)
    - inference_steps_range: 推理步数范围 [min, max, default]
    - supports_negative_prompt: 是否支持负面提示词
    - supports_seed: 是否支持种子
    """
    from providers import get_video_model_spec_dict
    spec = get_video_model_spec_dict(model_name)
    return {"model": model_name, "spec": spec}


@app.get("/api/video/model-specs")
async def video_model_specs():
    """获取所有视频模型参数约束预设"""
    from config import VIDEO_MODEL_SPECS
    return {k: v.model_dump() for k, v in VIDEO_MODEL_SPECS.items()}


@app.post("/api/video/cancel/{task_id}")
async def video_cancel(task_id: str):
    """取消视频任务"""
    if task_id not in video_tasks:
        raise HTTPException(status_code=404, detail=f"任务 '{task_id}' 不存在")
    video_tasks[task_id]["status"] = "cancelled"
    return {"ok": True, "message": f"任务 '{task_id}' 已取消"}


@app.get("/api/preview/images")
async def preview_images():
    """返回图库中最近的图片base64列表（供视频页取图用）"""
    import base64 as _b64
    items = []
    for discovered in sorted(GALLERY_DIR.glob("*.png"), reverse=True)[:40]:
        try:
            f, payload, mime_type, prompt_text = await asyncio.to_thread(
                _load_gallery_image_payload,
                discovered.name,
            )
            data = _b64.b64encode(payload).decode()
            model_name = f.stem.split("_")[0] if f.stem else "unknown"
            items.append({
                "filename": f.name,
                "data": f"data:{mime_type};base64,{data}",
                "prompt": prompt_text,
                "model": model_name,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(f.stat().st_mtime)),
            })
        except Exception:
            continue
    return {"items": items}


# ──────────────────────────────────────────────────────────────
# 概览看板 Dashboard
# ──────────────────────────────────────────────────────────────
import shutil as _shutil

@app.get("/api/dashboard")
async def get_dashboard():
    """概览看板数据聚合"""
    now = time.time()
    try:
      providers = cfg_mgr.config.providers
    except Exception:
      providers = []

    # ── 系统信息 ──
    try:
        disk = _shutil.disk_usage("/")
        disk_total_gb = round(disk.total / (1024**3), 1)
        disk_used_gb = round(disk.used / (1024**3), 1)
        disk_free_gb = round(disk.free / (1024**3), 1)
        disk_pct = round(disk.used / disk.total * 100, 1)
    except Exception:
        disk_total_gb = disk_used_gb = disk_free_gb = disk_pct = 0

    # 图库大小
    gallery_size = 0
    gallery_count = 0
    try:
        for f in GALLERY_DIR.glob("*"):
            if f.is_file():
                gallery_size += f.stat().st_size
                gallery_count += 1
    except Exception:
        pass

    # 视频大小
    video_size = 0
    video_count = 0
    video_dir = STORAGE_DIR / "videos"
    try:
        for f in video_dir.glob("*"):
            if f.is_file():
                video_size += f.stat().st_size
                video_count += 1
    except Exception:
        pass

    def _fmt_size(b):
        if b < 1024: return f"{b} B"
        if b < 1024**2: return f"{b/1024:.1f} KB"
        if b < 1024**3: return f"{b/1024**2:.1f} MB"
        return f"{b/1024**3:.2f} GB"

    # ── Provider 概览 ──
    provider_overview = []
    for p in providers:
        provider_overview.append({
            "id": p.id,
            "name": p.name,
            "type": p.type,
            "enabled": p.enabled,
            "configured": bool(p.api_key),
            "model": p.model,
            "color": p.color,
        })

    # ── 图片生成统计 ──
    img_total = 0
    img_success = 0
    img_failed = 0
    img_times = []
    img_per_provider = {}
    for gen_id, record in generation_history.items():
        img_total += 1
        results = record.get("results", {})
        for pid, r in results.items():
            base_pid = pid.rsplit("_", 1)[0] if pid.rsplit("_", 1)[-1].isdigit() else pid
            if base_pid not in img_per_provider:
                img_per_provider[base_pid] = {"success": 0, "failed": 0, "times": []}
            if r.get("success"):
                img_success += 1
                img_per_provider[base_pid]["success"] += 1
                if r.get("elapsed_seconds"):
                    img_per_provider[base_pid]["times"].append(r["elapsed_seconds"])
                    img_times.append(r["elapsed_seconds"])
            else:
                img_failed += 1
                img_per_provider[base_pid]["failed"] += 1

    img_avg_time = round(sum(img_times) / len(img_times), 1) if img_times else 0

    # ── 视频生成统计 ──
    vid_total = 0
    vid_success = 0
    vid_failed = 0
    vid_per_provider = {}
    for task_id, record in video_tasks.items():
        vid_total += 1
        pid = record.get("provider_id", "unknown")
        if pid not in vid_per_provider:
            vid_per_provider[pid] = {"success": 0, "failed": 0, "running": 0}
        status = record.get("status", "")
        if status == "completed":
            vid_success += 1
            vid_per_provider[pid]["success"] += 1
        elif status in ("failed", "error", "cancelled"):
            vid_failed += 1
            vid_per_provider[pid]["failed"] += 1
        else:
            vid_per_provider[pid]["running"] += 1

    # ── 最近活动 ──
    recent_logs = []
    try:
        logs_path = STORAGE_DIR / "logs.jsonl"
        if logs_path.exists():
            lines = logs_path.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-10:]:
                if line.strip():
                    recent_logs.append(_json.loads(line))
    except Exception:
        pass

    # ── 评分 ──
    # 连通性 (40): 有 api_key 的 image/video provider 占比
    image_video_providers = [p for p in providers if p.type in ("image", "video")]
    configured_count = sum(1 for p in image_video_providers if p.api_key)
    connectivity_score = (configured_count / max(len(image_video_providers), 1)) * 40

    # 配置完整性 (30): 有 model 的 provider 占比
    model_count = sum(1 for p in image_video_providers if p.model)
    config_score = (model_count / max(len(image_video_providers), 1)) * 30

    # 磁盘空间 (15): 空闲 > 10GB 满分, < 1GB 零分
    disk_score = min(15, max(0, (disk_free_gb / 10) * 15)) if disk_free_gb > 0 else 0

    # 依赖版本 (15): 基础分，有 provider 配置即可
    dep_score = 15 if configured_count > 0 else 0

    total_score = round(connectivity_score + config_score + disk_score + dep_score)

    # ── 平台信息 ──
    _os_name = platform.system()           # Windows / Linux / Darwin
    _os_release = platform.release()       # 10 / 22H2 / 5.15.0
    _os_version = platform.version()       # 10.0.19041
    _os_machine = platform.machine()       # AMD64 / x86_64 / ARM64
    _os_arch = "64-bit" if _os_machine in ("AMD64", "x86_64", "arm64", "aarch64") else "32-bit"
    _python_ver = platform.python_version()
    _hostname = platform.node()

    if _os_name == "Windows":
        try:
            _os_full = f"Windows {platform.platform().split('-')[0].replace('Windows', '').strip() or _os_release}"
        except Exception:
            _os_full = f"Windows {_os_release}"
        # Try to get Windows 10/11 edition
        try:
            ver = platform.version()
            build = int(ver.split('.')[-1]) if ver.split('.')[-1].isdigit() else 0
            if build >= 22000:
                _os_full = f"Windows 11 (Build {build})"
            elif build >= 10240:
                _os_full = f"Windows 10 (Build {build})"
        except Exception:
            pass
    elif _os_name == "Linux":
        try:
            _os_full = f"{platform.freedesktop_os_release().get('PRETTY_NAME', f'Linux {_os_release}')}"
        except Exception:
            _os_full = f"Linux {_os_release}"
    elif _os_name == "Darwin":
        _os_full = f"macOS {platform.mac_ver()[0]}"
    else:
        _os_full = f"{_os_name} {_os_release}"

    return {
        "system": {
            "os": _os_full,
            "arch": _os_arch,
            "machine": _os_machine,
            "python": _python_ver,
            "hostname": _hostname,
            "uptime_seconds": int(now - app_start_time),
            "disk_total_gb": disk_total_gb,
            "disk_used_gb": disk_used_gb,
            "disk_free_gb": disk_free_gb,
            "disk_pct": disk_pct,
            "gallery_size": _fmt_size(gallery_size),
            "gallery_count": gallery_count,
            "video_size": _fmt_size(video_size),
            "video_count": video_count,
        },
        "providers": provider_overview,
        "stats": {
            "image": {
                "total": img_total,
                "success": img_success,
                "failed": img_failed,
                "avg_time": img_avg_time,
                "per_provider": {k: {"success": v["success"], "failed": v["failed"], "avg_time": round(sum(v["times"])/len(v["times"]), 1) if v["times"] else 0} for k, v in img_per_provider.items()},
            },
            "video": {
                "total": vid_total,
                "success": vid_success,
                "failed": vid_failed,
                "per_provider": vid_per_provider,
            },
        },
        "recent_logs": recent_logs,
        "score": {
            "total": total_score,
            "connectivity": round(connectivity_score),
            "config": round(config_score),
            "disk": round(disk_score),
            "dependency": round(dep_score),
        },
    }


@app.get("/api/proxy")
async def get_proxy_config():
    """获取代理配置"""
    proxy = cfg_mgr.config.proxy
    return {
        "enabled": proxy.enabled,
        "type": proxy.type,
        "host": proxy.host,
        "port": proxy.port,
        "username": proxy.username,
        "has_password": bool(proxy.password),
    }


class ProxySaveRequest(BaseModel):
    enabled: bool = False
    type: str = "http"
    host: str = "127.0.0.1"
    port: int = 10808
    username: str = ""
    password: str = ""


@app.post("/api/proxy")
async def save_proxy_config(req: ProxySaveRequest):
    """保存代理配置"""
    from config import ProxyConfig
    cfg_mgr.config.proxy = ProxyConfig(
        enabled=req.enabled,
        type=req.type,
        host=req.host,
        port=req.port,
        username=req.username,
        password=req.password,
    )
    cfg_mgr.save()
    return {"ok": True, "message": "代理配置已保存"}


@app.post("/api/proxy/test")
async def test_proxy():
    """测试代理连通性"""
    import socket
    proxy = cfg_mgr.config.proxy
    if not proxy.enabled or not proxy.host:
        return {"ok": False, "message": "代理未启用"}

    endpoints = {
        "OpenAI": ("api.openai.com", 443),
        "Gemini": ("generativelanguage.googleapis.com", 443),
    }
    results = {}
    for name, (host, port) in endpoints.items():
        try:
            start = time.time()
            s = socket.create_connection((proxy.host, proxy.port), timeout=5)
            s.sendall(f'CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n'.encode())
            resp = s.recv(4096).decode()
            s.close()
            if '200' in resp:
                elapsed = round((time.time() - start) * 1000)
                results[name] = {"status": "ok", "ms": elapsed}
            else:
                results[name] = {"status": "error", "ms": 0, "error": "Proxy CONNECT rejected"}
        except Exception as e:
            results[name] = {"status": "error", "ms": 0, "error": str(e)[:80]}
    all_ok = all(r["status"] == "ok" for r in results.values())
    return {"ok": all_ok, "results": results}


@app.get("/api/keypool/{provider_id}")
async def get_keypool_status(provider_id: str):
    """获取指定 Provider 的多账号轮询状态"""
    from providers.key_pool import key_pool_manager
    cfg = cfg_mgr.config
    p = next((p for p in cfg.providers if p.id == provider_id), None)
    if not p:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' 不存在")
    keys = p.get_effective_keys()
    pool = key_pool_manager.get_or_create(provider_id, keys)
    return {
        "ok": True,
        "provider_id": provider_id,
        "total_keys": pool.size,
        "available_keys": pool.available_count,
        "keys": pool.get_status(),
    }


@app.get("/api/dashboard/connectivity")
async def check_connectivity():
    """一键连通性检测：测试所有 provider base_url 的延迟"""
    import socket
    providers = cfg_mgr.config.providers
    proxy_host, proxy_port = _detect_proxy()
    results = {}
    for p in providers:
        url = p.base_url.rstrip("/")
        if not url:
            results[p.id] = {"status": "no_url", "ms": 0}
            continue
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)
            start = time.time()
            try:
                s = socket.create_connection((host, port), timeout=3)
                if parsed.scheme == 'https' and proxy_host:
                    s.sendall(f'CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n'.encode())
                    s.recv(4096)
                s.close()
            except socket.timeout:
                if proxy_host:
                    s = socket.create_connection((proxy_host, proxy_port), timeout=3)
                    s.sendall(f'CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}:{port}\r\n\r\n'.encode())
                    s.recv(4096)
                    s.close()
                else:
                    raise
            elapsed = round((time.time() - start) * 1000)
            results[p.id] = {"status": "ok", "ms": elapsed}
        except Exception as e:
            results[p.id] = {"status": "error", "ms": 0, "error": str(e)[:80]}
    return {"results": results}


@app.get("/api/dashboard/network")
async def check_network_status():
    """检测国内外主流大模型厂商端点网络连通性（HTTP HEAD 请求，自动使用系统代理）"""
    import httpx as _httpx

    endpoints = {
        "OpenAI": ("https://api.openai.com/v1/models", True),
        "Gemini": ("https://generativelanguage.googleapis.com/", True),
        "Anthropic": ("https://api.anthropic.com/v1/messages", True),
        "Agnes": ("https://apihub.agnes-ai.com/v1/models", False),
        "Qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1/models", False),
        "Zhipu": ("https://open.bigmodel.cn/api/paas/v4/models", False),
        "Volcengine": ("https://visual.volcengineapi.com/", False),
        "Baidu": ("https://aip.baidubce.com/", False),
        "Tencent": ("https://hunyuan.tencentcloudapi.com/", False),
        "Moonshot": ("https://api.moonshot.cn/v1/models", False),
        "DeepSeek": ("https://api.deepseek.com/v1/models", False),
        "MiniMax": ("https://api.minimax.chat/v1/models", False),
    }

    proxy_host, proxy_port = _detect_proxy()
    proxy_url = None
    if proxy_host:
        proxy_url = f"http://{proxy_host}:{proxy_port}"

    results = {}

    async def _test_one(name, url, need_proxy):
        try:
            start = time.time()
            _verify_ssl = verify_ssl_enabled()
            async with _httpx.AsyncClient(
                timeout=_httpx.Timeout(5.0),
                verify=_verify_ssl,
                proxy=proxy_url if (need_proxy and proxy_url) else None,
                follow_redirects=True,
            ) as client:
                r = await client.head(url)
                elapsed = round((time.time() - start) * 1000)
                # 200/301/302/401/403 都算可达
                if r.status_code < 500:
                    results[name] = {"status": "ok", "ms": elapsed}
                else:
                    results[name] = {"status": "error", "ms": elapsed, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            # 如果需要代理但代理失败，尝试直连
            if need_proxy and proxy_url:
                try:
                    start = time.time()
                    _verify_ssl = verify_ssl_enabled()
                    async with _httpx.AsyncClient(timeout=_httpx.Timeout(5.0), verify=_verify_ssl, follow_redirects=True) as client:
                        r = await client.head(url)
                        elapsed = round((time.time() - start) * 1000)
                        if r.status_code < 500:
                            results[name] = {"status": "ok", "ms": elapsed}
                        else:
                            results[name] = {"status": "error", "ms": elapsed, "error": f"HTTP {r.status_code}"}
                except Exception:
                    results[name] = {"status": "error", "ms": 0, "error": str(e)[:60]}
            else:
                results[name] = {"status": "error", "ms": 0, "error": str(e)[:60]}

    # 并发测试所有端点
    import asyncio as _asyncio
    tasks = [_test_one(name, url, need) for name, (url, need) in endpoints.items()]
    await _asyncio.gather(*tasks)

    return {"results": results, "proxy": {"host": proxy_host, "port": proxy_port}}


@app.get("/api/dashboard/ip-info")
async def get_ip_info():
    """获取本机 IP 深度质检报告（来自 testisp.info）"""
    import httpx as _httpx
    try:
        _verify_ssl = verify_ssl_enabled()
        async with _httpx.AsyncClient(timeout=15.0, verify=_verify_ssl, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Referer": "https://testisp.info/",
                "Origin": "https://testisp.info",
            }
            r = await client.get("https://testisp.info/api/check", headers=headers)
            data = r.json()
            geo = data.get("geo", {})
            isp = data.get("isp", {})
            risk = data.get("risk", {})
            return {
                "ip": data.get("ip", ""),
                "is_local": data.get("is_local", False),
                "data_source": data.get("data_source", ""),
                "country": geo.get("country", ""),
                "country_code": geo.get("country_code", ""),
                "city": geo.get("city", ""),
                "timezone": geo.get("timezone", ""),
                "is_native": geo.get("is_native", False),
                "native_type": geo.get("native_type", ""),
                "native_flag": geo.get("native_flag", ""),
                "drift_km": geo.get("drift_km", 0),
                "has_drift": geo.get("has_drift", False),
                "asn": isp.get("asn", ""),
                "org": isp.get("org", ""),
                "rdns": isp.get("rdns", ""),
                "isp_type": isp.get("type", ""),
                "isp_flag": isp.get("flag", ""),
                "isp_warning": isp.get("warning", ""),
                "tcp_rtt": risk.get("tcp_rtt"),
                "rtt_type": risk.get("rtt_type", ""),
                "threat_listed": risk.get("threat_listed", False),
            }
    except Exception as e:
        return {"error": str(e)[:100]}
    except Exception as e:
        return {"error": str(e)[:100]}


@app.get("/api/dashboard/resources")
async def get_host_resources():
    """获取宿主机资源占用信息"""
    import psutil as _psutil
    import platform as _platform
    try:
        cpu_pct = _psutil.cpu_percent(interval=0.5)
        cpu_freq = _psutil.cpu_freq()
        mem = _psutil.virtual_memory()
        swap = _psutil.swap_memory()
        net = _psutil.net_io_counters()
        disk = _shutil.disk_usage("/")
        boot_time = _psutil.boot_time()
        uptime_sec = time.time() - boot_time

        # Top processes by CPU
        top_procs = []
        try:
            for proc in _psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                info = proc.info
                if info['cpu_percent'] and info['cpu_percent'] > 0:
                    top_procs.append({
                        'pid': info['pid'],
                        'name': (info['name'] or '')[:20],
                        'cpu': round(info['cpu_percent'], 1),
                        'mem': round(info['memory_percent'] or 0, 1),
                    })
            top_procs.sort(key=lambda x: x['cpu'], reverse=True)
            top_procs = top_procs[:5]
        except Exception:
            pass

        return {
            "cpu_percent": cpu_pct,
            "cpu_count": _psutil.cpu_count(),
            "cpu_count_physical": _psutil.cpu_count(logical=False),
            "cpu_freq_mhz": round(cpu_freq.current, 0) if cpu_freq else 0,
            "mem_total_gb": round(mem.total / (1024**3), 1),
            "mem_used_gb": round(mem.used / (1024**3), 1),
            "mem_available_gb": round(mem.available / (1024**3), 1),
            "mem_percent": mem.percent,
            "swap_total_gb": round(swap.total / (1024**3), 1) if swap.total else 0,
            "swap_used_gb": round(swap.used / (1024**3), 1) if swap.total else 0,
            "swap_percent": swap.percent if swap.total else 0,
            "disk_total_gb": round(disk.total / (1024**3), 1),
            "disk_used_gb": round(disk.used / (1024**3), 1),
            "disk_free_gb": round(disk.free / (1024**3), 1),
            "disk_percent": round(disk.used / disk.total * 100, 1),
            "net_sent_mb": round(net.bytes_sent / (1024**2), 1),
            "net_recv_mb": round(net.bytes_recv / (1024**2), 1),
            "net_packets_sent": net.packets_sent,
            "net_packets_recv": net.packets_recv,
            "uptime_seconds": int(uptime_sec),
            "platform": _platform.system(),
            "platform_release": _platform.release(),
            "top_processes": top_procs,
        }
    except Exception as e:
        return {"error": str(e)[:100]}


def _detect_proxy():
    """检测代理设置（优先使用用户配置，其次系统代理）"""
    # 优先使用用户在界面保存的代理配置
    try:
        proxy = cfg_mgr.config.proxy
        if proxy.enabled and proxy.host:
            return proxy.host, proxy.port
    except Exception:
        pass
    # 回退到系统代理
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
        proxy_enable, _ = winreg.QueryValueEx(key, "ProxyEnable")
        if proxy_enable:
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            if proxy_server and ':' in proxy_server:
                parts = proxy_server.split(':')
                return parts[0], int(parts[1])
        winreg.CloseKey(key)
    except Exception:
        pass
    return None, None


@app.get("/api/server/control")
async def server_control(action: str = "status"):
    """Report status only; process mutation belongs to the owned local launcher."""
    if action == "status":
        return {"status": "running", "port": GENBOX_PORT}
    raise HTTPException(
        status_code=405,
        detail="为防止误停进程，请使用本机 GenBox Lab 启动器执行停止或重启",
    )


# ──────────────────────────────────────────────────────────────
# 自动更新系统
# ──────────────────────────────────────────────────────────────
class UpdateApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


@app.get("/api/update/check")
async def check_for_updates(request: Request):
    """Read the canonical release state without browser-selected routing."""
    if request.query_params:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "update_check_parameters_forbidden",
                "message": "update checks do not accept browser-supplied URLs or mirrors",
            },
        )
    from updater import check_update
    info = await check_update()
    return {
        "available": info.available,
        "current_version": info.current_version,
        "latest_version": info.latest_version,
        "release_notes": info.release_notes,
        "update_type": info.update_type,
        "automatic_apply_available": info.automatic_apply_available,
        "manual_install_required": info.manual_install_required,
    }


@app.get("/api/update/mirrors")
async def test_update_mirrors():
    """Retire browser-selectable update mirrors."""
    raise HTTPException(
        status_code=410,
        detail={
            "code": "update_mirror_check_unavailable",
            "message": "update mirror selection is unavailable",
        },
    )


@app.post("/api/update/apply")
async def apply_software_update(body: UpdateApplyRequest, request: Request):
    """Fail closed before any automatic update side effect can begin."""
    del body
    if request.query_params:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "update_apply_parameters_forbidden",
                "message": "update apply does not accept URLs or mirrors",
            },
        )
    from updater import update_apply_unavailable_detail
    raise HTTPException(
        status_code=503,
        detail=update_apply_unavailable_detail(),
    )


@app.get("/api/update/info")
async def get_update_info():
    """获取当前更新环境信息"""
    from updater import detect_update_type, CURRENT_VERSION, get_app_dir
    update_type = detect_update_type()
    app_dir = get_app_dir()
    return {
        "current_version": CURRENT_VERSION,
        "update_type": update_type.value,
        "app_dir": str(app_dir),
        "platform": sys.platform,
        "is_frozen": getattr(sys, 'frozen', False),
        "automatic_apply_available": False,
        "manual_install_required": True,
    }


# ──────────────────────────────────────────────────────────────
# 安全策略：ADMINKEY 认证中间件
# ──────────────────────────────────────────────────────────────
AUTH_EXEMPT_PATHS = {
    "/api/setup/status",
    "/api/runtime/status",
    "/api/sync/push",
    "/api/sync/push/status",
    "/favicon.ico",
}

@app.middleware("http")
async def admin_auth_middleware(request: Request, call_next):
    """生产模式下校验 ADMINKEY"""
    if not is_prod_mode():
        return await call_next(request)

    path = request.url.path
    # 静态文件免认证
    if not path.startswith("/api/"):
        return await call_next(request)
    # 白名单免认证（首次设置流程）
    if path in AUTH_EXEMPT_PATHS:
        return await call_next(request)

    # 校验 Header
    admin_key = request.headers.get("X-Admin-Key", "")
    if not verify_admin_key(admin_key):
        return JSONResponse(status_code=401, content={"error": "未授权，请先登录", "code": "AUTH_REQUIRED"})
    return await call_next(request)


# ──────────────────────────────────────────────────────────────
# 远程同步：chatgpt2api 兼容部署图片拉取
# 拉取接口由全局 admin 中间件保护；push 使用独立的来源身份密钥。
# ──────────────────────────────────────────────────────────────
sync_tasks: Dict[str, dict] = {}
push_commit_lock = threading.Lock()


def _save_synced_image(data: bytes, deployment_name: str, remote_path: str,
                       remote_created_at: str, prompt: str = "", model: str = ""):
    """保存远端同步来的图片到本地图库，写入 PNG 元数据。返回 (local_path, filename)。"""
    from io import BytesIO
    from PIL import Image, PngImagePlugin
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c if c.isalnum() else "_" for c in (deployment_name or "remote")[:20])
    filename = f"remote_{safe_name}_{ts}_{uuid.uuid4().hex[:6]}.png"
    try:
        img = Image.open(BytesIO(data))
        buf = BytesIO()
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Prompt", prompt or "")
        metadata.add_text("Model", model or "remote-sync")
        metadata.add_text("CreatedAt", remote_created_at or ts)
        metadata.add_text("SourcePath", remote_path)
        metadata.add_text("SourceSHA256", sha256_bytes(data))
        metadata.add_text("Source", "cloud")
        metadata.add_text("SourceDeployment", deployment_name)
        metadata.add_text("Tags", "cloud-sync")
        img.save(buf, format="PNG", pnginfo=metadata)
        out = buf.getvalue()
    except Exception as e:  # noqa
        print(f"[Sync] PNG 元数据写入失败，直接保存: {e}")
        out = data
    out_path = GALLERY_DIR / filename
    out_path.write_bytes(out)
    return str(out_path), filename


def _refresh_synced_image_metadata(local_path: str, deployment_name: str, remote_path: str,
                                   remote_created_at: str, prompt: str, model: str) -> bool:
    """为历史同步图片补写来源、提示词和模型元数据。"""
    from PIL import Image, PngImagePlugin

    path = Path(local_path)
    if not path.is_absolute():
        path = GALLERY_DIR / path.name
    if not path.is_file() or path.suffix.lower() != ".png":
        return False
    try:
        with Image.open(path) as source:
            source.load()
            image = source.copy()
            existing = {k: v for k, v in source.info.items() if isinstance(v, str)}
        desired = {
            **existing,
            "Prompt": prompt or existing.get("Prompt", ""),
            "Model": model or existing.get("Model", "remote-sync"),
            "CreatedAt": remote_created_at or existing.get("CreatedAt", ""),
            "SourcePath": remote_path,
            "Source": "cloud",
            "SourceDeployment": deployment_name,
            "Tags": "cloud-sync",
        }
        if all(existing.get(key) == value for key, value in desired.items()):
            return False
        metadata = PngImagePlugin.PngInfo()
        for key, value in desired.items():
            metadata.add_text(key, value)
        temp_path = path.with_suffix(".sync-meta.tmp")
        image.save(temp_path, format="PNG", pnginfo=metadata)
        temp_path.replace(path)
        return True
    except Exception as e:  # noqa
        print(f"[Sync] 历史图片元数据修复失败 {path.name}: {e}")
        return False


@app.get("/api/sync/deployments")
async def sync_list_deployments():
    """列出已配置的远程部署（不含 token 明文）。"""
    deps = sync_store.list_deployments()
    return {"deployments": [d.model_dump(exclude={"api_key"}) for d in deps]}


@app.post("/api/sync/deployments")
async def sync_upsert_deployment(body: dict = {}):
    """新增/更新远程部署。"""
    if not body.get("base_url"):
        raise HTTPException(status_code=400, detail="base_url 必填")
    dep = sync_store.upsert_deployment(body)
    return {"deployment": dep.model_dump(exclude={"api_key"})}


@app.delete("/api/sync/deployments/{deployment_id}")
async def sync_delete_deployment(deployment_id: str):
    ok = sync_store.delete_deployment(deployment_id)
    if not ok:
        raise HTTPException(status_code=404, detail="部署不存在")
    return {"deleted": True}


@app.post("/api/sync/test")
async def sync_test_connection(body: dict = {}):
    """测试部署连通性与 admin 权限；支持已存部署或内联 base_url+api_key。"""
    dep_id = body.get("deployment_id") or body.get("id")
    dep = sync_store.get_deployment(dep_id) if dep_id else None
    if not dep:
        base = body.get("base_url", "")
        key = body.get("api_key", "")
        if not base:
            raise HTTPException(status_code=400, detail="缺少部署或 base_url")
        dep = SyncDeployment(id="__test__", name="test", base_url=base, api_key=key)
    client = ChatGPT2APIClient(dep.base_url, dep.api_key)
    try:
        info = await client.probe()
        return {"ok": True, **info}
    except Exception as e:  # noqa
        return {"ok": False, "error": str(e)[:200]}


@app.post("/api/sync/preview")
async def sync_preview(body: dict = {}):
    """列出远端图片并去重，返回待选卡片（已同步/本地重复会被过滤或标记）。"""
    dep_id = body.get("deployment_id", "")
    dep = sync_store.get_deployment(dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail="部署不存在")
    start_date = body.get("start_date", "")
    end_date = body.get("end_date", "")
    client = ChatGPT2APIClient(dep.base_url, dep.api_key)
    try:
        raw = await client.list_all_images(start_date, end_date)
    except Exception as e:  # noqa
        raise HTTPException(status_code=502, detail=f"远端列表失败: {str(e)[:200]}")
    try:
        remote_metadata = await client.list_image_metadata()
    except Exception as e:  # noqa
        print(f"[Sync] 远端提示词日志不可用，继续无提示词预览: {e}")
        remote_metadata = {}

    manifest = SyncManifest()
    local_idx = LocalImageIndex()

    # ── 第一级：path+size 快速过滤，收集需哈希校验的候选 ──
    pending = []
    for item in raw:
        path = item.get("path", "")
        if manifest.is_synced(dep_id, path, item.get("size", 0)):
            entry = manifest.get(f"{dep_id}::{path}") or {}
            remote_url = client.resolve_url(item.get("url", ""))
            meta = remote_metadata.get(remote_url, {})
            _refresh_synced_image_metadata(
                entry.get("local_path", ""), dep.name, path, item.get("created_at", ""),
                str(meta.get("prompt") or ""), str(meta.get("model") or ""),
            )
            continue
        if item.get("type", "image") != "image":
            continue
        pending.append(item)

    # 上游文件名格式为 <epoch>_<md5(image_bytes)>.png，可无网络完成精确内容去重。
    # 不符合该格式的兼容部署仍列为 new，导入时会下载并用 SHA-256 二次校验。
    local_idx.ensure_md5_index()
    candidates = []
    md5_pattern = re.compile(r"(?:^|_)([0-9a-fA-F]{32})(?:\.[^.]+)?$")

    for item in pending:
        path = item.get("path", "")
        rec = RemoteImageRecord(
            deployment_id=dep_id, path=path,
            name=item.get("name", ""), filename=item.get("filename", ""),
            url=client.resolve_url(item.get("url", "")),
            thumbnail_url=client.resolve_url(item.get("thumbnail_url", "")),
            created_at=item.get("created_at", ""),
            size=item.get("size", 0),
            width=item.get("width"), height=item.get("height"),
            remote_type=item.get("type", "image"),
        )
        meta = remote_metadata.get(rec.url, {})
        rec.prompt = str(item.get("prompt") or meta.get("prompt") or "")
        rec.model = str(item.get("model") or meta.get("model") or "")
        proxy_thumbnail = (
            "/api/sync/thumbnail?deployment_id=" + quote(dep_id, safe="")
            + "&url=" + quote(rec.thumbnail_url, safe="")
        ) if rec.thumbnail_url else ""
        match = md5_pattern.search(rec.filename or path.rsplit("/", 1)[-1])
        remote_md5 = match.group(1).lower() if match else ""
        if remote_md5 and local_idx.contains_md5(remote_md5):
            manifest.add(dep_id, path, local_idx.md5_index[remote_md5], "", rec.size, rec.created_at)
            candidates.append(SyncCandidate(
                deployment_id=dep_id, path=path, name=rec.name,
                url=rec.url,
                thumbnail_url=proxy_thumbnail, created_at=rec.created_at,
                size=rec.size, width=rec.width, height=rec.height, aspect=rec.aspect,
                status="duplicate-local", reason="本地已存在相同内容图片",
                prompt=rec.prompt, model=rec.model,
            ).model_dump())
            continue
        candidates.append(SyncCandidate(
            deployment_id=dep_id, path=path, name=rec.name,
            url=rec.url,
            thumbnail_url=proxy_thumbnail, created_at=rec.created_at,
            size=rec.size, width=rec.width, height=rec.height, aspect=rec.aspect,
            status="new", prompt=rec.prompt, model=rec.model,
        ).model_dump())
    return {"candidates": candidates, "total": len(candidates)}


@app.get("/api/sync/thumbnail")
async def sync_thumbnail(deployment_id: str, url: str):
    """同源代理并缓存远端缩略图，避免浏览器 CSP/跨域限制。"""
    dep = sync_store.get_deployment(deployment_id)
    if not dep:
        raise HTTPException(status_code=404, detail="部署不存在")
    remote = urlsplit(url)
    expected = urlsplit(dep.base_url)
    if remote.scheme not in ("http", "https") or remote.netloc.lower() != expected.netloc.lower():
        raise HTTPException(status_code=400, detail="缩略图地址不属于该部署")

    cache_dir = STORAGE_DIR / "sync_thumbnails"
    cache_dir.mkdir(exist_ok=True)
    cache_file = cache_dir / f"{sha256_bytes(url.encode('utf-8'))}.png"
    headers = {"Cache-Control": "public, max-age=86400"}
    if cache_file.exists():
        return FileResponse(cache_file, media_type="image/png", headers=headers)

    try:
        data = await ChatGPT2APIClient(dep.base_url, dep.api_key).download(url)
    except Exception as e:  # noqa
        raise HTTPException(status_code=502, detail=f"缩略图加载失败: {str(e)[:160]}")
    cache_file.write_bytes(data)
    return Response(content=data, media_type="image/png", headers=headers)


@app.post("/api/sync/import")
async def sync_import(body: dict = {}):
    """导入选中的远端图片（后台任务，带进度）。"""
    dep_id = body.get("deployment_id", "")
    items = body.get("items", [])
    dep = sync_store.get_deployment(dep_id)
    if not dep:
        raise HTTPException(status_code=404, detail="部署不存在")
    if not items:
        raise HTTPException(status_code=400, detail="未选择图片")
    task_id = uuid.uuid4().hex[:12]
    sync_tasks[task_id] = {
        "status": "running", "total": len(items), "done": 0,
        "errors": [], "results": [],
    }

    async def _run():
        client = ChatGPT2APIClient(dep.base_url, dep.api_key)
        manifest = SyncManifest()
        local_idx = LocalImageIndex()
        sem = asyncio.Semaphore(4)
        for it in items:
            async with sem:
                try:
                    url = client.resolve_url(it.get("url", ""))
                    data = await client.download(url)
                    h = sha256_bytes(data)
                    if local_idx.contains_hash(h):
                        manifest.add(dep_id, it.get("path", ""), local_idx.index[h], h,
                                     it.get("size", 0), it.get("created_at", ""))
                        sync_tasks[task_id]["results"].append(
                            {"path": it.get("path"), "status": "duplicate-local"})
                        sync_tasks[task_id]["done"] += 1
                        continue
                    _, fname = _save_synced_image(
                        data, dep.name, it.get("path", ""), it.get("created_at", ""),
                        it.get("prompt", ""), it.get("model", ""),
                    )
                    local_idx.index[h] = fname
                    manifest.add(dep_id, it.get("path", ""), str(GALLERY_DIR / fname), h,
                                 it.get("size", 0), it.get("created_at", ""))
                    sync_tasks[task_id]["results"].append(
                        {"path": it.get("path"), "status": "imported", "file": fname})
                except Exception as e:  # noqa
                    sync_tasks[task_id]["errors"].append(
                        {"path": it.get("path"), "error": str(e)[:160]})
                sync_tasks[task_id]["done"] += 1
        local_idx.save()
        sync_tasks[task_id]["status"] = "done"

    asyncio.create_task(_run())
    return {"task_id": task_id, "total": len(items)}


@app.post("/api/sync/push")
async def sync_push_image(
    image: UploadFile = File(...),
    remote_path: str = Form(...),
    source_sha256: str = Form(""),
    created_at: str = Form(""),
    prompt: str = Form(""),
    model: str = Form(""),
    x_genbox_source: str = Header(default=""),
    x_genbox_key: str = Header(default=""),
):
    """Receive one image from an authenticated remote deployment.

    A successful response is the durable acknowledgement a sender may use before
    applying its separately configured source-retention policy.
    """
    try:
        authenticated = authenticate_push_source(x_genbox_source, x_genbox_key)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not authenticated:
        raise HTTPException(status_code=401, detail="无效的推送来源或 API Key")
    try:
        remote_path = validate_remote_path(remote_path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = await image.read()
    try:
        metadata = validate_image_payload(payload, image.content_type or "")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        expected_source_sha256 = validate_source_sha256(source_sha256)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid source_sha256") from exc
    if expected_source_sha256 and expected_source_sha256 != metadata["sha256"]:
        raise HTTPException(status_code=422, detail="source_sha256 does not match image")

    with push_commit_lock:
        manifest = SyncManifest()
        existing = manifest.get(f"{x_genbox_source}::{remote_path}")
        existing_path = (
            manifest._safe_gallery_path(existing, GALLERY_DIR) if existing else None
        )
        if (
            existing
            and existing.get("sha256") == metadata["sha256"]
            and existing_path is not None
            and manifest.local_file_is_current(existing, GALLERY_DIR)
        ):
            filename = existing_path.name
            status = "already-imported"
        else:
            local_index = LocalImageIndex()
            local_index.ensure_sha256_index()
            local_index.index.update(manifest.local_sha256_index(GALLERY_DIR))
            local_index.save()
            if local_index.contains_hash(metadata["sha256"]):
                filename = local_index.index[metadata["sha256"]]
                status = "duplicate-local"
            else:
                _, filename = _save_synced_image(
                    payload, x_genbox_source, remote_path, created_at, prompt, model,
                )
                local_index.index[metadata["sha256"]] = filename
                local_index.save()
                status = "imported"

            local_path = str(GALLERY_DIR / filename)
            manifest.add(
                x_genbox_source, remote_path, local_path, metadata["sha256"],
                metadata["size"], created_at,
            )

        # Source-deletion authority is granted only for this managed source
        # when (a) the sender provisioned it under an explicit receiver-side
        # grant, and (b) this request commits the same bytes this path now
        # holds. A duplicate-local import from another path or the default
        # (ungranted) state never grants deletion (ADR-024/026).
        grant_delete = False
        try:
            grant_delete = _push_source_deletion_granted(x_genbox_source)
        except Exception:  # noqa: BLE001 - a broken grant registry must fail closed
            grant_delete = False
        authorized_status = status in ("imported", "already-imported")

        return {
            "ok": True,
            "contract_version": PUSH_CONTRACT_VERSION,
            "status": status,
            "source_id": x_genbox_source,
            "remote_path": remote_path,
            "sha256": metadata["sha256"],
            "local_file": filename,
            "width": metadata["width"],
            "height": metadata["height"],
            # Deletion authority is granted only when the push committed this
            # exact content for a source whose owner explicitly enabled it.
            "safe_to_delete_source": bool(grant_delete and authorized_status),
        }


@app.get("/api/sync/push/status")
async def sync_push_status(
    x_genbox_source: str = Header(default=""),
    x_genbox_key: str = Header(default=""),
):
    """Validate a push identity without creating a gallery item."""
    try:
        authenticated = authenticate_push_source(x_genbox_source, x_genbox_key)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not authenticated:
        raise HTTPException(status_code=401, detail="无效的推送来源或 API Key")
    return {
        "ok": True,
        "contract_version": PUSH_CONTRACT_VERSION,
        "source_id": x_genbox_source,
        "max_image_bytes": push_max_image_bytes(),
    }


@app.get("/api/sync/status/{task_id}")
async def sync_task_status(task_id: str):
    t = sync_tasks.get(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="任务不存在")
    return t


@app.get("/api/extensions/targets")
async def extension_list_targets():
    return {"targets": [target.model_dump() for target in extensions_store.list_targets()]}


@app.get("/api/extensions/targets/batch")
async def extension_get_batch_targets():
    return {"target_ids": extensions_store.get_batch_target_ids()}


@app.put("/api/extensions/targets/batch")
async def extension_save_batch_targets(body: ExtensionBatchTargetsRequest):
    return {"target_ids": extensions_store.save_batch_target_ids(body.target_ids)}


@app.get("/api/extensions/catalog")
async def extension_catalog():
    return public_catalog()


@app.get("/api/extensions/store")
async def extension_store():
    return extensions_store.public_store_projection()


@app.post("/api/extensions/images/integration-check")
async def extension_image_integration_check(body: ImageIntegrationCheckRequest):
    """Classify a pinned image from the local capability catalog only."""
    try:
        return {"image": body.image.strip(), **check_image_integration(body.image)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="immutable_image_required") from exc


@app.post("/api/extensions/targets")
async def extension_save_target(body: dict = {}):
    target = extensions_store.save_target_metadata(body)
    return {"target": target.model_dump()}


@app.delete("/api/extensions/targets/{target_id}")
async def extension_delete_target(target_id: str):
    if not extensions_store.get_target(target_id):
        raise HTTPException(status_code=404, detail="目标不存在")
    try:
        revoke_target_push_sources(target_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Push 凭据注册表暂不可用") from exc
    if not extensions_store.delete_target(target_id):
        raise HTTPException(status_code=404, detail="目标不存在")
    return {"deleted": True}


def _bind_confirmed_extension_target(body, *, plan_confirmation: bool = False):
    saved_target = extensions_store.get_target(body.target.id)
    if not saved_target:
        raise HTTPException(status_code=404, detail="请先保存 VPS，再执行远程操作")
    if not is_canonical_host_key_trust(
        saved_target.host_key_algorithm, saved_target.host_key
    ):
        raise HTTPException(status_code=409, detail="请先读取并确认 SSH 主机指纹")
    if (
        body.target.host != saved_target.host
        or body.target.port != saved_target.port
        or body.target.username != saved_target.username
    ):
        if plan_confirmation:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "VPS 连接身份与已确认部署计划不一致，请重新生成安全计划",
                    "diagnostic": {
                        "code": "deployment_plan_identity_changed",
                        "stage": "plan_confirmation",
                        "retry_safe": False,
                        "task_created": False,
                    },
                },
            )
        raise HTTPException(status_code=409, detail="VPS 连接信息已变化，请重新保存并确认主机指纹")
    if plan_confirmation and saved_target.target_role != "isolated-development":
        raise HTTPException(
            status_code=403,
            detail="当前目标已标记为生产机（只读），不能生成或执行部署计划；请选择隔离开发机。",
        )
    return body.model_copy(update={
        "target": saved_target,
        "expected_host_key_algorithm": saved_target.host_key_algorithm,
        "expected_host_key": saved_target.host_key,
        "trust_host_key": True,
    })


async def _validate_read_only_discovery_intent(
    body: ExtensionDiscoveryRequest,
) -> ValidatedDiscoveryPlan:
    """Bind one discovery click to the saved target and freshly observed key.

    The probe performs SSH key exchange only. Authentication and the existing
    backend-owned discovery commands remain in the subsequent discovery call.
    The approval record is intentionally in-memory and request-scoped: it is
    not target metadata, a task record, or a credential store.
    """
    observed_algorithm, observed_fingerprint = await probe_host_key(body.target)
    expected_algorithm = body.expected_host_key_algorithm
    expected_fingerprint = body.expected_host_key
    if not (
        hmac.compare_digest(expected_algorithm, observed_algorithm)
        and hmac.compare_digest(expected_fingerprint, observed_fingerprint)
    ):
        raise SSHConnectionError(
            "VPS 当前 SSH 主机身份与已确认记录不一致，已拒绝开始环境检查。",
            code="ssh_host_key_mismatch",
            stage="host_key_verification",
        )
    plan = {
        "authorization": {
            "scope": "read-only-discovery",
            "target_role": body.target.target_role,
            "host": body.target.host,
            "port": body.target.port,
            "username": body.target.username,
            "approval_record_id": f"l2-{uuid.uuid4().hex}",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        },
        "trust": {
            "expected_host": body.target.host,
            "expected_port": body.target.port,
            "expected_algorithm": expected_algorithm,
            "expected_fingerprint": expected_fingerprint,
            "observed_host": body.target.host,
            "observed_port": body.target.port,
            "observed_algorithm": observed_algorithm,
            "observed_fingerprint": observed_fingerprint,
        },
        "operations": [
            {"id": "identity"},
            {"id": "os_release"},
            {"id": "cpu_architecture"},
            {"id": "cpu_count"},
            {"id": "memory_summary"},
            {"id": "home_directory"},
            {"id": "python_version"},
            {"id": "uv_version"},
            {"id": "docker_version"},
            {"id": "compose_version"},
            {"id": "docker_ps"},
            {"id": "compose_ls"},
            {"id": "listening_ports"},
            {"id": "capacity", "path": "/"},
        ],
    }
    try:
        return validate_read_only_discovery_plan(plan)
    except DiscoveryPlanValidationError as exc:
        raise SSHConnectionError(
            "本次只读环境检查的安全范围无效，已拒绝连接。",
            code="read_only_discovery_plan_rejected",
            stage="discovery_authorization",
        ) from exc


READ_ONLY_DISCOVERY_TIMEOUT_SECONDS = 45


def _safe_extension_ssh_error(exc: Exception, *, error: str, code: str, stage: str) -> HTTPException:
    if isinstance(exc, (SSHAuthenticationError, SSHConnectionError)):
        return HTTPException(
            status_code=401 if isinstance(exc, SSHAuthenticationError) else 400,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        )
    return HTTPException(
        status_code=400,
        detail={
            "error": error,
            "diagnostic": {"code": code, "stage": stage, "retry_safe": False},
        },
    )


def _resolve_discovered_instance_handle(target_id: str, handle: str, discovery: dict) -> dict:
    candidates = discovery.get("instances", [])
    handle_matches = [
        (index, item) for index, item in enumerate(candidates)
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and hmac.compare_digest(public_instance_handle(target_id, item["id"]), handle)
    ]
    raw_matches = [
        (index, item) for index, item in enumerate(candidates)
        if isinstance(item, dict) and item.get("id") == handle
    ]
    if len(handle_matches) > 1 or len(raw_matches) > 1:
        raise ValueError("deployment_instance_handle_invalid")
    if handle_matches and raw_matches and handle_matches[0][0] != raw_matches[0][0]:
        raise ValueError("deployment_instance_handle_invalid")
    if handle_matches:
        return handle_matches[0][1]
    if raw_matches:
        return raw_matches[0][1]
    raise ValueError("deployment_instance_handle_invalid")


def _resolve_plan_discovery_references(body: ExtensionPlanRequest, discovery: dict) -> ExtensionPlanRequest:
    updates = {}
    if body.strategy == "existing" and body.instance_id.startswith("i-"):
        instance = _resolve_discovered_instance_handle(body.target.id, body.instance_id, discovery)
        updates.update({
            "instance_id": instance["id"],
            "service_port": instance.get("service_port"),
            "image": instance.get("image") or body.image,
        })
    if body.clone_scope in {"media", "working-copy"} and body.clone_source_id.startswith("i-"):
        source = _resolve_discovered_instance_handle(body.target.id, body.clone_source_id, discovery)
        updates.update({
            "clone_source_id": source["id"],
            "image": source.get("image") or body.image,
        })
    return body.model_copy(update=updates) if updates else body


def _resolve_stored_instance_handle(instance_handle: str, target_id: str = ""):
    candidates = extensions_store.list_instances(target_id)
    matches = [
        (index, item) for index, item in enumerate(candidates)
        if hmac.compare_digest(public_instance_handle(item.target_id, item.id), instance_handle)
    ]
    raw_matches = [(index, item) for index, item in enumerate(candidates) if item.id == instance_handle]
    if len(matches) > 1 or len(raw_matches) > 1:
        return None
    if matches and raw_matches and matches[0][0] != raw_matches[0][0]:
        return None
    if matches:
        return matches[0][1]
    if raw_matches:
        return raw_matches[0][1]
    return None


def _require_managed_existing_instance(instance_id: str, target_id: str = ""):
    instance = _resolve_stored_instance_handle(instance_id, target_id)
    if (
        not instance
        or instance.managed is not True
        or str(instance.ownership or "") != "managed"
    ):
        raise HTTPException(
            status_code=403,
            detail={
                "error": "external_instance_adoption_required",
                "message": "外部实例在完成已验证的 adoption flow 前仅可查看，不能进入部署或托管生命周期。",
            },
        )
    return instance


def _public_instance_projection(instance) -> dict:
    return public_instance_access(instance)


@app.post("/api/extensions/ssh/test")
async def extension_test_ssh(body: ExtensionTestRequest):
    body = _bind_confirmed_extension_target(body)
    try:
        return await test_extension_connection(body)
    except (SSHAuthenticationError, SSHConnectionError) as exc:
        raise HTTPException(
            status_code=401 if isinstance(exc, SSHAuthenticationError) else 400,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "SSH 诊断未完成，原始错误已隐藏。请勿连续重试。",
                "diagnostic": {"code": "ssh_check_failed", "stage": "ssh_check", "retry_safe": False},
            },
        ) from exc


@app.post("/api/extensions/ssh/host-key/probe")
async def extension_probe_ssh_host_key(body: ExtensionHostKeyProbeRequest):
    target = extensions_store.get_target(body.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="请先保存 VPS，再读取主机指纹")
    try:
        algorithm, fingerprint = await probe_host_key(target)
    except SSHConnectionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "读取 SSH 主机指纹失败，原始错误已隐藏。",
                "diagnostic": {"code": "ssh_host_key_probe_failed", "stage": "host_key_probe", "retry_safe": False},
            },
        ) from exc
    return {
        "target_id": target.id,
        "algorithm": algorithm,
        "fingerprint": fingerprint,
    }


@app.post("/api/extensions/ssh/host-key/pair/start")
async def extension_start_ssh_host_key_pairing(body: ExtensionHostKeyPairingStartRequest):
    """Create a one-time helper for a user-trusted SSH terminal session."""
    target = extensions_store.get_target(body.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="请先保存 VPS，再开始配对")
    try:
        algorithm, fingerprint = await probe_host_key(target)
        record = host_key_pairings.create(target, algorithm, fingerprint)
        helper = build_host_key_pairing_helper(record)
    except SSHConnectionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "无法开始 SSH 主机身份配对，请稍后重试",
                "diagnostic": {"code": "ssh_host_key_pair_start_failed", "stage": "host_key_pair_start", "retry_safe": False},
            },
        ) from exc
    return {
        "pairing_id": record.pairing_id,
        "expires_at": int(record.expires_at),
        "expires_in_seconds": max(0, int(record.expires_at - time.time())),
        "helper_command": helper,
    }


@app.post("/api/extensions/ssh/host-key/pair/complete")
async def extension_complete_ssh_host_key_pairing(body: ExtensionHostKeyPairingCompleteRequest):
    """Validate and consume a helper response before persisting host trust."""
    record = host_key_pairings.consume(body.pairing_id)
    if not record:
        raise HTTPException(status_code=409, detail="配对已过期、取消或已经使用")
    parsed = parse_host_key_pairing_response(body.response)
    target = extensions_store.get_target(record.target_id)
    expected_proof = hashlib.sha256(
        f"{record.algorithm}:{record.fingerprint}:{record.challenge}".encode("utf-8")
    ).hexdigest()
    if not parsed or not hmac.compare_digest(parsed["code"], record.challenge) or not hmac.compare_digest(parsed["proof"], expected_proof):
        raise HTTPException(status_code=400, detail="配对回执格式或挑战值无效")
    if not target or target_identity_digest(target) != record.target_identity:
        raise HTTPException(status_code=409, detail="VPS 连接信息已修改，请重新开始配对")
    try:
        current_algorithm, current_fingerprint = await probe_host_key(target)
    except SSHConnectionError as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc), "diagnostic": exc.diagnostic}) from exc
    if current_algorithm != record.algorithm or current_fingerprint != record.fingerprint:
        raise HTTPException(status_code=409, detail="SSH 主机身份在配对期间发生变化，未保存")
    if is_canonical_host_key_trust(target.host_key_algorithm, target.host_key):
        if target.host_key_algorithm != record.algorithm or target.host_key != record.fingerprint:
            raise HTTPException(status_code=409, detail="VPS 已保存的主机身份与本次配对不一致")
    try:
        saved = extensions_store.confirm_target_host_key(target, record.algorithm, record.fingerprint)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="VPS 连接信息在配对期间发生变化，未保存") from exc
    return {"target": saved.model_dump(), "verified": True}


@app.post("/api/extensions/ssh/host-key/pair/cancel")
async def extension_cancel_ssh_host_key_pairing(body: ExtensionHostKeyPairingCancelRequest):
    """Discard a one-time pairing without revealing whether it existed."""
    host_key_pairings.discard(body.pairing_id)
    return {"cancelled": True}


@app.post("/api/extensions/ssh/host-key/reset")
async def extension_reset_ssh_host_key(body: ExtensionHostKeyResetRequest):
    """Discard one saved trust record only after an explicit local user action."""
    target = extensions_store.reset_target_host_key(body.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="请先保存 VPS，再重置服务器身份记录")
    return {"target": target.model_dump(), "reset": True}


@app.post("/api/extensions/ssh/host-key/confirm")
async def extension_confirm_ssh_host_key(body: ExtensionHostKeyConfirmRequest):
    target = extensions_store.get_target(body.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="请先保存 VPS，再确认主机指纹")
    try:
        current_algorithm, current_fingerprint = await probe_host_key(target)
    except SSHConnectionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        ) from exc
    algorithm_matches = hmac.compare_digest(body.algorithm, current_algorithm)
    fingerprint_matches = hmac.compare_digest(body.fingerprint, current_fingerprint)
    if not (algorithm_matches and fingerprint_matches):
        raise HTTPException(status_code=409, detail="VPS 主机身份在确认前发生变化，已拒绝保存")
    if is_canonical_host_key_trust(target.host_key_algorithm, target.host_key):
        saved_algorithm_matches = hmac.compare_digest(target.host_key_algorithm, current_algorithm)
        saved_fingerprint_matches = hmac.compare_digest(target.host_key, current_fingerprint)
        if not (saved_algorithm_matches and saved_fingerprint_matches):
            raise HTTPException(status_code=409, detail="VPS 已保存的主机身份与当前值不一致，已拒绝覆盖")
    try:
        saved = extensions_store.confirm_target_host_key(
            target, current_algorithm, current_fingerprint
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="VPS 连接信息在确认期间发生变化，已拒绝保存指纹") from exc
    return {"target": saved.model_dump()}


@app.post("/api/extensions/deploy")
async def extension_start_deploy(body: ExtensionDeployRequest):
    try:
        validate_deployment_capability(body.project_id, body.strategy, body.deployment_mode)
        if body.strategy == "existing":
            _require_managed_existing_instance(body.instance_id, body.target.id)
        body = _bind_confirmed_extension_target(body, plan_confirmation=True)
        task_id = await extension_tasks.create(body)
        return {"task_id": task_id}
    except HTTPException:
        raise
    except DeploymentAttemptConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        ) from exc
    except DeploymentNoTaskError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "deployment_request_rejected",
                "diagnostic": {
                    "code": "extension_deploy_request_rejected",
                    "stage": "plan_confirmation",
                    "retry_safe": False,
                    "task_created": False,
                },
            },
        ) from exc
    except Exception as exc:
        raise _safe_extension_ssh_error(
            exc,
            error="部署前远程复核或本地任务事务未完成，原始错误已隐藏。",
            code="extension_deploy_preflight_failed",
            stage="deployment_preflight",
        ) from exc


@app.post("/api/extensions/discover")
async def extension_discover(body: ExtensionDiscoveryRequest):
    body = _bind_confirmed_extension_target(body)
    try:
        approved_plan = await _validate_read_only_discovery_intent(body)
        discovery = await asyncio.wait_for(
            discover_environment(body, approved_plan=approved_plan),
            timeout=READ_ONLY_DISCOVERY_TIMEOUT_SECONDS,
        )
        public = deployment_plans.public_discovery(discovery, body.target.id)
        _save_store_environment_projection(body.target, discovery, public)
        return public
    except asyncio.TimeoutError as exc:
        raise _safe_extension_ssh_error(
            SSHConnectionError(
                "只读环境检查在限定时间内未完成，已停止本次检查。无需重新确认服务器身份；"
                "请检查隔离开发机的 SSH/Docker 响应后，再进行一次检查。",
                code="read_only_discovery_timeout",
                stage="environment_discovery",
            ),
            error="VPS 环境检查未完成，原始错误已隐藏。",
            code="extension_discovery_failed",
            stage="environment_discovery",
        ) from exc
    except Exception as exc:
        raise _safe_extension_ssh_error(
            exc,
            error="VPS 环境检查未完成，原始错误已隐藏。",
            code="extension_discovery_failed",
            stage="environment_discovery",
        ) from exc


def _save_store_environment_projection(target, discovery: dict, public: dict) -> None:
    """Persist only complete, successful discovery evidence for Store use."""
    verified = extensions_store.verified_environment_projection(target, discovery, public)
    verified_facts = extensions_store.verified_environment_facts(target, discovery, public)
    if verified is not None and verified_facts is not None:
        extensions_store.save_environment_observation(verified, verified_facts)


@app.post("/api/extensions/deploy/plan")
async def extension_deploy_plan(body: ExtensionPlanRequest):
    try:
        validate_deployment_capability(body.project_id, body.strategy, body.deployment_mode)
        validate_deployment_image(body.image, body.strategy, body.clone_scope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:240]) from exc
    if body.strategy == "existing":
        _require_managed_existing_instance(body.instance_id, body.target.id)
    saved_target = extensions_store.get_target(body.target.id)
    if not saved_target or saved_target.target_role != "isolated-development":
        raise HTTPException(
            status_code=403,
            detail="当前目标仅允许只读检查；请把服务器用途改为隔离开发机后再生成部署计划。",
        )
    body = _bind_confirmed_extension_target(body)
    if not body.approve_plan_discovery:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "生成安全计划前需要明确确认两次部署前只读复核；本次未连接服务器。",
                "diagnostic": {
                    "code": "plan_discovery_approval_required",
                    "stage": "plan_discovery",
                    "retry_safe": True,
                },
            },
        )
    try:
        initial_discovery = await asyncio.wait_for(
            discover_environment(body),
            timeout=READ_ONLY_DISCOVERY_TIMEOUT_SECONDS,
        )
        body = _resolve_plan_discovery_references(body, initial_discovery)
        path_requirements = deployment_plans.path_requirements(body, initial_discovery)
        discovery = await asyncio.wait_for(
            discover_environment(body, path_checks=path_requirements),
            timeout=READ_ONLY_DISCOVERY_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "生成安全计划前的只读复核在限定时间内未完成，已停止本次复核。无需重新确认服务器身份。",
                "diagnostic": {
                    "code": "plan_discovery_timeout",
                    "stage": "plan_discovery",
                    "retry_safe": True,
                },
            },
        ) from exc
    except Exception as exc:
        raise _safe_extension_ssh_error(
            exc,
            error="生成部署计划前的 VPS 检查未完成，原始错误已隐藏。",
            code="extension_plan_discovery_failed",
            stage="plan_discovery",
        ) from exc
    try:
        plan = deployment_plans.create(
            body,
            discovery,
            path_requirements=path_requirements,
        )
        return {
            "plan": plan,
            "discovery": deployment_plans.public_discovery(discovery, body.target.id),
        }
    except DeploymentNoTaskError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error": str(exc), "diagnostic": exc.diagnostic},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "deployment_plan_rejected",
                "diagnostic": {
                    "code": "extension_plan_rejected",
                    "stage": "plan_generation",
                    "retry_safe": False,
                    "task_created": False,
                },
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "部署计划未生成，原始错误已隐藏。",
                "diagnostic": {"code": "extension_plan_failed", "stage": "plan_generation", "retry_safe": False},
            },
        ) from exc


@app.get("/api/extensions/tasks/{task_id}")
async def extension_task_status(task_id: str):
    state = extension_tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="任务不存在")
    return state


@app.get("/api/extensions/tasks")
async def extension_task_list():
    return extension_tasks.list_summary()


@app.post("/api/extensions/tasks/{task_id}/delivery")
async def extension_task_delivery(task_id: str, body: ExtensionDeliveryClaimRequest):
    delivery = extension_tasks.take_delivery(task_id, body.deployment_attempt_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="一次性交付信息不存在或已读取")
    response = {
        "instance": delivery["instance"],
        "shown_once": bool(delivery.get("admin_key")),
    }
    if delivery.get("admin_key"):
        response["admin_key"] = delivery["admin_key"]
    return response


@app.post("/api/extensions/tasks/{task_id}/resume")
async def extension_task_resume(task_id: str, body: ExtensionTaskResumeRequest):
    instance = extension_tasks.resume_access(task_id, body.target_id)
    if instance is None:
        return {"resumable": False}
    return {"resumable": True, "instance": instance}


@app.get("/api/extensions/instances")
async def extension_instances(target_id: str = ""):
    return {
        "instances": [
            _public_instance_projection(item)
            for item in extensions_store.list_instances(target_id)
        ]
    }


def _managed_push_source_access(instance_handle: str):
    """Resolve an opaque managed chatgpt2api instance and its verified destination."""
    if re.fullmatch(r"i-[a-f0-9]{32}", instance_handle or "") is None:
        raise HTTPException(status_code=404, detail="托管实例不存在")
    instance = _resolve_stored_instance_handle(instance_handle)
    if (
        not instance
        or instance.managed is not True
        or str(instance.ownership or "") != "managed"
        or instance.project != "chatgpt2api"
        or not hmac.compare_digest(
            public_instance_handle(instance.target_id, instance.id), instance_handle
        )
    ):
        raise HTTPException(status_code=404, detail="托管实例不存在")
    target = extensions_store.get_target(instance.target_id)
    if not target or not target.network_verified_at:
        raise HTTPException(status_code=409, detail="GenBox 私网地址尚未验证")
    try:
        parsed = urlsplit(target.network_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("invalid network URL")
        parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=409, detail="GenBox 私网地址尚未验证") from exc
    path = parsed.path.rstrip("/") + "/api/sync/push"
    destination_url = urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))
    return instance, destination_url


def _push_source_error(exc: Exception):
    if isinstance(exc, ValueError) and str(exc) == "managed Push source already exists":
        raise HTTPException(status_code=409, detail="该实例已有有效的 Push 凭据，请轮换或撤销后再创建") from exc
    raise HTTPException(status_code=503, detail="Push 凭据注册表暂不可用") from exc


def _push_source_deletion_granted(source_id: str) -> bool:
    """True only when this managed Push source has explicit deletion grant.

    Reads the durable registry read-only through the public query of the
    receiving-side record; a damaged registry fails closed (False) rather than
    ever granting deletion.
    """
    if not source_id:
        return False
    try:
        granted = push_source_deletion_granted(source_id)
    except Exception:  # noqa: BLE001 - fail closed on registry errors
        return False
    return granted


_PUSH_KEY_SAVE_CONFIRMATION_TTL_SECONDS = 120


class _PushKeySaveConfirmations:
    """Short-lived, one-time, in-memory authorization for local Push-key save."""

    def __init__(self):
        self._lock = threading.RLock()
        self._records: dict[str, dict[str, object]] = {}

    @staticmethod
    def _key_digest(push_key: str) -> str:
        return hashlib.sha256(push_key.encode("utf-8")).hexdigest()

    def issue(self, instance_handle: str, source_id: str, push_key: str) -> tuple[str, int]:
        now = time.time()
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._records = {
                item_token: record
                for item_token, record in self._records.items()
                if float(record["expires_at"]) > now
            }
            self._records[token] = {
                "expires_at": now + _PUSH_KEY_SAVE_CONFIRMATION_TTL_SECONDS,
                "instance_handle": instance_handle,
                "source_id": source_id,
                "key_digest": self._key_digest(push_key),
            }
        return token, _PUSH_KEY_SAVE_CONFIRMATION_TTL_SECONDS

    def consume(self, instance_handle: str, source_id: str, push_key: str, token: str) -> bool:
        if not token:
            return False
        with self._lock:
            record = self._records.pop(token, None)
        if not record or float(record["expires_at"]) <= time.time():
            return False
        return all((
            hmac.compare_digest(str(record["instance_handle"]), instance_handle),
            hmac.compare_digest(str(record["source_id"]), source_id),
            hmac.compare_digest(str(record["key_digest"]), self._key_digest(push_key)),
        ))


_push_key_save_confirmations = _PushKeySaveConfirmations()


@app.get("/api/extensions/push-sources/{instance_handle}")
async def extension_push_source_status(instance_handle: str):
    instance, destination_url = _managed_push_source_access(instance_handle)
    try:
        sources = list_push_sources(instance.target_id, instance.id)
    except Exception as exc:
        _push_source_error(exc)
    return {
        "instance_handle": instance_handle,
        "destination_url": destination_url,
        "configured": bool(sources),
        "source": sources[0] if sources else None,
        "saved_locally": bool(
            credential_vault.status().get("configured")
            and any(
                item.get("instance_id") == instance.id
                and ("genbox_" + "push" + "_key") in item.get("fields", [])
                for item in credential_vault.list_metadata()
            )
        ),
    }


@app.post("/api/extensions/push-sources")
async def extension_push_source_create(body: PushSourceProvisionRequest):
    instance, destination_url = _managed_push_source_access(body.instance_handle)
    try:
        source, push_key = create_push_source(instance.target_id, instance.id)
    except Exception as exc:
        _push_source_error(exc)
    return {
        "instance_handle": body.instance_handle,
        "destination_url": destination_url,
        "source": source,
        "push_key": push_key,
        "shown_once": True,
    }


@app.post("/api/extensions/push-sources/{instance_handle}/{source_id}/rotate")
async def extension_push_source_rotate(instance_handle: str, source_id: str, body: PushSourceRotateRequest | None = None):
    body = body or PushSourceRotateRequest()
    instance, destination_url = _managed_push_source_access(instance_handle)
    try:
        rotated = rotate_push_source(source_id, instance.target_id, instance.id)
    except Exception as exc:
        _push_source_error(exc)
    if rotated is None:
        raise HTTPException(status_code=404, detail="Push 来源不存在")
    source, push_key = rotated
    local_save = {
        "requested": False,
        "saved": False,
        "pending": False,
        "recovery_action": "",
        "error": "",
    }
    return {
        "instance_handle": instance_handle,
        "destination_url": destination_url,
        "source": source,
        "push_key": push_key,
        "shown_once": True,
        "remote_rotated": True,
        "local_save": local_save,
    }


@app.delete("/api/extensions/push-sources/{instance_handle}/{source_id}")
async def extension_push_source_delete(instance_handle: str, source_id: str):
    instance, _destination_url = _managed_push_source_access(instance_handle)
    try:
        revoked = revoke_push_source(source_id, instance.target_id, instance.id)
    except Exception as exc:
        _push_source_error(exc)
    if not revoked:
        raise HTTPException(status_code=404, detail="Push 来源不存在")
    return {"instance_handle": instance_handle, "revoked": True}


@app.patch("/api/extensions/push-sources/{instance_handle}/{source_id}/grant-delete")
async def extension_push_source_grant_delete(instance_handle: str, source_id: str, body: PushSourceGrantDeleteRequest):
    instance, _destination_url = _managed_push_source_access(instance_handle)
    try:
        updated = set_push_source_grant_delete(
            source_id, instance.target_id, instance.id, body.enabled
        )
    except Exception as exc:
        _push_source_error(exc)
    if not updated:
        raise HTTPException(status_code=404, detail="Push 来源不存在")
    return {
        "instance_handle": instance_handle,
        "source_id": source_id,
        "grant_delete": bool(body.enabled),
    }


def _save_managed_push_configuration(instance, destination_url: str, source_id: str, push_key: str) -> None:
    """Save only a newly issued key after the explicit local-save intent."""
    try:
        existing = credential_vault.get(instance.id)
    except KeyError:
        existing = ManagedCredential(genbox_push_key=push_key)
    values = existing.model_dump()
    values.update({"genbox_push_key": push_key, "genbox_push_source_id": source_id, "genbox_push_url": destination_url})
    credential_vault.upsert(instance.id, ManagedCredential(**values))


def _clear_managed_push_configuration(instance) -> None:
    """Remove only the local Push fields before a remote key rotation."""
    try:
        existing = credential_vault.get(instance.id)
    except (KeyError, PermissionError):
        return
    values = existing.model_dump()
    values.update({"genbox_push_key": "", "genbox_push_source_id": "", "genbox_push_url": ""})
    credential_vault.delete(instance.id)
    if any(value for value in values.values()):
        credential_vault.upsert(instance.id, ManagedCredential(**values))


def _local_push_save_error(exc: Exception) -> str:
    """Expose only a recovery category after a completed remote rotation."""
    if isinstance(exc, PermissionError):
        return "vault_locked"
    if isinstance(exc, RuntimeError):
        return "vault_unavailable"
    return "vault_save_failed"


@app.post("/api/extensions/vault/credentials/{instance_id}/push-key/confirmation")
async def extension_confirm_vault_save_push_key(
    instance_id: str, body: PushKeyLocalSaveConfirmationRequest,
):
    """Issue a short-lived, one-time confirmation bound to the displayed key."""
    instance = _managed_vault_instance(instance_id)
    try:
        _instance, _destination_url = _managed_push_source_access(instance_id)
        sources = list_push_sources(instance.target_id, instance.id)
        if not any(item.get("source_id") == body.source_id for item in sources):
            raise ValueError("Push source is no longer active; create or rotate again")
        if not source_key_belongs_to_instance(
            body.source_id, instance.target_id, instance.id, body.push_key,
        ):
            raise ValueError("Push key does not match the current managed source; create or rotate again")
        token, expires_in_seconds = _push_key_save_confirmations.issue(
            instance_id, body.source_id, body.push_key,
        )
        return {
            "confirmation_token": token,
            "expires_in_seconds": expires_in_seconds,
        }
    except Exception as exc:
        if isinstance(exc, ValueError) and str(exc).startswith("Push "):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _vault_error(exc)


@app.put("/api/extensions/vault/credentials/{instance_id}/push-key")
async def extension_vault_save_push_key(instance_id: str, body: PushKeyLocalSaveRequest):
    """Save a Push key only after consuming its server-issued confirmation."""
    instance = _managed_vault_instance(instance_id)
    try:
        if not _push_key_save_confirmations.consume(
            instance_id, body.source_id, body.push_key, body.confirmation_token,
        ):
            raise ValueError("Push-key local-save confirmation is missing, expired, replayed, or invalid")
        _instance, destination_url = _managed_push_source_access(instance_id)
        if destination_url != body.destination_url:
            raise ValueError("Push destination changed; create or rotate again")
        sources = list_push_sources(instance.target_id, instance.id)
        if not any(item.get("source_id") == body.source_id for item in sources):
            raise ValueError("Push source is no longer active; create or rotate again")
        if not source_key_belongs_to_instance(body.source_id, instance.target_id, instance.id, body.push_key):
            raise ValueError("Push key does not match the current managed source; create or rotate again")
        credential_vault._require_unlocked()
        _save_managed_push_configuration(instance, destination_url, body.source_id, body.push_key)
        return {"saved_locally": True, "remote_unchanged": True}
    except Exception as exc:
        if isinstance(exc, PermissionError):
            raise HTTPException(status_code=423, detail=str(exc)) from exc
        if isinstance(exc, OSError):
            raise HTTPException(status_code=503, detail="vault_save_failed") from exc
        if isinstance(exc, ValueError) and str(exc).startswith("Push"):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _vault_error(exc)


def _managed_vault_instance(instance_id: str):
    instance = _resolve_stored_instance_handle(instance_id)
    if (
        not instance
        or instance.managed is not True
        or str(instance.ownership or "") != "managed"
    ):
        raise HTTPException(status_code=404, detail="托管实例不存在")
    return instance


def _vault_error(exc: Exception):
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=423, detail=str(exc)) from exc
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail="未保存该实例凭证") from exc
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc


# Image updates are deliberately short-lived and single-use.  The plan binds
# an opaque public handle to an immutable image, while the SSH credential is
# retrieved only by the apply request after the vault has been unlocked.
_managed_image_update_plans: dict[str, dict] = {}
_managed_image_update_plans_lock = threading.RLock()
_MANAGED_IMAGE_UPDATE_PLAN_TTL_SECONDS = 300


class ManagedImageUpdateTaskManager:
    """Public-only task projection for the bounded managed-image update."""

    _TASK_ID_RE = re.compile(r"^iu-task-[a-f0-9]{16}$")
    _STATUSES = {"queued", "running", "completed", "failed", "interrupted"}
    _PHASES = {"queued", "connect", "update", "verify", "complete", "failed", "recovery"}
    _STEP_IDS = ("connect", "update", "verify")

    def __init__(self):
        self.path = STORAGE_DIR / "managed_image_update_tasks.json"
        self.lock = threading.RLock()
        self.tasks: dict[str, dict] = {}
        self.runners: dict[str, asyncio.Task] = {}
        self._load()

    def _load(self):
        try:
            payload = _json.loads(self.path.read_text(encoding="utf-8"))
            records = payload.get("tasks", []) if isinstance(payload, dict) else []
            self.tasks = {}
            for item in records:
                state = self._public_state(item)
                if state:
                    self.tasks[state["id"]] = state
        except (OSError, ValueError, TypeError):
            self.tasks = {}
        changed = False
        for state in self.tasks.values():
            if state.get("status") in {"queued", "running"}:
                state["status"] = "interrupted"
                state["phase"] = "recovery"
                state["error"] = "GenBox 重启时更新任务中断，请检查隔离实例后重新生成核对清单。"
                changed = True
        if changed:
            self._persist()

    def _persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        records = [state for state in (self._public_state(item) for item in self.tasks.values()) if state]
        temporary.write_text(_json.dumps({"tasks": records}, ensure_ascii=True), encoding="utf-8")
        os.replace(temporary, self.path)

    @classmethod
    def _public_state(cls, raw: dict | None) -> dict | None:
        """Return only the bounded, secret-free task projection."""
        if not isinstance(raw, dict):
            return None
        task_id = str(raw.get("id", ""))
        if not cls._TASK_ID_RE.fullmatch(task_id):
            return None
        status = str(raw.get("status", ""))
        if status not in cls._STATUSES:
            return None
        phase = str(raw.get("phase", "queued"))
        if phase not in cls._PHASES:
            phase = "recovery" if status == "interrupted" else "queued"
        try:
            progress = max(0, min(100, int(raw.get("progress", 0))))
        except (TypeError, ValueError):
            progress = 0
        handle = str(raw.get("instance_handle", ""))
        if re.fullmatch(r"i-[a-f0-9]{32}", handle) is None:
            return None
        image = str(raw.get("image", ""))
        if not is_immutable_image_reference(image):
            return None
        raw_steps = raw.get("steps", [])
        by_id = {item.get("id"): item for item in raw_steps if isinstance(item, dict)} if isinstance(raw_steps, list) else {}
        steps = []
        for step_id in cls._STEP_IDS:
            item = by_id.get(step_id, {})
            step_status = str(item.get("status", "pending"))
            if step_status not in {"pending", "running", "success", "failed", "interrupted"}:
                step_status = "pending"
            steps.append({"id": step_id, "status": step_status})
        logs = []
        raw_logs = raw.get("logs", [])
        if isinstance(raw_logs, list):
            for item in raw_logs[-100:]:
                if isinstance(item, dict):
                    logs.append({"time": str(item.get("time", ""))[:32], "message": str(item.get("message", ""))[:240]})
        state = {
            "id": task_id, "status": status, "phase": phase, "progress": progress,
            "instance_handle": handle, "image": image,
            "error": str(raw.get("error"))[:240] if raw.get("error") else None,
            "steps": steps, "logs": logs,
            "created_at": str(raw.get("created_at", ""))[:64], "updated_at": str(raw.get("updated_at", ""))[:64],
        }
        result = raw.get("result")
        if isinstance(result, dict) and isinstance(result.get("health_verified"), bool):
            state["result"] = {"health_verified": result["health_verified"]}
        return state

    def _state(self, task_id: str) -> dict | None:
        state = self.tasks.get(task_id)
        public = self._public_state(state)
        return _json.loads(_json.dumps(public, ensure_ascii=True)) if public else None

    def get(self, task_id: str) -> dict | None:
        with self.lock:
            return self._state(task_id)

    def list(self, instance_handle: str | None = None) -> list[dict]:
        with self.lock:
            states = [self._public_state(item) for item in self.tasks.values()]
            states = [item for item in states if item and (not instance_handle or item["instance_handle"] == instance_handle)]
            ordered = sorted(states, key=lambda item: item.get("updated_at", ""), reverse=True)
            return _json.loads(_json.dumps(ordered, ensure_ascii=True))

    def create(self, instance_handle: str, image: str, runner_factory) -> str:
        task_id = "iu-task-" + uuid.uuid4().hex[:16]
        now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        state = {
            "id": task_id, "status": "queued", "phase": "queued", "progress": 0,
            "instance_handle": instance_handle, "image": image, "error": None,
            "steps": [
                {"id": "connect", "status": "pending"},
                {"id": "update", "status": "pending"},
                {"id": "verify", "status": "pending"},
            ], "logs": [], "created_at": now, "updated_at": now,
        }
        with self.lock:
            self.tasks[task_id] = state
            self._persist()
            runner = asyncio.create_task(self._run(task_id, runner_factory))
            self.runners[task_id] = runner
        return task_id

    async def _run(self, task_id: str, runner_factory):
        def update(status, phase, progress, step_index=None, step_status=None, message=None):
            with self.lock:
                state = self.tasks.get(task_id)
                if not state:
                    return
                state.update({"status": status, "phase": phase, "progress": progress,
                              "updated_at": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")})
                if step_index is not None:
                    state["steps"][step_index]["status"] = step_status or status
                if message:
                    state["logs"].append({"time": time.strftime("%H:%M:%S"), "message": message})
                self._persist()
        try:
            update("running", "connect", 10, 0, "running", "正在连接隔离实例")
            update("running", "update", 25, 1, "running", "正在拉取并切换不可变镜像")
            result = await runner_factory()
            if not result.get("health_verified"):
                raise RuntimeError("health_verification_failed")
            update("running", "verify", 90, 2, "running", "健康检查通过，正在保存结果")
            with self.lock:
                state = self.tasks.get(task_id)
                if state:
                    state["status"] = "completed"; state["progress"] = 100; state["phase"] = "complete"
                    for step in state["steps"]: step["status"] = "success"
                    state["result"] = {"health_verified": True}
                    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                    self._persist()
        except asyncio.CancelledError:
            raise
        except Exception:
            with self.lock:
                state = self.tasks.get(task_id)
                if state:
                    state["status"] = "failed"; state["phase"] = "failed"; state["error"] = "镜像更新未完成，原实例配置已保留或已回滚。"
                    state["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
                    self._persist()
        finally:
            with self.lock:
                self.runners.pop(task_id, None)


managed_image_update_tasks = ManagedImageUpdateTaskManager()


def _managed_image_update_instance(instance_handle: str):
    if re.fullmatch(r"i-[a-f0-9]{32}", instance_handle or "") is None:
        raise HTTPException(status_code=404, detail="managed_instance_not_found")
    instance = _resolve_stored_instance_handle(instance_handle)
    if (
        not instance
        or not instance.managed
        or str(instance.ownership or "") != "managed"
        or instance.project != "chatgpt2api"
        or instance.strategy != "isolated"
        or instance.deployment_mode != "compose"
        or not hmac.compare_digest(public_instance_handle(instance.target_id, instance.id), instance_handle)
    ):
        raise HTTPException(status_code=404, detail="managed_instance_not_found")
    target = extensions_store.get_target(instance.target_id)
    if not target or target.target_role != "isolated-development":
        raise HTTPException(status_code=403, detail="isolated_development_only")
    return instance, target


def _stored_ssh_credential(instance, target) -> SSHCredential:
    saved = credential_vault.get(instance.id)
    if saved.ssh_password and saved.ssh_private_key:
        raise ValueError("saved_ssh_credential_invalid")
    if not saved.ssh_password and not saved.ssh_private_key:
        raise PermissionError("saved_ssh_credential_required")
    elevation = "password_sudo" if saved.sudo_password else "none"
    return SSHCredential(
        password=saved.ssh_password,
        private_key=saved.ssh_private_key,
        passphrase=saved.ssh_passphrase,
        sudo_password=saved.sudo_password,
        elevation=elevation,
    )


def _take_managed_image_update_plan(plan_id: str) -> dict:
    now = time.time()
    with _managed_image_update_plans_lock:
        expired = [key for key, item in _managed_image_update_plans.items()
                   if float(item.get("expires_at", 0)) <= now]
        for key in expired:
            _managed_image_update_plans.pop(key, None)
        plan = _managed_image_update_plans.get(plan_id)
        if plan:
            _managed_image_update_instance(plan.get("instance_handle", ""))
            _managed_image_update_plans.pop(plan_id, None)
    if not plan:
        raise HTTPException(status_code=409, detail="managed_image_update_plan_unavailable")
    return plan


@app.get("/api/extensions/vault/status")
async def extension_vault_status():
    return credential_vault.status()


@app.post("/api/extensions/vault/setup")
async def extension_vault_setup(body: VaultPasswordRequest):
    try:
        return credential_vault.setup(body.password)
    except Exception as exc:
        _vault_error(exc)


@app.post("/api/extensions/vault/unlock")
async def extension_vault_unlock(body: VaultPasswordRequest):
    try:
        return credential_vault.unlock(body.password)
    except Exception as exc:
        _vault_error(exc)


@app.post("/api/extensions/vault/lock")
async def extension_vault_lock():
    return credential_vault.lock()


@app.get("/api/extensions/vault/credentials")
async def extension_vault_list():
    try:
        credentials = []
        for item in credential_vault.list_metadata():
            instance = extensions_store.get_instance(item.get("instance_id", ""))
            if (
                not instance
                or instance.managed is not True
                or str(instance.ownership or "") != "managed"
            ):
                continue
            credentials.append({
                "instance_handle": public_instance_handle(instance.target_id, instance.id),
                "updated_at": item.get("updated_at", ""),
                "fields": list(item.get("fields", [])),
            })
        return {"credentials": credentials}
    except Exception as exc:
        _vault_error(exc)


@app.get("/api/extensions/vault/credentials/{instance_id}")
async def extension_vault_get(instance_id: str):
    instance = _managed_vault_instance(instance_id)
    try:
        return {
            "instance_handle": public_instance_handle(instance.target_id, instance.id),
            "credential": credential_vault.get(instance.id).model_dump(),
        }
    except Exception as exc:
        _vault_error(exc)


@app.put("/api/extensions/vault/credentials/{instance_id}")
async def extension_vault_upsert(instance_id: str, body: ManagedCredentialUpsertRequest):
    instance = _managed_vault_instance(instance_id)
    try:
        try:
            existing = credential_vault.get(instance.id)
        except KeyError:
            existing = None
        values = body.credential.model_dump()
        push_fields = ("genbox_push_key", "genbox_push_source_id", "genbox_push_url")
        submitted_push = any(values[name] for name in push_fields)
        if submitted_push:
            raise ValueError("GenBox Push configuration must use the dedicated confirmation flow")
        elif existing:
            old = existing.model_dump()
            values.update({name: old[name] for name in push_fields})
        saved = credential_vault.upsert(instance.id, ManagedCredential(**values))
        return {"credential": {
            "instance_handle": public_instance_handle(instance.target_id, instance.id),
            "updated_at": saved.get("updated_at", ""),
            "fields": list(saved.get("fields", [])),
        }}
    except Exception as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(("Push", "GenBox Push")):
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        _vault_error(exc)


@app.delete("/api/extensions/vault/credentials/{instance_id}")
async def extension_vault_delete(instance_id: str):
    instance = _managed_vault_instance(instance_id)
    try:
        if not credential_vault.delete(instance.id):
            raise KeyError(instance.id)
        return {"deleted": True}
    except Exception as exc:
        _vault_error(exc)


@app.delete("/api/extensions/vault/credentials/{instance_id}/push-key")
async def extension_vault_delete_push_key(instance_id: str):
    """Delete only the local Push-key fields; never revoke or alter the source."""
    instance = _managed_vault_instance(instance_id)
    try:
        saved = credential_vault.get(instance.id)
        values = saved.model_dump()
        values.update({"genbox_push_key": "", "genbox_push_source_id": "", "genbox_push_url": ""})
        if any(values.get(name) for name in ("admin_key", "ssh_password", "ssh_private_key", "username", "password", "api_key", "note")):
            credential_vault.upsert(instance.id, ManagedCredential(**values))
        else:
            credential_vault.delete(instance.id)
        return {"deleted": True, "remote_unchanged": True}
    except Exception as exc:
        _vault_error(exc)


@app.post("/api/extensions/instances/image-update/plan")
async def extension_managed_image_update_plan(body: ManagedImageUpdatePlanRequest):
    """Prepare a reviewed update for one GenBox-managed isolated instance."""
    if not is_immutable_image_reference(body.image):
        raise HTTPException(status_code=400, detail="immutable_image_required")
    instance, target = _managed_image_update_instance(body.instance_handle)
    try:
        # This checks that the vault is unlocked and contains a usable SSH
        # credential without returning or persisting any secret material.
        _stored_ssh_credential(instance, target)
    except Exception as exc:
        _vault_error(exc)
    plan_id = "iu-" + secrets.token_urlsafe(24)
    expires_at = time.time() + _MANAGED_IMAGE_UPDATE_PLAN_TTL_SECONDS
    plan = {
        "plan_id": plan_id,
        "instance_id": instance.id,
        "instance_handle": body.instance_handle,
        "target_id": target.id,
        "image": body.image.strip(),
        "expires_at": expires_at,
    }
    with _managed_image_update_plans_lock:
        _managed_image_update_plans[plan_id] = plan
    return {
        "plan_id": plan_id,
        "instance_handle": body.instance_handle,
        "image": body.image.strip(),
        "expires_at": int(expires_at),
        "operations": ["pull_immutable_image", "backup_configuration", "recreate_app", "verify_health"],
    }


@app.post("/api/extensions/instances/image-update/apply")
async def extension_managed_image_update_apply(body: ManagedImageUpdateApplyRequest):
    """Consume one update plan and return a task immediately."""
    plan = _take_managed_image_update_plan(body.plan_id)
    instance, target = _managed_image_update_instance(plan["instance_handle"])
    if instance.id != plan["instance_id"] or target.id != plan["target_id"]:
        raise HTTPException(status_code=409, detail="managed_image_update_context_changed")
    try:
        credential = _stored_ssh_credential(instance, target)
    except Exception as exc:
        _vault_error(exc)

    async def run_update():
        try:
            return await update_managed_image(
                instance_id=instance.id, target=target, credential=credential, image=plan["image"],
            )
        finally:
            credential.password = None
            credential.private_key = None
            credential.passphrase = None
            credential.sudo_password = None

    task_id = managed_image_update_tasks.create(plan["instance_handle"], plan["image"], run_update)
    return {"ok": True, "task_id": task_id, "instance_handle": plan["instance_handle"], "image": plan["image"]}


@app.get("/api/extensions/instances/image-update/tasks")
async def extension_managed_image_update_task_list(instance_handle: str | None = None):
    if instance_handle and re.fullmatch(r"i-[a-f0-9]{32}", instance_handle) is None:
        raise HTTPException(status_code=400, detail="managed_instance_handle_invalid")
    if instance_handle:
        _managed_image_update_instance(instance_handle)
    return {"tasks": managed_image_update_tasks.list(instance_handle)}


@app.get("/api/extensions/instances/image-update/tasks/{task_id}")
async def extension_managed_image_update_task_status(task_id: str):
    state = managed_image_update_tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="managed_image_update_task_not_found")
    _managed_image_update_instance(state["instance_handle"])
    return state


@app.post("/api/extensions/instances/reset-admin-key")
async def extension_reset_admin_key(body: ExtensionKeyResetRequest):
    body = _bind_confirmed_extension_target(body)
    try:
        instance = _resolve_stored_instance_handle(body.instance_id, body.target.id)
        if not instance:
            raise PermissionError("managed_instance_not_found")
        body = body.model_copy(update={"instance_id": instance.id})
        return await reset_managed_admin_key(body)
    except Exception as exc:
        raise _safe_extension_ssh_error(
            exc,
            error="管理员密钥轮换未完成，原始错误已隐藏。",
            code="extension_key_reset_failed",
            stage="admin_key_reset",
        ) from exc


@app.post("/api/extensions/tasks/{task_id}/cancel")
async def extension_cancel_task(task_id: str):
    if not extension_tasks.cancel(task_id):
        raise HTTPException(status_code=409, detail="任务无法取消")
    return {"cancelled": True}


@app.post("/api/extensions/network/connect")
async def extension_connect_network(body: NetworkConnectRequest):
    body = _bind_confirmed_extension_target(body)
    task_id = network_tasks.create(body)
    return {"task_id": task_id}


@app.get("/api/extensions/network/local/tailscale/status")
async def extension_local_tailscale_status():
    return await asyncio.to_thread(local_status)


@app.post("/api/extensions/network/local/tailscale/install")
async def extension_local_tailscale_install():
    return {"task_id": local_install_tasks.create()}


@app.get("/api/extensions/network/local/tailscale/install/{task_id}")
async def extension_local_tailscale_install_status(task_id: str):
    state = local_install_tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="安装任务不存在")
    return state


@app.post("/api/extensions/network/local/tailscale/login")
async def extension_local_tailscale_login():
    try:
        return await asyncio.to_thread(begin_login)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:240]) from exc


@app.post("/api/extensions/network/local/tailscale/serve")
async def extension_local_tailscale_serve():
    try:
        return await asyncio.to_thread(enable_genbox_serve)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)[:240]) from exc


@app.get("/api/extensions/network/tasks/{task_id}")
async def extension_network_task_status(task_id: str):
    state = network_tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="连接任务不存在")
    return state


# ──────────────────────────────────────────────────────────────
# 静态文件（必须在所有 API 路由之后挂载）
# ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")


# ──────────────────────────────────────────────────────────────
# 启动
# ──────────────────────────────────────────────────────────────
def _first_run_setup() -> None:
    """Collect the initial deployment mode without using an HTTP bootstrap."""
    from config import _read_env, _write_env

    if "--reset-admin" in sys.argv:
        new_key = reset_admin_key()
        print("[Admin Reset] A new administrator key was generated.")
        print(new_key)
        raise SystemExit(0)

    if "APP_MODE" in _read_env() or os.environ.get("APP_MODE", "").strip():
        return

    interactive = bool(
        sys.stdin is not None
        and hasattr(sys.stdin, "isatty")
        and sys.stdin.isatty()
    )
    if not interactive:
        _write_env({"APP_MODE": "prod"})
        print(
            "[Setup] Non-interactive startup selected production mode / "
            "非交互式启动已选择生产模式。Configure ADMIN_KEY in the executable "
            "data .env before starting / 请先在可执行文件数据目录的 .env 中配置 ADMIN_KEY。"
        )
        return

    print("GenBox first-run setup / GenBox 首次启动设置")
    print("[1] Local desktop / 本地桌面（开发模式，仅限本机）")
    print("[2] Server/VPS / 服务器或 VPS（带身份认证的生产模式）")
    print("[3] Docker/headless / Docker 或无界面（生产模式；需手动配置 ADMIN_KEY）")

    while True:
        try:
            choice = input("Select deployment mode (1/2/3) / 选择部署模式（1/2/3）：").strip()
        except (EOFError, KeyboardInterrupt):
            _write_env({"APP_MODE": "prod"})
            print(
                "[Setup] Input ended; production mode selected / 输入结束，已选择生产模式。"
                " Configure ADMIN_KEY before starting / 启动前请配置 ADMIN_KEY。"
            )
            return

        if choice == "1":
            _write_env({"APP_MODE": "dev"})
            print("[Setup] Local mode enabled; access is restricted to this computer. / "
                  "本地模式已启用；访问仅限此电脑。")
            return

        if choice == "2":
            _write_env({"APP_MODE": "prod"})
            origins = input(
                "Allowed browser origins / 允许的浏览器来源（逗号分隔，回车使用默认值）："
            ).strip()
            if origins:
                _write_env({"ALLOWED_ORIGINS": origins})
            admin_key = generate_admin_key()
            print("[Setup] Production mode enabled. Save this administrator key now. / "
                  "生产模式已启用，请立即保存管理员密钥：")
            print(admin_key)
            return

        if choice == "3":
            _write_env({"APP_MODE": "prod"})
            print(
                "[Setup] Docker/headless production mode enabled. / Docker 或无界面生产模式已启用。"
                " Set ADMIN_KEY in .env before starting the service. / 启动服务前请在 .env 中设置 ADMIN_KEY。"
            )
            return

        print("[Setup] Enter 1, 2, or 3. / 请输入 1、2 或 3。")


def prepare_runtime_environment(executable_data_dir: Path, bundle_dir: Path) -> Optional[Path]:
    """Reload runtime environment from user data, falling back to bundle defaults."""
    from dotenv import load_dotenv
    from config import PROCESS_ENV_APP_MODE, PROCESS_ENV_GENBOX_PORT

    executable_env = Path(executable_data_dir) / ".env"
    bundle_env = Path(bundle_dir) / ".env"
    selected_env = executable_env if executable_env.is_file() else bundle_env
    if selected_env.is_file():
        load_dotenv(selected_env, override=True)
    if PROCESS_ENV_APP_MODE is not None:
        os.environ["APP_MODE"] = PROCESS_ENV_APP_MODE
    if PROCESS_ENV_GENBOX_PORT is not None:
        os.environ["GENBOX_PORT"] = PROCESS_ENV_GENBOX_PORT

    cfg_mgr._config = None
    return selected_env if selected_env.is_file() else None


def _require_production_admin_key(app_mode: str) -> None:
    if app_mode != "prod" or get_admin_key():
        return
    raise SystemExit(
        "[Security] Startup blocked: production mode requires ADMIN_KEY in the "
        "executable data .env. Configure it before starting Docker or headless mode."
    )


def run_http_server(app_mode: str, port: int, host: Optional[str] = None) -> None:
    """Run Uvicorn with loopback enforced for unauthenticated development mode."""
    normalized_mode = app_mode.strip().lower()
    resolved_host = "127.0.0.1" if normalized_mode == "dev" else (host or "0.0.0.0")
    uvicorn.run(
        app,
        host=resolved_host,
        port=port,
        reload=False,
        use_colors=False,
    )


def run_application() -> None:
    """Prepare first-run state, reload it in-process, enforce auth, and serve."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    _first_run_setup()
    prepare_runtime_environment(BASE_DIR, BASE_PATH)

    configured_mode = os.getenv("APP_MODE", "prod").strip().lower()
    app_mode = "dev" if configured_mode == "dev" else "prod"
    try:
        port = int(os.getenv("GENBOX_PORT", "8891"))
    except ValueError as exc:
        raise SystemExit("[Startup] GENBOX_PORT must be a valid integer / GENBOX_PORT 必须是有效整数。") from exc
    if not 1 <= port <= 65535:
        raise SystemExit("[Startup] GENBOX_PORT must be between 1 and 65535 / GENBOX_PORT 必须在 1 到 65535 之间。")

    _require_production_admin_key(app_mode)

    local_host = "127.0.0.1" if app_mode == "dev" else "localhost"
    local_url = f"http://{local_host}:{port}"
    mode_str = "PRODUCTION" if is_prod_mode() else "DEVELOPMENT"
    mode_label = f"{mode_str} / {'生产模式' if is_prod_mode() else '开发模式'}"
    print(f"[GenBox] v{__version__} | {mode_label} | {local_url}")
    print(f"[GenBox] Media / 媒体目录: {GALLERY_DIR}")
    print(f"[GenBox] Providers / Provider 配置: {STORAGE_DIR / 'providers.json'}")

    if (
        getattr(sys, "frozen", False)
        and os.getenv("GENBOX_NO_BROWSER", "").lower() not in {"1", "true", "yes"}
    ):
        def _open_browser() -> None:
            time.sleep(1.5)
            try:
                webbrowser.open(local_url)
            except Exception:
                pass

        threading.Thread(target=_open_browser, daemon=True).start()

    run_http_server(app_mode, port)


if __name__ == "__main__":
    run_application()

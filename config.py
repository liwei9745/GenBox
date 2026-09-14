"""
全局配置：动态 Provider 注册系统
- storage/providers.json: 运行时配置（前端可写）
- .env: 默认值兜底
"""
import json
import os
import re
import sys
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlsplit
from pydantic import BaseModel

from dotenv import load_dotenv

# Capture trusted process injection before any dotenv file can mutate os.environ.
# Runtime reloads may override other values, but orchestrator-provided runtime
# mode and container port must remain authoritative over .env values.
PROCESS_ENV_APP_MODE = (
    os.environ["APP_MODE"] if "APP_MODE" in os.environ else None
)
PROCESS_ENV_GENBOX_PORT = (
    os.environ["GENBOX_PORT"] if "GENBOX_PORT" in os.environ else None
)

# ──────────────────────────────────────────────────────────────
# PyInstaller 路径兼容
# ──────────────────────────────────────────────────────────────
def get_base_dir() -> Path:
    """获取基础目录（兼容 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后，配置文件放在可执行文件同目录
        return Path(sys.executable).parent
    else:
        # 源码运行
        return Path(__file__).parent

BASE_DIR = get_base_dir()

# 加载 .env（优先从可执行文件目录加载）
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # 尝试从 _MEIPASS 加载（打包后的临时目录）
    if getattr(sys, 'frozen', False):
        load_dotenv(Path(sys._MEIPASS) / ".env", override=False)

# 运行时数据目录（始终放在可执行文件同目录）
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(exist_ok=True)
GALLERY_DIR = STORAGE_DIR / "gallery"
GALLERY_DIR.mkdir(exist_ok=True)

PROVIDERS_FILE = STORAGE_DIR / "providers.json"


def verify_ssl_enabled() -> bool:
    """Verify outbound TLS unless an operator explicitly opts out."""
    configured = os.getenv("VERIFY_SSL")
    if configured is None:
        return True
    return configured.strip().lower() not in {"false", "0", "no", "off"}


# ──────────────────────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────────────────────
class EndpointConfig(BaseModel):
    """单个端点配置（URL + API Key）"""
    url: str = ""
    key: str = ""
    enabled: bool = True
    name: str = ""             # 端点备注名（可选）

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        short_url = self.url.replace("https://", "").replace("http://", "")
        if len(short_url) > 30:
            short_url = short_url[:30] + "..."
        return short_url


def _is_masked_secret(value: str) -> bool:
    return "****" in str(value or "")


class PrecisionEditProfile(str, Enum):
    """Allowlisted request shapes for annotation-based image editing."""

    OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE = (
        "openai_images_edits_multipart_repeated_image"
    )
    OPENAI_IMAGES_EDITS_MULTIPART_IMAGE_ARRAY = (
        "openai_images_edits_multipart_image_array"
    )
    OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE = (
        "openai_images_edits_multipart_single_source_image"
    )
    OPENAI_IMAGES_EDITS_JSON_DATA_URL_SINGLE_SOURCE_IMAGE = (
        "openai_images_edits_json_data_url_single_source_image"
    )
    GEMINI_GENERATE_CONTENT = "gemini_generate_content"


PRECISION_EDIT_CAPABILITY = "precision_edit"
PRECISION_MODEL_ALIAS_FIELDS = ("alias_of", "canonical_model")
PRECISION_MODEL_SIZE_FIELDS = ("supported_sizes", "supportedSizes", "sizes", "dimensions")
PRECISION_MODEL_SIZE_POLICY_FIELD = "size_policy"
PRECISION_GPT_IMAGE_2_FLEXIBLE_SIZE_POLICY = "gpt_image_2_flexible"
PRECISION_MODEL_ALIAS_MAX_DEPTH = 1
PRECISION_MODEL_DEFAULT_MAX_OUTPUT_PIXELS = 64 * 1024 * 1024

# Exact-size legality for the documented gpt-image-2 image protocol.  These
# limits intentionally remain separate from the generic capability validator:
# custom/OpenAI-compatible providers may expose legacy dimensions such as
# 64x64, while gpt-image-2 requests must satisfy the protocol itself.
GPT_IMAGE_2_SIZE_ALIGNMENT = 16
GPT_IMAGE_2_MIN_OUTPUT_PIXELS = 655_360
GPT_IMAGE_2_MAX_OUTPUT_PIXELS = 8_294_400
GPT_IMAGE_2_MAX_SIDE = 3_840
GPT_IMAGE_2_EXPERIMENTAL_MAX_WIDTH = 2_560
GPT_IMAGE_2_EXPERIMENTAL_MAX_HEIGHT = 1_440
GPT_IMAGE_2_CANONICAL_PRESETS = {
    "1k": "1024x1024",
    "2k": "2048x1152",
    "4k": "3840x2160",
}

# This is a documentation catalogue, not a provider capability grant.  The
# public GPT Image 2 documentation names the three standard GPT Image sizes,
# gives 1536x864 as a flexible-size example, recommends QHD as a dependable
# upper target, and labels UHD-class requests as experimental.  A gateway can
# still return a different canvas, so strict dispatch must continue to use
# only the selected connection's explicit ``supported_sizes`` declaration.
GPT_IMAGE_2_DOCUMENTED_SIZE_PRESETS = (
    {
        "id": "standard-square",
        "size": "1024x1024",
        "tier": "standard",
        "ratio": "1:1",
        "evidence": "official_standard",
        "experimental": False,
    },
    {
        "id": "standard-landscape",
        "size": "1536x1024",
        "tier": "standard",
        "ratio": "3:2",
        "evidence": "official_standard",
        "experimental": False,
    },
    {
        "id": "standard-portrait",
        "size": "1024x1536",
        "tier": "standard",
        "ratio": "2:3",
        "evidence": "official_standard",
        "experimental": False,
    },
    {
        "id": "flexible-example-landscape",
        "size": "1536x864",
        "tier": "flexible",
        "ratio": "16:9",
        "evidence": "official_example",
        "experimental": False,
    },
    {
        "id": "qhd-landscape",
        "size": "2560x1440",
        "tier": "2k",
        "ratio": "16:9",
        "evidence": "official_recommended",
        "experimental": False,
    },
    {
        "id": "uhd-landscape",
        "size": "3840x2160",
        "tier": "4k",
        "ratio": "16:9",
        "evidence": "official_experimental",
        "experimental": True,
    },
)

GPT_IMAGE_DOCUMENTED_STANDARD_MODELS = frozenset(
    {"gpt-image-1", "gpt-image-1.5", "gpt-image-1-mini"}
)

# Gemini image models use the native GenerateContent imageConfig contract.
# These are documentation presets only: a provider/model still needs an
# explicit precision capability record before dispatch is authorized.
GEMINI_NATIVE_IMAGE_MODELS = frozenset({
    "gemini-2.5-flash-image",
    "gemini-3-pro-image",
    "gemini-3.1-flash-image",
})
GEMINI_25_FLASH_IMAGE = "gemini-2.5-flash-image"
GEMINI_3_PRO_IMAGE = "gemini-3-pro-image"
GEMINI_31_FLASH_IMAGE = "gemini-3.1-flash-image"

def _gemini_preset(size: str, ratio: str, tier: str, *, image_size: Optional[str] = None) -> Dict[str, Any]:
    item = {
        "id": f"gemini-{tier.lower()}-{ratio.replace(':', 'x')}",
        "size": size,
        "tier": tier,
        "ratio": ratio,
        "evidence": "official_native_image_config",
        "experimental": False,
        "provider": "gemini",
        "image_config": {"aspectRatio": ratio},
    }
    if image_size is not None:
        item["image_config"]["imageSize"] = image_size
    return item


def gemini_precision_model_presets(canonical_model: object) -> Tuple[Dict[str, Any], ...]:
    """Return native Gemini GenerateContent presets for one exact model.

    The returned values describe request mapping only. They do not grant
    precision editing or provider access, and unsupported arbitrary dimensions
    must not be synthesized from these ratios.
    """
    model = str(canonical_model or "").strip()
    if model == GEMINI_25_FLASH_IMAGE:
        table = {
            "1:1": "1024x1024", "2:3": "832x1248", "3:2": "1248x832",
            "9:16": "768x1344", "16:9": "1344x768", "21:9": "1536x672",
        }
        return tuple(_gemini_preset(size, ratio, "1K") for ratio, size in table.items())
    if model == GEMINI_3_PRO_IMAGE:
        tables = {
            "1K": {
                "1:1": "1024x1024", "2:3": "848x1264", "3:2": "1264x848",
                "4:5": "928x1152", "5:4": "1152x928", "9:16": "768x1376",
                "16:9": "1376x768", "21:9": "1584x672",
            },
            "2K": {
                "1:1": "2048x2048", "2:3": "1696x2528", "3:2": "2528x1696",
                "4:5": "1856x2304", "5:4": "2304x1856", "9:16": "1536x2752",
                "16:9": "2752x1536", "21:9": "3168x1344",
            },
            "4K": {
                "1:1": "4096x4096", "2:3": "3392x5056", "3:2": "5056x3392",
                "4:5": "3712x4608", "5:4": "4608x3712", "9:16": "3072x5504",
                "16:9": "5504x3072", "21:9": "6336x2688",
            },
        }
        return tuple(
            _gemini_preset(size, ratio, tier, image_size=tier)
            for tier, table in tables.items()
            for ratio, size in table.items()
        )
    if model == GEMINI_31_FLASH_IMAGE:
        table = {
            "1:1": (1024, 1024), "1:4": (512, 2048), "1:8": (384, 3072),
            "2:3": (848, 1264), "3:2": (1264, 848), "3:4": (896, 1200),
            "4:1": (2048, 512), "4:3": (1200, 896), "4:5": (928, 1152),
            "5:4": (1152, 928), "8:1": (3072, 384), "9:16": (768, 1376),
            "16:9": (1376, 768), "21:9": (1584, 672),
        }
        presets = []
        for tier, numerator, denominator in (("512", 1, 2), ("1K", 1, 1), ("2K", 2, 1), ("4K", 4, 1)):
            for ratio, (width, height) in table.items():
                # Google's published 512/21:9 row is internally inconsistent;
                # do not invent dimensions pending clarification. Extreme 4K
                # rows exceed the application's existing 8192-side limit.
                if tier == "512" and ratio == "21:9":
                    continue
                size = f"{width * numerator // denominator}x{height * numerator // denominator}"
                if normalize_precision_capability_size(size):
                    presets.append(_gemini_preset(size, ratio, tier, image_size=tier))
        return tuple(presets)
    return ()


def gemini_precision_preset_for_size(canonical_model: object, size: object) -> Optional[Dict[str, Any]]:
    normalized = normalize_precision_capability_size(size)
    if not normalized:
        return None
    for preset in gemini_precision_model_presets(canonical_model):
        if preset["size"] == normalized:
            return dict(preset)
    return None


def documented_precision_model_size_presets(canonical_model: object) -> Tuple[Dict[str, Any], ...]:
    """Return non-authorizing model-documentation presets for one canonical model.

    This helper deliberately does not infer gateway support.  Consumers must
    intersect any display catalogue with persisted model capability metadata
    before enabling a strict resize submission.
    """
    if canonical_model in GPT_IMAGE_DOCUMENTED_STANDARD_MODELS:
        return tuple(item for item in GPT_IMAGE_2_DOCUMENTED_SIZE_PRESETS if item["tier"] == "standard")
    if canonical_model != "gpt-image-2":
        return gemini_precision_model_presets(canonical_model)
    return tuple(dict(item) for item in GPT_IMAGE_2_DOCUMENTED_SIZE_PRESETS)


@dataclass(frozen=True)
class PrecisionModelCapabilityResolution:
    """Fail-closed effective capability for one selected provider model."""

    selected_model: str
    canonical_model: str = ""
    capability: Optional[Dict[str, Any]] = None
    supported_sizes: Tuple[str, ...] = ()
    alias_depth: int = 0
    structure_valid: bool = False
    precision_edit_confirmed: bool = False
    size_declaration_present: bool = False
    size_declaration_valid: bool = False
    flexible_sizes: bool = False
    reason: str = "precision_model_unknown"


def normalize_precision_capability_size(
    value: object,
    *,
    max_output_pixels: int = PRECISION_MODEL_DEFAULT_MAX_OUTPUT_PIXELS,
) -> Optional[str]:
    """Accept only canonical WIDTHxHEIGHT strings within precision limits."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"([1-9]\d{1,4})x([1-9]\d{1,4})", value)
    if not match:
        return None
    width, height = int(match.group(1)), int(match.group(2))
    if (
        width < 64
        or height < 64
        or width > 8192
        or height > 8192
        or width * height > max_output_pixels
    ):
        return None
    normalized = f"{width}x{height}"
    return normalized if normalized == value else None


def gpt_image_2_size_error(value: object) -> Optional[Tuple[str, str]]:
    """Return a structured legality error for one exact gpt-image-2 size.

    This helper does not inspect provider declarations.  A size can be legal
    under the upstream protocol and still be rejected later when the selected
    provider/model has not explicitly declared support for it.
    """
    if not isinstance(value, str):
        return "precision_target_size_invalid", "size must be WIDTHxHEIGHT"
    match = re.fullmatch(r"([1-9]\d{1,4})x([1-9]\d{1,4})", value)
    if not match:
        return "precision_target_size_invalid", "size must be WIDTHxHEIGHT"
    width, height = int(match.group(1)), int(match.group(2))
    if width > GPT_IMAGE_2_MAX_SIDE or height > GPT_IMAGE_2_MAX_SIDE:
        return "precision_target_size_side_exceeded", "gpt-image-2 dimensions cannot exceed 3840 pixels per side"
    if width % GPT_IMAGE_2_SIZE_ALIGNMENT or height % GPT_IMAGE_2_SIZE_ALIGNMENT:
        return "precision_target_size_alignment_invalid", "gpt-image-2 dimensions must be divisible by 16"
    ratio = width / height
    if ratio < (1 / 3) or ratio > 3:
        return "precision_target_size_aspect_invalid", "gpt-image-2 aspect ratio must be between 1:3 and 3:1"
    pixels = width * height
    if pixels < GPT_IMAGE_2_MIN_OUTPUT_PIXELS:
        return "precision_target_size_pixels_too_small", "gpt-image-2 output must contain at least 655360 pixels"
    if pixels > GPT_IMAGE_2_MAX_OUTPUT_PIXELS:
        return "precision_target_size_pixels_exceeded", "gpt-image-2 output cannot exceed 8294400 pixels"
    return None


def validate_gpt_image_2_size(value: object) -> Tuple[bool, str]:
    """Return ``(is_valid, reason_code)`` for an exact gpt-image-2 size."""
    error = gpt_image_2_size_error(value)
    return (error is None, "" if error is None else error[0])


def precision_capability_size_declaration(
    capability: object,
    *,
    max_output_pixels: int = PRECISION_MODEL_DEFAULT_MAX_OUTPUT_PIXELS,
) -> Tuple[bool, bool, Tuple[str, ...], str]:
    """Return strict size metadata without accepting partial invalid declarations."""
    if not isinstance(capability, dict):
        return False, False, (), "precision_size_declaration_missing"

    present_fields = [field for field in PRECISION_MODEL_SIZE_FIELDS if field in capability]
    if not present_fields:
        return False, False, (), "precision_size_declaration_missing"

    field_sizes = []
    for field in present_fields:
        raw_values = capability[field]
        if isinstance(raw_values, str):
            values = [raw_values]
        elif isinstance(raw_values, (list, tuple)):
            values = list(raw_values)
        else:
            return True, False, (), "precision_size_declaration_invalid"
        if not values:
            return True, False, (), "precision_size_declaration_invalid"

        sizes = []
        seen = set()
        for value in values:
            normalized = normalize_precision_capability_size(
                value,
                max_output_pixels=max_output_pixels,
            )
            if normalized is None:
                return True, False, (), "precision_size_declaration_invalid"
            if normalized not in seen:
                sizes.append(normalized)
                seen.add(normalized)
        field_sizes.append(tuple(sizes))

    first_sizes = field_sizes[0]
    first_set = set(first_sizes)
    if any(set(sizes) != first_set for sizes in field_sizes[1:]):
        return True, False, (), "precision_size_declaration_collision"
    return True, True, first_sizes, ""


def precision_capability_flexible_size_policy(capability: object) -> Tuple[bool, bool, str]:
    """Read the opt-in flexible-size policy without treating unknown values as safe.

    The policy is intentionally separate from ``supported_sizes``: a precise
    whitelist remains the default for every model, while the GPT Image 2
    envelope can be explicitly enabled only after operator confirmation.
    """
    if not isinstance(capability, dict):
        return False, False, "precision_size_policy_invalid"
    if PRECISION_MODEL_SIZE_POLICY_FIELD not in capability:
        return True, False, ""
    value = capability.get(PRECISION_MODEL_SIZE_POLICY_FIELD)
    if value == PRECISION_GPT_IMAGE_2_FLEXIBLE_SIZE_POLICY:
        return True, True, ""
    return False, False, "precision_size_policy_invalid"


def _precision_model_alias_target(capability: object) -> Tuple[Optional[str], str]:
    if not isinstance(capability, dict):
        return None, ""
    present_fields = [field for field in PRECISION_MODEL_ALIAS_FIELDS if field in capability]
    if not present_fields:
        return None, ""

    targets = []
    for field in present_fields:
        raw_target = capability[field]
        if not isinstance(raw_target, str) or not raw_target or raw_target != raw_target.strip():
            return None, "precision_alias_target_invalid"
        targets.append(raw_target)
    if len(set(targets)) != 1:
        return None, "precision_alias_target_collision"
    return targets[0], ""


def resolve_precision_model_capability(
    model_capabilities: object,
    selected_model: object,
    *,
    max_output_pixels: int = PRECISION_MODEL_DEFAULT_MAX_OUTPUT_PIXELS,
) -> PrecisionModelCapabilityResolution:
    """Resolve one direct alias to one canonical capability without name guessing."""
    model_id = selected_model if isinstance(selected_model, str) else ""
    if not model_id or model_id != model_id.strip() or not isinstance(model_capabilities, dict):
        return PrecisionModelCapabilityResolution(selected_model=model_id)

    selected = model_capabilities.get(model_id)
    if model_id in model_capabilities and not isinstance(selected, dict):
        return PrecisionModelCapabilityResolution(
            selected_model=model_id,
            reason="precision_model_record_invalid",
        )
    if selected is None:
        selected = {}

    alias_target, alias_error = _precision_model_alias_target(selected)
    if alias_error:
        return PrecisionModelCapabilityResolution(selected_model=model_id, reason=alias_error)

    canonical_model = model_id
    canonical = selected
    alias_depth = 0
    if alias_target is not None:
        if alias_target == model_id:
            return PrecisionModelCapabilityResolution(
                selected_model=model_id,
                reason="precision_alias_cycle",
            )
        alias_depth = 1
        canonical_model = alias_target
        canonical = model_capabilities.get(canonical_model)
        if not isinstance(canonical, dict):
            return PrecisionModelCapabilityResolution(
                selected_model=model_id,
                canonical_model=canonical_model,
                alias_depth=alias_depth,
                reason="precision_alias_target_unknown",
            )
        next_target, next_error = _precision_model_alias_target(canonical)
        if next_error:
            return PrecisionModelCapabilityResolution(
                selected_model=model_id,
                canonical_model=canonical_model,
                alias_depth=alias_depth,
                reason=next_error,
            )
        if next_target is not None:
            reason = (
                "precision_alias_cycle"
                if next_target in {model_id, canonical_model}
                else "precision_alias_chain_too_deep"
            )
            return PrecisionModelCapabilityResolution(
                selected_model=model_id,
                canonical_model=canonical_model,
                alias_depth=alias_depth,
                reason=reason,
            )

    size_present, size_valid, sizes, size_reason = precision_capability_size_declaration(
        canonical,
        max_output_pixels=max_output_pixels,
    )
    policy_valid, flexible_sizes, policy_reason = precision_capability_flexible_size_policy(canonical)
    precision_confirmed = canonical.get(PRECISION_EDIT_CAPABILITY) is True
    reason = ""
    if not precision_confirmed:
        reason = "precision_edit_unconfirmed"
    elif not size_present:
        reason = "precision_size_declaration_missing"
    elif not size_valid:
        reason = size_reason
    elif not policy_valid:
        reason = policy_reason

    return PrecisionModelCapabilityResolution(
        selected_model=model_id,
        canonical_model=canonical_model,
        capability=canonical,
        supported_sizes=sizes,
        alias_depth=alias_depth,
        structure_valid=True,
        precision_edit_confirmed=precision_confirmed,
        size_declaration_present=size_present,
        size_declaration_valid=size_valid,
        flexible_sizes=flexible_sizes and policy_valid,
        reason=reason,
    )


class ProviderConfig(BaseModel):
    """单个 Provider 配置"""
    id: str                    # 唯一标识 (如 gpt-image, gemini, my-flux)
    name: str                  # 显示名称 (如 GPT Image 2)
    type: str                  # "image" | "llm" | "video"
    api_key: str = ""
    api_keys: List[str] = []   # 多账号轮询（优先于 api_key）
    base_url: str = ""
    endpoints: List[EndpointConfig] = []  # 多端点（URL+Key），用于端点轮询/容灾
    model: str = ""            # 默认模型 ID
    models: List[str] = []     # 可选模型列表（用于下拉选择）
    size: str = ""             # 图片尺寸（仅 image 类型）
    quality: str = ""          # 图片质量（仅 image 类型）
    enabled: bool = True
    color: str = "#0ea5e9"     # UI 卡片颜色
    display_name: str = ""     # 看板分组显示名称（空=使用 name）
    capabilities: Dict[str, bool] = {}  # 能力声明: {"t2i": True, "i2i": True, "i2v": False}
    precision_edit_profile: Optional[PrecisionEditProfile] = None
    skip_proxy: bool = False   # 跳过全局代理（直连）
    endpoint_type: str = "auto"  # 端点协议类型: auto|openai|gemini|qwen|agnes|volc_ark_plan|volc_ark
    extra: Dict[str, Any] = {} # 扩展参数

    def get_effective_keys(self) -> List[str]:
        """获取有效的 API Key 列表（api_keys 优先，fallback 到 api_key）"""
        keys = [k for k in (self.api_keys or []) if k and k.strip() and not _is_masked_secret(k)]
        if not keys and self.api_key and self.api_key.strip() and not _is_masked_secret(self.api_key):
            keys = [self.api_key.strip()]
        return keys

    def get_active_endpoints(self) -> List[EndpointConfig]:
        """获取启用的端点列表；如果没有端点则从 base_url+api_key 构造一个"""
        active = [
            ep for ep in (self.endpoints or [])
            if ep.enabled and ep.url and ep.key and not _is_masked_secret(ep.key)
        ]
        if active:
            return active
        effective_keys = self.get_effective_keys()
        if self.base_url and effective_keys:
            key = effective_keys[0] if effective_keys else self.api_key
            return [EndpointConfig(url=self.base_url, key=key)]
        return []


def normalize_precision_model_override(value: object) -> Dict[str, Any]:
    """Validate only supported per-model transports; never accept request templates."""
    if not isinstance(value, dict):
        raise ValueError("precision protocol override must be an object")
    protocol = value.get("protocol")
    if protocol not in {"openai", "gemini"}:
        raise ValueError("precision protocol override requires openai or gemini")
    default_profile = (
        PrecisionEditProfile.GEMINI_GENERATE_CONTENT
        if protocol == "gemini"
        else PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE
    )
    try:
        profile = PrecisionEditProfile(value.get("profile") or default_profile)
    except (TypeError, ValueError):
        raise ValueError("precision protocol profile is unsupported") from None
    if (profile == PrecisionEditProfile.GEMINI_GENERATE_CONTENT) != (protocol == "gemini"):
        raise ValueError("precision protocol and request profile do not match")
    size_model = value.get("size_model", "")
    if not isinstance(size_model, str) or (
        size_model and not documented_precision_model_size_presets(size_model)
    ):
        raise ValueError("precision size model must be a documented model family")
    capabilities = value.get("capabilities", {})
    if not isinstance(capabilities, dict):
        raise ValueError("precision override capabilities must be an object")
    if set(capabilities) - {"precision_edit", "supported_sizes"}:
        raise ValueError("precision override capabilities cannot inherit aliases or size policies")
    confirmed = capabilities.get("precision_edit", False)
    if not isinstance(confirmed, bool):
        raise ValueError("precision override confirmation must be boolean")
    normalized_capabilities = {"precision_edit": confirmed}
    if "supported_sizes" in capabilities:
        raw_sizes = capabilities.get("supported_sizes")
        if not isinstance(raw_sizes, list):
            raise ValueError("precision override supported sizes are invalid")
        if raw_sizes:
            present, valid, sizes, _ = precision_capability_size_declaration(capabilities)
            if not present or not valid:
                raise ValueError("precision override supported sizes are invalid")
            normalized_capabilities["supported_sizes"] = list(sizes)
        else:
            normalized_capabilities["supported_sizes"] = []
    return {
        "protocol": protocol,
        "profile": profile.value,
        "size_model": size_model,
        "capabilities": normalized_capabilities,
    }


def resolve_image_protocol(provider: ProviderConfig) -> str:
    """Match established text-to-image detection without importing providers."""
    url = str(getattr(provider, "base_url", "") or "").lower()
    if "googleapis" in url or "gemini.google.com" in url:
        return "gemini"
    if "agnes" in url:
        return "agnes"
    if "qwen" in url or "wanx" in url:
        return "qwen"
    if url.rstrip("/").endswith("/v1"):
        return "openai"
    for value in (getattr(provider, "id", ""), getattr(provider, "model", "")):
        value = str(value or "").lower()
        if "agnes" in value:
            return "agnes"
        if "qwen" in value or "wanx" in value:
            return "qwen"
    return "openai"


def precision_documented_gateway_recipe(provider: ProviderConfig, model: str) -> Dict[str, str]:
    """Exact public gateway recipes, not grants or successful runtime evidence."""
    get_endpoints = getattr(provider, "get_active_endpoints", None)
    endpoints = get_endpoints() if callable(get_endpoints) else []
    urls = [endpoint.url for endpoint in endpoints] or [getattr(provider, "base_url", "")]
    origins = set()
    for url in urls:
        try:
            parsed = urlsplit(str(url or ""))
            if (
                parsed.scheme != "https" or parsed.port not in (None, 443)
                or parsed.username is not None or parsed.password is not None
                or parsed.query or parsed.fragment
                or parsed.path.rstrip("/") not in ("", "/v1")
            ):
                return {}
            origins.add(parsed.hostname)
        except ValueError:
            return {}
    if len(origins) != 1:
        return {}
    host = next(iter(origins))
    recipe = None
    if host == "api.velapi.cc":
        recipe = {
            "nano-banana-2-2k": (GEMINI_31_FLASH_IMAGE, "2K"),
            "nano-banana-2-2k-sp": (GEMINI_31_FLASH_IMAGE, "2K"),
            "nano-banana-2-4K": (GEMINI_31_FLASH_IMAGE, "4K"),
            "nano-banana-pro-2k": (GEMINI_3_PRO_IMAGE, "2K"),
            "nano-banana-pro-2k-sp": (GEMINI_3_PRO_IMAGE, "2K"),
            "nano-banana-pro-4K": (GEMINI_3_PRO_IMAGE, "4K"),
        }.get(model)
    elif host == "api.klong.lat":
        recipe = {
            "nano-banana2": (GEMINI_31_FLASH_IMAGE, ""),
            "nano-banana-pro": (GEMINI_3_PRO_IMAGE, ""),
        }.get(model)
    if recipe is None:
        return {}
    profile = (
        PrecisionEditProfile.OPENAI_IMAGES_EDITS_JSON_DATA_URL_SINGLE_SOURCE_IMAGE.value
        if host == "api.velapi.cc"
        else PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_SINGLE_SOURCE_IMAGE.value
    )
    return {
        "protocol": "openai",
        "profile": profile,
        "size_model": recipe[0], "size_tier": recipe[1],
        "source": "gateway_documentation",
        "gateway": "vel" if host == "api.velapi.cc" else "klong",
    }


def precision_automatic_connection_info(provider: ProviderConfig, model: str) -> Dict[str, str]:
    """Nonsecret automatic recipe, ignoring manual overrides."""
    recipe = precision_documented_gateway_recipe(provider, model)
    if recipe:
        return recipe
    protocol = str(getattr(provider, "endpoint_type", "auto") or "auto")
    if protocol == "auto":
        protocol = resolve_image_protocol(provider)
    configured = getattr(provider, "precision_edit_profile", None)
    profile = getattr(configured, "value", configured) or ""
    if not profile:
        if protocol == "gemini" and model in GEMINI_NATIVE_IMAGE_MODELS:
            profile = PrecisionEditProfile.GEMINI_GENERATE_CONTENT.value
        elif protocol == "openai":
            # Keep the historical OpenAI edit body when no explicit profile
            # exists; adapters may still replace it with a documented
            # gateway recipe for an exact host/model pair.
            profile = PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE.value
    extra = getattr(provider, "extra", None)
    extra = extra if isinstance(extra, dict) else {}
    resolution = resolve_precision_model_capability(extra.get("model_capabilities"), model)
    size_model = resolution.canonical_model if resolution.structure_valid else model
    return {
        "protocol": protocol, "profile": profile, "size_model": size_model,
        "size_tier": "", "source": "provider_default", "gateway": "",
    }


def resolve_precision_provider(provider: ProviderConfig, model: str) -> ProviderConfig:
    """Create an isolated, idempotent precision configuration for an exact model."""
    extra = getattr(provider, "extra", None)
    extra = extra if isinstance(extra, dict) else {}
    if extra.get("_precision_resolved_model") == model or extra.get("_precision_override_model") == model:
        return provider
    overrides = extra.get("precision_model_overrides")
    if not isinstance(overrides, dict) or model not in overrides:
        recipe = precision_documented_gateway_recipe(provider, model)
        if not recipe:
            if getattr(provider, "endpoint_type", "auto") != "auto":
                return provider
            if not getattr(provider, "base_url", "") and not (
                callable(getattr(provider, "get_active_endpoints", None))
                and provider.get_active_endpoints()
            ):
                return provider
            recipe = precision_automatic_connection_info(provider, model)
            if recipe["protocol"] not in {"openai", "gemini"} or not recipe["profile"]:
                return provider
        copy_model = getattr(provider, "model_copy", None)
        effective = copy_model(deep=True) if callable(copy_model) else deepcopy(provider)
        effective.endpoint_type = recipe["protocol"]
        effective.precision_edit_profile = PrecisionEditProfile(recipe["profile"])
        effective.extra["_precision_resolved_model"] = model
        effective.extra["_precision_connection_source"] = recipe["source"]
        effective.extra["_precision_size_model"] = recipe["size_model"]
        return effective
    raw_override = overrides[model]
    recipe = precision_documented_gateway_recipe(provider, model)
    if isinstance(raw_override, dict) and raw_override.get("protocol") == "openai" and not raw_override.get("profile") and recipe:
        raw_override = {**raw_override, "profile": recipe["profile"]}
    override = normalize_precision_model_override(raw_override)
    copy_model = getattr(provider, "model_copy", None)
    effective = copy_model(deep=True) if callable(copy_model) else deepcopy(provider)
    effective.endpoint_type = override["protocol"]
    effective.precision_edit_profile = PrecisionEditProfile(override["profile"])
    effective.extra.pop("precision_model_overrides", None)
    effective.extra["_precision_override_model"] = model
    effective.extra["_precision_resolved_model"] = model
    effective.extra["_precision_connection_source"] = "manual"
    effective.extra["_precision_size_model"] = override["size_model"] or recipe.get("size_model", "")
    capabilities = effective.extra.get("model_capabilities")
    if not isinstance(capabilities, dict):
        capabilities = {}
        effective.extra["model_capabilities"] = capabilities
    capabilities[model] = deepcopy(override["capabilities"])
    effective.capabilities["precision_edit"] = override["capabilities"]["precision_edit"]
    return effective


def precision_connection_info(provider: ProviderConfig, model: str) -> Dict[str, Any]:
    """Effective model connection without credentials or endpoint URLs."""
    automatic = precision_automatic_connection_info(provider, model)
    effective = resolve_precision_provider(provider, model)
    extra = getattr(effective, "extra", None)
    extra = extra if isinstance(extra, dict) else {}
    profile = getattr(effective, "precision_edit_profile", None)
    profile = getattr(profile, "value", profile) or ""
    protocol = str(getattr(effective, "endpoint_type", "auto") or "auto")
    if protocol == "auto":
        protocol = resolve_image_protocol(effective)
    if not profile and protocol == "openai":
        profile = PrecisionEditProfile.OPENAI_IMAGES_EDITS_MULTIPART_REPEATED_IMAGE.value
    return {
        "protocol": protocol, "profile": profile,
        "size_model": precision_size_model(effective, model),
        "source": extra.get("_precision_connection_source", "provider_default"),
        "size_tier": automatic.get("size_tier", ""),
        "automatic": automatic,
    }


def precision_size_model(provider: ProviderConfig, model: str) -> str:
    """Resolve a catalogue identity independently from the outbound model ID."""
    effective = resolve_precision_provider(provider, model)
    extra = effective.extra if isinstance(effective.extra, dict) else {}
    if extra.get("_precision_override_model") == model or extra.get("_precision_resolved_model") == model:
        return extra.get("_precision_size_model") or model
    resolution = resolve_precision_model_capability(extra.get("model_capabilities"), model)
    return resolution.canonical_model if resolution.structure_valid else model


def documented_precision_provider_size_presets(provider: ProviderConfig, model: str) -> Tuple[Dict[str, Any], ...]:
    """Return official candidates with separate gateway-documentation evidence.

    A gateway's short ratio list is not the model's complete native catalog.
    Keep all model-documentation candidates visible for planning, while marking
    the subset explicitly named by a gateway. Neither collection grants a
    strict request; persisted per-provider/model size evidence still does that.
    """
    presets = documented_precision_model_size_presets(precision_size_model(provider, model))
    recipe = precision_documented_gateway_recipe(provider, model)
    tier = recipe.get("size_tier")
    if tier:
        presets = tuple(item for item in presets if str(item.get("tier", "")).upper() == tier)
    gateway_ratios = (
        {"1:1", "16:9", "9:16", "4:3", "3:4"}
        if recipe.get("gateway") == "vel"
        else set()
    )
    output = []
    for item in presets:
        gateway_declared = bool(recipe and item.get("ratio") in gateway_ratios)
        # Observed failures are scoped to this exact gateway/model, not a
        # universal maximum-side interpretation of the model's 4K tier.
        warning = ""
        if recipe.get("gateway") == "klong" and model == "nano-banana2":
            warning = {
                "6144x768": "observed_geometry_mismatch",
                "2048x8192": "observed_output_safety_limit",
            }.get(item["size"], "")
        output.append({
            **dict(item),
            "evidence": (
                "gateway_documented_candidate"
                if gateway_declared
                else "official_model_candidate"
            ),
            "official_model_candidate": True,
            "gateway_declared_candidate": gateway_declared,
            "gateway": recipe.get("gateway", ""),
            "experimental": True if recipe else bool(item.get("experimental")),
            "reliability_warning": warning,
        })
    return tuple(output)


class ProxyConfig(BaseModel):
    """网络代理配置"""
    enabled: bool = False
    type: str = "http"        # http / socks5
    host: str = "127.0.0.1"
    port: int = 10808
    username: str = ""
    password: str = ""


class VideoModelSpec(BaseModel):
    """视频模型参数约束定义"""
    resolutions: List[str] = ["720p", "1080p"]  # 支持的分辨率档位
    duration_options: List[int] = [5, 10]        # 支持的时长选项(秒)
    fps_options: List[int] = [24]                # 支持的FPS选项
    frame_rule: str = ""                         # 帧数规则: "8n+1", "4n+1", ""(无限制)
    max_frames: int = 441                        # 最大帧数
    min_frames: int = 9                          # 最小帧数
    inference_steps_range: Optional[List[int]] = None  # 推理步数范围 [min, max, default]
    supports_negative_prompt: bool = True        # 是否支持负面提示词
    supports_seed: bool = True                   # 是否支持种子
    supports_image_input: bool = True            # 是否支持图片输入
    max_image_count: int = 1                     # 最大图片输入数量
    max_prompt_length: int = 2000                # 最大提示词长度


# 各视频模型参数约束预设
VIDEO_MODEL_SPECS: Dict[str, VideoModelSpec] = {
    # Google Veo 3.x
    "veo-3": VideoModelSpec(
        resolutions=["720p", "1080p", "4K"],
        duration_options=[4, 6, 8],
        fps_options=[24],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=False,
        max_image_count=1,
    ),
    # Google Veo 2.x
    "veo-2": VideoModelSpec(
        resolutions=["720p"],
        duration_options=[5, 8],
        fps_options=[24],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=False,
    ),
    # OpenAI Sora
    "sora": VideoModelSpec(
        resolutions=["720p", "1080p"],
        duration_options=[4, 8, 12, 16, 20],
        fps_options=[24],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=False,
        max_image_count=2,
    ),
    # Kling V2.x
    "kling-v2": VideoModelSpec(
        resolutions=["720p", "1080p"],
        duration_options=[5, 10],
        fps_options=[24],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=False,
        max_image_count=1,
    ),
    # MiniMax / Hailuo
    "hailuo": VideoModelSpec(
        resolutions=["768p", "1080p"],
        duration_options=[6, 10],
        fps_options=[24],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=False,
        max_image_count=1,
    ),
    # Alibaba Wanx 2.1
    "wanx2.1": VideoModelSpec(
        resolutions=["480p", "720p"],
        duration_options=[5],
        fps_options=[30],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=True,
    ),
    # Alibaba Wan 2.6/2.7
    "wan2": VideoModelSpec(
        resolutions=["720p", "1080p"],
        duration_options=list(range(2, 16)),
        fps_options=[30],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=True,
    ),
    # Tencent HunyuanVideo
    "hunyuan": VideoModelSpec(
        resolutions=["480p", "720p"],
        duration_options=[5],
        fps_options=[24],
        frame_rule="4n+1",
        min_frames=5,
        max_frames=133,
        inference_steps_range=[8, 50, 50],
        supports_negative_prompt=False,
        supports_seed=False,
    ),
    # ByteDance Seedance
    "seedance": VideoModelSpec(
        resolutions=["480p", "720p", "1080p", "2K"],
        duration_options=list(range(4, 16)),
        fps_options=[24],
        frame_rule="",
        supports_negative_prompt=False,
        supports_seed=True,
        max_image_count=9,
    ),
    # Agnes Video
    "agnes": VideoModelSpec(
        resolutions=["480p", "720p", "1080p"],
        duration_options=list(range(3, 19)),
        fps_options=[24, 30, 60],
        frame_rule="8n+1",
        min_frames=9,
        max_frames=441,
        inference_steps_range=[1, 100, 30],
        supports_negative_prompt=True,
        supports_seed=True,
        max_image_count=4,
    ),
}


class ProvidersConfig(BaseModel):
    """完整配置文件"""
    providers: List[ProviderConfig] = []
    proxy: ProxyConfig = ProxyConfig()
    version: int = 1


# ──────────────────────────────────────────────────────────────
# 默认配置（首次运行自动生成，或从 .env 读取真实值）
# ──────────────────────────────────────────────────────────────
DEFAULT_PROVIDERS: List[Dict[str, Any]] = [
    {
        "id": "gpt-image",
        "name": "GPT Image 2",
        "type": "image",
        "api_key": os.getenv("GPT_IMAGE_API_KEY", ""),
        "base_url": os.getenv("GPT_IMAGE_BASE_URL", "https://api.openai.com/v1"),
        "model": "gpt-image-2",
        "models": [],
        "size": "1024x1024",
        "quality": "high",
        "color": "#22c55e",
        "enabled": False,
        "capabilities": {"t2i": True, "i2i": True},
    },
    {
        "id": "gemini",
        "name": "Gemini 3.1 Flash",
        "type": "image",
        "api_key": os.getenv("GEMINI_API_KEY", ""),
        "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com"),
        "model": "gemini-2.0-flash-exp-image-generation",
        "models": [],
        "size": "",
        "quality": "",
        "color": "#3b82f6",
        "enabled": False,
        "capabilities": {"t2i": True, "i2i": True},
    },
    {
        "id": "qwen",
        "name": "Qwen2API",
        "type": "image",
        "api_key": os.getenv("QWEN_API_KEY", ""),
        "base_url": os.getenv("QWEN_BASE_URL", "http://localhost:8090/v1"),
        "model": "qwen3.6-plus",
        "models": [],
        "size": "1024*1024",
        "quality": "",
        "color": "#f97316",
        "enabled": False,
        "capabilities": {"t2i": True, "i2i": False},
    },
    {
        "id": "llm-default",
        "name": "LLM 提示词优化",
        "type": "llm",
        "api_key": os.getenv("LLM_API_KEY", ""),
        "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        "model": "gpt-4o-mini",
        "models": [],
        "size": "",
        "quality": "",
        "color": "#a855f7",
        "enabled": False,
        "capabilities": {},
    },
]


# ──────────────────────────────────────────────────────────────
# 配置管理器
# ──────────────────────────────────────────────────────────────
class ConfigManager:
    """管理 Provider 配置的加载/保存/读取"""

    def __init__(self):
        self._config: Optional[ProvidersConfig] = None

    @property
    def config(self) -> ProvidersConfig:
        if self._config is None:
            self._config = self._load()
        return self._config

    def _load(self) -> ProvidersConfig:
        """加载配置：providers.json 优先，.env 仅兜底空字段"""
        if PROVIDERS_FILE.exists():
            try:
                raw = json.loads(PROVIDERS_FILE.read_text(encoding="utf-8"))
                cfg = ProvidersConfig(**raw)
                self._sync_env_to_config(cfg)
                return cfg
            except Exception as e:
                print(f"[Config] providers.json 解析失败，使用默认配置: {e}")

        cfg = ProvidersConfig(providers=[ProviderConfig(**p) for p in DEFAULT_PROVIDERS])
        self._sync_env_to_config(cfg)
        self._save(cfg)
        return cfg

    def _sync_env_to_config(self, cfg: ProvidersConfig):
        """启动时将 .env 的值同步到 config（仅当 providers.json 中该字段为空时才用 .env 兜底）"""
        env_map = {
            "gpt-image": {"api_key": "GPT_IMAGE_API_KEY", "base_url": "GPT_IMAGE_BASE_URL"},
            "gemini": {"api_key": "GEMINI_API_KEY", "base_url": "GEMINI_BASE_URL"},
            "qwen": {"api_key": "QWEN_API_KEY", "base_url": "QWEN_BASE_URL"},
            "llm-default": {"api_key": "LLM_API_KEY", "base_url": "LLM_BASE_URL"},
            "agnes-image": {"api_key": "AGNES_API_KEY", "base_url": "AGNES_BASE_URL"},
            "agnes-video": {"api_key": "AGNES_API_KEY", "base_url": "AGNES_BASE_URL"},
            "gemini-video": {"api_key": "GEMINI_API_KEY", "base_url": "GEMINI_BASE_URL"},
            "qwen-video": {"api_key": "QWEN_API_KEY", "base_url": "QWEN_BASE_URL"},
        }
        for p in cfg.providers:
            if p.id in env_map:
                for field, env_key in env_map[p.id].items():
                    env_val = os.getenv(env_key, "")
                    current_val = getattr(p, field, "")
                    if env_val and not current_val:
                        setattr(p, field, env_val)

    def _save(self, cfg: ProvidersConfig):
        """内部保存方法"""
        PROVIDERS_FILE.write_text(
            cfg.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8"
        )
        self._config = cfg

    def save(self, cfg: ProvidersConfig = None):
        """保存配置到 providers.json，并同步回 .env"""
        target = cfg or self._config
        if target is None:
            return
        PROVIDERS_FILE.write_text(
            target.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8"
        )
        self._config = target
        self._sync_config_to_env(target)

    def _sync_config_to_env(self, cfg: ProvidersConfig):
        """前端保存后，将 API Key 同步写回 .env 文件"""
        env_file = BASE_DIR / ".env"
        env_map = {
            "gpt-image": {"api_key": "GPT_IMAGE_API_KEY", "base_url": "GPT_IMAGE_BASE_URL"},
            "gemini": {"api_key": "GEMINI_API_KEY", "base_url": "GEMINI_BASE_URL"},
            "qwen": {"api_key": "QWEN_API_KEY", "base_url": "QWEN_BASE_URL"},
            "llm-default": {"api_key": "LLM_API_KEY", "base_url": "LLM_BASE_URL"},
            "agnes-image": {"api_key": "AGNES_API_KEY", "base_url": "AGNES_BASE_URL"},
            "agnes-video": {"api_key": "AGNES_API_KEY", "base_url": "AGNES_BASE_URL"},
            "gemini-video": {"api_key": "GEMINI_API_KEY", "base_url": "GEMINI_BASE_URL"},
            "qwen-video": {"api_key": "QWEN_API_KEY", "base_url": "QWEN_BASE_URL"},
        }
        # 读取现有 .env
        env_lines = []
        if env_file.exists():
            env_lines = env_file.read_text(encoding="utf-8").splitlines()

        # 构建需要写入的键值对
        updates = {}
        for p in cfg.providers:
            if p.id in env_map:
                for field, env_key in env_map[p.id].items():
                    val = getattr(p, field, "")
                    # 如果有 endpoints，优先用第一个启用端点的值
                    if not val and p.endpoints:
                        active_eps = [ep for ep in p.endpoints if ep.enabled and ep.url and ep.key]
                        if active_eps:
                            if field == "base_url":
                                val = active_eps[0].url
                            elif field == "api_key":
                                val = active_eps[0].key
                    if val:
                        updates[env_key] = val

        # 更新现有行或追加
        updated_keys = set()
        for i, line in enumerate(env_lines):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key = stripped.split("=", 1)[0].strip()
                if key in updates:
                    env_lines[i] = f"{key}={updates[key]}"
                    updated_keys.add(key)

        # 追加新的键值对
        for key, val in updates.items():
            if key not in updated_keys:
                env_lines.append(f"{key}={val}")

        env_file.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    def get_image_providers(self) -> List[ProviderConfig]:
        """获取所有启用的图片生成 Provider"""
        return [p for p in self.config.providers if p.type == "image" and p.enabled]

    def get_video_providers(self) -> List[ProviderConfig]:
        """获取所有启用的视频生成 Provider"""
        return [p for p in self.config.providers if p.type == "video" and p.enabled]

    def get_llm_provider(self) -> Optional[ProviderConfig]:
        """获取第一个启用的 LLM Provider"""
        for p in self.config.providers:
            if p.type == "llm" and p.enabled and p.api_key:
                return p
        return None

    def reload(self):
        """强制重新加载"""
        self._config = None
        return self.config


# 全局单例
cfg_mgr = ConfigManager()


# ──────────────────────────────────────────────────────────────
# 兼容旧代码的 Settings 对象（逐步废弃）
# ──────────────────────────────────────────────────────────────
class LegacySettings:
    """兼容层：让旧 provider 代码继续工作"""

    @property
    def gpt_image_api_key(self):
        p = self._find("gpt-image"); return p.api_key if p else ""

    @property
    def gpt_image_base_url(self):
        p = self._find("gpt-image"); return p.base_url if p else "https://api.openai.com/v1"

    @property
    def gpt_image_model(self):
        p = self._find("gpt-image"); return p.model if p else "gpt-image-2"

    @property
    def gpt_image_size(self):
        p = self._find("gpt-image"); return p.size if p else "1024x1024"

    @property
    def gpt_image_quality(self):
        p = self._find("gpt-image"); return p.quality if p else "high"

    @property
    def gemini_api_key(self):
        p = self._find("gemini"); return p.api_key if p else ""

    @property
    def gemini_base_url(self):
        p = self._find("gemini"); return p.base_url if p else "https://generativelanguage.googleapis.com"

    @property
    def gemini_model(self):
        p = self._find("gemini"); return p.model if p else "gemini-3.1-flash-preview-05-20"

    @property
    def qwen_api_key(self):
        p = self._find("qwen"); return p.api_key if p else ""

    @property
    def qwen_base_url(self):
        p = self._find("qwen"); return p.base_url if p else "http://localhost:8090/v1"

    @property
    def qwen_model(self):
        p = self._find("qwen"); return p.model if p else "qwen2.5-72b-instruct"

    @property
    def qwen_size(self):
        p = self._find("qwen"); return p.size if p else "1024*1024"

    @property
    def llm_api_key(self):
        p = self._find("llm-default"); return p.api_key if p else ""

    @property
    def llm_base_url(self):
        p = self._find("llm-default"); return p.base_url if p else "https://api.openai.com/v1"

    @property
    def llm_model(self):
        p = self._find("llm-default"); return p.model if p else "gpt-4o-mini"

    @property
    def host(self): return "0.0.0.0"

    @property
    def port(self): return 8765

    @property
    def debug(self): return True

    class Config:
        extra = "allow"

    def _find(self, pid: str):
        for p in cfg_mgr.config.providers:
            if p.id == pid:
                return p
        return None


settings = LegacySettings()


# ──────────────────────────────────────────────────────────────
# ADMINKEY 管理（生产模式安全策略）
# ──────────────────────────────────────────────────────────────
import secrets
import hashlib
import sys

def _get_env_path() -> Path:
    return BASE_DIR / ".env"

def _read_env() -> dict:
    """读取 .env 为字典"""
    env = {}
    p = _get_env_path()
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def _write_env(updates: dict):
    """更新 .env 中的键值对"""
    env = _read_env()
    env.update(updates)
    lines = [f"{k}={v}" for k, v in env.items()]
    _get_env_path().write_text("\n".join(lines) + "\n", encoding="utf-8")

def _hash_admin_key(key: str) -> str:
    """SHA256 哈希管理密钥"""
    return hashlib.sha256(key.encode()).hexdigest()

def get_admin_key() -> str:
    """获取当前 ADMIN_KEY（从 .env）"""
    return os.getenv("ADMIN_KEY", "").strip()

def get_admin_key_hash() -> str:
    """获取当前 ADMIN_KEY 的哈希值"""
    key = get_admin_key()
    if not key:
        return ""
    return _hash_admin_key(key)

def is_prod_mode() -> bool:
    """是否生产模式（启用认证）"""
    return os.getenv("APP_MODE", "prod").strip().lower() != "dev"

def verify_admin_key(key: str) -> bool:
    """校验管理密钥（使用哈希比对）"""
    if not is_prod_mode():
        return True  # 开发模式免认证
    stored_hash = get_admin_key_hash()
    if not stored_hash:
        return False
    return secrets.compare_digest(_hash_admin_key(key), stored_hash)

def generate_admin_key() -> str:
    """生成随机管理密钥并写入 .env"""
    key = secrets.token_urlsafe(12)  # 16 字符
    _write_env({"ADMIN_KEY": key})
    # 同步更新运行时环境变量
    os.environ["ADMIN_KEY"] = key
    return key

def reset_admin_key() -> str:
    """重置管理密钥（命令行用）"""
    key = generate_admin_key()
    return key

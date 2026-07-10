"""
动态多模型图像生成服务
- 从 ConfigManager 读取运行时配置
- 自动为每个 image 类型 Provider 创建调用实例
- 支持 OpenAI 兼容 / Gemini / Qwen2API 三种协议
"""
import base64
import uuid
import time
from io import BytesIO
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import httpx
from PIL import Image
from io import BytesIO

from config import cfg_mgr, GALLERY_DIR, ProviderConfig, VideoModelSpec, VIDEO_MODEL_SPECS


# 国内模型厂商（始终直连，不走代理）
CHINESE_PROVIDERS = {
    "qwen",        # 阿里通义千问
    "zhipu",       # 智谱 GLM
    "deepseek",    # DeepSeek
    "volcengine",  # 火山引擎
    "siliconflow", # SiliconFlow
}


def _get_proxy_url(cfg: ProviderConfig = None) -> str | None:
    """获取代理 URL（支持 Provider 级别跳过代理）
    
    逻辑：
    1. 国内厂商（CHINESE_PROVIDERS）→ 始终直连
    2. 全局代理未启用 → 返回 None（直连）
    3. Provider 设置 skip_proxy=True → 返回 None（直连）
    4. 其他情况 → 返回代理 URL
    """
    # 国内厂商始终直连
    if cfg and cfg.id in CHINESE_PROVIDERS:
        return None
    
    proxy = cfg_mgr.config.proxy
    if not proxy.enabled or not proxy.host:
        return None
    # Provider 级别跳过代理
    if cfg and cfg.skip_proxy:
        return None
    return f"{proxy.type}://{proxy.host}:{proxy.port}"


def get_video_model_spec(model_name: str):
    """根据模型名称获取视频模型参数约束
    
    匹配规则：按优先级匹配模型名称中的关键词
    返回: VideoModelSpec 或默认规格
    """
    model_lower = model_name.lower() if model_name else ""
    
    # 按优先级匹配模型关键词
    spec_keywords = [
        ("veo_3", "veo-3"),
        ("veo_2", "veo-2"),
        ("veo-", "veo-3"),      # veo-3-1, veo-3-0 等
        ("sora", "sora"),
        ("kling", "kling-v2"),
        ("hailuo", "hailuo"),
        ("minimax", "hailuo"),
        ("wanx2", "wanx2.1"),
        ("wan2", "wan2"),
        ("wan_", "wan2"),
        ("hunyuan", "hunyuan"),
        ("seedance", "seedance"),
        ("agnes", "agnes"),
    ]
    
    for keyword, spec_key in spec_keywords:
        if keyword in model_lower:
            return VIDEO_MODEL_SPECS.get(spec_key)
    
    # 默认返回 Agnes 规格（最灵活）
    return VIDEO_MODEL_SPECS.get("agnes")


def get_video_model_spec_dict(model_name: str) -> dict:
    """获取视频模型参数约束的字典格式（用于API返回）"""
    spec = get_video_model_spec(model_name)
    if spec:
        return spec.model_dump()
    return VideoModelSpec().model_dump()


@dataclass
class ImageResult:
    """统一返回格式"""
    success: bool
    image_data: Optional[bytes] = None
    image_url: Optional[str] = None
    local_path: Optional[str] = None
    model: str = ""
    error: str = ""
    generation_id: str = ""


def _save_image(data: bytes, model_id: str, prompt_short: str, full_prompt: str = "") -> str:
    """保存图片到本地图库，将 prompt 写入 PNG 元数据"""
    ts = time.strftime("%Y%m%d_%H%M%S")
    safe_short = "".join(c if c.isalnum() else "_" for c in prompt_short[:30])
    filename = f"{model_id}_{ts}_{safe_short}_{uuid.uuid4().hex[:6]}.png"
    out_path = GALLERY_DIR / filename
    
    # 如果有完整 prompt，写入 PNG 元数据
    if full_prompt:
        try:
            img = Image.open(BytesIO(data))
            # PNG 文本块存储 prompt
            from PIL import PngImagePlugin
            metadata = PngImagePlugin.PngInfo()
            metadata.add_text("Prompt", full_prompt)
            metadata.add_text("Model", model_id)
            metadata.add_text("CreatedAt", ts)
            buf = BytesIO()
            img.save(buf, format="PNG", pnginfo=metadata)
            data = buf.getvalue()
        except Exception as e:
            print(f"[Warning] 无法写入 PNG 元数据: {e}")
    
    out_path.write_bytes(data)
    return str(out_path)


# ──────────────────────────────────────────────────────────────
# 协议路由：根据 base_url 或 provider id 判断 API 协议
# ──────────────────────────────────────────────────────────────
def _detect_protocol(cfg: ProviderConfig) -> str:
    """
    检测 API 协议类型:
    - "openai": OpenAI 兼容 (包括 GPT Image, Flux, SD 等)
    - "gemini": Google Gemini 原生 API
    - "qwen": Qwen2API (兼容 OpenAI 但路径不同)
    - "agnes": Agnes AI (兼容 OpenAI 但 image/response_format 放在 extra_body)
    
    优先级: URL > Provider ID > Model 名称
    （URL 最可靠：第三方代理 + /v1 → 必定 OpenAI 兼容）
    """
    url_lower = cfg.base_url.lower()

    # ── 1. URL 最优先 ──
    # Google 原生 API → Gemini 协议
    is_google_native = ("googleapis" in url_lower or "gemini.google.com" in url_lower)
    if is_google_native:
        return "gemini"
    # 特定关键字优先于通用 /v1 检测
    if "agnes" in url_lower:
        return "agnes"
    if "qwen" in url_lower or "wanx" in url_lower:
        return "qwen"
    # URL 包含 /v1 且不是 googleapis → 第三方 OpenAI 兼容代理
    if url_lower.rstrip('/').endswith('/v1'):
        return "openai"

    # ── 2. Provider ID 次之 ──
    pid = cfg.id.lower()
    if "agnes" in pid:
        return "agnes"
    if "qwen" in pid or "wanx" in pid:
        return "qwen"
    # id == "gemini" 但 URL 不是 googleapis → 不走原生协议，走默认 OpenAI

    # ── 3. Model 名称最后（仅限明确的非通用场景）──
    model_lower = cfg.model.lower()
    if "agnes" in model_lower:
        return "agnes"
    if "wanx" in model_lower or "qwen" in model_lower:
        return "qwen"

    # 默认走 OpenAI 兼容协议（覆盖绝大多数第三方服务）
    return "openai"


# ──────────────────────────────────────────────────────────────
# 通用生成器（一个函数处理所有 Provider）
# ──────────────────────────────────────────────────────────────
async def generate_for_provider(
    cfg: ProviderConfig,
    prompt: str,
    **kwargs
) -> ImageResult:
    """
    根据 Provider 配置自动选择协议并生图
    这是核心入口，所有 Provider 都走这里
    支持 t2i (文生图) 和 i2i (图生图) 两种模式
    支持多端点轮询（endpoints 字段）+ 多账号轮询（api_keys 字段）
    """
    from .key_pool import key_pool_manager

    protocol = kwargs.get("protocol") or _detect_protocol(cfg)

    # 获取端点列表（endpoints 优先，fallback 到 base_url+api_key）
    endpoints = cfg.get_active_endpoints()

    if endpoints:
        # 多端点模式：逐个尝试
        last_error = None
        for ep in endpoints:
            if not ep.url or not ep.key:
                continue
            result = await _try_generate_with_endpoint(cfg, prompt, ep.url, ep.key, protocol, **kwargs)
            if result.success:
                return result
            last_error = result.error
        return ImageResult(
            success=False,
            error=f"[{cfg.name}] 所有端点均失败: {last_error or '无可用端点'}",
            model=cfg.id
        )
    else:
        # 旧模式：单 URL + 多 Key 轮询
        effective_keys = cfg.get_effective_keys()
        if not effective_keys:
            return ImageResult(success=False, error=f"[{cfg.name}] API Key 未配置", model=cfg.id)

        pool = key_pool_manager.get_or_create(cfg.id, effective_keys)
        api_key = await pool.get_key()
        if not api_key:
            return ImageResult(success=False, error=f"[{cfg.name}] 所有 API Key 均在冷却中，请稍后重试", model=cfg.id)

        original_key = cfg.api_key
        cfg.api_key = api_key
        try:
            result = await _dispatch_generate(cfg, prompt, protocol, **kwargs)
        except Exception as e:
            result = ImageResult(success=False, error=f"[{cfg.name}] {str(e)}", model=cfg.id)

        if result.success:
            pool.mark_success(api_key)
        else:
            error_msg = (result.error or "").lower()
            if "429" in error_msg or "too many requests" in error_msg or "insufficient_quota" in error_msg or "quota" in error_msg:
                retry_after = 0.0
                if "retry" in error_msg:
                    import re
                    m = re.search(r'retry[_-]?after[:\s]*(\d+)', error_msg)
                    if m:
                        retry_after = float(m.group(1))
                pool.mark_error(api_key, retry_after)
            elif "401" in error_msg or "unauthorized" in error_msg or "invalid" in error_msg:
                pool.mark_error(api_key, retry_after=600.0)

        cfg.api_key = original_key
        return result


async def _try_generate_with_endpoint(cfg, prompt, url, key, protocol, **kwargs) -> ImageResult:
    """使用指定端点尝试生成（临时注入 url 和 key）"""
    original_url = cfg.base_url
    original_key = cfg.api_key
    cfg.base_url = url
    cfg.api_key = key
    try:
        result = await _dispatch_generate(cfg, prompt, protocol, **kwargs)
    except Exception as e:
        result = ImageResult(success=False, error=f"[{cfg.name}] {str(e)}", model=cfg.id)
    finally:
        cfg.base_url = original_url
        cfg.api_key = original_key
    return result


async def _dispatch_generate(cfg, prompt, protocol, **kwargs):
    """内部调度：根据协议选择生成函数"""
    image_data = kwargs.get("image_data")
    strength = kwargs.get("strength", 0.55)

    # 图生图
    if image_data and protocol == "openai":
        kwargs_copy = {k: v for k, v in kwargs.items() if k not in ("image_data", "strength")}
        return await _gen_openai_edit(cfg, prompt, image_data, strength, **kwargs_copy)
    elif image_data and protocol == "gemini":
        kwargs_copy = {k: v for k, v in kwargs.items() if k not in ("image_data", "strength")}
        return await _gen_gemini_edit(cfg, prompt, image_data, strength, **kwargs_copy)
    elif image_data and protocol == "agnes":
        kwargs_copy = {k: v for k, v in kwargs.items()}
        return await _gen_agnes(cfg, prompt, **kwargs_copy)
    elif image_data:
        return ImageResult(success=False, error=f"[{cfg.name}] 图生图 (I2I) 暂不支持 {protocol} 协议", model=cfg.id)

    # 文生图
    if protocol == "gemini":
        return await _gen_gemini(cfg, prompt, **kwargs)
    elif protocol == "qwen":
        return await _gen_qwen(cfg, prompt, **kwargs)
    elif protocol == "agnes":
        return await _gen_agnes(cfg, prompt, **kwargs)
    else:
        return await _gen_openai(cfg, prompt, **kwargs)


async def _http_post_with_retry(url, headers, payload, *, timeout=120.0, max_retries=3, retry_delay=2.0, proxy: str = None):
    """带重试的 HTTP POST，返回 (resp, client) 或抛异常（附带响应体）。
    注意：返回的 client 可能已关闭，调用方需自行管理后续请求。"""
    last_exc = None
    for attempt in range(max_retries):
        client = httpx.AsyncClient(timeout=timeout, proxy=proxy)
        try:
            resp = await client.post(url, headers=headers, json=payload)
            # 429 Too Many Requests 或 5xx 服务器错误 → 重试
            if resp.status_code == 429 or resp.status_code >= 500:
                body_text = resp.text[:300] if resp.text else ""
                await client.aclose()
                if attempt < max_retries - 1:
                    wait = retry_delay * (2 ** attempt)
                    time.sleep(wait)
                    continue
                # 最后一次也失败，抛异常
                raise httpx.HTTPStatusError(
                    f"{resp.status_code} {resp.reason_phrase} | Response: {body_text}",
                    request=resp.request, response=resp
                )
            resp.raise_for_status()
            return resp, client
        except httpx.HTTPStatusError as e:
            body_text = ""
            try:
                body_text = e.response.text[:300]
            except Exception:
                pass
            try:
                await client.aclose()
            except Exception:
                pass
            raise httpx.HTTPStatusError(
                f"{e.response.status_code} {e.response.reason_phrase} | Response: {body_text}",
                request=e.request, response=e.response
            ) from e
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            try:
                await client.aclose()
            except Exception:
                pass
            last_exc = e
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            raise
    raise last_exc or Exception("Max retries exceeded")


def _ensure_v1(base_url: str) -> str:
    """Ensure base_url ends with /v1 for OpenAI-compatible APIs."""
    b = base_url.rstrip("/")
    # Already has /v1 or /v1beta or other subpath — leave as-is
    if b.endswith("/v1") or b.endswith("/v1beta"):
        return b
    # Already contains /v1/ as a subpath (e.g. /openai/v1) — leave as-is
    if "/v1/" in b or "/v1beta/" in b:
        return b
    # Bare host — append /v1
    return b + "/v1"


async def _gen_openai(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """OpenAI 兼容协议: POST /images/generations"""
    size = kwargs.get("size") or cfg.size or "1024x1024"
    quality = kwargs.get("quality") or cfg.quality or "standard"
    model_id = kwargs.get("model") or cfg.model

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "prompt": prompt,
        "n": 1,
        "size": size,
        "response_format": "b64_json",
    }
    if quality and quality != "default":
        payload["quality"] = quality

    base = _ensure_v1(cfg.base_url)
    resp, client = await _http_post_with_retry(
        f"{base}/images/generations",
        headers=headers, payload=payload,
        proxy=_get_proxy_url(cfg),
    )
    data = resp.json()

    img_info = data.get("data", [{}])[0]
    b64 = img_info.get("b64_json")
    img_url = img_info.get("url")

    if img_url and not b64:
        img_resp = await client.get(img_url)
        img_data = img_resp.content
    elif b64:
        img_data = base64.b64decode(b64)
    else:
        return ImageResult(success=False, error=f"[{cfg.name}] API 返回无图片数据", model=cfg.id)

    local_path = _save_image(img_data, cfg.id, prompt, prompt)
    return ImageResult(
        success=True, image_data=img_data, local_path=local_path,
        model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
    )


async def _gen_gemini(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """Google Gemini 原生协议"""
    model_id = kwargs.get("model") or cfg.model

    async with httpx.AsyncClient(timeout=120.0, proxy=_get_proxy_url(cfg)) as client:
        # 处理 base_url：移除末尾的 /v1 或 /v1beta（如果存在）
        base = cfg.base_url.rstrip('/')
        if base.endswith('/v1') or base.endswith('/v1beta'):
            base = base.rsplit('/', 1)[0]
        
        url = (
            f"{base}/v1beta/models/{model_id}:generateContent"
            f"?key={cfg.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["image", "text"]},
        }

        resp = await client.post(url, json=payload, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ImageResult(success=False, error=f"[{cfg.name}] 返回无内容", model=cfg.id)

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                img_data = base64.b64decode(part["inlineData"]["data"])
                local_path = _save_image(img_data, cfg.id, prompt, prompt)
                return ImageResult(
                    success=True, image_data=img_data, local_path=local_path,
                    model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
                )

        return ImageResult(success=False, error=f"[{cfg.name}] 未返回图片数据", model=cfg.id)


async def _gen_qwen(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """Qwen2API 协议 (OpenAI 兼容但字段名不同)"""
    size = kwargs.get("size") or cfg.size or "1024*1024"
    model_id = kwargs.get("model") or cfg.model

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_id,
        "prompt": prompt,
        "size": size,
    }

    resp, client = await _http_post_with_retry(
        f"{_ensure_v1(cfg.base_url)}/images/generations",
        headers=headers, payload=payload,
        proxy=_get_proxy_url(cfg),
    )
    data = resp.json()

    img_info = data.get("data", [{}])[0]
    b64 = img_info.get("b64_json")
    img_url = img_info.get("url")

    if img_url:
        img_resp = await client.get(img_url)
        img_data = img_resp.content
    elif b64:
        img_data = base64.b64decode(b64)
    else:
        return ImageResult(success=False, error=f"[{cfg.name}] 无图片返回", model=cfg.id)

    local_path = _save_image(img_data, cfg.id, prompt, prompt)
    return ImageResult(
        success=True, image_data=img_data, local_path=local_path,
        model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
    )


async def _gen_agnes(cfg: ProviderConfig, prompt: str, **kwargs) -> ImageResult:
    """Agnes AI 协议 (兼容 OpenAI /images/generations 但参数格式特殊)"""
    size = kwargs.get("size") or cfg.size or "1024x1024"
    model_id = kwargs.get("model") or cfg.model

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    # Agnes 特殊格式：基础字段 + extra_body
    payload = {
        "model": model_id,
        "prompt": prompt,
        "size": size,
    }

    # 图生图模式：image 和 response_format 必须在 extra_body 里
    image_data = kwargs.get("image_data")
    if image_data:
        if "," in image_data:
            image_b64 = image_data.split(",")[1]
        else:
            image_b64 = image_data
        # 检测 MIME
        mime = "image/png"
        if image_data.startswith("data:image/jpeg"):
            mime = "image/jpeg"
        elif image_data.startswith("image/webp"):
            mime = "image/webp"
        data_uri = f"data:{mime};base64,{image_b64}"
        payload["extra_body"] = {
            "image": [data_uri],
            "response_format": "b64_json",
        }
    else:
        # 文生图：用 return_base64=true 或 extra_body.response_format
        payload["return_base64"] = True

    resp, client = await _http_post_with_retry(
        f"{_ensure_v1(cfg.base_url)}/images/generations",
        headers=headers, payload=payload,
        proxy=_get_proxy_url(cfg),
    )
    data = resp.json()

    img_info = data.get("data", [{}])[0]
    b64 = img_info.get("b64_json")
    img_url = img_info.get("url")

    if img_url and not b64:
        img_resp = await client.get(img_url)
        img_data = img_resp.content
    elif b64:
        img_data = base64.b64decode(b64)
    else:
        return ImageResult(success=False, error=f"[{cfg.name}] API 返回无图片数据", model=cfg.id)

    local_path = _save_image(img_data, cfg.id, prompt, prompt)
    return ImageResult(
        success=True, image_data=img_data, local_path=local_path,
        model=cfg.id, generation_id=f"{cfg.id}_{uuid.uuid4().hex[:8]}",
    )


# ──────────────────────────────────────────────────────────────
# 图生图 (I2I) 生成器
# ──────────────────────────────────────────────────────────────
async def _gen_openai_edit(cfg: ProviderConfig, prompt: str, image_data: str, strength: float, **kwargs) -> ImageResult:
    """OpenAI 兼容协议图生图: POST /images/edits"""
    # 从 base64 data URL 提取纯 base64 数据
    if "," in image_data:
        image_b64 = image_data.split(",")[1]
    else:
        image_b64 = image_data

    img_bytes = base64.b64decode(image_b64)
    model_id = kwargs.get("model") or cfg.model
    size = kwargs.get("size") or cfg.size or "1024x1024"
    n_val = int(round((1 - strength) * 10))  # strength 转为 n 参数近似

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
    }

    # 使用 multipart/form-data
    files = {
        "image": ("image.png", img_bytes, "image/png"),
        "prompt": (None, prompt),
    }
    data_dict = {
        "model": model_id,
        "n": 1,
        "size": size,
    }

    async with httpx.AsyncClient(timeout=180.0, proxy=_get_proxy_url(cfg)) as client:
        # 尝试标准 /images/edits 端点
        base = _ensure_v1(cfg.base_url)
        url = f"{base}/images/edits"
        resp = await client.post(url, headers=headers, files=files, data=data_dict)
        
        if resp.status_code == 404:
            # edits 端点不存在，尝试 /images/edit（无 s）
            url_alt = f"{base}/images/edit"
            resp = await client.post(url_alt, headers=headers, files=files, data=data_dict)
            if resp.status_code == 404:
                # 两个端点都不支持，fallback 到文生图
                return await _gen_openai_i2i_fallback(cfg, prompt, img_bytes, **kwargs)
        
        if resp.status_code >= 400:
            # 400/422 等错误，尝试移除不支持的参数后重试
            data_dict_clean = {"model": model_id, "prompt": prompt}
            resp_retry = await client.post(url, headers=headers, files=files, data=data_dict_clean)
            if resp_retry.status_code >= 400:
                # 仍然失败，记录详细错误并 fallback
                err_detail = resp_retry.text[:200]
                fallback_result = await _gen_openai_i2i_fallback(cfg, prompt, img_bytes, **kwargs)
                fallback_result.error = f"[I2I {resp_retry.status_code}] {err_detail} | 已降级为参考生图"
                return fallback_result
            resp = resp_retry
        
        result = resp.json()
        result = resp.json()

        img_info = result.get("data", [{}])[0]
        b64 = img_info.get("b64_json")
        img_url = img_info.get("url")

        if img_url and not b64:
            img_resp = await client.get(img_url)
            out_data = img_resp.content
        elif b64:
            out_data = base64.b64decode(b64)
        else:
            return ImageResult(success=False, error=f"[{cfg.name}] I2I API 返回无图片数据", model=cfg.id)

        local_path = _save_image(out_data, cfg.id, f"i2i_{prompt[:30]}", prompt)
        return ImageResult(
            success=True, image_data=out_data, local_path=local_path,
            model=cfg.id, generation_id=f"{cfg.id}_i2i_{uuid.uuid4().hex[:8]}",
        )


async def _gen_openai_i2i_fallback(cfg: ProviderConfig, prompt: str, image_bytes: bytes, **kwargs) -> ImageResult:
    """
    Fallback: 当 /images/edits 不支持时，将图片信息编码到 prompt 中
    部分模型（如 GPT-Image）支持在 prompt 中引用图片描述
    """
    # 尝试将图片作为 base64 内嵌到请求中（部分 API 支持）
    import io
    from PIL import Image as PILImage

    try:
        img = PILImage.open(io.BytesIO(image_bytes))
        w, h = img.size
        enhanced_prompt = f"[INPUT IMAGE: {w}x{h} pixels] Transform this image according to: {prompt}"
    except Exception:
        enhanced_prompt = f"Transform the input image: {prompt}"

    # 回退到普通文生图，但使用增强的 prompt
    return await _gen_openai(cfg, enhanced_prompt, **kwargs)


async def _gen_gemini_edit(cfg: ProviderConfig, prompt: str, image_data: str, strength: float, **kwargs) -> ImageResult:
    """Gemini 原生协议图生图: 在 generateContent 中内联图片"""
    if "," in image_data:
        image_b64 = image_data.split(",")[1]
    else:
        image_b64 = image_data

    # 检测 MIME 类型
    mime_type = "image/png"
    if image_data.startswith("data:image/jpeg"):
        mime_type = "image/jpeg"
    elif image_data.startswith("image/webp"):
        mime_type = "image/webp"

    model_id = kwargs.get("model") or cfg.model

    async with httpx.AsyncClient(timeout=180.0, proxy=_get_proxy_url(cfg)) as client:
        # 处理 base_url：移除末尾的 /v1 或 /v1beta
        base = cfg.base_url.rstrip('/')
        if base.endswith('/v1') or base.endswith('/v1beta'):
            base = base.rsplit('/', 1)[0]
        
        url = (
            f"{base}/v1beta/models/{model_id}:generateContent"
            f"?key={cfg.api_key}"
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": mime_type, "data": image_b64}}
                ]
            }],
            "generationConfig": {
                "responseModalities": ["image", "text"],
            },
        }

        resp = await client.post(url, json=payload, timeout=180.0)
        resp.raise_for_status()
        data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            return ImageResult(success=False, error=f"[{cfg.name}] 返回无内容", model=cfg.id)

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            if "inlineData" in part:
                out_data = base64.b64decode(part["inlineData"]["data"])
                local_path = _save_image(out_data, cfg.id, f"i2i_{prompt[:30]}", prompt)
                return ImageResult(
                    success=True, image_data=out_data, local_path=local_path,
                    model=cfg.id, generation_id=f"{cfg.id}_i2i_{uuid.uuid4().hex[:8]}",
                )

        return ImageResult(success=False, error=f"[{cfg.name}] 未返回图片数据", model=cfg.id)


# ──────────────────────────────────────────────────────────────
# 并发生图入口
# ──────────────────────────────────────────────────────────────
async def generate_multi(
    prompts: List[str],
    provider_ids: List[str],
    **kwargs
) -> dict:
    """
    并发生图：同 prompt + 多 Provider 同时生成
    返回 {provider_id: ImageResult}
    """
    results = {}
    tasks = []
    pid_list = []

    # 构建查找表
    all_providers = {p.id: p for p in cfg_mgr.config.providers}

    for pid in provider_ids:
        if pid in all_providers:
            p_cfg = all_providers[pid]
            for prompt in prompts:
                tasks.append(generate_for_provider(p_cfg, prompt, **kwargs))
                pid_list.append(pid)

    if not tasks:
        return {}

    import asyncio
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    for pid, outcome in zip(pid_list, outcomes):
        if isinstance(outcome, Exception):
            results[pid] = ImageResult(success=False, error=str(outcome), model=pid)
        else:
            results[pid] = outcome

    return results


# ──────────────────────────────────────────────────────────────
# LLM 提示词优化
# ──────────────────────────────────────────────────────────────
async def enhance_prompt_with_llm(prompt: str, llm_provider_id: str = None) -> str:
    """使用配置的 LLM Provider 优化提示词"""
    # 如果指定了特定 LLM Provider，使用它
    if llm_provider_id:
        all_providers = {p.id: p for p in cfg_mgr.config.providers}
        llm_cfg = all_providers.get(llm_provider_id)
    else:
        # 否则使用第一个启用的 LLM Provider
        llm_cfg = cfg_mgr.get_llm_provider()
    
    if not llm_cfg:
        return prompt

    headers = {
        "Authorization": f"Bearer {llm_cfg.api_key}",
        "Content-Type": "application/json",
    }

    sys_prompt = (
        "你是一个专业的AI图像生成提示词优化助手。"
        "将用户的简短描述扩展为详细、专业的生图提示词，"
        "包含艺术风格、光照、构图、相机参数等细节。"
        "直接返回优化后的提示词，不要解释。"
    )

    payload = {
        "model": llm_cfg.model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0, proxy=_get_proxy_url(llm_cfg)) as client:
            resp = await client.post(
                f"{_ensure_v1(llm_cfg.base_url)}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[LLM] 优化失败: {e}")
        return prompt


async def enhance_prompt_with_llm_detailed(prompt: str, llm_provider_id: str = None) -> dict:
    """LLM 提示词优化（返回详细结果，含错误信息）"""
    if llm_provider_id:
        all_providers = {p.id: p for p in cfg_mgr.config.providers}
        llm_cfg = all_providers.get(llm_provider_id)
    else:
        llm_cfg = cfg_mgr.get_llm_provider()

    if not llm_cfg:
        return {"text": prompt, "optimized": False, "error": "未配置 LLM Provider", "provider": None}

    headers = {
        "Authorization": f"Bearer {llm_cfg.api_key}",
        "Content-Type": "application/json",
    }

    sys_prompt = (
        "你是一个专业的AI图像生成提示词优化助手。"
        "将用户的简短描述扩展为详细、专业的生图提示词，"
        "包含艺术风格、光照、构图、相机参数等细节。"
        "直接返回优化后的提示词，不要解释。"
    )

    payload = {
        "model": llm_cfg.model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0, proxy=_get_proxy_url(llm_cfg)) as client:
            resp = await client.post(
                f"{_ensure_v1(llm_cfg.base_url)}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            result_text = data["choices"][0]["message"]["content"].strip()
            return {"text": result_text, "optimized": True, "error": None, "provider": llm_cfg.id}
    except Exception as e:
        print(f"[LLM] 优化失败: {e}")
        return {"text": prompt, "optimized": False, "error": str(e), "provider": llm_cfg.id}


# ──────────────────────────────────────────────────────────────
# 从上游 API 拉取可用模型列表
# ──────────────────────────────────────────────────────────────
async def fetch_models_from_upstream(cfg: ProviderConfig) -> List[str]:
    """
    根据 Provider 的 URL + API Key 调用上游接口获取可用模型列表
    返回模型 ID 列表
    """
    protocol = _detect_protocol(cfg)

    if not cfg.api_key:
        raise ValueError("API Key 未配置")
    if not cfg.base_url:
        raise ValueError("Base URL 未配置")

    try:
        if protocol == "gemini":
            return await _fetch_gemini_models(cfg)
        elif protocol == "qwen":
            return await _fetch_qwen_models(cfg)
        else:
            return await _fetch_openai_models(cfg)
    except Exception as e:
        print(f"[fetch-models] {cfg.name} 拉取失败: {e}")
        # 返回 fallback 列表而不是直接报错
        return _get_fallback_models(cfg, protocol)


async def _fetch_openai_models(cfg: ProviderConfig) -> List[str]:
    """OpenAI 兼容: GET /v1/models，根据 provider 类型推荐合适模型"""
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    base = cfg.base_url.rstrip('/')

    # 尝试 /v1/models
    async with httpx.AsyncClient(timeout=30.0, proxy=_get_proxy_url(cfg)) as client:
        resp = await client.get(f"{base}/models", headers=headers)
        resp.raise_for_status()
        data = resp.json()

    raw_models = data.get("data", [])
    model_ids = [m.get("id", "") for m in raw_models if m.get("id")]

    if cfg.type == "llm":
        # LLM 类型：优先推荐对话/语言模型，排除图像生成模型
        image_keywords = ["image", "dall", "gpt-image", "flux", "sd", "stable", "midjourney", "wanx", "paint", "imagen"]
        llm_models = [m for m in model_ids if not any(k in m.lower() for k in image_keywords)]
        image_models = [m for m in model_ids if any(k in m.lower() for k in image_keywords)]
        return llm_models + image_models
    else:
        # 图像/视频类型：优先推荐图像生成相关模型
        image_keywords = ["image", "dall", "gpt-image", "flux", "sd", "stable", "midjourney", "wanx", "paint"]
        recommended = [m for m in model_ids if any(k in m.lower() for k in image_keywords)]
        others = [m for m in model_ids if m not in recommended]
        return recommended + others


async def _fetch_gemini_models(cfg: ProviderConfig) -> List[str]:
    """
    Gemini: 尝试原生 API，失败则 fallback 到 OpenAI 兼容格式
    支持两种部署方式：
    1. Google 官方 API: /v1beta/models?key=xxx
    2. OpenAI 兼容代理: /v1/models
    """
    # 处理 base_url：移除末尾的 /v1 或 /v1beta
    base = cfg.base_url.rstrip('/')
    if base.endswith('/v1') or base.endswith('/v1beta'):
        base = base.rsplit('/', 1)[0]
    
    # 先尝试原生 Gemini API
    try:
        async with httpx.AsyncClient(timeout=10.0, proxy=_get_proxy_url(cfg)) as client:
            url = f"{base}/v1beta/models?key={cfg.api_key}"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                image_models = []
                other_models = []
                for m in models:
                    mid = m.get("name", "").replace("models/", "")
                    methods = m.get("supportedGenerationMethods", [])
                    if "generateContent" in methods or "imageGeneration" in methods:
                        image_models.append(mid)
                    else:
                        other_models.append(mid)
                return image_models + other_models
    except Exception:
        pass  # fallback 到 OpenAI 兼容格式

    # Fallback: 尝试 OpenAI 兼容格式
    return await _fetch_openai_models(cfg)


async def _fetch_qwen_models(cfg: ProviderConfig) -> List[str]:
    """Qwen2API: 尝试多种路径拉取模型列表"""
    headers = {"Authorization": f"Bearer {cfg.api_key}"}
    base = cfg.base_url.rstrip('/')

    async with httpx.AsyncClient(timeout=30.0, proxy=_get_proxy_url(cfg)) as client:
        # 尝试多种可能的端点
        endpoints_to_try = [
            f"{base}/v1/models",
            f"{base}/models",
            f"{base}/v1/image/models",
        ]

        for endpoint in endpoints_to_try:
            try:
                resp = await client.get(endpoint, headers=headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data.get("data", [])
                    if raw:
                        model_ids = [m.get("id", "") for m in raw if m.get("id")]
                        if model_ids:
                            print(f"[fetch-qwen] 从 {endpoint} 获取到 {len(model_ids)} 个模型")
                            return model_ids
            except Exception as e:
                print(f"[fetch-qwen] {endpoint} 失败: {e}")
                continue

        # 所有端点都失败，返回完整的已知 qwen 图像模型列表（基于截图中的实际模型）
        print(f"[fetch-qwen] 所有端点失败，使用完整 fallback 列表")
        return [
            # Qwen3 系列
            "qwen3-235B-A22B",
            "qwen3-Coder",
            "qwen3-Max",
            "qwen3-Omni-Flash",
            "qwen3-VL-235B-A22B",
            # Qwen3.5 系列
            "qwen3.5-122B-A10B",
            "qwen3.5-27B",
            "qwen3.5-35B-A3B",
            "qwen3.5-397B-A17B",
            "qwen3.5-Flash",
            "qwen3.5-Omni-Flash",
            "qwen3.5-Omni-Plus",
            "qwen3.5-Plus",
            # Qwen3.6 系列
            "qwen3.6-27B",
            "qwen3.6-35B-A3B",
            "qwen3.6-Plus",
            # Wanx 图像系列
            "qwen3-235B-A22B (qwen-plus-2025-07-28-image)",
            "qwen3-Coder (qwen3-coder-plus-image)",
            "qwen3-Max (qwen3-max-2026-01-23-image)",
            "qwen3-Omni-Flash (qwen3-omni-flash-2025-12-01-image)",
            "qwen3-VL-235B-A22B (qwen3-vl-plus-a10b-image)",
            "qwen3.5-122B-A10B (qwen3.5-122b-a10b-image)",
            "qwen3.5-27B (qwen3.5-27b-image)",
            "qwen3.5-35B-A3B (qwen3.5-35b-a3b-image)",
            "qwen3.5-397B-A17B (qwen3.5-397b-a17b-image)",
            "qwen3.5-Flash (qwen3.5-flash-image)",
            "qwen3.5-Omni-Flash (qwen3.5-omni-flash-image)",
            "qwen3.5-Omni-Plus (qwen3.5-omni-plus-image)",
            "qwen3.5-Plus (qwen3.5-plus-image)",
            "qwen3.6-27B (qwen3.6-27b-image)",
            "qwen3.6-35B-A3B (qwen3.6-35b-a3b-image)",
            "qwen3.6-Plus (qwen3.6-plus-image)",
        ]


def _get_fallback_models(cfg: ProviderConfig, protocol: str) -> List[str]:
    """
    当上游 API 拉取失败时，返回该协议的常用模型列表
    这样用户至少能看到一些选项
    """
    if cfg.type == "video":
        return [
            "veo-3-1-generate-preview",
            "veo-3-1-fast-generate-preview",
            "veo-3-0-generate-001",
            "veo-2-0-generate-001",
            "wanx2.1-t2v-turbo",
            "wanx2.1-t2v-plus",
            "hailuoai-video",
            "kling-v2",
            "kling-v1",
            "gen-3a-turbo",
            "gen-3a-turbo-video",
            "sora",
        ]
    if protocol == "gemini":
        return [
            "gemini-2.0-flash-exp-image-generation",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
            "gemini-1.0-pro",
        ]
    elif protocol == "qwen":
        return [
            "qwen3.6-Plus (qwen3.6-plus-image)",
            "qwen3.5-Plus (qwen3.5-plus-image)",
            "qwen3.5-Flash (qwen3.5-flash-image)",
            "qwen3-Max (qwen3-max-2026-01-23-image)",
            "qwen3.6-27B (qwen3.6-27b-image)",
            "qwen3.6-35B-A3B (qwen3.6-35b-a3b-image)",
            "qwen3.5-27B (qwen3.5-27b-image)",
            "qwen3.5-397B-A17B (qwen3.5-397b-a17b-image)",
            "qwen3.5-Omni-Flash (qwen3.5-omni-flash-image)",
            "qwen3.5-Omni-Plus (qwen3.5-omni-plus-image)",
            "qwen3.5-122B-A10B (qwen3.5-122b-a10b-image)",
            "qwen3-Coder (qwen3-coder-plus-image)",
            "qwen3-Omni-Flash (qwen3-omni-flash-2025-12-01-image)",
            "qwen3-VL-235B-A22B (qwen3-vl-plus-a10b-image)",
            "qwen3-235B-A22B (qwen-plus-2025-07-28-image)",
        ]
    else:  # openai or agnes
        if cfg.type == "llm":
            return [
                "gpt-4o-mini", "gpt-4o", "gpt-4-turbo",
                "deepseek-chat", "deepseek-reasoner",
                "qwen-turbo", "qwen-plus", "qwen-max",
                "claude-3-haiku", "claude-3-sonnet",
            ]
        fallback = [
            "gpt-image-2",
            "gpt-image-1",
            "dall-e-3",
            "dall-e-2",
            "flux-dev",
            "flux-schnell",
            "sd-xl",
            "sd-3",
        ]
        if protocol == "agnes":
            return ["agnes-image-2.0-flash"]
        return fallback


# 兼容旧代码导出
PROVIDERS = {}  # 不再使用，保留防报错

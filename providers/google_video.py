"""Google-native video contracts and bounded transport, separate from Flow2API."""

import base64
import binascii
import json
import re
import time
import warnings
from io import BytesIO
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image, UnidentifiedImageError

HOST = "generativelanguage.googleapis.com"
BASE = f"https://{HOST}/v1beta"
MAX_VIDEO_BYTES = 256 * 1024 * 1024


def is_official(url):
    return urlsplit(url).hostname == HOST


def model_spec(model):
    omni = model in ("gemini-omni-1.1-flash", "gemini-omni-flash-preview")
    veo31 = bool(re.fullmatch(r"veo-3\.1-(?:fast-|lite-)?generate-preview", model))
    veo3 = bool(re.fullmatch(r"veo-3\.0-(?:fast-)?generate-001", model))
    veo2 = model == "veo-2.0-generate-001"
    if not (omni or veo31 or veo3 or veo2):
        raise ValueError("该模型尚无已验证的 Google 原生视频参数，请选择 Veo 或 Gemini Omni 视频模型。")
    return {
        "native_google": True, "family": "omni" if omni else "veo",
        "resolutions": (["360p", "720p", "1080p", "4k"] if omni else
                        ["720p"] if veo2 else ["720p", "1080p"] if veo3 or "lite" in model
                        else ["720p", "1080p", "4k"]),
        "duration_options": [] if omni else [5, 6, 7, 8] if veo2 else [8] if veo3 else [4, 6, 8],
        "duration_mode": "model" if omni else "seconds",
        "fps_options": [24], "frame_rule": "",
        "inference_steps_range": None,
        "supports_negative_prompt": False, "supports_seed": False,
        "max_image_count": 3 if omni or veo31 and "lite" not in model else 1,
        "image_roles": (["reference", "first_frame", "first_last"] if omni else
                        ["first_frame", "first_last", "reference"] if veo31 and "lite" not in model else
                        ["first_frame", "first_last"] if veo31 else ["first_frame"]),
    }


def image_part(value):
    if not isinstance(value, str) or len(value) > 15 * 1024 * 1024:
        raise ValueError("参考图片格式或大小无效。")
    match = re.fullmatch(r"data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=\r\n]+)", value)
    if not match:
        raise ValueError("Google 视频参考图需要本地 PNG、JPEG 或 WebP 图片。")
    try:
        raw = base64.b64decode(match[2], validate=True)
        if not raw or len(raw) > 10 * 1024 * 1024:
            raise ValueError
    except (ValueError, binascii.Error):
        raise ValueError("参考图片 Base64 无效或超过 10MB。") from None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as image:
                if Image.MIME.get(image.format) != match[1]:
                    raise ValueError
                image.verify()
    except (ValueError, OSError, SyntaxError, UnidentifiedImageError,
            Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("参考图片内容损坏或与 PNG/JPEG/WebP 格式声明不一致，请重新上传。") from None
    return {"mimeType": match[1], "data": match[2]}


def build_request(req, model):
    spec = model_spec(model)
    if req.mode not in ("ti2vid", "i2vid", "keyframes"):
        raise ValueError("不支持的视频生成模式。")
    if not req.prompt.strip():
        raise ValueError("请输入视频提示词。")
    if req.frame_rate != 24:
        raise ValueError("Google 原生视频输出固定为 24 FPS。")
    resolution = req.resolution or {360: "360p", 720: "720p", 1080: "1080p", 2160: "4k"}.get(min(req.width, req.height))
    aspect = req.aspect_ratio or ("16:9" if req.width >= req.height else "9:16")
    if resolution not in spec["resolutions"] or aspect not in ("16:9", "9:16"):
        raise ValueError("当前模型不支持所选分辨率或画幅比例。")
    images = [image_part(value) for value in (req.image or [])] if req.mode != "ti2vid" else []
    role = "first_last" if req.mode == "keyframes" else req.image_role or "first_frame"
    if req.mode != "ti2vid" and not images:
        raise ValueError("请先上传参考图片。")
    if images:
        if role not in spec["image_roles"]:
            raise ValueError("当前模型不支持所选图片用途。")
        if role == "first_last" and len(images) != 2:
            raise ValueError("首尾帧需要恰好两张图片。")
        if role == "first_frame" and len(images) != 1:
            raise ValueError("首帧模式需要恰好一张图片。")
        if role == "reference" and len(images) > spec["max_image_count"]:
            raise ValueError("参考图片数量超过当前模型上限。")
    if req.num_inference_steps is not None or req.negative_prompt:
        raise ValueError("当前 Google 视频接口不支持此处的推理步数或负面提示词参数。")
    if spec["family"] == "omni":
        if req.seed is not None or req.duration_seconds is not None:
            raise ValueError("Omni 当前使用模型决定时长，不支持此处的 Seed 或固定秒数参数。")
        content = [{"type": "image", "mime_type": img["mimeType"], "data": img["data"]} for img in images]
        content.append({"type": "text", "text": req.prompt})
        return BASE + "/interactions", {
            "model": model, "input": content, "background": False, "store": False, "stream": False,
            "response_format": {"type": "video", "resolution": resolution, "aspect_ratio": aspect, "delivery": "inline"},
        }
    duration = req.duration_seconds if req.duration_seconds is not None else 8
    if duration not in spec["duration_options"]:
        raise ValueError("当前 Veo 模型不支持所选时长。")
    if (resolution in ("1080p", "4k") or images and role == "reference") and duration != 8:
        raise ValueError("Veo 高清输出或参考图模式需要 8 秒时长。")
    if req.seed is not None:
        raise ValueError("当前 Google Developer API 视频适配器未启用 Seed，请清空后重试。")
    instance = {"prompt": req.prompt}
    if images:
        # Match python-genai's _Image_to_mldev, not generateContent's inlineData.
        veo_images = [{"bytesBase64Encoded": img["data"], "mimeType": img["mimeType"]} for img in images]
        if role == "reference":
            instance["referenceImages"] = [{"image": img, "referenceType": "asset"} for img in veo_images]
        else:
            instance["image"] = veo_images[0]
            if role == "first_last":
                instance["lastFrame"] = veo_images[1]
    params = {"aspectRatio": aspect, "durationSeconds": duration, "resolution": resolution}
    return f"{BASE}/models/{model}:predictLongRunning", {"instances": [instance], "parameters": params}


class GoogleVideoError(Exception):
    """Public, bounded error with no upstream response body or credential."""


def _error_hint(error):
    """Emit only fixed vocabulary; upstream text can echo credentials and media."""
    if not isinstance(error, dict):
        return ""
    status = error.get("status")
    statuses = ("INVALID_ARGUMENT", "FAILED_PRECONDITION", "PERMISSION_DENIED",
                "UNAUTHENTICATED", "RESOURCE_EXHAUSTED", "NOT_FOUND", "INTERNAL",
                "UNAVAILABLE", "DEADLINE_EXCEEDED")
    parts = [status] if isinstance(status, str) and status in statuses else []
    fields = []
    details = error.get("details", [])
    if isinstance(details, list):
        for detail in details[:20]:
            if not isinstance(detail, dict) or detail.get("@type") != "type.googleapis.com/google.rpc.BadRequest":
                continue
            violations = detail.get("fieldViolations", [])
            if isinstance(violations, list):
                fields.extend(item.get("field", "") for item in violations[:20] if isinstance(item, dict))
    # Never echo arbitrary field paths, descriptions, URLs or error messages.
    known_fields = ("inlineData", "bytesBase64Encoded", "mimeType", "referenceImages",
                    "lastFrame", "image", "durationSeconds", "aspectRatio", "resolution",
                    "seed", "personGeneration", "response_format", "mime_type", "delivery",
                    "background", "store", "stream", "model", "input")
    text = error.get("message", "")
    text = text[:65536] if isinstance(text, str) else ""
    mentioned = " ".join(field[:512] for field in fields if isinstance(field, str))
    names = [name for name in known_fields if re.search(
        r"(?<![\w])" + re.escape(name) + r"(?![\w])", mentioned + " " + text)]
    if names:
        parts.append("涉及字段：" + ", ".join(names))
    if "delivery" in names and "store" in names:
        parts.append("请检查视频返回方式 delivery 与交互存储 store 的组合兼容性")
    lowered = text.lower()
    categories = (
        (("api key not valid", "api_key_invalid", "invalid api key"), "API Key 无效"),
        (("billing", "paid tier"), "请检查项目付费状态"),
        (("location is not supported", "region", "country"), "请检查模型地区可用性"),
        (("quota", "rate limit", "resource exhausted"), "请检查配额与速率限制"),
        (("safety", "policy", "responsible ai", "rai filter"), "请求被内容安全规则拦截"),
        (("decode image", "invalid image", "image format", "mime type"), "请检查图片编码与格式"),
        (("unknown name", "unknown field", "unrecognized field"), "请求包含接口不接受的字段"),
        (("not supported", "unsupported"), "所选参数或功能不受此模型支持"),
        (("not found", "does not exist"), "请检查模型或文件是否可用"),
    )
    for needles, label in categories:
        if any(needle in lowered for needle in needles):
            parts.append(label)
            break
    return "；".join(parts)


def _check_response(response, stage):
    if response.is_success:
        return
    code = response.status_code
    hint = {401: "请检查 API Key", 403: "请检查模型权限与可用地区",
            429: "请检查配额与速率限制", 400: "请检查模型参数与图片要求"}.get(code, "请稍后检查任务状态")
    data = bytearray()
    diagnostic = ""
    try:
        for chunk in response.iter_bytes(chunk_size=8192):
            data.extend(chunk)
            if len(data) > 64 * 1024:
                break
        else:
            result = json.loads(data)
            if isinstance(result, dict):
                diagnostic = _error_hint(result.get("error"))
    except (ValueError, httpx.HTTPError):
        pass
    suffix = f"；{diagnostic}" if diagnostic else ""
    raise GoogleVideoError(f"Google 视频{stage}返回 HTTP {code}，{hint}{suffix}；未自动重试生成。")


def _json(client, method, url, key, payload=None, *, stage="提交",
          max_bytes=8 * 1024 * 1024, cancelled=lambda: False):
    with client.stream(method, url, headers={"x-goog-api-key": key},
                       **({"json": payload} if payload is not None else {})) as response:
        _check_response(response, stage)
        data = bytearray()
        for chunk in response.iter_bytes(chunk_size=64 * 1024):
            if cancelled():
                raise GoogleVideoError("视频任务已取消。")
            data.extend(chunk)
            if len(data) > max_bytes:
                raise GoogleVideoError("Google 视频任务响应超过大小限制。")
        try:
            result = json.loads(data)
        except ValueError:
            raise GoogleVideoError(f"Google 视频{stage}响应不是有效的 JSON。") from None
        if not isinstance(result, dict):
            raise GoogleVideoError("Google 视频任务响应格式无效。")
        return result


def _save_inline_video(video, destination, cancelled):
    """Decode in bounded blocks; publish only after validating the local MP4."""
    encoded = video.get("data")
    if video.get("mime_type") != "video/mp4" or not isinstance(encoded, str) or not encoded:
        raise GoogleVideoError("Google Omni 未返回有效的内联 MP4 视频。")
    if len(encoded) > 4 * ((MAX_VIDEO_BYTES + 2) // 3):
        raise GoogleVideoError("Google Omni 视频超过本地保存大小限制。")
    temporary = destination.with_suffix(".part")
    try:
        length = 0
        with temporary.open("xb") as output:
            for offset in range(0, len(encoded), 64 * 1024):
                if cancelled():
                    raise GoogleVideoError("视频任务已取消。")
                block = encoded[offset:offset + 64 * 1024]
                if "=" in block and offset + len(block) != len(encoded):
                    raise GoogleVideoError("Google Omni 视频 Base64 数据无效。")
                try:
                    decoded = base64.b64decode(block, validate=True)
                except (ValueError, binascii.Error):
                    raise GoogleVideoError("Google Omni 视频 Base64 数据无效。") from None
                length += len(decoded)
                if length > MAX_VIDEO_BYTES:
                    raise GoogleVideoError("Google Omni 视频超过本地保存大小限制。")
                output.write(decoded)
        with temporary.open("rb") as content:
            header = content.read(32)
        if length < 12 or header[4:8] != b"ftyp":
            raise GoogleVideoError("Google Omni 返回的文件不是有效的 MP4 视频。")
        if cancelled():
            raise GoogleVideoError("视频任务已取消。")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def _file_id(uri):
    parsed = urlsplit(uri)
    if (parsed.scheme != "https" or parsed.hostname != HOST or parsed.port not in (None, 443)
            or parsed.username or parsed.password or parsed.fragment):
        raise GoogleVideoError("Google 视频下载地址未通过安全校验。")
    match = re.fullmatch(r"/(?:v1beta|v1)/files/([A-Za-z0-9_-]+)(?::download)?", parsed.path)
    if not match:
        raise GoogleVideoError("Google 视频文件标识无效。")
    return match[1]


def _download(client, file_id, key, destination, cancelled):
    url = f"{BASE}/files/{file_id}:download?alt=media"
    temporary = destination.with_suffix(".part")
    try:
        for _ in range(4):
            parsed = urlsplit(url)
            host = parsed.hostname or ""
            trusted = host == HOST
            storage = host == "storage.googleapis.com" or host.endswith(".storage.googleapis.com")
            if (parsed.scheme != "https" or parsed.port not in (None, 443) or
                    parsed.username or parsed.password or not (trusted or storage)):
                raise GoogleVideoError("Google 视频下载重定向未通过安全校验。")
            with client.stream("GET", url, headers={"x-goog-api-key": key} if trusted else {}) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                _check_response(response, "下载")
                length = 0
                with temporary.open("xb") as output:
                    for chunk in response.iter_bytes():
                        if cancelled():
                            raise GoogleVideoError("视频任务已取消。")
                        length += len(chunk)
                        if length > MAX_VIDEO_BYTES:
                            raise GoogleVideoError("视频文件超过本地下载大小限制。")
                        output.write(chunk)
                with temporary.open("rb") as content:
                    header = content.read(32)
                if length < 12 or header[4:8] != b"ftyp":
                    raise GoogleVideoError("Google 返回的文件不是有效的 MP4 视频。")
                temporary.replace(destination)
                return
        raise GoogleVideoError("Google 视频下载重定向次数过多。")
    finally:
        temporary.unlink(missing_ok=True)


def run_generation(url, payload, key, destination, *, proxy=None, cancelled=lambda: False,
                   on_stage=lambda stage: None, client_factory=httpx.Client, sleep=time.sleep):
    """One paid POST only; poll and download stay backend-only."""
    with client_factory(proxy=proxy, timeout=httpx.Timeout(600, connect=30),
                        follow_redirects=False, trust_env=False) as client:
        if cancelled():
            return False
        on_stage("generating")
        # Inline Omni media needs Base64 expansion plus a bounded JSON envelope.
        limit = 4 * ((MAX_VIDEO_BYTES + 2) // 3) + 1024 * 1024 if "/interactions" in url else 8 * 1024 * 1024
        result = _json(client, "POST", url, key, payload, max_bytes=limit, cancelled=cancelled)
        if "/interactions" in url:
            # Synchronous Omni: the REST output lives in steps, not SDK output_video.
            if result.get("status") != "completed":
                raise GoogleVideoError("Google Omni 未返回已完成的视频；未自动重试生成。")
            videos = [part for step in result.get("steps", []) if step.get("type") == "model_output"
                      for part in step.get("content", []) if part.get("type") == "video"]
            if videos and "data" in videos[0]:
                on_stage("downloading")
                _save_inline_video(videos[0], Path(destination), cancelled)
                return True
            uri = videos[0].get("uri") if videos else None
        else:
            operation = result.get("name", "")
            if not re.fullmatch(r"(?:models/[A-Za-z0-9_.-]+/)?operations/[A-Za-z0-9_.-]+", operation):
                raise GoogleVideoError("Google Veo 未返回有效的任务标识。")
            for _ in range(180):
                if cancelled():
                    return False
                if result.get("done"):
                    break
                sleep(10)
                result = _json(client, "GET", BASE + "/" + operation, key, stage="任务查询")
            else:
                raise GoogleVideoError("Google 视频任务等待超时；未自动重新生成。")
            if result.get("error"):
                hint = _error_hint(result["error"])
                raise GoogleVideoError("Google 视频任务失败" + (f"；{hint}" if hint else "，请检查权限、配额或内容限制") + "；未自动重试生成。")
            samples = result.get("response", {}).get("generateVideoResponse", {}).get("generatedSamples", [])
            uri = samples[0].get("video", {}).get("uri") if samples else None
        if not isinstance(uri, str):
            raise GoogleVideoError("Google 未返回可下载的视频，可能被内容策略拦截。")
        file_id = _file_id(uri)
        on_stage("downloading")
        if "/interactions" in url:
            for _ in range(120):
                if cancelled():
                    return False
                info = _json(client, "GET", BASE + "/files/" + file_id, key, stage="文件查询")
                if info.get("state") == "ACTIVE":
                    break
                if info.get("state") == "FAILED":
                    raise GoogleVideoError("Google 视频文件处理失败。")
                sleep(5)
            else:
                raise GoogleVideoError("Google 视频文件处理超时。")
        if cancelled():
            return False
        _download(client, file_id, key, Path(destination), cancelled)
        return True

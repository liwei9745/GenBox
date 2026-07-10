"""
GenBox v2 - 多模型生图生视频服务
FastAPI 主入口
"""
import os
import sys
import platform
import threading
import asyncio
import json as _json
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

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

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    cfg_mgr, GALLERY_DIR, STORAGE_DIR, ProviderConfig, ProvidersConfig,
    is_prod_mode, get_admin_key, verify_admin_key, generate_admin_key, reset_admin_key,
)
from providers import generate_multi, enhance_prompt_with_llm, enhance_prompt_with_llm_detailed, ImageResult, fetch_models_from_upstream, _save_image


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
    mode: str = "t2i"                # "t2i" 文生图 | "i2i" 图生图
    image_data: Optional[str] = None  # base64 图片数据 (i2i 模式)
    strength: float = 0.55            # 变换强度 (i2i 模式)
    continuous: bool = False          # 连续生图模式（保持一致性）
    system_prompt: Optional[str] = None  # 系统提示词（专业模式）
    continuous_id: Optional[str] = None  # 连续生图会话 ID（用于保持一致性）
    quantities: dict = {}              # {provider_id: 数量(int)}，如 {"gpt-image": 2, "gemini": 1}
    # ── Per-provider 设置 ──
    provider_settings: dict = {}       # {provider_id: {quality, size, ...}}
    # ── 尺寸自适应：小图生成 + 本地放大 ──
    upscale_to: Optional[str] = None
    upscale_method: str = "lanczos3"
    upscale_ratio: str = "original"  # 宽高比：1:1, 16:9, 21:9, 4:3, 3:2, 9:16, 3:4, original


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
    extra: dict = {}


# ──────────────────────────────────────────────────────────────
# FastAPI 实例
# ──────────────────────────────────────────────────────────────
app = FastAPI(title="GenBox", version="2.0.0")
app_start_time = time.time()

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8891,http://127.0.0.1:8891").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
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
        # 获取允许的源
        allowed_origins = set(ALLOWED_ORIGINS)
        # 本地地址也允许
        local_origins = {"http://localhost:8891", "http://127.0.0.1:8891", "http://localhost:8890", "http://127.0.0.1:8890"}
        allowed_origins.update(local_origins)
        # 检查 Origin
        if origin:
            origin_host = origin.split("://")[1].split("/")[0] if "://" in origin else origin
            allowed_hosts = set()
            for o in allowed_origins:
                if "://" in o:
                    allowed_hosts.add(o.split("://")[1].split("/")[0])
            if origin_host not in allowed_hosts:
                return JSONResponse(status_code=403, content={"error": "CSRF 验证失败", "code": "CSRF_REJECTED"})
        # 检查 Referer
        elif referer:
            referer_host = referer.split("://")[1].split("/")[0] if "://" in referer else referer
            allowed_hosts = set()
            for o in allowed_origins:
                if "://" in o:
                    allowed_hosts.add(o.split("://")[1].split("/")[0])
            if referer_host not in allowed_hosts:
                return JSONResponse(status_code=403, content={"error": "CSRF 验证失败", "code": "CSRF_REJECTED"})
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

# 连续生图会话状态（内存存储）
continuous_sessions: dict = {}  # {session_id: {"images": [...], "prompts": [...], "context": "..."}}

# ──────────────────────────────────────────────────────────────
# 生图任务队列（带并发控制，防风控）
# ──────────────────────────────────────────────────────────────
image_tasks: dict = {}        # {gen_id: {status, progress, providers: {pid: {status, log, result}}, ...}}
image_gen_semaphore = None    # 延迟初始化（FastAPI lifespan）
MAX_CONCURRENT_GENERATIONS = 16  # 最大并发生图数，可调


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
        try:
            from PIL import Image
            with Image.open(f) as img:
                if img.info and "Prompt" in img.info:
                    prompt_text = img.info["Prompt"]
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


@app.get("/api/providers")
async def list_providers():
    """获取所有 Provider 配置（API Key 脱敏）"""
    from providers.key_pool import key_pool_manager
    providers_data = []
    for p in cfg_mgr.config.providers:
        d = p.model_dump(exclude={"api_key", "api_keys", "endpoints"})
        d["has_key"] = bool(p.api_key or p.api_keys)
        d["has_keys"] = len(p.get_effective_keys()) > 1
        d["key_count"] = len(p.get_effective_keys())
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
            ep_dict = {"url": ep.url, "model": ep.model, "enabled": ep.enabled}
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
            d["has_key"] = bool(p.api_key or p.api_keys)
            keys = p.get_effective_keys()
            if keys:
                d["api_key_masked"] = keys[0][:4] + "****" + keys[0][-4:] if len(keys[0]) > 8 else "****"
            d["endpoints"] = []
            for ep in (p.endpoints or []):
                ep_dict = {"url": ep.url, "model": ep.model, "enabled": ep.enabled}
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

    new_p = ProviderConfig(**req.model_dump())

    if existing_idx is not None:
        cfg.providers[existing_idx] = new_p
    else:
        cfg.providers.append(new_p)

    cfg_mgr.save(cfg)
    _write_log("provider", f"Provider '{req.id}' 已保存", {"type": req.type})
    return {"ok": True, "message": f"Provider '{req.id}' 已保存", "id": req.id}


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
    """检查是否需要首次设置向导"""
    providers = cfg_mgr.config.providers
    has_key = any(p.api_key for p in providers if p.type in ("image", "video"))
    has_enabled = any(p.enabled for p in providers if p.type in ("image", "video"))
    return {
        "needs_setup": not has_key,
        "has_configured_provider": has_key,
        "has_enabled_provider": has_enabled,
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
                    _verify_ssl = os.getenv("VERIFY_SSL", "false").lower() == "true"
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
                    "message": "(使用推荐列表，上游 API 未响应)" if is_fallback else "",
                    "provider_type": p.type,
                }
            except Exception as e:
                return {
                    "success": False,
                    "detail": f"拉取失败: {str(e)}。请确认 URL 支持 GET /v1/models 接口，或手动输入模型名称。",
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
@app.post("/api/generate")
async def generate(req: GenerateRequest, request: Request):
    global generation_counter, image_gen_semaphore
    if image_gen_semaphore is None:
        image_gen_semaphore = asyncio.Semaphore(MAX_CONCURRENT_GENERATIONS)

    # 速率限制
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip, "generate"):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    generation_counter += 1
    gen_id = f"gen_{generation_counter:04d}_{uuid.uuid4().hex[:6]}"

    # LLM 优化提示词（仅对文生图模式）
    original_prompt = req.prompt
    enhanced_by_llm = None
    llm_error_msg = None
    if req.enhance_prompt and req.mode == "t2i":
        enhanced_by_llm = await enhance_prompt_with_llm(req.prompt, req.llm_provider_id)
        if enhanced_by_llm == req.prompt:
            # LLM 未配置或调用失败（返回了原始 prompt）
            llm_error_msg = "LLM 优化未生效，请检查 Provider 配置"

    # 确定要调用的 Provider 列表
    if req.providers:
        provider_ids = list(dict.fromkeys(req.providers))
    else:
        provider_ids = [p.id for p in cfg_mgr.get_image_providers()]

    if not provider_ids:
        raise HTTPException(status_code=400, detail="无可用的生图模型，请先在设置中配置")

    # 构建参数
    kwargs = {}
    if req.size: kwargs["size"] = req.size
    if req.quality: kwargs["quality"] = req.quality
    if req.mode == "i2i" and req.image_data:
        kwargs["image_data"] = req.image_data
        kwargs["strength"] = req.strength

    all_providers = {p.id: p for p in cfg_mgr.config.providers}

    # 构建任务列表 (pid, seq, qty) + per-provider kwargs
    task_list = []
    provider_kwargs_map = {}  # {pid: kwargs} per-provider overrides
    for pid in provider_ids:
        qty = req.quantities.get(pid, 1) if req.quantities else 1
        # 为每个 provider 构建独立的 kwargs
        p_kwargs = dict(kwargs)  # 复制全局 kwargs
        p_setting = req.provider_settings.get(pid, {})
        if p_setting.get("size"):
            p_kwargs["size"] = p_setting["size"]
        if p_setting.get("quality"):
            p_kwargs["quality"] = p_setting["quality"]
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
        "mode": req.mode,
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
        # ── 尺寸自适应 ──
        "upscale_to": req.upscale_to,
        "upscale_method": req.upscale_method,
        "upscale_ratio": req.upscale_ratio,
    }

    # 后台处理
    asyncio.create_task(_process_image_gen(gen_id))

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
    """后台逐个处理生图任务（带并发控制）"""
    global image_gen_semaphore
    task = image_tasks.get(gen_id)
    if not task:
        return

    task["status"] = "generating"
    task["start_time"] = time.time()

    from providers import generate_for_provider as _gen_one

    async def _run_one(key, pid, seq, p_cfg, prompt, kwargs):
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
                    state["log"].append(f"[{time.strftime('%H:%M:%S')}] ⚠ 放大失败(保留原图): {str(ue)[:80]}")

            if res.success:
                state["status"] = "completed"
                state["progress"] = 100
                state["log"].append(f"[{time.strftime('%H:%M:%S')}] ✔ 完成 ({res.elapsed_seconds}s)")
            else:
                state["status"] = "failed"
                state["progress"] = 100
                state["log"].append(f"[{time.strftime('%H:%M:%S')}] ✗ 失败: {res.error[:120]}")
                # 写入详细错误日志到 logs.jsonl
                _write_log("generation_error", f"{pid} 失败: {res.error[:200]}", {
                    "provider_id": pid,
                    "model": cfg.model if cfg else pid,
                    "error": res.error[:500],
                    "mode": task.get("mode", "t2i"),
                    "elapsed_seconds": res.elapsed_seconds,
                })

            state["result"] = {
                "success": res.success,
                "local_path": res.local_path,
                "generation_id": res.generation_id,
                "error": res.error,
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
            state["status"] = "failed"
            state["progress"] = 100
            state["log"].append(f"[{time.strftime('%H:%M:%S')}] ✗ 异常: {str(e)[:120]}")
            state["result"] = {
                "success": False, "local_path": None, "generation_id": None,
                "error": str(e), "model": pid, "prompt": prompt,
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
            if i > 0:
                await asyncio.sleep(1.5)
            key = f"{p}_{s}" if q > 1 else p
            p_cfg = task["all_providers"].get(p)
            if p_cfg:
                p_kwargs = task.get("provider_kwargs_map", {}).get(p, task["kwargs"])
                await _run_one(key, p, s, p_cfg, task["enhanced_prompt"] or task["prompt"], p_kwargs)

    await asyncio.gather(*[_run_provider_group(pid, items) for pid, items in provider_tasks.items()])

    # 全部完成
    elapsed = round(time.time() - task["start_time"], 1)
    task["status"] = "completed"
    task["progress"] = 100

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
        for key, res in task["results"].items():
            if res["success"] and res["local_path"]:
                continuous_sessions[cid]["images"].append(res["local_path"])
        continuous_sessions[cid]["context"] = " | ".join(continuous_sessions[cid]["prompts"][-3:])
        task["continuous_id"] = cid

    # 记录历史
    generation_history[gen_id] = {
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
    _save_history_entry(generation_history[gen_id])

    ok_count = sum(1 for r in task["results"].values() if r.get("success"))
    _write_log("generate", f"生图完成: {ok_count}/{len(task['providers'])} 成功 ({elapsed}s)", {"gen_id": gen_id})


@app.get("/api/generate/status/{gen_id}")
async def get_generate_status(gen_id: str):
    task = image_tasks.get(gen_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 计算整体进度（加权平均每个 provider 的进度）
    states = task["provider_states"]
    total = len(states)
    if total > 0:
        progress = round(sum(s.get("progress", 0) for s in states.values()) / total)
    else:
        progress = 0

    # 判断最终状态
    status = task["status"]
    if status == "completed":
        pass
    else:
        done = sum(1 for s in states.values() if s.get("status") in ("completed", "failed"))
        if done >= total and total > 0:
            status = "completed"
            task["status"] = "completed"

    elapsed = round(time.time() - task["start_time"], 1) if task.get("start_time") else 0

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
        "results": task["results"] if status == "completed" else {},
        "group_timings": {pid: {"total": round(sum(img["elapsed"] for img in imgs), 1), "images": imgs}
                          for pid, imgs in _calc_group_timings(task["results"]).items()} if status == "completed" else {},
    }


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
    n: int = 1                       # 生成数量 1-4


@app.post("/api/images/variations")
async def image_variations(req: VariationRequest):
    """图片变形：基于输入图片生成变体（OpenAI /images/variations 协议）"""
    import base64 as _b64
    import httpx as _httpx

    # 解析图片
    if "," in req.image_data:
        img_b64 = req.image_data.split(",")[1]
    else:
        img_b64 = req.image_data
    try:
        img_bytes = _b64.b64decode(img_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="图片数据无效")

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
    last_error = None

    for ep in endpoints:
        url = f"{ep.url.rstrip('/')}/images/variations"
        headers = {"Authorization": f"Bearer {ep.key}"}
        files = {"image": ("image.png", img_bytes, "image/png")}
        data = {"model": model_id, "n": min(req.n, 4), "size": req.size, "response_format": "b64_json"}

        try:
            _verify_ssl = os.getenv("VERIFY_SSL", "false").lower() == "true"
            async with _httpx.AsyncClient(timeout=180.0, verify=_verify_ssl) as client:
                resp = await client.post(url, headers=headers, files=files, data=data)
                if resp.status_code >= 400:
                    last_error = f"端点 {ep.url[:40]}... HTTP {resp.status_code}"
                    continue  # 尝试下一个端点
                result = resp.json()
                break  # 成功
        except Exception as e:
            last_error = f"端点 {ep.url[:40]}... {str(e)[:60]}"
            continue  # 尝试下一个端点
    else:
        raise HTTPException(status_code=502, detail=f"所有端点均失败: {last_error}")

    # 解析结果
    images_out = []
    for item in result.get("data", []):
        b64_data = item.get("b64_json")
        if b64_data:
            raw = _b64.b64decode(b64_data)
            local_path = _save_image(raw, provider.id, "variation", "")
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
async def thumbnail(filename: str):
    # 先查图片目录
    fpath = GALLERY_DIR / filename
    if fpath.exists():
        return FileResponse(str(fpath))
    # 再查视频缩略图目录
    thumb_name = Path(filename).stem + "_thumb.jpg"
    thumb_path = VIDEO_THUMBS_DIR / thumb_name
    if thumb_path.exists():
        return FileResponse(str(thumb_path))
    # 尝试从视频生成缩略图
    video_path = VIDEO_DIR / filename
    if video_path.exists():
        gen = _generate_video_thumbnail(video_path)
        if gen and gen.exists():
            return FileResponse(str(gen))
    raise HTTPException(status_code=404, detail="缩略图不存在")


@app.get("/api/gallery/image/{filename}")
async def gallery_image(filename: str):
    fpath = GALLERY_DIR / filename
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(str(fpath), media_type="image/png")


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
    fpath = GALLERY_DIR / filename
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="图片不存在")
    data = _b64.b64encode(fpath.read_bytes()).decode()
    return {"filename": filename, "data": f"data:image/png;base64,{data}"}


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
    """检测视频 Provider 的 API 协议类型: 'agnes' | 'gemini' | 'openai'"""
    base = provider.base_url.lower()
    pid = provider.id.lower()
    if "agnes" in pid or "agnes" in base:
        return "agnes"
    if "gemini" in pid or "localhost:38000" in base or "google" in base or "flow2api" in base:
        return "gemini"
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
                                    sse_error_msg = err.get("message", str(err))
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
            raise HTTPException(status_code=e.response.status_code, detail=f"视频 API 错误: {e.response.text[:500]}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"视频 API 调用失败: {str(e)}")

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
    else:
        payload = _build_agnes_payload(req, effective_model)
        api_url = f"{base_url}/videos"
        try:
            async with _httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(api_url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except _httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=f"视频 API 错误: {e.response.text[:500]}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"视频 API 调用失败: {str(e)}")
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
    fpath = VIDEO_DIR / filename
    if not fpath.exists():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    return FileResponse(str(fpath), media_type="video/mp4")


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
    for f in sorted(GALLERY_DIR.glob("*.png"), reverse=True)[:40]:
        try:
            data = _b64.b64encode(f.read_bytes()).decode()
            prompt_text = ""
            model_name = f.stem.split("_")[0] if f.stem else "unknown"
            try:
                from PIL import Image
                with Image.open(f) as img:
                    if img.info and "Prompt" in img.info:
                        prompt_text = img.info["Prompt"]
            except Exception:
                pass
            items.append({
                "filename": f.name,
                "data": f"data:image/png;base64,{data}",
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
            _verify_ssl = os.getenv("VERIFY_SSL", "false").lower() == "true"
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
                    _verify_ssl = os.getenv("VERIFY_SSL", "false").lower() == "true"
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
        _verify_ssl = os.getenv("VERIFY_SSL", "false").lower() == "true"
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
    """服务器控制：status/start/restart/stop"""
    import subprocess
    if action == "status":
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:8891/", timeout=2)
            return {"status": "running", "port": 8891}
        except Exception:
            return {"status": "stopped", "port": 8891}
    elif action == "restart":
        subprocess.Popen(["python", "main.py"], cwd=str(STORAGE_DIR.parent))
        return {"status": "restarting"}
    elif action == "stop":
        os._exit(0)
        return {"status": "stopping"}
    return {"status": "unknown"}


# ──────────────────────────────────────────────────────────────
# 自动更新系统
# ──────────────────────────────────────────────────────────────
@app.get("/api/update/check")
async def check_for_updates(mirror: str = ""):
    """检查是否有可用更新"""
    from updater import check_update
    info = await check_update(mirror)
    return {
        "available": info.available,
        "current_version": info.current_version,
        "latest_version": info.latest_version,
        "release_notes": info.release_notes,
        "download_url": info.download_url,
        "update_type": info.update_type,
    }


@app.get("/api/update/mirrors")
async def test_update_mirrors():
    """测试所有 GitHub 代理线路的连通性和延迟"""
    from updater import test_all_mirrors
    results = await test_all_mirrors()
    return {
        "mirrors": [
            {
                "name": r.name,
                "url": r.url,
                "latency_ms": r.latency_ms,
                "available": r.available,
                "error": r.error,
            }
            for r in results
        ],
        "recommended": results[0].name if results and results[0].available else None,
    }


@app.post("/api/update/apply")
async def apply_update(mirror: str = "", download_url: str = ""):
    """执行更新"""
    from updater import apply_update
    result = await apply_update(mirror, download_url)
    return result


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
    }


# ──────────────────────────────────────────────────────────────
# 安全策略：ADMINKEY 认证中间件
# ──────────────────────────────────────────────────────────────
AUTH_EXEMPT_PATHS = {
    "/api/setup/status", "/api/setup/confirm", "/api/setup/first-run",
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


@app.get("/api/setup/status")
async def setup_status():
    """检查是否需要首次设置"""
    admin_key = get_admin_key()
    providers = cfg_mgr.config.providers
    has_provider_key = any(p.api_key for p in providers if p.type in ("image", "video"))
    return {
        "prod_mode": is_prod_mode(),
        "has_admin_key": bool(admin_key),
        "needs_first_run": is_prod_mode() and not admin_key,
        "has_provider_key": has_provider_key,
    }


@app.post("/api/setup/first-run")
async def setup_first_run():
    """首次启动：生成 ADMINKEY 并返回"""
    key = generate_admin_key()
    return {"admin_key": key, "message": "请保存此密钥，关闭后无法再次查看！"}


@app.post("/api/setup/confirm")
async def setup_confirm():
    """确认已保存密钥"""
    return {"ok": True, "message": "设置完成"}


# ──────────────────────────────────────────────────────────────
# 静态文件（必须在所有 API 路由之后挂载）
# ──────────────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=str(BASE_PATH / "static")), name="static")


# ──────────────────────────────────────────────────────────────
# 启动
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    # 命令行参数：--reset-admin
    if "--reset-admin" in sys.argv:
        new_key = reset_admin_key()
        print(f"[Admin Reset] 新密钥已生成: {new_key}")
        print(f"[Admin Reset] 已写入 .env")
        print(f"[Admin Reset] 请重启服务")
        sys.exit(0)

    # 首次启动：交互式选择模式
    def _first_run_setup():
        """首次启动时引导用户完成配置"""
        from config import _read_env, _write_env, BASE_DIR
        import secrets
        
        env = _read_env()
        # 检查是否已配置过
        if "APP_MODE" in env:
            return  # 已配置，跳过
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║                   🎉 欢迎使用 GenBox!                       ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  首次启动，请选择部署方式：                                   ║
║                                                              ║
║  [1] 本地使用（推荐新手）                                     ║
║      - 无需认证，打开即用                                    ║
║      - 仅本机可访问                                          ║
║      - 适合个人电脑调试                                      ║
║                                                              ║
║  [2] VPS/云服务器部署                                         ║
║      - 需要管理员密钥登录                                    ║
║      - 可通过公网访问                                        ║
║      - 安全性高                                              ║
║                                                              ║
║  [3] Docker 部署                                             ║
║      - 使用 docker-compose 一键部署                          ║
║      - 参考 .env.example 配置                                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        while True:
            try:
                choice = input("请选择 (1/2/3): ").strip()
                if choice == "1":
                    # 本地开发模式
                    _write_env({"APP_MODE": "dev"})
                    print("\n✅ 已启用本地模式（无需认证，仅限本机访问）\n")
                    break
                elif choice == "2":
                    # VPS 模式
                    _write_env({"APP_MODE": "prod"})
                    print("\n✅ 已启用生产模式（需要认证）\n")
                    
                    # 询问 CORS 配置
                    print("─" * 50)
                    print("📡 网络配置")
                    print("─" * 50)
                    print("为了让浏览器能访问 API，需要配置允许的源。")
                    print("如果有域名请输入域名，否则输入服务器 IP。")
                    print("多个地址用逗号分隔，直接回车跳过（默认仅本机）。")
                    print()
                    
                    origins_input = input("允许的源 (如 http://your-ip:8891): ").strip()
                    if origins_input:
                        _write_env({"ALLOWED_ORIGINS": origins_input})
                        print(f"✅ 已设置 CORS: {origins_input}\n")
                    else:
                        print("⏭️  跳过，使用默认配置（仅本机）\n")
                    
                    # 自动生成并显示管理密钥
                    admin_key = secrets.token_urlsafe(16)
                    _write_env({"ADMIN_KEY": admin_key})
                    print("─" * 50)
                    print("🔐 管理员密钥已自动生成")
                    print("─" * 50)
                    print(f"\n   {admin_key}\n")
                    print("⚠️  请立即保存此密钥！关闭后无法再次查看！")
                    print("   建议保存到密码管理器。\n")
                    break
                elif choice == "3":
                    # Docker 模式
                    print("\n🐳 Docker 部署指引：")
                    print("─" * 50)
                    print("1. 复制环境配置文件：")
                    print("   cp .env.example .env")
                    print()
                    print("2. 编辑 .env 文件，填入你的 API Key：")
                    print("   nano .env")
                    print()
                    print("3. 启动容器：")
                    print("   docker-compose up -d")
                    print()
                    print("4. 查看日志：")
                    print("   docker-compose logs -f")
                    print()
                    print("详细说明请参考 README.md 的 Docker 部署章节。")
                    print("─" * 50)
                    
                    # Docker 默认使用 prod 模式
                    _write_env({"APP_MODE": "prod"})
                    print("\n✅ Docker 部署默认启用生产模式\n")
                    break
                else:
                    print("❌ 请输入 1、2 或 3")
            except (EOFError, KeyboardInterrupt):
                # 无交互环境（如 Docker），默认使用 prod 模式
                _write_env({"APP_MODE": "prod"})
                print("\n✅ 无交互环境，默认启用生产模式\n")
                break

    # 执行首次启动设置
    _first_run_setup()

    # 重新加载环境变量
    from dotenv import load_dotenv
    load_dotenv(BASE_PATH / ".env", override=True)

    # 生产模式：检查 ADMINKEY
    if is_prod_mode():
        admin_key = get_admin_key()
        if not admin_key:
            key = generate_admin_key()
            print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    🔐 首次启动 - 安全密钥                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  管理密钥已生成，请立即保存：                                 ║
║                                                              ║
║  {key}                                                      ║
║                                                              ║
║  ⚠️  此密钥仅显示一次，关闭后无法再次查看！                    ║
║  ⚠️  请复制保存到安全位置（如密码管理器）                      ║
║                                                              ║
║  使用方式：                                                  ║
║  1. 打开浏览器访问 http://localhost:8891                      ║
║  2. 在登录页输入此密钥                                        ║
║  3. 或在 API 请求头中添加: X-Admin-Key: <密钥>               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
            """)
        else:
            print(f"[Security] 管理密钥已加载")

    mode_str = "PRODUCTION 🔒" if is_prod_mode() else "DEVELOPMENT ⚠️"
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                      GenBox v2.0.0                          ║
╠══════════════════════════════════════════════════════════════╣
║  模式:     {mode_str:<46}║
║  地址:     http://localhost:8891                             ║
║  端口:     8891                                              ║
║  媒体库:   {str(GALLERY_DIR):<46}║
║  配置:     {str(STORAGE_DIR / 'providers.json'):<46}║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 自动打开浏览器
    def _open_browser():
        time.sleep(1.5)
        try:
            webbrowser.open("http://localhost:8891")
        except Exception:
            pass  # 无头环境忽略
    threading.Thread(target=_open_browser, daemon=True).start()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8891,
        reload=False,
    )

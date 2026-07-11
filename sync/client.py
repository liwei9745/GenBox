"""
远程 chatgpt2api 兼容部署的客户端。

端点契约（pinned 2252046f）：
- GET /version                  -> {"version": "x.y.z"}
- GET /auth/status              -> {"authenticated": true, "role": "admin", ...}
- GET /api/images               -> 分页图片清单（admin Bearer）
- GET /images/{path}            -> 原始文件（无认证，但本客户端服务端下载）

注意：
- base_url 归一化时去掉结尾的 /v1（管理 API 在宿主根路径）。
- created_at 视为 Asia/Shanghai。
"""
import hashlib
import socket
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse

import httpx
import ipaddress


_BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_url_safe(url: str) -> tuple:
    """复制到本模块以避免与 main.py 循环依赖；校验主机非内网。"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return False, "无效的 URL"
        try:
            ip_str = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(ip_str)
            for net in _BLOCKED_IP_RANGES:
                if ip in net:
                    return False, f"目标 IP {ip_str} 属于保留地址范围"
        except socket.gaierror:
            return False, f"无法解析域名: {hostname}"
        return True, None
    except Exception as e:  # noqa
        return False, f"URL 解析失败: {str(e)[:50]}"


def _normalize_base_url(base_url: str) -> str:
    """去掉结尾的 /v1 与多余斜杠，保留宿主根。"""
    u = (base_url or "").strip().rstrip("/")
    if u.lower().endswith("/v1"):
        u = u[:-3].rstrip("/")
    return u


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_image_metadata(log_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """从远端调用日志中提取 image URL -> prompt/model 映射。"""
    result: Dict[str, Dict[str, str]] = {}
    for item in log_items or []:
        detail = item.get("detail") if isinstance(item, dict) else None
        if not isinstance(detail, dict) or not str(detail.get("endpoint", "")).startswith("/v1/images/"):
            continue
        prompt = str(detail.get("request_text_full") or detail.get("request_text") or "")
        model = str(detail.get("model") or "")
        urls = detail.get("urls") or []
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            if url:
                result[str(url)] = {"prompt": prompt, "model": model}
    return result


class ChatGPT2APIClient:
    """一个远程部署的轻量客户端。"""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self.base_url = _normalize_base_url(base_url)
        self.api_key = api_key
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def _safe_url(self, path: str) -> str:
        return urljoin(self.base_url + "/", path.lstrip("/"))

    async def probe(self) -> Dict[str, Any]:
        """探测版本与权限；非 admin 时抛出。"""
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as c:
            try:
                vr = await c.get(self._safe_url("/version"))
                version = vr.json().get("version") if vr.status_code == 200 else None
            except Exception:  # noqa
                version = None
            try:
                ar = await c.get(self._safe_url("/auth/status"), headers=self._headers())
                auth = ar.json() if ar.status_code == 200 else {}
            except Exception:  # noqa
                auth = {}
        authenticated = bool(auth.get("authenticated")) or auth.get("role") == "admin"
        if not authenticated:
            raise PermissionError("远端鉴权失败：需要 admin Bearer token")
        return {
            "version": version,
            "authenticated": authenticated,
            "role": auth.get("role", "unknown"),
        }

    async def list_all_images(
        self,
        start_date: str = "",
        end_date: str = "",
        media_type: str = "image",
        page_size: int = 200,
        max_pages: int = 50,
    ) -> List[Dict[str, Any]]:
        """分页拉取全部图片记录（admin Bearer）。"""
        items: List[Dict[str, Any]] = []
        offset = 0
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as c:
            for _ in range(max_pages):
                params = {
                    "limit": page_size,
                    "offset": offset,
                    "media_type": media_type,
                }
                if start_date:
                    params["start_date"] = start_date
                if end_date:
                    params["end_date"] = end_date
                r = await c.get(
                    self._safe_url("/api/images"),
                    params=params,
                    headers=self._headers(),
                )
                if r.status_code != 200:
                    raise RuntimeError(f"远端列表失败: HTTP {r.status_code}")
                data = r.json()
                batch = data.get("items", [])
                items.extend(batch)
                if not data.get("has_more") or len(batch) < page_size:
                    break
                offset += page_size
        return items

    async def list_image_metadata(self) -> Dict[str, Dict[str, str]]:
        """读取远端生图调用日志，按结果 URL 关联提示词与模型。"""
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as c:
            r = await c.get(
                self._safe_url("/api/logs"),
                params={"type": "call", "limit": 20000},
                headers=self._headers(),
            )
            if r.status_code != 200:
                raise RuntimeError(f"远端日志失败: HTTP {r.status_code}")
            return extract_image_metadata(r.json().get("items", []))

    async def download(self, url: str) -> bytes:
        """服务端下载原始文件，校验主机与跳转。"""
        safe, err = is_url_safe(url)
        if not safe:
            raise ValueError(f"不安全的下载地址: {err}")
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=False) as c:
            r = await c.get(url, headers=self._headers())
            if r.status_code != 200:
                raise RuntimeError(f"下载失败: HTTP {r.status_code}")
            return r.content

    def resolve_url(self, url: str) -> str:
        """将清单中的相对/绝对 url 解析为可下载地址。"""
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return self._safe_url(url)

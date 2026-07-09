"""
全局配置：动态 Provider 注册系统
- storage/providers.json: 运行时配置（前端可写）
- .env: 默认值兜底
"""
import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from dotenv import load_dotenv

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
    extra: Dict[str, Any] = {} # 扩展参数

    def get_effective_keys(self) -> List[str]:
        """获取有效的 API Key 列表（api_keys 优先，fallback 到 api_key）"""
        keys = [k for k in (self.api_keys or []) if k and k.strip()]
        if not keys and self.api_key and self.api_key.strip():
            keys = [self.api_key.strip()]
        return keys

    def get_active_endpoints(self) -> List[EndpointConfig]:
        """获取启用的端点列表；如果没有端点则从 base_url+api_key 构造一个"""
        active = [ep for ep in (self.endpoints or []) if ep.enabled and ep.url and ep.key]
        if active:
            return active
        if self.base_url and (self.api_key or self.get_effective_keys()):
            key = self.api_key or (self.get_effective_keys()[0] if self.get_effective_keys() else "")
            return [EndpointConfig(url=self.base_url, key=key)]
        return []


class ProxyConfig(BaseModel):
    """网络代理配置"""
    enabled: bool = False
    type: str = "http"        # http / socks5
    host: str = "127.0.0.1"
    port: int = 10808
    username: str = ""
    password: str = ""


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
    return os.getenv("ADMIN_KEY", "")

def get_admin_key_hash() -> str:
    """获取当前 ADMIN_KEY 的哈希值"""
    key = get_admin_key()
    if not key:
        return ""
    return _hash_admin_key(key)

def is_prod_mode() -> bool:
    """是否生产模式（启用认证）"""
    return os.getenv("APP_MODE", "prod") == "prod"

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

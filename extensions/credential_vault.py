import base64
import json
import os
import threading
import time
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import STORAGE_DIR
from extensions.models import ManagedCredential


VAULT_FILE = STORAGE_DIR / "extension-credentials.vault.json"
VAULT_VERSION = 1
KDF_ITERATIONS = 1_200_000
_VERIFIER = b"genbox-extension-vault-v1"


class CredentialVault:
    def __init__(self, path: Path = VAULT_FILE):
        self.path = path
        self._fernet: Fernet | None = None
        self._mutex = threading.RLock()

    def status(self) -> dict:
        with self._mutex:
            data = self._read() if self.path.exists() else None
            return {
                "configured": data is not None,
                "unlocked": self._fernet is not None,
                "entry_count": len(data.get("entries", {})) if data else 0,
            }

    def setup(self, password: str) -> dict:
        with self._mutex:
            if self.path.exists():
                raise ValueError("凭证库已设置")
            salt = os.urandom(16)
            fernet = self._derive(password, salt, KDF_ITERATIONS)
            data = {
                "version": VAULT_VERSION,
                "kdf": "pbkdf2-sha256",
                "iterations": KDF_ITERATIONS,
                "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
                "verifier": fernet.encrypt(_VERIFIER).decode("ascii"),
                "entries": {},
            }
            self._write(data)
            self._fernet = fernet
            return self.status()

    def unlock(self, password: str) -> dict:
        with self._mutex:
            data = self._require_configured()
            salt = base64.urlsafe_b64decode(data["salt"].encode("ascii"))
            fernet = self._derive(password, salt, int(data["iterations"]))
            try:
                if fernet.decrypt(data["verifier"].encode("ascii")) != _VERIFIER:
                    raise ValueError("解锁密码错误")
            except (InvalidToken, ValueError, TypeError) as exc:
                raise ValueError("解锁密码错误") from exc
            self._fernet = fernet
            return self.status()

    def lock(self) -> dict:
        with self._mutex:
            self._fernet = None
            return self.status()

    def list_metadata(self) -> list[dict]:
        with self._mutex:
            data = self._require_configured()
            return [
                {
                    "instance_id": instance_id,
                    "updated_at": entry.get("updated_at", ""),
                    "fields": list(entry.get("fields", [])),
                }
                for instance_id, entry in sorted(data["entries"].items())
            ]

    def get(self, instance_id: str) -> ManagedCredential:
        with self._mutex:
            fernet = self._require_unlocked()
            entry = self._require_configured()["entries"].get(instance_id)
            if not entry:
                raise KeyError(instance_id)
            try:
                payload = fernet.decrypt(entry["ciphertext"].encode("ascii"))
            except InvalidToken as exc:
                self._fernet = None
                raise ValueError("凭证库数据无法解密，已自动锁定") from exc
            return ManagedCredential.model_validate_json(payload)

    def upsert(self, instance_id: str, credential: ManagedCredential) -> dict:
        with self._mutex:
            fernet = self._require_unlocked()
            data = self._require_configured()
            fields = [name for name, value in credential.model_dump().items() if value]
            data["entries"][instance_id] = {
                "ciphertext": fernet.encrypt(credential.model_dump_json().encode("utf-8")).decode("ascii"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "fields": fields,
            }
            self._write(data)
            return next(item for item in self.list_metadata() if item["instance_id"] == instance_id)

    def delete(self, instance_id: str) -> bool:
        with self._mutex:
            self._require_unlocked()
            data = self._require_configured()
            if instance_id not in data["entries"]:
                return False
            del data["entries"][instance_id]
            self._write(data)
            return True

    def _require_configured(self) -> dict:
        if not self.path.exists():
            raise RuntimeError("凭证库尚未设置")
        return self._read()

    def _require_unlocked(self) -> Fernet:
        if self._fernet is None:
            raise PermissionError("凭证库已锁定")
        return self._fernet

    def _read(self) -> dict:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("version") != VAULT_VERSION or data.get("kdf") != "pbkdf2-sha256":
            raise RuntimeError("不支持的凭证库格式")
        return data

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, self.path)
        os.chmod(self.path, 0o600)

    @staticmethod
    def _derive(password: str, salt: bytes, iterations: int) -> Fernet:
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations)
        return Fernet(base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8"))))


credential_vault = CredentialVault()

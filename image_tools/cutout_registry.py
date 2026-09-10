"""Fail-closed registry for local cutout adapters.

Registration is descriptive until an adapter is both verified by this build
and reports ``available=true`` plus ``executable=true`` at runtime. Candidate
algorithms remain visible without becoming executable or triggering downloads.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Protocol

from image_tools.cutout_onnx import (
    ADAPTER_ID as U2NET_ADAPTER_ID,
    CUTOUT_CONTRACT,
    CutoutAdapterError,
    CutoutInputError,
    CutoutUnavailableError,
)


MAX_FALLBACK_ATTEMPTS = 1
U2NET_ALGORITHM = "U2Net human segmentation ONNX"


class CutoutAdapterProtocol(Protocol):
    adapter_id: str

    def capabilities(self) -> Mapping[str, Any]: ...

    async def process_async(
        self,
        image_data: object,
        *,
        timeout_seconds: object = None,
    ) -> Mapping[str, Any]: ...

    def save_atomic(
        self,
        png_bytes: object,
        gallery_dir: object,
        *,
        expected_size: Optional[tuple[int, int]] = None,
    ) -> object: ...


@dataclass(frozen=True)
class CutoutAdapterDescriptor:
    """Non-sensitive provenance and runtime metadata for one adapter."""

    adapter_id: str
    algorithm: str
    status: str
    source_page: str
    weights_source: str
    license_name: str
    license_status: str
    weight_sha256: Optional[str]
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    aliases: tuple[str, ...] = field(default_factory=tuple)
    reason: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "algorithm": self.algorithm,
            "status": self.status,
            "source_page": self.source_page,
            "weights_source": self.weights_source,
            "license": {
                "name": self.license_name,
                "status": self.license_status,
            },
            "weight_sha256": self.weight_sha256,
            "dependencies": list(self.dependencies),
            "aliases": list(self.aliases),
            "reason": self.reason,
        }


class UnavailableCutoutAdapter:
    """Described candidate that cannot execute until evidence is complete."""

    def __init__(self, descriptor: CutoutAdapterDescriptor) -> None:
        self.descriptor = descriptor
        self.adapter_id = descriptor.adapter_id
        self.algorithm_aliases = descriptor.aliases
        self.contract = CUTOUT_CONTRACT

    def capabilities(self) -> dict[str, Any]:
        reason = self.descriptor.reason or "cutout_adapter_unavailable"
        return {
            "contract": CUTOUT_CONTRACT,
            "available": False,
            "executable": False,
            "adapters": [],
            "adapter": self.adapter_id,
            "algorithm": self.descriptor.algorithm,
            "verification_status": self.descriptor.status,
            "state": "unavailable",
            "reason": reason,
            "code": reason,
            "needs_model": True,
            "needs_dependency": True,
            "descriptor": self.descriptor.to_dict(),
        }

    async def process_async(
        self,
        image_data: object,
        *,
        timeout_seconds: object = None,
    ) -> Mapping[str, Any]:
        del image_data, timeout_seconds
        raise CutoutUnavailableError(
            self.descriptor.reason or "cutout_adapter_unavailable",
            "该抠图算法尚未完成权重、许可证或运行依赖验证",
            state="unavailable",
            adapter=self.adapter_id,
            needs_model=True,
            needs_dependency=True,
            descriptor=self.descriptor.to_dict(),
        )


MODNET_DESCRIPTOR = CutoutAdapterDescriptor(
    adapter_id="modnet-photographic-portrait",
    algorithm="MODNet photographic portrait matting",
    status="UNVERIFIED",
    source_page="https://github.com/ZHKKKe/MODNet",
    weights_source="No fixed, locally verified GenBox checkpoint",
    license_name="Apache-2.0 code; checkpoint terms unverified",
    license_status="UNVERIFIED",
    weight_sha256=None,
    dependencies=("onnxruntime", "Pillow", "numpy"),
    aliases=("modnet", "modnet portrait", "modnet photographic portrait matting"),
    reason="modnet_weights_license_and_sha256_unverified",
)

BIREFNET_DESCRIPTOR = CutoutAdapterDescriptor(
    adapter_id="birefnet-v1-lite",
    algorithm="BiRefNet v1 lite",
    status="UNVERIFIED",
    source_page="https://github.com/ZhengPeng7/BiRefNet",
    weights_source="No fixed, locally verified GenBox checkpoint",
    license_name="Checkpoint license unverified",
    license_status="UNVERIFIED",
    weight_sha256=None,
    dependencies=("torch", "Pillow", "numpy"),
    aliases=("birefnet", "birefnet lite", "birefnet v1 lite"),
    reason="birefnet_weights_license_and_sha256_unverified",
)

RMBG_2_DESCRIPTOR = CutoutAdapterDescriptor(
    adapter_id="rmbg-2.0",
    algorithm="BRIA RMBG-2.0 (BiRefNet architecture)",
    status="UNVERIFIED",
    source_page="https://huggingface.co/briaai/RMBG-2.0",
    weights_source="Hugging Face gated repository briaai/RMBG-2.0",
    license_name="bria-rmbg-2.0",
    license_status="NON_COMMERCIAL_ONLY_UNVERIFIED",
    weight_sha256=None,
    dependencies=("torch", "transformers", "Pillow", "numpy"),
    aliases=("rmbg", "rmbg 2.0", "bria rmbg 2.0", "bria rmbg-2.0"),
    reason="rmbg_weights_license_and_sha256_unverified",
)

INSPYRENET_DESCRIPTOR = CutoutAdapterDescriptor(
    adapter_id="inspyrenet",
    algorithm="InSPyReNet salient object segmentation",
    status="UNVERIFIED",
    source_page="https://github.com/plemeri/InSPyReNet",
    weights_source="No fixed, locally verified GenBox checkpoint",
    license_name="MIT code; checkpoint terms unverified",
    license_status="UNVERIFIED",
    weight_sha256=None,
    dependencies=("torch", "Pillow", "numpy"),
    aliases=("inspyrenet", "inspyrenet salient object segmentation"),
    reason="inspyrenet_weights_license_and_sha256_unverified",
)


def _algorithm_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().casefold())


class CutoutAdapterRegistry:
    """Ordered adapter registry with strict selection and bounded fallback."""

    def __init__(
        self,
        adapters: Iterable[CutoutAdapterProtocol] = (),
        *,
        default_adapter_id: Optional[str] = None,
    ) -> None:
        self._adapters: dict[str, CutoutAdapterProtocol] = {}
        self._verified: dict[str, bool] = {}
        self._algorithms: dict[str, str] = {}
        self._aliases: dict[str, tuple[str, ...]] = {}
        self._algorithm_aliases: dict[str, str] = {}
        self._default_adapter_id = default_adapter_id
        for adapter in adapters:
            self.register(adapter)
        if self._default_adapter_id is None and self._adapters:
            self._default_adapter_id = next(iter(self._adapters))

    def register(
        self,
        adapter: CutoutAdapterProtocol,
        *,
        verified: Optional[bool] = None,
        algorithm: Optional[str] = None,
        algorithm_aliases: Iterable[str] = (),
    ) -> CutoutAdapterProtocol:
        adapter_id = str(getattr(adapter, "adapter_id", "")).strip()
        if not adapter_id:
            raise ValueError("cutout adapter must define a non-empty adapter_id")
        if adapter_id in self._adapters:
            raise ValueError(f"cutout adapter already registered: {adapter_id}")

        descriptor = getattr(adapter, "descriptor", None)
        if verified is None:
            status = str(getattr(descriptor, "status", "VERIFIED")).upper()
            verified = status == "VERIFIED"

        canonical_algorithm = str(
            algorithm
            or getattr(descriptor, "algorithm", "")
            or getattr(adapter, "algorithm", "")
            or adapter_id
        ).strip()
        if not canonical_algorithm:
            raise ValueError("cutout adapter must define a non-empty algorithm")

        aliases = [canonical_algorithm]
        aliases.extend(algorithm_aliases)
        aliases.extend(getattr(adapter, "algorithm_aliases", ()) or ())
        public_aliases: list[str] = []
        for alias in aliases:
            alias = str(alias).strip()
            key = _algorithm_key(alias)
            if not key:
                continue
            existing = self._algorithm_aliases.get(key)
            if existing is not None and existing != adapter_id:
                raise ValueError(f"cutout algorithm alias already registered: {alias}")
            self._algorithm_aliases[key] = adapter_id
            if alias not in public_aliases:
                public_aliases.append(alias)

        self._adapters[adapter_id] = adapter
        self._verified[adapter_id] = bool(verified)
        self._algorithms[adapter_id] = canonical_algorithm
        self._aliases[adapter_id] = tuple(public_aliases)
        if self._default_adapter_id is None:
            self._default_adapter_id = adapter_id
        return adapter

    def replace(
        self,
        adapter_id: str,
        adapter: CutoutAdapterProtocol,
        *,
        verified: Optional[bool] = None,
        algorithm: Optional[str] = None,
        algorithm_aliases: Iterable[str] = (),
    ) -> CutoutAdapterProtocol:
        """Atomically replace one descriptive adapter with a runtime adapter.

        This is used after an optional model import has passed its manifest,
        license, and runtime checks.  The default adapter is preserved and
        aliases owned by the old entry are removed before registration, so a
        failed replacement cannot leave stale algorithm mappings behind.
        """
        old_id = str(adapter_id).strip()
        if not old_id or old_id not in self._adapters:
            raise ValueError(f"cutout adapter is not registered: {adapter_id}")
        old_aliases = self._aliases.pop(old_id, ())
        for alias in old_aliases:
            key = _algorithm_key(alias)
            if self._algorithm_aliases.get(key) == old_id:
                self._algorithm_aliases.pop(key, None)
        self._adapters.pop(old_id, None)
        self._verified.pop(old_id, None)
        self._algorithms.pop(old_id, None)
        if self._default_adapter_id == old_id:
            self._default_adapter_id = None
        try:
            result = self.register(
                adapter,
                verified=verified,
                algorithm=algorithm,
                algorithm_aliases=algorithm_aliases,
            )
        except Exception:
            # The old entry is intentionally not reconstructed here: callers
            # only invoke replace with a validated adapter and can rebuild the
            # default registry if construction fails.
            raise
        if self._default_adapter_id is None:
            self._default_adapter_id = next(iter(self._adapters), None)
        return result

    def get(self, adapter_id: str) -> Optional[CutoutAdapterProtocol]:
        return self._adapters.get(str(adapter_id))

    def ids(self) -> tuple[str, ...]:
        return tuple(self._adapters)

    def _probe_adapter(self, adapter_id: str) -> dict[str, Any]:
        adapter = self._adapters[adapter_id]
        try:
            capability = dict(adapter.capabilities())
        except Exception:
            capability = {
                "contract": CUTOUT_CONTRACT,
                "available": False,
                "executable": False,
                "adapter": adapter_id,
                "state": "unavailable",
                "reason": "cutout_capability_probe_failed",
                "code": "cutout_capability_probe_failed",
            }
        capability["contract"] = CUTOUT_CONTRACT
        capability["adapter"] = adapter_id
        capability["algorithm"] = self._algorithms[adapter_id]
        capability["aliases"] = list(self._aliases[adapter_id])
        capability["verification_status"] = (
            "VERIFIED" if self._verified[adapter_id] else "UNVERIFIED"
        )
        if not self._verified[adapter_id]:
            capability["available"] = False
            capability["executable"] = False
        capability["adapters"] = (
            [adapter_id] if self._is_executable(adapter_id, capability) else []
        )
        return capability

    def _is_executable(self, adapter_id: str, capability: Mapping[str, Any]) -> bool:
        return (
            self._verified.get(adapter_id) is True
            and capability.get("available") is True
            and capability.get("executable") is True
        )

    def probe(self) -> dict[str, Any]:
        ids = list(self._adapters)
        capabilities = [self._probe_adapter(adapter_id) for adapter_id in ids]
        executable = [
            adapter_id
            for adapter_id, capability in zip(ids, capabilities)
            if self._is_executable(adapter_id, capability)
        ]
        primary_id = executable[0] if executable else self._default_adapter_id
        primary = dict(capabilities[ids.index(primary_id)]) if primary_id in self._adapters else {}
        primary.update({
            "contract": CUTOUT_CONTRACT,
            "available": bool(executable),
            "executable": bool(executable),
            "adapters": executable,
            "state": "ready" if executable else str(primary.get("state") or "unavailable"),
            "adapter_capabilities": capabilities,
        })
        if primary_id is not None:
            primary.setdefault("adapter", primary_id)
        if not executable:
            primary.setdefault("code", "cutout_adapter_unavailable")
            primary.setdefault("reason", primary["code"])
            primary.setdefault("message", "当前没有已验证且可执行的抠图适配器")
        return primary

    def resolve_request(
        self,
        *,
        adapter: Optional[str] = None,
        algorithm: Optional[str] = None,
    ) -> str:
        adapter_id: Optional[str] = None
        algorithm_id: Optional[str] = None
        if adapter is not None:
            if not isinstance(adapter, str) or not adapter or adapter != adapter.strip():
                raise CutoutInputError(
                    "cutout_adapter_invalid",
                    "adapter must be a canonical cutout adapter ID",
                    field="adapter",
                )
            candidate = adapter.strip()
            if candidate not in self._adapters:
                raise CutoutInputError(
                    "cutout_adapter_unknown",
                    "adapter is not a registered cutout adapter ID",
                    field="adapter",
                    adapter=candidate,
                )
            adapter_id = candidate

        if algorithm is not None:
            key = _algorithm_key(algorithm)
            if not key or key not in self._algorithm_aliases:
                raise CutoutInputError(
                    "cutout_algorithm_unknown",
                    "algorithm is not a supported compatibility alias or description",
                    field="algorithm",
                )
            algorithm_id = self._algorithm_aliases[key]

        selected = adapter_id or self._default_adapter_id
        if selected is None or selected not in self._adapters:
            raise CutoutUnavailableError(
                "cutout_adapter_unavailable",
                "当前没有已验证且可执行的抠图适配器",
                state="unavailable",
                adapters=[],
            )
        if algorithm_id is not None and selected != algorithm_id:
            raise CutoutInputError(
                "cutout_adapter_algorithm_conflict",
                "adapter and algorithm resolve to different cutout adapters",
                adapter=selected,
                algorithm_adapter=algorithm_id,
            )
        return selected

    def resolve(
        self,
        requested_adapter: Optional[str] = None,
    ) -> tuple[Optional[CutoutAdapterProtocol], list[dict[str, Any]]]:
        """Compatibility helper returning only an explicitly executable adapter."""

        selected_id = self.resolve_request(adapter=requested_adapter)
        capability = self._probe_adapter(selected_id)
        attempts = [{"adapter": selected_id, "capability": capability}]
        if self._is_executable(selected_id, capability):
            return self._adapters[selected_id], attempts
        return None, attempts

    @staticmethod
    def _fallback_allowed(exc: CutoutAdapterError) -> bool:
        return (
            exc.status_code >= 500
            and exc.details.get("background_continues") is not True
            and exc.details.get("busy") is not True
        )

    @staticmethod
    async def _invoke(
        adapter: CutoutAdapterProtocol,
        image_data: object,
        timeout_seconds: object,
    ) -> Mapping[str, Any]:
        if timeout_seconds is None:
            return await adapter.process_async(image_data)
        return await adapter.process_async(image_data, timeout_seconds=timeout_seconds)

    async def process_async(
        self,
        image_data: object,
        *,
        adapter: Optional[str] = None,
        algorithm: Optional[str] = None,
        requested_adapter: Optional[str] = None,
        timeout_seconds: object = None,
    ) -> dict[str, Any]:
        if requested_adapter is not None:
            if adapter is not None and adapter != requested_adapter:
                raise CutoutInputError(
                    "cutout_adapter_conflict",
                    "adapter and requested_adapter conflict",
                    field="adapter",
                )
            adapter = requested_adapter
        selected_id = self.resolve_request(adapter=adapter, algorithm=algorithm)
        selected_capability = self._probe_adapter(selected_id)
        attempts = [{"adapter": selected_id, "capability": selected_capability}]
        if not self._is_executable(selected_id, selected_capability):
            code = str(
                selected_capability.get("code")
                or selected_capability.get("reason")
                or "cutout_adapter_unavailable"
            )
            raise CutoutUnavailableError(
                code,
                str(selected_capability.get("message") or "请求的抠图适配器不可执行"),
                state=str(selected_capability.get("state") or "unavailable"),
                adapter=selected_id,
                adapters=[],
                attempts=attempts,
            )

        try:
            result = await self._invoke(self._adapters[selected_id], image_data, timeout_seconds)
            output = dict(result)
            output["adapter"] = selected_id
            return output
        except CutoutAdapterError as exc:
            if not self._fallback_allowed(exc):
                raise
            first_failure: CutoutAdapterError = exc
            failures = [{"adapter": selected_id, "code": exc.code}]
        except Exception:
            first_failure = CutoutAdapterError(
                "cutout_failed",
                "本地抠图失败，未保存结果",
                status_code=500,
                adapter=selected_id,
                available=True,
                executable=True,
                adapters=[selected_id],
                cancel_supported=False,
            )
            failures = [{"adapter": selected_id, "code": "cutout_failed"}]

        fallback_ids: list[str] = []
        for candidate_id in self._adapters:
            if candidate_id == selected_id:
                continue
            capability = self._probe_adapter(candidate_id)
            if self._is_executable(candidate_id, capability):
                fallback_ids.append(candidate_id)
            if len(fallback_ids) >= MAX_FALLBACK_ATTEMPTS:
                break
        if not fallback_ids:
            raise first_failure

        for candidate_id in fallback_ids:
            try:
                result = await self._invoke(self._adapters[candidate_id], image_data, timeout_seconds)
                output = dict(result)
                output["adapter"] = candidate_id
                output["fallback_from"] = selected_id
                return output
            except CutoutAdapterError as exc:
                failures.append({"adapter": candidate_id, "code": exc.code})
            except Exception:
                failures.append({"adapter": candidate_id, "code": "cutout_failed"})
        raise CutoutAdapterError(
            "cutout_all_adapters_failed",
            "所有已验证的抠图适配器均执行失败",
            status_code=500,
            adapter=selected_id,
            available=True,
            executable=True,
            adapters=[selected_id, *fallback_ids],
            cancel_supported=False,
            fallback_attempts=len(fallback_ids),
            failures=failures,
        )


def create_default_registry(
    onnx_adapter: Optional[CutoutAdapterProtocol] = None,
) -> CutoutAdapterRegistry:
    """Build the local registry without importing optional candidate runtimes."""

    from image_tools.cutout_onnx import CutoutONNXAdapter

    primary = onnx_adapter or CutoutONNXAdapter()
    if not str(getattr(primary, "adapter_id", "")).strip():
        setattr(primary, "adapter_id", U2NET_ADAPTER_ID)
    registry = CutoutAdapterRegistry(default_adapter_id=U2NET_ADAPTER_ID)
    registry.register(
        primary,
        verified=True,
        algorithm=U2NET_ALGORITHM,
        algorithm_aliases=(
            "u2net",
            "u2net human seg",
            "u2net human segmentation",
            "u2net human segmentation onnx",
            "u2net_human_seg",
            U2NET_ADAPTER_ID,
        ),
    )
    registry.register(UnavailableCutoutAdapter(MODNET_DESCRIPTOR), verified=False)
    registry.register(UnavailableCutoutAdapter(BIREFNET_DESCRIPTOR), verified=False)
    registry.register(UnavailableCutoutAdapter(RMBG_2_DESCRIPTOR), verified=False)
    registry.register(UnavailableCutoutAdapter(INSPYRENET_DESCRIPTOR), verified=False)
    return registry


build_cutout_registry = create_default_registry


__all__ = [
    "BIREFNET_DESCRIPTOR",
    "MAX_FALLBACK_ATTEMPTS",
    "MODNET_DESCRIPTOR",
    "INSPYRENET_DESCRIPTOR",
    "CutoutAdapterDescriptor",
    "CutoutAdapterProtocol",
    "CutoutAdapterRegistry",
    "RMBG_2_DESCRIPTOR",
    "UnavailableCutoutAdapter",
    "U2NET_ALGORITHM",
    "build_cutout_registry",
    "create_default_registry",
]

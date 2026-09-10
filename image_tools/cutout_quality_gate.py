"""Repeatable local runtime evidence gate for cutout adapters.

The gate intentionally uses a generated image and blocks Python network access
while the ONNX session is created and exercised.  It proves a local structural
contract only; human-edge quality requires separately authorized samples.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import multiprocessing
import os
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

from PIL import Image, ImageDraw

from image_tools.cutout_modnet import MODNET_ADAPTER_ID, ModNetONNXAdapter
from image_tools.cutout_modnet_import import ModNetModelImportManager
from image_tools.cutout_onnx import ADAPTER_ID as U2NET_ADAPTER_ID
from image_tools.cutout_onnx import CutoutONNXAdapter, validate_output_png


QUALITY_GATE_CONTRACT = "genbox-cutout-quality-gate-v1"
SYNTHETIC_SAMPLE_ID = "synthetic-full-body-v1"
SYNTHETIC_SAMPLE_SIZE = (96, 128)
SUPPORTED_ADAPTERS = (U2NET_ADAPTER_ID, MODNET_ADAPTER_ID)
QUALITY_GATE_TIMEOUT_SECONDS = 120
_OFFLINE_ENV = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "HF_DATASETS_OFFLINE": "1",
}


class CutoutQualityGateError(RuntimeError):
    """A bounded quality-gate failure with a stable public code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = str(code)
        self.message = str(message)


@contextmanager
def deny_python_network() -> Iterator[list[str]]:
    """Block Python DNS/socket entry points and record attempted operations."""

    attempts: list[str] = []
    original_socket = socket.socket
    original_create_connection = socket.create_connection
    original_getaddrinfo = socket.getaddrinfo
    previous_env = {key: os.environ.get(key) for key in _OFFLINE_ENV}

    class OfflineSocket(original_socket):
        def connect(self, address):  # type: ignore[override]
            attempts.append("socket.connect")
            raise CutoutQualityGateError(
                "network_attempt_blocked",
                "抠图运行时尝试访问网络，断网门禁已阻止",
            )

        def connect_ex(self, address):  # type: ignore[override]
            attempts.append("socket.connect_ex")
            raise CutoutQualityGateError(
                "network_attempt_blocked",
                "抠图运行时尝试访问网络，断网门禁已阻止",
            )

    def blocked_create_connection(*_args: Any, **_kwargs: Any):
        attempts.append("socket.create_connection")
        raise CutoutQualityGateError(
            "network_attempt_blocked",
            "抠图运行时尝试访问网络，断网门禁已阻止",
        )

    def blocked_getaddrinfo(*_args: Any, **_kwargs: Any):
        attempts.append("socket.getaddrinfo")
        raise CutoutQualityGateError(
            "network_attempt_blocked",
            "抠图运行时尝试解析网络地址，断网门禁已阻止",
        )

    try:
        os.environ.update(_OFFLINE_ENV)
        socket.socket = OfflineSocket
        socket.create_connection = blocked_create_connection
        socket.getaddrinfo = blocked_getaddrinfo
        yield attempts
    finally:
        socket.socket = original_socket
        socket.create_connection = original_create_connection
        socket.getaddrinfo = original_getaddrinfo
        for key, value in previous_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def synthetic_sample_data_url() -> str:
    """Return a deterministic, non-user RGB image with a full-body silhouette."""

    width, height = SYNTHETIC_SAMPLE_SIZE
    image = Image.new("RGB", (width, height), (226, 234, 241))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        shade = 226 - int(24 * y / max(1, height - 1))
        draw.line((0, y, width, y), fill=(shade, shade + 8, min(255, shade + 18)))

    subject = (45, 62, 83)
    edge = (82, 104, 124)
    draw.ellipse((35, 12, 61, 38), fill=subject)
    draw.polygon(((28, 43), (68, 43), (61, 83), (35, 83)), fill=subject)
    draw.line((31, 48, 17, 76), fill=edge, width=7)
    draw.line((65, 48, 79, 76), fill=edge, width=7)
    draw.polygon(((35, 80), (47, 80), (42, 121), (27, 121)), fill=subject)
    draw.polygon(((49, 80), (61, 80), (69, 121), (54, 121)), fill=subject)
    draw.line((34, 17, 29, 8), fill=edge, width=2)
    draw.line((40, 14, 38, 4), fill=edge, width=2)
    draw.line((55, 15, 60, 6), fill=edge, width=2)

    output = io.BytesIO()
    image.save(output, format="PNG")
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return "data:image/png;base64," + encoded


def _build_adapter(adapter_id: str, base_path: Path):
    if adapter_id == U2NET_ADAPTER_ID:
        return CutoutONNXAdapter(base_path=base_path)
    if adapter_id == MODNET_ADAPTER_ID:
        manager = ModNetModelImportManager(base_path=base_path)
        status = manager.status()
        manifest = manager.manifest()
        if manifest is None:
            raise CutoutQualityGateError(
                "modnet_model_unavailable",
                "MODNet 用户模型未安装或清单校验失败",
            )
        return ModNetONNXAdapter(
            base_path=base_path,
            model_manifest=manifest,
            license_confirmed=bool(status.get("license_confirmed")),
            license_source=str(status.get("license_source") or ""),
        )
    raise CutoutQualityGateError("adapter_unknown", "未知抠图适配器")


def _alpha_evidence(image_bytes: bytes) -> dict[str, int | list[int]]:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.load()
        alpha = image.getchannel("A")
        histogram = alpha.histogram()
        extrema = alpha.getextrema()
    return {
        "extrema": [int(extrema[0]), int(extrema[1])],
        "transparent_pixels": int(histogram[0]),
        "opaque_pixels": int(histogram[255]),
        "soft_alpha_pixels": int(sum(histogram[1:255])),
    }


def run_adapter_gate(adapter: Any) -> dict[str, Any]:
    """Run one adapter behind the offline guard and return bounded evidence.

    This helper is intentionally used only by the isolated worker below.  The
    socket guard replaces process-global Python networking entry points, so it
    must never run in the FastAPI process or another shared application worker.
    """

    adapter_id = str(getattr(adapter, "adapter_id", "") or "unknown")
    started = time.perf_counter()
    attempts: list[str] = []
    try:
        invalidate = getattr(adapter, "invalidate_session", None)
        if callable(invalidate):
            invalidate()
        with deny_python_network() as attempts:
            capability = dict(adapter.capabilities())
            if not capability.get("available") or not capability.get("executable"):
                reason = str(capability.get("reason") or capability.get("code") or "adapter_unavailable")
                raise CutoutQualityGateError(reason, "抠图适配器未通过运行能力探测")
            if capability.get("cpu_execution_provider") is not True:
                raise CutoutQualityGateError(
                    "cpu_provider_unverified",
                    "抠图适配器未明确证明仅使用 CPUExecutionProvider",
                )
            result = dict(adapter.process(synthetic_sample_data_url()))

        image_bytes = bytes(result.get("image_bytes") or b"")
        checked = validate_output_png(image_bytes, SYNTHETIC_SAMPLE_SIZE)
        alpha = _alpha_evidence(image_bytes)
        if attempts:
            raise CutoutQualityGateError(
                "network_attempt_blocked",
                "抠图运行时触发了网络访问",
            )
        model = dict(capability.get("model") or {})
        return {
            "contract": QUALITY_GATE_CONTRACT,
            "adapter": adapter_id,
            "passed": True,
            "sample": {"id": SYNTHETIC_SAMPLE_ID, "size": list(SYNTHETIC_SAMPLE_SIZE)},
            "runtime": {
                "cpu_execution_provider": True,
                "python_network_blocked": True,
                "network_attempts": 0,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            },
            "output": {
                "format": checked["format"],
                "mode": checked["mode"],
                "size": [checked["width"], checked["height"]],
                "alpha": alpha,
            },
            "model": {
                key: model[key]
                for key in ("filename", "size_bytes", "sha256", "md5")
                if key in model
            },
            "quality_scope": {
                "synthetic_structure": "VERIFIED",
                "authorized_human_legs_hair_soft_edges": "UNVERIFIED",
            },
        }
    except CutoutQualityGateError as exc:
        code, message = exc.code, exc.message
    except Exception:
        code, message = "quality_gate_failed", "本地抠图质量门禁执行失败"
    return {
        "contract": QUALITY_GATE_CONTRACT,
        "adapter": adapter_id,
        "passed": False,
        "code": code,
        "message": message,
        "runtime": {
            "python_network_blocked": True,
            "network_attempts": len(attempts),
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        },
        "quality_scope": {
            "synthetic_structure": "UNVERIFIED",
            "authorized_human_legs_hair_soft_edges": "UNVERIFIED",
        },
    }


def _adapter_gate_worker(adapter_id: str, base_path: str, result_queue: Any) -> None:
    """Execute a guarded adapter probe in a disposable interpreter process."""

    try:
        adapter = _build_adapter(adapter_id, Path(base_path))
        result_queue.put(run_adapter_gate(adapter))
    except CutoutQualityGateError as exc:
        result_queue.put({
            "contract": QUALITY_GATE_CONTRACT,
            "adapter": adapter_id,
            "passed": False,
            "code": exc.code,
            "message": exc.message,
            "quality_scope": {
                "synthetic_structure": "UNVERIFIED",
                "authorized_human_legs_hair_soft_edges": "UNVERIFIED",
            },
        })
    except Exception:
        result_queue.put({
            "contract": QUALITY_GATE_CONTRACT,
            "adapter": adapter_id,
            "passed": False,
            "code": "quality_gate_worker_failed",
            "message": "本地抠图质量门禁子进程执行失败",
            "quality_scope": {
                "synthetic_structure": "UNVERIFIED",
                "authorized_human_legs_hair_soft_edges": "UNVERIFIED",
            },
        })


def _isolated_adapter_gate_report(adapter_id: str, base_path: Path) -> dict[str, Any]:
    """Return one report without mutating the caller's networking globals."""

    context = multiprocessing.get_context("spawn")
    result_queue = context.Queue(maxsize=1)
    process = context.Process(
        target=_adapter_gate_worker,
        args=(adapter_id, str(base_path), result_queue),
        daemon=True,
    )
    process.start()
    process.join(QUALITY_GATE_TIMEOUT_SECONDS)
    try:
        if process.is_alive():
            process.terminate()
            process.join()
            return {
                "contract": QUALITY_GATE_CONTRACT,
                "adapter": adapter_id,
                "passed": False,
                "code": "quality_gate_timeout",
                "message": "本地抠图质量门禁超时",
                "quality_scope": {
                    "synthetic_structure": "UNVERIFIED",
                    "authorized_human_legs_hair_soft_edges": "UNVERIFIED",
                },
            }
        try:
            return result_queue.get_nowait()
        except Exception:
            return {
                "contract": QUALITY_GATE_CONTRACT,
                "adapter": adapter_id,
                "passed": False,
                "code": "quality_gate_worker_no_report",
                "message": "本地抠图质量门禁未返回结果",
                "quality_scope": {
                    "synthetic_structure": "UNVERIFIED",
                    "authorized_human_legs_hair_soft_edges": "UNVERIFIED",
                },
            }
    finally:
        result_queue.close()
        result_queue.join_thread()


def run_quality_gate(
    *,
    base_path: os.PathLike[str] | str,
    adapter_ids: Sequence[str] = SUPPORTED_ADAPTERS,
) -> dict[str, Any]:
    root = Path(base_path).resolve()
    results = []
    for adapter_id in adapter_ids:
        results.append(_isolated_adapter_gate_report(str(adapter_id), root))
    return {
        "contract": QUALITY_GATE_CONTRACT,
        "passed": bool(results) and all(item.get("passed") is True for item in results),
        "results": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run local cutout runtime evidence gates")
    parser.add_argument(
        "--adapter",
        action="append",
        choices=SUPPORTED_ADAPTERS,
        dest="adapters",
        help="Adapter to check; repeat for more than one. Defaults to both.",
    )
    parser.add_argument("--base-path", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    report = run_quality_gate(
        base_path=args.base_path,
        adapter_ids=tuple(args.adapters or SUPPORTED_ADAPTERS),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

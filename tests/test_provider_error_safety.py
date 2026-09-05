"""Safety and regressions for provider-level error text and generation logging.

These tests do not touch the network. They cover the two production defects
reported against packaged GenBox:
- ``_safe_text`` must never raise ``UnicodeEncodeError: 'ascii'`` and must
  preserve non-ASCII body text instead of dropping it.
- The image-generation error log path in ``main.py`` must not reference an
  undefined ``cfg`` symbol (``NameError: name 'cfg' is not defined``).
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest


def test_safe_text_never_raises_ascii_codec_error():
    from providers import _safe_text

    for value in (
        "plain ascii",
        "中文错误信息",
        "\ud83d\udd00 开始生成 - 模型: GPT Image 2",
        "Invalid token (request id: 1234)",  # upstream style
        None,
        401,
        b"raw bytes",
    ):
        out = _safe_text(value)
        assert isinstance(out, str)
        # Round-trip through an ascii-only sink must not raise.
        assert out.encode("utf-8").decode("utf-8") == out


def test_safe_text_preserves_non_ascii_text():
    from providers import _safe_text

    source = "所有端点均失败: API Key 无效"
    assert _safe_text(source) == source


def test_exception_text_keeps_type_when_exception_message_is_empty():
    from providers import _exception_text

    assert _exception_text(TimeoutError()) == "TimeoutError"


@pytest.mark.parametrize(
    ("technical", "friendly"),
    [
        ("HTTP 400: unsupported image model", "模型名称"),
        ("HTTP 503: model_not_found: No available channel", "没有可用的图片编辑通道"),
    ],
)
def test_friendly_generation_error_explains_precision_endpoint_failures(technical, friendly):
    from providers import _friendly_generation_error

    message = _friendly_generation_error(technical)
    assert friendly in message
    assert technical in message


@pytest.mark.parametrize(
    ("technical", "secrets"),
    [
        (
            'HTTP 503: {"code":"provider_unavailable","api_key":"syntheticJsonKey123",'
            '"refresh_token":"syntheticRefresh456"}',
            ("syntheticJsonKey123", "syntheticRefresh456"),
        ),
        (
            "HTTP 503: Authorization: Bearer syntheticBearer789",
            ("syntheticBearer789",),
        ),
        (
            "HTTP 401: x-api-key: syntheticHeaderKey321; Authorization: Basic syntheticBasic654",
            ("syntheticHeaderKey321", "syntheticBasic654"),
        ),
        (
            "HTTP 503: ftp://synthetic-user:synthetic-pass@example.test/fail"
            "?access_token=syntheticQuery999",
            ("synthetic-user", "synthetic-pass", "syntheticQuery999"),
        ),
        (
            "HTTP 503: upstream echoed SK-SYNTHETICUPPER123456 RK-SYNTHETICUPPER456789 "
            "PK-SYNTHETICUPPER789012",
            (
                "SK-SYNTHETICUPPER123456",
                "RK-SYNTHETICUPPER456789",
                "PK-SYNTHETICUPPER789012",
            ),
        ),
    ],
)
def test_friendly_generation_error_redacts_upstream_credentials(technical, secrets):
    from providers import _friendly_generation_error

    message = _friendly_generation_error(technical)

    assert technical.split(":", 1)[0] in message
    assert "[REDACTED]" in message
    for secret in secrets:
        assert secret not in message


def test_friendly_generation_error_bounds_redacted_technical_detail():
    from providers import _friendly_generation_error

    technical = (
        'HTTP 503: {"code":"provider_unavailable","diagnostic":"'
        + "x" * 280
        + '","api_key":"syntheticLongCredential"}'
    )

    message = _friendly_generation_error(technical)

    assert "syntheticLongCredential" not in message
    assert "[REDACTED]" in message
    assert "x" * 201 not in message


def test_friendly_generation_error_uses_configured_key_redaction_before_excerpt():
    from providers import _friendly_generation_error

    secret = "syntheticConfiguredCredential"
    provider = _provider(secret)
    technical = (
        'HTTP 503: {"code":"provider_unavailable","diagnostic":"'
        + "x" * 120
        + secret
        + ' remains unavailable"}'
    )

    message = _friendly_generation_error(technical, provider)

    assert secret not in message
    assert "[REDACTED]" in message


def test_redaction_consumes_complete_escaped_json_credential_value():
    from providers import _redact_sensitive_text

    secret_prefix = "syntheticEscapedPrefix"
    secret_suffix = "syntheticEscapedSuffix"
    technical = (
        'HTTP 503: {"api_key":"'
        + secret_prefix
        + r'\"'
        + secret_suffix
        + '","diagnostic":"channel unavailable"}'
    )

    redacted = _redact_sensitive_text(technical)

    assert secret_prefix not in redacted
    assert secret_suffix not in redacted
    assert '"api_key":"[REDACTED]"' in redacted
    assert '"diagnostic":"channel unavailable"' in redacted


def test_redaction_consumes_complete_escaped_pseudo_json_credential_value():
    from providers import _redact_sensitive_text

    technical = r"HTTP 503: {'api_key':'prefix\'suffix','diagnostic':'channel unavailable'}"

    redacted = _redact_sensitive_text(technical)

    assert "prefix" not in redacted
    assert "suffix" not in redacted
    assert "'api_key':'[REDACTED]'" in redacted
    assert "'diagnostic':'channel unavailable'" in redacted


def test_redaction_is_strictly_idempotent_for_existing_markers():
    from providers import _redact_sensitive_text

    technical = (
        "HTTP 401: Authorization: Bearer syntheticBearer; "
        "https://user:pass@example.test/fail?token=syntheticQuery; "
        'x-api-key="syntheticHeader"'
    )
    once = _redact_sensitive_text(technical)

    assert _redact_sensitive_text(once) == once
    assert "[REDACTED]]" not in once


def test_redaction_removes_gemini_query_api_key():
    from providers import _redact_sensitive_text

    opaque_key = "OpaqueGeminiKey"
    technical = (
        "HTTP 503: GET https://generativelanguage.example/v1beta/models/"
        f"mock:generateContent?key={opaque_key}&alt=json"
    )

    redacted = _redact_sensitive_text(technical)

    assert opaque_key not in redacted
    assert "?key=[REDACTED]&alt=json" in redacted


@pytest.mark.parametrize("technical", [
    "key=OpaqueGeminiKey",
    "KEY=OpaqueGeminiKey&alt=json",
    '{"key":"OpaqueGeminiKey","detail":"failed"}',
])
def test_redaction_removes_bare_or_json_gemini_key(technical):
    from providers import _redact_sensitive_text

    redacted = _redact_sensitive_text(technical)

    assert "OpaqueGeminiKey" not in redacted
    assert "[REDACTED]" in redacted


@pytest.mark.parametrize("scheme", ["http", "https", "ftp"])
def test_redaction_removes_url_userinfo_for_supported_schemes(scheme):
    from providers import _redact_sensitive_text

    redacted = _redact_sensitive_text(
        f"{scheme}://synthetic-user:synthetic-pass@example.test/result"
    )

    assert redacted == f"{scheme}://[REDACTED]@example.test/result"


@pytest.mark.parametrize("scheme", ["ssh", "postgres", "postgresql", "redis", "rediss", "ws", "wss"])
def test_redaction_removes_url_userinfo_for_additional_schemes(scheme):
    from providers import _redact_sensitive_text

    redacted = _redact_sensitive_text(
        f"{scheme}://synthetic-user:synthetic-pass@example.test/result"
    )

    assert redacted == f"{scheme}://[REDACTED]@example.test/result"


@pytest.mark.parametrize("scheme", ["amqp", "amqps", "custom+tls"])
def test_redaction_removes_url_userinfo_for_generic_authority_schemes(scheme):
    from providers import _redact_sensitive_text

    redacted = _redact_sensitive_text(
        f"{scheme}://synthetic-user:synthetic-pass@example.test/result"
    )

    assert redacted == f"{scheme}://[REDACTED]@example.test/result"


def test_redaction_uses_final_authority_at_sign_for_url_userinfo():
    from providers import _redact_sensitive_text

    redacted = _redact_sensitive_text(
        "amqps://synthetic-user:first-part@second-part@example.test/vhost"
    )

    assert redacted == "amqps://[REDACTED]@example.test/vhost"
    assert "first-part" not in redacted
    assert "second-part" not in redacted


@pytest.mark.parametrize(
    "technical",
    [
        "person@example.test",
        "mailto:person@example.test",
        "https://example.test/users/person@example.test",
        "https://example.test/search?email=person@example.test",
    ],
)
def test_url_userinfo_redaction_avoids_email_and_path_false_positives(technical):
    from providers import _redact_sensitive_text

    assert _redact_sensitive_text(technical) == technical


@pytest.mark.parametrize(
    ("technical", "secret", "suffix"),
    [
        (
            "GET https://example.test/v1?token=syntheticQueryToken; retryable=true",
            "syntheticQueryToken",
            "; retryable=true",
        ),
        (
            "GET https://example.test/v1?access_token=syntheticPunctToken).",
            "syntheticPunctToken",
            ").",
        ),
        (
            'HTTP 401: {"api_key":"syntheticJsonHeader","detail":"denied"}',
            "syntheticJsonHeader",
            '"detail":"denied"',
        ),
        (
            "HTTP 401: X-Api-Key: syntheticHeaderToken; retryable=false",
            "syntheticHeaderToken",
            "; retryable=false",
        ),
    ],
)
def test_redaction_handles_query_json_header_variants_and_preserves_diagnostics(
    technical, secret, suffix
):
    from providers import _redact_sensitive_text

    redacted = _redact_sensitive_text(technical)

    assert secret not in redacted
    assert "[REDACTED]" in redacted
    assert suffix in redacted
    assert _redact_sensitive_text(redacted) == redacted


def test_redaction_consumes_malformed_bearer_suffix_after_bracket():
    from providers import _redact_sensitive_text

    redacted = _redact_sensitive_text(
        "Authorization: Bearer syntheticBearer]still-secret; retryable=true"
    )

    assert redacted == "Authorization: [REDACTED]; retryable=true"
    assert "syntheticBearer" not in redacted
    assert "still-secret" not in redacted
    assert _redact_sensitive_text(redacted) == redacted


def test_provider_redaction_replaces_exact_configured_key_before_generic_patterns():
    from providers import _provider_error_text

    secret = "OpaqueExactPrefix?token=OpaqueExactSuffix"
    provider = _provider(secret)
    redacted = _provider_error_text(f"upstream echoed {secret}; channel unavailable", provider)

    assert secret not in redacted
    assert "OpaqueExactPrefix" not in redacted
    assert "OpaqueExactSuffix" not in redacted
    assert redacted == "upstream echoed [REDACTED]; channel unavailable"


def test_retry_response_redacts_full_configured_secret_before_excerpt(monkeypatch):
    import httpx
    import providers

    secret = "SyntheticCrossBoundaryCredential-ABCDEFGHIJKLMN"
    provider = _provider(secret)
    body = "diagnostic=" + ("x" * 275) + secret + "; retryable=true"
    response = httpx.Response(
        503,
        text=body,
        request=httpx.Request("POST", "https://example.test/v1/images/generations"),
    )

    class FakeAsyncClient:
        async def post(self, *_args, **_kwargs):
            return response

        async def aclose(self):
            return None

    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **_kwargs: FakeAsyncClient())

    with pytest.raises(httpx.HTTPStatusError) as raised:
        asyncio.run(
            providers._http_post_with_retry(
                "https://example.test/v1/images/generations",
                {},
                {},
                cfg=provider,
                max_retries=1,
            )
        )

    message = str(raised.value)
    assert secret not in message
    assert "SyntheticCrossBoundary" not in message
    assert "ABCDEFGHIJKLMN" not in message
    assert "[REDACTED]" in message


def test_legacy_generate_for_provider_sanitizes_failed_image_result(monkeypatch):
    import providers
    from config import ProviderConfig
    from providers.key_pool import key_pool_manager

    secret = "OpaqueLegacyPrefix?token=OpaqueLegacySuffix"
    provider = _provider(secret)

    class FakePool:
        async def get_key(self):
            return secret

        def mark_success(self, _key):
            return None

        def mark_error(self, _key, retry_after=0.0):
            return None

    async def fake_dispatch(_cfg, _prompt, _protocol, **_kwargs):
        return providers.ImageResult(
            success=False,
            error=f"upstream echo {secret}; Authorization: Bearer syntheticLegacyBearer",
            model=provider.id,
        )

    monkeypatch.setattr(ProviderConfig, "get_active_endpoints", lambda _self: [])
    monkeypatch.setattr(key_pool_manager, "get_or_create", lambda *_args, **_kwargs: FakePool())
    monkeypatch.setattr(providers, "_dispatch_generate", fake_dispatch)

    result = asyncio.run(providers.generate_for_provider(provider, "safe prompt"))

    assert result.success is False
    assert secret not in result.error
    assert "OpaqueLegacyPrefix" not in result.error
    assert "syntheticLegacyBearer" not in result.error
    assert result.error.count("[REDACTED]") >= 2


def test_generate_multi_sanitizes_normal_failed_image_result(monkeypatch):
    import providers

    secret = "OpaqueMultiPrefix?token=OpaqueMultiSuffix"
    provider = _provider(secret, provider_id="synthetic-multi")

    async def fake_generate(_cfg, _prompt, **_kwargs):
        return providers.ImageResult(
            success=False,
            error=f"upstream echo {secret}",
            model=provider.id,
        )

    monkeypatch.setattr(providers.cfg_mgr.config, "providers", [provider])
    monkeypatch.setattr(providers, "generate_for_provider", fake_generate)

    results = asyncio.run(providers.generate_multi(["safe prompt"], [provider.id]))
    error = results[provider.id].error

    assert secret not in error
    assert "OpaqueMultiPrefix" not in error
    assert "OpaqueMultiSuffix" not in error
    assert "[REDACTED]" in error


@pytest.mark.parametrize("failure_mode", ["result", "exception"])
def test_background_generation_sanitizes_before_log_persistence_and_browser(
    monkeypatch, failure_mode
):
    import main
    import providers

    secret = f"OpaqueBackground{failure_mode}?token=OpaqueBackgroundSuffix"
    provider = _provider(secret, provider_id=f"synthetic-background-{failure_mode}")
    gen_id = f"synthetic_background_{failure_mode}"
    persisted = []
    written_logs = []

    async def fake_generate(_cfg, _prompt, **_kwargs):
        detail = f"upstream echo {secret}; Authorization: Bearer syntheticBackgroundBearer"
        if failure_mode == "exception":
            raise RuntimeError(detail)
        return providers.ImageResult(success=False, error=detail, model=provider.id)

    main.image_tasks[gen_id] = _background_task(provider)
    main.generation_history.pop(gen_id, None)
    monkeypatch.setattr(providers, "generate_for_provider", fake_generate)
    monkeypatch.setattr(
        main,
        "_save_history_entry",
        lambda entry: persisted.append(json.loads(json.dumps(entry, ensure_ascii=False))),
    )
    monkeypatch.setattr(
        main,
        "_write_log",
        lambda category, message, details=None: written_logs.append(
            {"category": category, "message": message, "details": details or {}}
        ),
    )

    try:
        asyncio.run(main._process_image_gen_impl(gen_id))
        browser_payload = asyncio.run(main.get_generate_status(gen_id))
        task_public = {
            "status": main.image_tasks[gen_id]["status"],
            "provider_states": main.image_tasks[gen_id]["provider_states"],
            "results": main.image_tasks[gen_id]["results"],
        }
        evidence = json.dumps(
            {
                "task": task_public,
                "history": main.generation_history.get(gen_id),
                "persisted": persisted,
                "logs": written_logs,
                "browser": browser_payload,
            },
            ensure_ascii=False,
            default=str,
        )

        assert secret not in evidence
        assert f"OpaqueBackground{failure_mode}" not in evidence
        assert "OpaqueBackgroundSuffix" not in evidence
        assert "syntheticBackgroundBearer" not in evidence
        assert "[REDACTED]" in evidence
    finally:
        main.image_tasks.pop(gen_id, None)
        main.generation_history.pop(gen_id, None)


def test_both_llm_failure_branches_print_only_sanitized_exceptions(monkeypatch, capsys):
    import providers

    secret = "OpaqueLlmPrefix?token=OpaqueLlmSuffix"
    provider = _provider(secret, provider_id="synthetic-llm", provider_type="llm")

    class FailingAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

        async def post(self, *_args, **_kwargs):
            raise RuntimeError(f"upstream echoed {secret}")

    monkeypatch.setattr(providers.cfg_mgr, "get_llm_provider", lambda: provider)
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **_kwargs: FailingAsyncClient())

    prompt = "safe prompt"
    assert asyncio.run(providers.enhance_prompt_with_llm(prompt)) == prompt
    simple_output = capsys.readouterr().out
    detailed = asyncio.run(providers.enhance_prompt_with_llm_detailed(prompt))
    detailed_output = capsys.readouterr().out

    evidence = simple_output + detailed_output + json.dumps(detailed, ensure_ascii=False)
    assert secret not in evidence
    assert "OpaqueLlmPrefix" not in evidence
    assert "OpaqueLlmSuffix" not in evidence
    assert evidence.count("[REDACTED]") >= 3


def test_safe_text_replaces_unrenderable_bytes_without_dropping_info():
    from providers import _safe_text

    value = "前缀: " + "\xff\xfe" + " 后缀"
    out = _safe_text(value)
    assert "前缀" in out
    assert "后缀" in out


def test_generation_error_log_uses_p_cfg_not_undefined_cfg():
    """The generation error writer must reference the in-scope provider cfg.

    Regression: main.py previously used ``cfg.model`` where ``cfg`` was not
    defined in ``_process_image_gen``, surfacing as
    ``NameError: name 'cfg' is not defined`` on every failed provider run.
    """
    source = _read_main()
    assert "generation_error" in source
    block = source.split('"generation_error"', 1)[1].split("state[\"result\"]", 1)[0]
    assert "p_cfg.model" in block
    # Reject a bare undefined ``cfg`` read (e.g. ``= cfg.model``), but allow
    # the in-scope ``p_cfg.model`` expression used in the fix.
    assert "= cfg.model" not in block


def test_generation_quantity_normalizes_invalid_and_stale_values():
    from main import _normalize_generation_quantity

    assert _normalize_generation_quantity(1) == 1
    assert _normalize_generation_quantity("3") == 3
    assert _normalize_generation_quantity(0) == 1
    assert _normalize_generation_quantity("not-a-number") == 1
    assert _normalize_generation_quantity(99) == 10


def _read_main() -> str:
    import pathlib

    return pathlib.Path(__file__).parents[1].joinpath("main.py").read_text(encoding="utf-8")


def _provider(
    secret: str,
    *,
    provider_id: str = "synthetic-provider",
    provider_type: str = "image",
):
    from config import ProviderConfig

    return ProviderConfig(
        id=provider_id,
        name="Synthetic Provider",
        type=provider_type,
        api_key=secret,
        base_url="https://example.test/v1",
        model="synthetic-model",
    )


def _background_task(provider) -> dict:
    return {
        "status": "queued",
        "progress": 0,
        "mode": "t2i",
        "prompt": "safe prompt",
        "enhanced_prompt": None,
        "llm_error": None,
        "providers": [provider.id],
        "provider_states": {
            provider.id: {
                "status": "queued",
                "progress": 0,
                "model": provider.id,
                "name": provider.name,
                "color": provider.color,
                "seq": 0,
                "qty": 1,
                "log": ["[system] queued"],
                "result": None,
            }
        },
        "task_list": [(provider.id, 0, 1)],
        "task_index": 0,
        "all_providers": {provider.id: provider},
        "kwargs": {},
        "provider_kwargs_map": {provider.id: {}},
        "start_time": time.time(),
        "results": {},
        "continuous": False,
        "continuous_id": None,
        "system_prompt": None,
        "original_prompt": "safe prompt",
        "upscale_to": None,
        "upscale_method": "lanczos3",
        "upscale_ratio": "original",
    }

"""Native Google contracts use synthetic HTTP only; no paid generation."""

import asyncio
import base64
import json
from io import BytesIO

import httpx
import pytest
from PIL import Image

import main
from config import ProviderConfig
from providers import google_video as google

KEY = "synthetic-google-secret"
MP4 = b"\0\0\0\x18ftypisom\0\0\0\0isommp42"
def image_data(format="PNG"):
    buffer = BytesIO()
    Image.new("RGB", (8, 8), (80, 140, 170)).save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode()


IMAGE_BYTES = image_data()
IMAGE = "data:image/png;base64," + IMAGE_BYTES


def request(**kwargs):
    return main.VideoGenerateRequest(prompt="synthetic scene", width=1280, height=720, **kwargs)


@pytest.mark.parametrize("model,family,durations", [
    ("gemini-omni-1.1-flash", "omni", []),
    ("gemini-omni-flash-preview", "omni", []),
    ("veo-3.1-generate-preview", "veo", [4, 6, 8]),
    ("veo-3.1-fast-generate-preview", "veo", [4, 6, 8]),
    ("veo-3.0-generate-001", "veo", [8]),
    ("veo-2.0-generate-001", "veo", [5, 6, 7, 8]),
])
def test_native_specs_do_not_inherit_agnes(model, family, durations):
    spec = google.model_spec(model)
    assert spec["family"] == family
    assert spec["duration_options"] == durations
    assert spec["fps_options"] == [24]
    assert spec["frame_rule"] == ""
    assert spec["inference_steps_range"] is None
    assert spec["supports_seed"] is False


def test_native_veo_request_preserves_images_and_seconds():
    url, payload = google.build_request(request(
        mode="i2vid", image=[IMAGE, IMAGE], image_role="first_last", duration_seconds=6,
    ), "veo-3.1-fast-generate-preview")
    assert url.endswith("/models/veo-3.1-fast-generate-preview:predictLongRunning")
    instance = payload["instances"][0]
    assert instance["image"] == {"mimeType": "image/png", "bytesBase64Encoded": IMAGE_BYTES}
    assert instance["lastFrame"] == instance["image"]
    assert payload["parameters"]["durationSeconds"] == 6
    assert "num_frames" not in payload["parameters"]


# Independent REST contract: googleapis/python-genai models.py, commit
# 6669bb635753e5071e489038945d494be58094bc: _Image_to_mldev,
# _VideoGenerationReferenceImage_to_mldev and _GenerateVideosConfig_to_mldev.
@pytest.mark.parametrize("role,count,expected_images", [
    ("first_frame", 1, {"image": {"bytesBase64Encoded": IMAGE_BYTES, "mimeType": "image/png"}}),
    ("first_last", 2, {
        "image": {"bytesBase64Encoded": IMAGE_BYTES, "mimeType": "image/png"},
        "lastFrame": {"bytesBase64Encoded": IMAGE_BYTES, "mimeType": "image/png"},
    }),
    ("reference", 3, {"referenceImages": [
        {"image": {"bytesBase64Encoded": IMAGE_BYTES, "mimeType": "image/png"}, "referenceType": "asset"},
        {"image": {"bytesBase64Encoded": IMAGE_BYTES, "mimeType": "image/png"}, "referenceType": "asset"},
        {"image": {"bytesBase64Encoded": IMAGE_BYTES, "mimeType": "image/png"}, "referenceType": "asset"},
    ]}),
])
def test_veo_image_roles_match_pinned_sdk_wire_contract(role, count, expected_images):
    _, payload = google.build_request(request(
        mode="i2vid", image=[IMAGE] * count, image_role=role, duration_seconds=8,
    ), "veo-3.1-generate-preview")
    assert payload == {
        "instances": [{"prompt": "synthetic scene", **expected_images}],
        "parameters": {"aspectRatio": "16:9", "durationSeconds": 8, "resolution": "720p"},
    }
    assert "inlineData" not in json.dumps(payload)


@pytest.mark.parametrize("format,mime", [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")])
def test_real_image_formats_are_accepted(format, mime):
    data = image_data(format)
    assert google.image_part(f"data:{mime};base64,{data}") == {"mimeType": mime, "data": data}


@pytest.mark.parametrize("image", [
    "data:image/png;base64," + base64.b64encode(b"synthetic-not-an-image").decode(),
    "data:image/jpeg;base64," + IMAGE_BYTES,
    "data:image/png;base64,%%%invalid",
    "data:image/png;base64," + IMAGE_BYTES[:28],
])
def test_invalid_image_content_is_rejected_locally(image):
    with pytest.raises(ValueError):
        google.image_part(image)


def test_omni_uses_interactions_and_no_unverified_duration():
    url, payload = google.build_request(request(mode="i2vid", image=[IMAGE], image_role="reference"),
                                       "gemini-omni-1.1-flash")
    assert url == google.BASE + "/interactions"
    assert payload["input"][0]["type"] == "image"
    assert payload["input"][0] == {"type": "image", "mime_type": "image/png", "data": IMAGE_BYTES}
    assert payload["response_format"] == {
        "type": "video", "resolution": "720p", "aspect_ratio": "16:9", "delivery": "inline"}
    assert payload["store"] is False
    assert "duration" not in json.dumps(payload)


@pytest.mark.parametrize("model", ["gemini-omni-1.1-flash", "gemini-omni-flash-preview"])
@pytest.mark.parametrize("resolution", ["360p", "720p", "1080p", "4k"])
def test_omni_inline_delivery_preserves_storage_opt_out(model, resolution):
    _, payload = google.build_request(request(resolution=resolution), model)
    assert payload["response_format"]["delivery"] == "inline"
    assert payload["response_format"]["resolution"] == resolution
    assert payload["store"] is False
    assert payload["background"] is False
    assert payload["stream"] is False


@pytest.mark.parametrize("model,kwargs", [
    ("gemini-2.5-flash", {}),
    ("gemini-omni-1.1-flash", {"duration_seconds": 5}),
    ("gemini-omni-1.1-flash", {"seed": 1}),
    ("gemini-omni-1.1-flash", {"resolution": "480p"}),
    ("veo-3.1-fast-generate-preview", {"duration_seconds": 5}),
    ("veo-3.1-fast-generate-preview", {"frame_rate": 30}),
    ("veo-3.1-fast-generate-preview", {"resolution": "1080p", "duration_seconds": 4}),
    ("veo-3.1-fast-generate-preview", {"mode": "i2vid"}),
    ("veo-3.1-fast-generate-preview", {"mode": "i2vid", "image": [IMAGE], "image_role": "first_last"}),
    ("veo-3.1-fast-generate-preview", {"mode": "i2vid", "image": [IMAGE], "image_role": "last_frame"}),
    ("veo-3.1-lite-generate-preview", {"mode": "i2vid", "image": [IMAGE], "image_role": "reference"}),
    ("veo-3.1-fast-generate-preview", {"num_inference_steps": 3}),
    ("veo-3.1-fast-generate-preview", {"seed": -1}),
    ("veo-3.1-fast-generate-preview", {"seed": 42}),
    ("veo-3.1-fast-generate-preview", {"mode": "i2vid", "image": ["http://127.0.0.1/private"]}),
])
def test_invalid_parameters_fail_before_transport(model, kwargs):
    with pytest.raises(ValueError):
        google.build_request(request(**kwargs), model)


def transport(handler):
    calls = []

    def respond(req):
        calls.append(req)
        return handler(req)

    def factory(**kwargs):
        assert kwargs["follow_redirects"] is False
        return httpx.Client(transport=httpx.MockTransport(respond))

    return calls, factory


@pytest.mark.parametrize("model", ["gemini-omni-1.1-flash", "gemini-omni-flash-preview"])
def test_omni_inline_video_needs_only_one_post_and_no_file_calls(tmp_path, model):
    # REST steps[].content[].data from the official Omni inline example.
    def handler(req):
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["store"] is False
        assert body["response_format"]["delivery"] == "inline"
        return httpx.Response(200, json={"status": "completed", "steps": [
            {"type": "model_output", "content": [
                {"type": "text", "text": "synthetic"},
                {"type": "video", "mime_type": "video/mp4", "data": base64.b64encode(MP4).decode()},
            ]},
        ]})
    calls, factory = transport(handler)
    url, payload = google.build_request(request(mode="i2vid", image=[IMAGE]), model)
    output = tmp_path / "inline.mp4"
    stages = []
    assert google.run_generation(url, payload, KEY, output, client_factory=factory, on_stage=stages.append)
    assert output.read_bytes() == MP4
    assert len(calls) == 1
    assert stages == ["generating", "downloading"]
    assert not output.with_suffix(".part").exists()


def test_omni_inline_response_can_exceed_old_json_limit(tmp_path):
    media = MP4 + b"\0" * (7 * 1024 * 1024)
    _, factory = transport(lambda req: httpx.Response(200, json={"status": "completed", "steps": [
        {"type": "model_output", "content": [
            {"type": "video", "mime_type": "video/mp4", "data": base64.b64encode(media).decode()},
        ]},
    ]}))
    url, payload = google.build_request(request(), "gemini-omni-1.1-flash")
    output = tmp_path / "large.mp4"
    assert google.run_generation(url, payload, KEY, output, client_factory=factory)
    assert output.read_bytes() == media


@pytest.mark.parametrize("part", [
    {"mime_type": "video/mp4", "data": "invalid!"},
    {"mime_type": "video/mp4", "data": ""},
    {"mime_type": "video/mp4", "data": 42},
    {"mime_type": "text/plain", "data": base64.b64encode(MP4).decode()},
    {"mime_type": "video/mp4", "data": base64.b64encode(b"not a video").decode()},
    {"mime_type": "video/mp4", "data": "\u2603"},
])
def test_bad_inline_video_is_not_published(tmp_path, part):
    output = tmp_path / "inline.mp4"
    with pytest.raises(google.GoogleVideoError):
        google._save_inline_video(part, output, lambda: False)
    assert not output.exists()
    assert not output.with_suffix(".part").exists()


def test_inline_size_limit_and_cancellation_clean_up(tmp_path, monkeypatch):
    output = tmp_path / "inline.mp4"
    part = {"mime_type": "video/mp4", "data": base64.b64encode(MP4).decode()}
    with pytest.raises(google.GoogleVideoError, match="已取消"):
        google._save_inline_video(part, output, lambda: True)
    assert not output.exists() and not output.with_suffix(".part").exists()
    # Same Base64 length as the limit, but decoded bytes exceed it.
    monkeypatch.setattr(google, "MAX_VIDEO_BYTES", len(MP4) - 1)
    with pytest.raises(google.GoogleVideoError, match="大小限制"):
        google._save_inline_video(part, output, lambda: False)
    assert not output.exists() and not output.with_suffix(".part").exists()
    monkeypatch.setattr(google, "MAX_VIDEO_BYTES", 3)
    with pytest.raises(google.GoogleVideoError, match="大小限制"):
        google._save_inline_video(part, output, lambda: False)
    assert not output.exists() and not output.with_suffix(".part").exists()


def test_inline_json_envelope_is_bounded_and_never_retries(tmp_path, monkeypatch):
    monkeypatch.setattr(google, "MAX_VIDEO_BYTES", 12)
    calls, factory = transport(lambda req: httpx.Response(200, content=b" " * (2 * 1024 * 1024)))
    url, payload = google.build_request(request(), "gemini-omni-1.1-flash")
    output = tmp_path / "inline.mp4"
    with pytest.raises(google.GoogleVideoError, match="响应超过大小限制"):
        google.run_generation(url, payload, KEY, output, client_factory=factory)
    assert len(calls) == 1 and not output.exists()


def test_omni_delivery_storage_error_remains_safe_and_no_retry(tmp_path):
    calls, factory = transport(lambda req: httpx.Response(400, json={"error": {
        "message": "delivery uri requires store true. " + KEY,
    }}))
    url, payload = google.build_request(request(), "gemini-omni-flash-preview")
    with pytest.raises(google.GoogleVideoError) as exc:
        google.run_generation(url, payload, KEY, tmp_path / "inline.mp4", client_factory=factory)
    assert "组合兼容性" in str(exc.value)
    assert KEY not in str(exc.value)
    assert len(calls) == 1


@pytest.mark.parametrize("family", ["veo", "omni"])
def test_native_submission_poll_download_and_public_result(tmp_path, family):
    def handler(req):
        assert KEY not in str(req.url)
        assert req.headers.get("x-goog-api-key") == KEY
        if req.method == "POST":
            if family == "veo":
                return httpx.Response(200, json={"name": "models/veo-3.1-fast-generate-preview/operations/test"})
            return httpx.Response(200, json={"status": "completed", "steps": [
                {"type": "model_output", "content": [{"type": "video", "uri": google.BASE + "/files/test:download?alt=media"}]}]})
        if "/operations/" in req.url.path:
            return httpx.Response(200, json={"done": True, "response": {"generateVideoResponse": {
                "generatedSamples": [{"video": {"uri": google.BASE + "/files/test"}}]}}})
        if req.url.path.endswith("/files/test"):
            return httpx.Response(200, json={"state": "ACTIVE"})
        return httpx.Response(200, content=MP4)

    calls, factory = transport(handler)
    model = "gemini-omni-1.1-flash" if family == "omni" else "veo-3.1-fast-generate-preview"
    url, payload = google.build_request(request(), model)
    output = tmp_path / "test.mp4"
    stages = []
    assert google.run_generation(url, payload, KEY, output, client_factory=factory,
                                 sleep=lambda _: None, on_stage=stages.append)
    assert output.read_bytes() == MP4
    assert sum(req.method == "POST" for req in calls) == 1
    assert stages == ["generating", "downloading"]
    assert not list(tmp_path.glob("*.part"))


def test_download_redirect_drops_key_for_google_storage(tmp_path):
    def handler(req):
        if req.url.host == google.HOST:
            assert req.headers["x-goog-api-key"] == KEY
            return httpx.Response(302, headers={"location": "https://storage.googleapis.com/synthetic/video"})
        assert "x-goog-api-key" not in req.headers
        return httpx.Response(200, content=MP4)
    calls, factory = transport(handler)
    with factory(follow_redirects=False) as client:
        google._download(client, "test", KEY, tmp_path / "test.mp4", lambda: False)
    assert len(calls) == 2


@pytest.mark.parametrize("uri", [
    "http://generativelanguage.googleapis.com/v1beta/files/test",
    "https://evil.invalid/v1beta/files/test",
    "https://generativelanguage.googleapis.com.evil.invalid/v1beta/files/test",
    "https://generativelanguage.googleapis.com:444/v1beta/files/test",
    "https://user:secret@generativelanguage.googleapis.com/v1beta/files/test",
    "https://generativelanguage.googleapis.com/v1beta/files/../../secret",
])
def test_untrusted_file_urls_are_rejected(uri):
    with pytest.raises(google.GoogleVideoError):
        google._file_id(uri)


def test_download_rejects_external_redirect_before_sending_key(tmp_path):
    calls, factory = transport(lambda req: httpx.Response(302, headers={"location": "https://evil.invalid/leak"}))
    with factory(follow_redirects=False) as client, pytest.raises(google.GoogleVideoError):
        google._download(client, "test", KEY, tmp_path / "test.mp4", lambda: False)
    assert len(calls) == 1


@pytest.mark.parametrize("code", [400, 401, 403, 429, 500])
def test_error_does_not_echo_upstream_secrets_or_retry(tmp_path, code):
    calls, factory = transport(lambda req: httpx.Response(code, json={"error": {"message": KEY}}))
    url, payload = google.build_request(request(), "veo-3.1-fast-generate-preview")
    with pytest.raises(google.GoogleVideoError) as exc:
        google.run_generation(url, payload, KEY, tmp_path / "test.mp4", client_factory=factory)
    assert KEY not in str(exc.value)
    assert str(code) in str(exc.value)
    assert len(calls) == 1


def test_structured_400_shows_safe_status_and_field_without_echoes(tmp_path):
    private = "synthetic-private-prompt"
    body = {"error": {
        "status": "INVALID_ARGUMENT",
        "message": f'Unknown name "inlineData": {KEY} {private} {IMAGE}',
        "details": [{
            "@type": "type.googleapis.com/google.rpc.BadRequest",
            "fieldViolations": [
                {"field": "instances[0].referenceImages[0].image.inlineData", "description": private},
                {"field": KEY + private + IMAGE},
            ],
        }],
    }}
    calls, factory = transport(lambda req: httpx.Response(400, json=body))
    url, payload = google.build_request(request(), "veo-3.1-generate-preview")
    with pytest.raises(google.GoogleVideoError) as exc:
        google.run_generation(url, payload, KEY, tmp_path / "test.mp4", client_factory=factory)
    message = str(exc.value)
    assert "提交返回 HTTP 400" in message
    assert "INVALID_ARGUMENT" in message
    assert "referenceImages" in message and "inlineData" in message
    assert "接口不接受的字段" in message
    assert all(value not in message for value in [KEY, private, IMAGE_BYTES])
    assert len(calls) == 1


@pytest.mark.parametrize("body", [
    b"not json", b'{"error":[]}', b'{"error":{"details":null,"message":{},"status":[]}}',
    b'{"error":{"message":"' + b"x" * (70 * 1024) + b'"}}',
], ids=["non-json", "wrong-error-type", "wrong-detail-types", "oversized-error"])
def test_malformed_or_oversized_errors_keep_http_failure(body):
    _, factory = transport(lambda req: httpx.Response(400, content=body))
    with factory(follow_redirects=False) as client, pytest.raises(google.GoogleVideoError) as exc:
        google._json(client, "POST", google.BASE + "/interactions", KEY, {})
    assert "HTTP 400" in str(exc.value)


@pytest.mark.parametrize("stage", ["任务查询", "文件查询", "下载"])
def test_error_identifies_non_submission_stage(tmp_path, stage):
    _, factory = transport(lambda req: httpx.Response(403, json={"error": {"status": "PERMISSION_DENIED"}}))
    with factory(follow_redirects=False) as client, pytest.raises(google.GoogleVideoError) as exc:
        if stage == "下载":
            google._download(client, "test", KEY, tmp_path / "test.mp4", lambda: False)
        else:
            google._json(client, "GET", google.BASE + "/files/test", KEY, stage=stage)
    assert stage in str(exc.value)
    assert "PERMISSION_DENIED" in str(exc.value)


@pytest.mark.parametrize("upstream,expected", [
    ("API key not valid. Please pass a valid API key.", "API Key 无效"),
    ("This request requires billing to be enabled.", "请检查项目付费状态"),
    ("User location is not supported for the API use.", "请检查模型地区可用性"),
    ("Unable to decode image", "请检查图片编码与格式"),
    ("Request blocked by safety policy", "请求被内容安全规则拦截"),
])
def test_known_error_categories_are_fixed_public_labels(upstream, expected):
    hint = google._error_hint({"message": upstream + KEY})
    assert expected in hint
    assert KEY not in hint


def test_native_route_uses_effective_key_and_local_task_id(monkeypatch, tmp_path):
    cfg = ProviderConfig(id="google", type="video", name="Google", base_url=google.BASE,
                         api_key="", api_keys=[KEY], model="gemini-omni-1.1-flash")
    monkeypatch.setattr(main.cfg_mgr, "get_video_providers", lambda: [cfg])
    monkeypatch.setattr(main, "VIDEO_DIR", tmp_path)
    monkeypatch.setattr(main, "video_tasks", {})
    monkeypatch.setattr(main, "_generate_video_thumbnail_async", lambda path: None)
    saved = []
    monkeypatch.setattr(main, "_save_video_history_entry", lambda info: saved.append(dict(info)))

    def run(url, payload, key, path, **kwargs):
        assert url == google.BASE + "/interactions"
        assert key == KEY
        path.write_bytes(MP4)
        return True

    monkeypatch.setattr(google, "run_generation", run)
    class ImmediateThread:
        def __init__(self, target, **kwargs):
            self.target = target
        def start(self):
            self.target()
    monkeypatch.setattr("threading.Thread", ImmediateThread)
    result = asyncio.run(main.video_generate(request(provider_id=cfg.id, model=cfg.model)))
    assert result["status"] == "queued"
    assert result["provider_type"] == "google_native"
    status = asyncio.run(main.video_status(result["task_id"]))
    assert status["status"] == "completed"
    assert status["video_url_local"].startswith("/api/video/file/google_")
    assert KEY not in json.dumps(status)
    assert "interactions" not in json.dumps(saved)


def test_spec_is_provider_scoped_and_gateway_is_not_native(monkeypatch):
    cfg = ProviderConfig(id="gateway", type="video", name="Gateway", api_key=KEY,
                         base_url="https://example.invalid/v1", model="veo-3.1-fast-generate-preview")
    monkeypatch.setattr(main.cfg_mgr, "get_video_providers", lambda: [cfg])
    data = asyncio.run(main.video_model_spec(cfg.model, cfg.id))
    assert not data["spec"].get("native_google")
    cfg.base_url = google.BASE
    data = asyncio.run(main.video_model_spec(cfg.model, cfg.id))
    assert data["spec"]["native_google"] is True


def test_cancellation_does_not_submit_or_download(tmp_path):
    calls, factory = transport(lambda req: pytest.fail("Cancelled task must not call upstream"))
    url, payload = google.build_request(request(), "veo-3.1-fast-generate-preview")
    assert not google.run_generation(url, payload, KEY, tmp_path / "test.mp4",
                                     client_factory=factory, cancelled=lambda: True)
    assert calls == []


@pytest.mark.parametrize("body", [b"", b"not a video", b'{"key":"synthetic-google-secret"}'])
def test_bad_download_is_not_published(tmp_path, body):
    calls, factory = transport(lambda req: httpx.Response(200, content=body))
    output = tmp_path / "test.mp4"
    with factory(follow_redirects=False) as client, pytest.raises(google.GoogleVideoError):
        google._download(client, "test", KEY, output, lambda: False)
    assert not output.exists()
    assert not output.with_suffix(".part").exists()


def test_poll_failure_does_not_retry_paid_post_or_return_raw_error(tmp_path):
    def handler(req):
        if req.method == "POST":
            return httpx.Response(200, json={"name": "operations/test"})
        return httpx.Response(200, json={"done": True, "error": {"message": KEY}})
    calls, factory = transport(handler)
    url, payload = google.build_request(request(), "veo-3.1-fast-generate-preview")
    with pytest.raises(google.GoogleVideoError) as exc:
        google.run_generation(url, payload, KEY, tmp_path / "test.mp4",
                              client_factory=factory, sleep=lambda _: None)
    assert KEY not in str(exc.value)
    assert [req.method for req in calls] == ["POST", "GET"]

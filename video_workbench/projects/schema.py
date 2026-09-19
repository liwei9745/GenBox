"""Strict validation of the WB-1 project shell, without timeline semantics."""

from datetime import datetime, timezone
import json
import re
import unicodedata

from ..media.ingest import _fail, _safe_id


MAX_PROJECT_BYTES = 4 * 1024 * 1024
_PROJECT_ID = re.compile(r"prj_[a-f0-9]{32}")
_DIGEST = re.compile(r"sha256:[a-f0-9]{64}")
_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z")
_FIELDS = {
    "schema_version", "project_id", "revision", "title", "output_profile",
    "asset_refs", "tracks", "candidate_refs", "created_at", "updated_at",
}


def invalid(field):
    return _fail("invalid_request", "admission", field=field)


def project_id(value):
    if type(value) is not str or not _PROJECT_ID.fullmatch(value):
        raise invalid("project_id")
    return value


def positive_revision(value, field="revision"):
    if type(value) is not int or value < 1:
        raise invalid(field)
    return value


def title(value):
    if type(value) is not str or any(
        unicodedata.category(char) in {"Cc", "Cs"} for char in value
    ):
        raise invalid("title")
    value = value.strip()
    if not value or len(value) > 200:
        raise invalid("title")
    return value


def _keys(value, expected, field):
    if type(value) is not dict or set(value) != expected:
        raise invalid(field)


def output_profile(value):
    _keys(value, {"profile_id", "canvas", "fps", "fit_mode"}, "output_profile")
    _keys(value["canvas"], {"width", "height"}, "output_profile")
    _keys(value["fps"], {"num", "den"}, "output_profile")
    if any(type(item) is not int for item in (
        *value["canvas"].values(), *value["fps"].values(),
    )):
        raise invalid("output_profile")
    profiles = {
        "landscape_1080p_30": {"width": 1920, "height": 1080},
        "portrait_1080p_30": {"width": 1080, "height": 1920},
    }
    identity = value["profile_id"]
    if (
        type(identity) is not str or identity not in profiles
        or value["canvas"] != profiles[identity]
        or value["fps"] != {"num": 30, "den": 1}
        or value["fit_mode"] != "contain"
    ):
        raise invalid("output_profile")
    return {
        "profile_id": identity, "canvas": dict(value["canvas"]),
        "fps": dict(value["fps"]), "fit_mode": "contain",
    }


def timestamp(value):
    if type(value) is not str or not _TIMESTAMP.fullmatch(value):
        raise invalid("timestamps")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise invalid("timestamps") from None


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def encode(document):
    try:
        raw = json.dumps(
            document, ensure_ascii=True, allow_nan=False, separators=(",", ":"),
        ).encode("ascii")
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise invalid("document") from None
    if len(raw) > MAX_PROJECT_BYTES:
        raise invalid("document")
    return raw


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError
        value[key] = item
    return value


def _reject_constant(_value):
    raise ValueError


def decode(raw):
    if len(raw) > MAX_PROJECT_BYTES:
        raise invalid("document")
    try:
        return json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
            parse_constant=_reject_constant,
        )
    except (ValueError, UnicodeError, RecursionError):
        raise invalid("document") from None


def validate(document, *, normalize_title=False):
    _keys(document, _FIELDS, "document")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise invalid("schema_version")
    project_id(document["project_id"])
    positive_revision(document["revision"])
    clean_title = title(document["title"])
    if not normalize_title and clean_title != document["title"]:
        raise invalid("title")
    output_profile(document["output_profile"])
    if timestamp(document["created_at"]) > timestamp(document["updated_at"]):
        raise invalid("timestamps")
    refs = document["asset_refs"]
    if type(refs) is not list:
        raise invalid("asset_refs")
    seen = set()
    for ref in refs:
        _keys(ref, {"asset_id", "kind", "digest"}, "asset_refs")
        identity = _safe_id(ref["asset_id"], field="asset_id")
        if identity in seen:
            raise invalid("asset_refs")
        seen.add(identity)
        if (
            type(ref["kind"]) is not str or ref["kind"] not in {"video", "audio", "image"}
            or type(ref["digest"]) is not str or not _DIGEST.fullmatch(ref["digest"])
        ):
            raise invalid("asset_refs")
    tracks = document["tracks"]
    if type(tracks) is not list or len(tracks) != 2:
        raise invalid("tracks")
    for track, (identity, kind) in zip(
        tracks, (("trk_picture", "picture"), ("trk_audio", "audio")),
    ):
        _keys(track, {"track_id", "kind", "clips"}, "tracks")
        if track["track_id"] != identity or track["kind"] != kind or type(track["clips"]) is not list:
            raise invalid("tracks")
        if track["clips"]:
            raise _fail("unsupported_capability", "validate", field="tracks")
    if type(document["candidate_refs"]) is not list:
        raise invalid("candidate_refs")
    if document["candidate_refs"]:
        raise _fail("unsupported_capability", "validate", field="candidate_refs")
    # A serialized copy both enforces the frozen byte limit and detaches drafts.
    result = decode(encode(document))
    result["title"] = clean_title
    return result

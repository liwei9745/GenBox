"""Sanitized error vocabulary for the WB-1 media boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class MediaProblem:
    """Public-safe error information.

    The manager never stores subprocess output, absolute paths or exception
    text in this object.
    """

    code: str
    stage: str
    message: str
    retryable: bool = False
    field: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "stage": self.stage,
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.field:
            payload["field"] = self.field
        return payload


class MediaIngestError(ValueError):
    """Exception carrying only a bounded, public-safe media problem."""

    def __init__(self, problem: MediaProblem) -> None:
        super().__init__(problem.message)
        self.problem = problem
        self.code = problem.code
        self.stage = problem.stage
        self.retryable = problem.retryable
        self.field = problem.field

    def as_dict(self) -> dict[str, Any]:
        return self.problem.as_dict()


def media_error(
    code: str,
    stage: str,
    message: str,
    *,
    retryable: bool = False,
    field: Optional[str] = None,
) -> MediaIngestError:
    return MediaIngestError(
        MediaProblem(
            code=code,
            stage=stage,
            message=message,
            retryable=retryable,
            field=field,
        )
    )


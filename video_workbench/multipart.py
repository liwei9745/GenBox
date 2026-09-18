"""Bound request parser allocations before invoking a media worker."""

from starlette.formparsers import MultiPartException, MultiPartParser
from python_multipart.exceptions import MultipartParseError

from .media.ingest import _kind_for_filename, _safe_filename
from .media.models import MediaLimits


class MediaMultipartParser(MultiPartParser):
    header_limit = 8192

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._header_bytes = 0
        self._part_bytes = 0
        self._total_bytes = 0
        self._file_limit = 0
        self._finished = False
        self._limits = MediaLimits()
        self.size_exceeded = False

    def on_part_begin(self):
        super().on_part_begin()
        self._header_bytes = 0
        self._part_bytes = 0
        self._file_limit = 0

    def _header_budget(self, length):
        self._header_bytes += length
        if self._header_bytes > self.header_limit:
            raise MultiPartException("header limit")

    def on_header_field(self, data, start, end):
        self._header_budget(end - start)
        super().on_header_field(data, start, end)

    def on_header_value(self, data, start, end):
        self._header_budget(end - start)
        super().on_header_value(data, start, end)

    def on_headers_finished(self):
        super().on_headers_finished()
        part = self._current_part
        if part.file is not None:
            if part.field_name != "files":
                raise MultiPartException("unknown field")
            name = _safe_filename(part.file.filename)
            kind = _kind_for_filename(name)
            self._file_limit = self._limits.byte_limit_for(kind)
        elif part.field_name != "request_id":
            raise MultiPartException("unknown field")

    def on_part_data(self, data, start, end):
        self._part_bytes += end - start
        self._total_bytes += end - start
        if self._total_bytes > self._limits.max_request_bytes or (
            self._current_part.file is not None and self._part_bytes > self._file_limit
        ):
            self.size_exceeded = True
            raise MultiPartException("media size limit")
        super().on_part_data(data, start, end)

    def on_end(self):
        self._finished = True
        super().on_end()

    async def parse(self):
        try:
            form = await super().parse()
            if not self._finished:
                raise MultiPartException("incomplete multipart body")
            return form
        except BaseException as error:
            # Includes disconnect/cancellation, not just malformed multipart.
            for handle in self._files_to_close_on_error:
                handle.close()
            if isinstance(error, MultipartParseError):
                raise MultiPartException("invalid multipart body") from None
            raise

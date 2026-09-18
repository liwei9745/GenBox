"""One runtime owner per store and explicit in-process media leases."""

from contextlib import contextmanager
import os
import threading

from .media.ingest import _fail


class StoreRuntime:
    def __init__(self, media):
        self.media = media
        self.lock = threading.RLock()
        self._handle = None
        self._closed = False
        self._leases = {}

    def acquire(self):
        with self.lock:
            if self._closed:
                raise _fail("conflict", "runtime")
            if self._handle is not None:
                return False
            self.media._ensure_directory(self.media.root)
            path = self.media.root / ".runtime.lock"
            self.media._assert_confined(path, self.media.root)
            handle = path.open("a+b")
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                handle.close()
                raise _fail("conflict", "runtime") from None
            self._handle = handle
            return True

    @contextmanager
    def lease(self, path):
        with self.lock:
            if self._closed or self._handle is None:
                raise _fail("conflict", "runtime")
            self.media._assert_confined(path, self.media.root)
            self._leases[path] = self._leases.get(path, 0) + 1
        try:
            yield
        finally:
            with self.lock:
                count = self._leases[path] - 1
                if count:
                    self._leases[path] = count
                else:
                    del self._leases[path]

    def leased(self, path):
        with self.lock:
            return bool(self._leases.get(path))

    def close(self):
        with self.lock:
            if self._leases:
                raise _fail("conflict", "runtime")
            if self._handle is not None:
                handle = self._handle
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_UN)
                handle.close()
                self._handle = None
            self._closed = True

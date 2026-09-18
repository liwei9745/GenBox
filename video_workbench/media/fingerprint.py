"""Change hints for browsing caches, never a substitute for content digests."""

import os
import stat


def change_token(path, info):
    if os.name != "nt" or not stat.S_ISREG(info.st_mode):
        return info.st_ctime_ns
    # Windows stat ctime is creation time. FILE_BASIC_INFO.ChangeTime also
    # changes when LastWriteTime is restored after a same-length overwrite.
    import ctypes
    from ctypes import wintypes
    import msvcrt

    class FileBasicInfo(ctypes.Structure):
        _fields_ = [
            ("creation", ctypes.c_longlong), ("access", ctypes.c_longlong),
            ("write", ctypes.c_longlong), ("change", ctypes.c_longlong),
            ("attributes", wintypes.DWORD),
        ]

    query = ctypes.WinDLL("kernel32", use_last_error=True).GetFileInformationByHandleEx
    query.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    query.restype = wintypes.BOOL
    value = FileBasicInfo()
    with path.open("rb") as handle:
        if not query(msvcrt.get_osfhandle(handle.fileno()), 0, ctypes.byref(value), ctypes.sizeof(value)):
            # Unsupported filesystems still work, but always rehash.
            return None
    return value.change or None

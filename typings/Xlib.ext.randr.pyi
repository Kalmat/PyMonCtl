from typing import Any


class MonitorInfo(str):
    def __getattr__(self, name: str) -> Any: ...

class GetScreenResourcesCurrent(str):
    def __getattr__(self, name: str) -> Any: ...

class GetOutputInfo(str):
    def __getattr__(self, name: str) -> Any: ...

class GetCrtcInfo(str):
    def __getattr__(self, name: str) -> Any: ...

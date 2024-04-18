from typing import Any


class loadBundleFunctions(str):
    def __getattr__(self, name: str) -> Any: ...

class loadBundleVariables(str):
    def __getattr__(self, name: str) -> Any: ...


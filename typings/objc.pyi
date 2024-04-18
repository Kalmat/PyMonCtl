from collections.abc import Buffer
from typing import Any, overload


class loadBundleFunctions(str):
    def __getattr__(self, name: str) -> Any: ...

    @overload
    def __new__(cls, object: object = ...) -> loadBundleFunctions: ...
    @overload
    def __new__(cls, object: Buffer, encoding: str = ..., errors: str = ...) -> loadBundleFunctions: ...

class loadBundleVariables(str):
    def __getattr__(self, name: str) -> Any: ...

    @overload
    def __new__(cls, object: object = ...) -> loadBundleVariables: ...
    @overload
    def __new__(cls, object: Buffer, encoding: str = ..., errors: str = ...) -> loadBundleVariables: ...


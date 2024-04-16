# https://github.com/ronaldoussoren/pyobjc/issues/198
# https://github.com/ronaldoussoren/pyobjc/issues/417
# https://github.com/ronaldoussoren/pyobjc/issues/419

from typing import Any


class CFSTR(str):
    def __getattr__(self, name: str) -> Any: ...

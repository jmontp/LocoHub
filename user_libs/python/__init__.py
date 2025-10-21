"""
Compatibility shim for legacy imports.

The Python library now lives under the `locohub` package. Prefer
`import locohub` directly and update code accordingly. This module
will be removed in a future release.
"""

from locohub import *  # noqa: F401,F403
from locohub import __all__ as _locohub_all  # type: ignore

__all__ = list(_locohub_all)

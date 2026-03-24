"""Email-specific CSS compiler built on Lightning CSS."""

from .compiler import CompilationResult, EmailCSSCompiler, OptimizedCSS
from .conversions import CSSConversion
from .shorthand import expand_shorthands

__all__ = [
    "CSSConversion",
    "CompilationResult",
    "EmailCSSCompiler",
    "OptimizedCSS",
    "expand_shorthands",
]

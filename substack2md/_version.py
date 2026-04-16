"""Single-source version string.

Kept in a dependency-free module so setuptools can read it during build
without importing the full ``_core`` module (which runs a runtime-
dependency check and would fail in a build-isolation environment).
"""

__version__ = "2.0.0"

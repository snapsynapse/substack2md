import subprocess
import sys


def test_missing_runtime_dependency_raises_importerror_not_systemexit():
    code = """
import builtins

real_import = builtins.__import__

def fake_import(name, *args, **kwargs):
    if name == "websocket":
        raise ModuleNotFoundError(name)
    return real_import(name, *args, **kwargs)

builtins.__import__ = fake_import

try:
    import substack2md
except SystemExit as exc:
    raise AssertionError(f"unexpected SystemExit: {exc}") from exc
except ImportError as exc:
    assert "Missing required dependencies" in str(exc)
else:
    raise AssertionError("expected ImportError")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

"""Install a supplied wheel in a fresh environment and exercise its CLI offline."""

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    if wheel.suffix != ".whl":
        parser.error("expected a built .whl file")
    with tempfile.TemporaryDirectory(prefix="substack2md-wheel-") as temporary:
        root = Path(temporary)
        environment = root / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        binaries = environment / ("Scripts" if os.name == "nt" else "bin")
        python = binaries / ("python.exe" if os.name == "nt" else "python")
        command = binaries / ("substack2md.exe" if os.name == "nt" else "substack2md")
        env = os.environ.copy()
        for key in ("PYTHONPATH", "PYTHONHOME", "SUBSTACK2MD_CONFIG", "SUBSTACK2MD_BASE_DIR"):
            env.pop(key, None)
        env["PYTHONNOUSERSITE"] = "1"

        def run(*arguments, **options):
            return subprocess.run(
                [str(argument) for argument in arguments], cwd=root, env=env, **options
            )

        run(python, "-m", "pip", "install", wheel, check=True)
        run(
            python,
            "-c",
            "import pathlib, sys, substack2md; "
            "assert pathlib.Path(substack2md.__file__).is_relative_to(sys.prefix); "
            "assert all(hasattr(substack2md, name) for name in substack2md.__all__)",
            check=True,
        )
        version = run(
            python,
            "-c",
            "from importlib.metadata import version; print(version('substack2md'))",
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for entrypoint in ((command,), (python, "-m", "substack2md")):
            reported = run(
                *entrypoint, "--version", check=True, capture_output=True, text=True
            ).stdout.strip()
            if reported != f"substack2md {version}":
                raise RuntimeError(
                    f"Version mismatch: {reported!r}, installed metadata {version!r}"
                )
            failed = run(
                *entrypoint,
                "--from-md",
                root / "missing.md",
                "--url",
                "https://example.substack.com/p/missing",
                "--base-dir",
                root / "failed-output",
                capture_output=True,
                text=True,
            )
            if failed.returncode == 0:
                raise RuntimeError(f"{entrypoint} returned success for a missing input file")
        run(command, "--help", check=True)
        source = root / "source.md"
        source.write_text("# Wheel smoke\n\nA sentence preserved by the installed CLI.\n")
        output = root / "output"
        run(
            command,
            "--from-md",
            source,
            "--url",
            "https://example.substack.com/p/wheel-smoke",
            "--base-dir",
            output,
            check=True,
        )
        notes = list(output.rglob("*.md"))
        if len(notes) != 1 or "A sentence preserved" not in notes[0].read_text():
            raise RuntimeError("Installed CLI did not produce the expected Markdown artifact")
        print(
            "Wheel smoke passed: isolated import, public API, console/module versions and "
            "failure exits, Markdown conversion"
        )


if __name__ == "__main__":
    main()

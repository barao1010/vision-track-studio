#!/usr/bin/env python3
"""Minimal, strict Vision Track Studio branding pass for current OBS upstream.
Does not remove third-party copyright or GPL notices.
"""
import argparse
from pathlib import Path

def replace_exact(path: Path, old: str, new: str):
    content = path.read_text(encoding="utf-8")
    if old not in content:
        raise RuntimeError(f"Expected upstream text not found in {path}: {old!r}")
    path.write_text(content.replace(old, new), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("obs_source", type=Path)
    args = parser.parse_args()
    src = args.obs_source.resolve()
    rc = src / "frontend/cmake/windows/obs.rc.in"
    entry = src / "frontend/obs-main.cpp"
    if not rc.is_file() or not entry.is_file():
        raise RuntimeError("Not an OBS source checkout (expected frontend/cmake/windows/obs.rc.in and frontend/obs-main.cpp)")
    replace_exact(rc, 'VALUE "FileDescription", "OBS Studio"', 'VALUE "FileDescription", "Vision Track Studio"')
    replace_exact(rc, 'VALUE "ProductName", "OBS Studio"', 'VALUE "ProductName", "Vision Track Studio"')
    replace_exact(rc, 'VALUE "CompanyName", "OBS"', 'VALUE "CompanyName", "Vision Track Studio"')
    replace_exact(entry, '"OBS Studio - "', '"Vision Track Studio - "')
    print("Branding pass applied (Windows VERSIONINFO, --version).")
    print("Not complete: UI titles, installer, profile isolation, executables and icon require separate review.")

if __name__ == "__main__":
    main()

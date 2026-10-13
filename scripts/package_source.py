"""GPL-2.0-or-later. Export corresponding sources including submodules."""
from pathlib import Path
import sys
import zipfile

with zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_DEFLATED) as archive:
    for argument in sys.argv[2:]:
        root = Path(argument)
        for file in root.rglob("*"):
            if not file.is_file():
                continue
            relative = file.relative_to(root)
            if any(part in {".git", ".deps", "__pycache__", "dist", "rundir"} or part.startswith("build_") for part in relative.parts):
                continue
            archive.write(file, str(Path(root.name) / relative))

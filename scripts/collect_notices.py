"""Collect installed distribution notices without editing their contents."""
from importlib.metadata import distributions
from pathlib import Path
import shutil
root = Path('dist/VisionTrackStudio/third-party-notices')
root.mkdir(parents=True, exist_ok=True)
for distribution in distributions():
    name = distribution.metadata.get('Name', 'unknown')
    for file in distribution.files or []:
        if any(part.lower().startswith(('license', 'copying', 'notice')) for part in file.parts):
            source = distribution.locate_file(file)
            if source.is_file():
                destination = root / name / str(file).replace('..', '_')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, destination)
python_license = Path(__import__('sys').base_prefix) / 'LICENSE.txt'
if python_license.exists():
    shutil.copyfile(python_license, root / 'Python-LICENSE.txt')

for path in Path('models').glob('LICENSE*'):
    shutil.copyfile(path, root / path.name)

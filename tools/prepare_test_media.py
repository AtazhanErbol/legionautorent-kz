"""Provide the one preserved image required by import-validation tests.

The full production catalogue belongs in its private media backup, not Git.
Never overwrite an existing media file. This helper is for tests only.
"""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / 'migration/test-fixtures/legacy-hero.webp'
target = root / 'media/cars/webp/2bf1760e14eda1f8ee28fb6b-1200.webp'
if not target.exists():
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
print('Import-test image available; existing media files preserved.')

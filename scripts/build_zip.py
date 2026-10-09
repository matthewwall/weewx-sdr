#!/usr/bin/env python3
"""Build the extension archive that weectl extension install can install.

scripts/build_zip.py

Writes dist/weewx-sdr-<version>.zip. The weewx installer wants the whole archive
to sit inside one top-level directory, with install.py at the root of that
directory, so that is the shape we write.
"""

import tomllib
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = REPO_ROOT / 'dist'

# What a release ships: the installer, the driver, and the documents that the
# weewx packaging guide expects an extension to carry. Tests, tooling, lock
# files and caches stay home.
INCLUDE = ('install.py', 'bin', 'README.md', 'changelog', 'license')


def _shipped_files():
    """The files to put in the archive, relative to the repository root."""
    shipped = []
    for name in INCLUDE:
        path = REPO_ROOT / name
        if path.is_file():
            shipped.append(path.relative_to(REPO_ROOT))
            continue
        for found in sorted(path.rglob('*')):
            if found.is_file() and '__pycache__' not in found.parts:
                shipped.append(found.relative_to(REPO_ROOT))
    return shipped


def main():
    pyproject = tomllib.loads((REPO_ROOT / 'pyproject.toml').read_text())
    version = pyproject['project']['version']
    top_dir = f'weewx-sdr-{version}'
    archive_path = DIST_DIR / f'{top_dir}.zip'
    DIST_DIR.mkdir(exist_ok=True)

    shipped = _shipped_files()
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for relative in shipped:
            archive.write(REPO_ROOT / relative, f'{top_dir}/{relative}')

    print(f'{archive_path.relative_to(REPO_ROOT)}: {len(shipped)} files')


if __name__ == '__main__':
    main()

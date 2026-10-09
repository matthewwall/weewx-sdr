#!/usr/bin/env python3
"""Write a new version into every file that states one.

scripts/bump_version.py 0.96b3
"""

import argparse
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# file -> (the line to write, the pattern matching the line to replace)
VERSIONS = {
    'pyproject.toml': ('version = "%s"', r'^version = .*$'),
    'install.py': ("VERSION = '%s'", r'^VERSION = .*$'),
    'bin/user/core.py': ("DRIVER_VERSION = '%s'", r'^DRIVER_VERSION = .*$'),
}


def main():
    parser = argparse.ArgumentParser(description='Write a version into every file that states one.')
    parser.add_argument('version', help='the new version, for example 0.96b3')
    version = parser.parse_args().version

    for name, (line, pattern) in VERSIONS.items():
        path = REPO_ROOT / name
        text, count = re.subn(pattern, line % version, path.read_text(), flags=re.M)
        if count != 1:
            raise SystemExit(f'{name}: expected exactly one version line, found {count}')
        path.write_text(text)
        print(f'{name}: {line % version}')


if __name__ == '__main__':
    main()

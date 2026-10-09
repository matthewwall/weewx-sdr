"""Verify the weewx-sdr extension installs and uninstalls through weecfg.

Adapted from weewx's src/weecfg/tests/test_config.py (TestExtensionInstall).
"""

import importlib.util
import shutil
import tempfile
import tomllib
from pathlib import Path

import pytest
import weecfg
import weecfg.extension
import weewx_data
from weeutil.printer import Printer

from user.core import DRIVER_VERSION

# Read-only source of a sample weewx.conf and the framework's 'user' package.
# Used only as a source; nothing under here is ever written to.
WEEWX_DATA_DIR = Path(weewx_data.__file__).parent
WEEWX_CONF = WEEWX_DATA_DIR / 'weewx.conf'

# The extension under test is this repository (which contains install.py).
REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_install():
    """Load the extension's install.py, which lives at the repo root."""
    spec = importlib.util.spec_from_file_location('sdr_install', REPO_ROOT / 'install.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


INSTALL = _load_install()


class TestExtensionInstall:
    """Installing and uninstalling this extension in a throwaway mini-WeeWX."""

    @staticmethod
    def _build_mini_weewx(weewx_root):
        """Build the directory layout that weecfg expects for a weewx install."""
        shutil.rmtree(weewx_root, ignore_errors=True)
        (weewx_root / 'skins').mkdir(parents=True, exist_ok=True)
        # The framework's own 'user' package, so 'user.<driver>' can be imported.
        shutil.copytree(WEEWX_DATA_DIR / 'bin' / 'user', weewx_root / 'bin' / 'user')
        shutil.copy(WEEWX_CONF, weewx_root)

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self.weewx_root = Path(tempfile.mkdtemp(prefix='weewx_sdr_test_'))
        self._build_mini_weewx(self.weewx_root)

        config_path = self.weewx_root / 'weewx.conf'
        self.config_path, self.config_dict = weecfg.read_config(str(config_path))
        self.engine = weecfg.extension.ExtensionEngine(
            self.config_path, self.config_dict, printer=Printer(verbosity=-1)
        )
        yield
        shutil.rmtree(self.weewx_root, ignore_errors=True)

    def test_files_list_is_complete(self):
        """Verifies the files listed in install.py match
        with the source code of the extension in bin/user/"""
        actual = sorted(
            p.relative_to(REPO_ROOT).as_posix()
            for p in (REPO_ROOT / 'bin' / 'user').glob('**/*.py')
        )
        assert INSTALL.FILES == actual

    def test_version_matches_pyproject(self):
        """Every version in the tree matches pyproject.toml: install.py's VERSION and the
        version the driver reports. Bump them together with scripts/bump_version.py."""
        pyproject = tomllib.loads((REPO_ROOT / 'pyproject.toml').read_text())
        version = pyproject['project']['version']

        assert INSTALL.VERSION == version, f'install.py says {INSTALL.VERSION}'
        assert DRIVER_VERSION == version, f'the driver says {DRIVER_VERSION}'

    def test_install(self):
        assert Path(self.engine.root_dict['WEEWX_ROOT']).resolve() == self.weewx_root.resolve()

        # install.py at the repo root drives the install.
        self.engine.install_extension(str(REPO_ROOT), no_confirm=True)

        user_dir = self.weewx_root / 'bin' / 'user'
        for rel_path in (
            'sdr.py',
            'core.py',
            'packet.py',
            'units.py',
            'brands/__init__.py',
            'brands/acurite.py',
        ):
            assert (user_dir / rel_path).is_file(), rel_path

        # The installer is archived so the extension can be uninstalled later.
        assert (user_dir / 'installer' / 'sdr' / 'install.py').is_file()

    def test_uninstall(self):
        """Uninstalling removes everything that was installed."""
        self.engine.install_extension(str(REPO_ROOT), no_confirm=True)

        user_dir = self.weewx_root / 'bin' / 'user'
        assert (user_dir / 'sdr.py').is_file()
        assert (user_dir / 'brands' / 'acurite.py').is_file()

        self.engine.uninstall_extension('sdr', no_confirm=True)

        assert not (user_dir / 'sdr.py').exists()
        assert not (user_dir / 'brands' / 'acurite.py').exists()
        assert not (user_dir / 'installer' / 'sdr').exists()

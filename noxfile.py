"""Nox sessions: run the test suite across Python and WeeWX versions.

Usage::

    nox                                   # every Python x WeeWX combination
    nox -p 3.13                           # all WeeWX releases on Python 3.13
    nox -s "tests-3.13(weewx='5.5.2')"    # a single Python x WeeWX combination
    nox -s latest                         # newest WeeWX on the newest Python
    nox -- -q -x                          # extra args are forwarded to pytest
"""

import nox

nox.needs_version = '>=2024.3.2'
nox.options.default_venv_backend = 'uv|virtualenv'

PYTHON_VERSIONS = ['3.11', '3.12', '3.13', '3.14']

# Latest release of each WeeWX minor series.
WEEWX_VERSIONS = ['5.0.2', '5.1.0', '5.2.0', '5.3.1', '5.4.0', '5.5.2']


@nox.session(python=PYTHON_VERSIONS)
@nox.parametrize('weewx', WEEWX_VERSIONS)
def tests(session, weewx):
    """Run the test suite against a specific WeeWX release."""
    session.install('--group', 'test')
    session.install(f'weewx=={weewx}')
    session.run('pytest', *session.posargs)


@nox.session(python=PYTHON_VERSIONS[-1], tags=['latest'])
def latest(session):
    """Run the test suite against the newest WeeWX on the newest Python."""
    session.install('--group', 'test')
    session.run('pytest', *session.posargs)

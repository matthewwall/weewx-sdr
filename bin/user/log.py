"""Logging helpers shared by the driver modules.

These live in their own module so that :mod:`user.packet` can use them without
importing :mod:`user.core` - which in turn imports :mod:`user.packet`.  Without
this split those two imports would be circular.
"""

import threading

try:
    # New-style weewx logging
    import logging

    import weeutil.logger  # noqa: F401  (imported for its logging side effects)

    # These helpers used to live in the monolithic sdr.py, which logged under
    # the 'user.sdr' name; keep that name so log output is unchanged.
    log = logging.getLogger('user.sdr')

    def logdbg(msg):
        log.debug(msg)

    def loginf(msg):
        log.info(msg)

    def logerr(msg):
        log.error(msg)

except ImportError:
    # Old-style weewx logging
    import syslog

    def logmsg(level, msg):
        syslog.syslog(level, 'sdr: %s: %s' % (threading.current_thread().name, msg))

    def logdbg(msg):
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        logmsg(syslog.LOG_ERR, msg)

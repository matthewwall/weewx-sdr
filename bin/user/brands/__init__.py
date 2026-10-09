"""Sensor packet subclasses, grouped by manufacturer.

Every module in this package is imported automatically and the classes it defines
are re-exported, so all the sensor classes are exposed automatically, users don't
have to remember to manually update a list of imports here.

PacketFactory finds parsers by introspecting this namespace, so a class that is
missing from it is a parser that never runs.
"""

import importlib
import inspect
import pkgutil


def _classes_defined_in_package():
    """Return every class that a module in this package defines, keyed by name."""
    classes = {}
    for _, module_name, _ in pkgutil.iter_modules(__path__):
        module = importlib.import_module('%s.%s' % (__name__, module_name))
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # __module__ excludes classes that the module imported rather than defined
            if obj.__module__ == module.__name__:
                classes[name] = obj
    return classes


_classes = _classes_defined_in_package()
globals().update(_classes)
del _classes

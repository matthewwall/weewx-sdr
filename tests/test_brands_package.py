"""``user.brands`` must stay a complete, unambiguous registry of packet classes.

``PacketFactory.known_packets()`` finds parsers by introspecting the package
namespace, so we want tests to verify we are correctly finding all the
declared Packet subclasses.
"""

import importlib
import inspect
import pkgutil

import user.brands as brands
from user.packet import PacketFactory


def classes_defined_in_brand_modules():
    """Return (module name, class name, class) for each class a module defines."""
    defined = []
    for _, module_name, _ in pkgutil.walk_packages(brands.__path__, brands.__name__ + '.'):
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # __module__ filters out classes imported into the module rather than
            # defined by it.
            if obj.__module__ == module_name:
                defined.append((module_name, name, obj))
    return defined


def test_the_package_exposes_every_class_a_brand_module_defines():
    defined = classes_defined_in_brand_modules()

    assert defined, 'found no classes at all - did the discovery break?'

    missing = [
        f'{module_name}.{name}'
        for module_name, name, obj in defined
        if getattr(brands, name, None) is not obj
    ]
    assert missing == [], f'defined in a brand module but not exposed by user.brands: {missing}'


def test_no_two_brand_modules_define_the_same_class_name():
    # shadowing is the one way the dynamic registry can still lose a class
    by_name = {}
    for module_name, name, _ in classes_defined_in_brand_modules():
        by_name.setdefault(name, []).append(module_name)

    shadowed = {name: modules for name, modules in by_name.items() if len(modules) > 1}
    assert shadowed == {}, f'the same class name is defined by several brand modules: {shadowed}'


def test_every_parser_is_discovered_by_the_factory(monkeypatch):
    parsers = [
        (module_name, name, obj)
        for module_name, name, obj in classes_defined_in_brand_modules()
        if hasattr(obj, 'IDENTIFIER')
    ]

    # known_packets() caches its result, so start from a cold cache
    monkeypatch.setattr(PacketFactory, 'KNOWN_PACKETS', [])
    known = PacketFactory.known_packets()

    undiscovered = [
        f'{module_name}.{name}' for module_name, name, obj in parsers if obj not in known
    ]
    assert undiscovered == [], f'not discoverable by PacketFactory: {undiscovered}'

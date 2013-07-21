# -*- coding: utf-8 -*-

"""
Simple utilities.
"""

from __future__ import print_function, division, absolute_import

import inspect
import textwrap
import collections

def hashable(x):
    try:
        hash(x)
        return True
    except TypeError:
        return False

def getsource(func):
    """Get source code without decorator for a function"""
    source = inspect.getsource(func)
    lines = source.splitlines()
    i = 0
    for i, line in enumerate(lines):
        if not line.lstrip().startswith('@'):
            break
    return textwrap.dedent("\n".join(lines[i:]))

def make_temper():
    """Return a function that returns temporary names"""
    temps = collections.defaultdict(int)

    def temper(name=None):
        count = temps[name]
        temps[name] += 1
        if name and count == 0:
            return name
        elif name:
            return '%s%d' % (name, count)
        else:
            return str(count)

    return temper
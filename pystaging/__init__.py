# -*- coding: utf-8 -*-
from __future__ import print_function, division, absolute_import

from os.path import dirname, abspath
import ast
import unittest

from pystaging.quotation import symbol, staging, quote, escape, run, string
from pystaging.astutils import astcompile

__version__ = '0.1'

# ______________________________________________________________________
# pystaging.test()

root = dirname(dirname(abspath(__file__)))
pattern = "test_*.py"

def test(root=root, pattern=pattern):
    """Run tests and return exit status"""
    tests =  unittest.TestLoader().discover(root, pattern=pattern)
    runner = unittest.TextTestRunner()
    result = runner.run(tests)
    return not result.wasSuccessful()
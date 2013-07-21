import unittest
from pystaging import *

@staging
def make_expr(c):
    return quote[a + b * escape[c]]

@staging(hygiene=True)
def make_stmt(c):
    with quote as body:
        result = a + b * escape[c]
    return body

@staging
def square(x):
    return quote[escape[x] * escape[x]]

@staging
def splice_expr(x):
    return escape[square(quote[x])]


class TestQuotation(unittest.TestCase):

    def test_quotation_expr(self):
        expr = make_expr(10)
        self.assertEqual(string(expr), "(a + (b * 10))")

    def test_quotation_stmt(self):
        s1 = make_stmt(10)
        env = {'a': 2, 'b': 5}
        run(s1, env)
        self.assertNotIn('result', env)
        self.assertEqual(env['staged.temp.result'], 2 + 5 * 10)

    def test_inline_splice_expr(self):
        self.assertEqual(splice_expr(10), 100)
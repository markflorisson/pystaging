# -*- coding: utf-8 -*-

"""
Support for multi-stage programming.
"""

from __future__ import print_function, division, absolute_import

import ast
import sys

from .utils import getsource, make_temper
from .astutils import astcompile, escape_ast, is_expr, is_stmt, wrap
from .visitors import replace, bindings, findquotes, ExprKill


prefix = 'staged.temp.'
temper = make_temper()

def temp(name):
    return temper(prefix + name)

#===------------------------------------------------------------------===
# Public interface
#===------------------------------------------------------------------===

class symbol(object):
    """Create a fresh symbol that can be shared between quotations"""
    def __init__(self, name):
        self.name = temp(name)

    @property
    def store(self):
        return ast.Name(self.name, ast.Store())

    @property
    def load(self):
        return ast.Name(self.name, ast.Load())


def staging(func=None, auto_escape=False, hygiene=False, debug=False):
    """
    Define a staging function, i.e. one that uses quote, escape or run.

        auto_escape: auto escape free variables in quotations
        hygiene:     auto name-mangle bound variables in quotations, for
                     "safe" use in run(), eval() or exec
    """
    def decorator(f):
        source = getsource(f)
        tree = ast.parse(source)

        env = {
            'globals': f.func_globals,
            'quotation_level': 0,
            'auto_escape': auto_escape, 'hygienic': hygiene,
        }
        quotes, escapes = findquotes(tree, env)
        exclude = quotes | escapes

        bound, free = bindings(tree, exclude=exclude)[tree.body[0]]
        env['locals'] = bound,

        tree, _ = process(tree, env, quotes, escapes)
        if debug:
            print(string(tree))

        code = astcompile(tree, env['globals']['__file__'])
        exec code in env['globals'], env['globals']
        return env['globals'][f.__name__]

    if func is not None:
        return decorator(func)
    return decorator

def quote(tree, env=None):
    """Quote a piece of code, returning an AST"""
    if env is not None:
        # Compile time
        env['quotation_level'] += 1

        preprocess(tree, env)
        tree, exclude = process(tree, env)
        postprocess(tree, env, exclude=exclude)

        env['quotation_level'] -= 1
        return escape_ast(tree, exclude=exclude)
    else:
        # Runtime, update AST locations
        ast.fix_missing_locations(tree)
        return tree

def ct_escape(tree, env, result_is_expr=True):
    """Compile-time escape operator"""
    result, _ = process(tree, env)

    if result_is_expr:
        # Generate runtime verification call
        escape_func = ast.Name('escape', ast.Load())
        result = ast.Call(escape_func, [result], [], None, None)

    if not env['quotation_level']:
        # Run escape code and splice in result, currently only
        # expressions are supported
        result = run(result, env['globals'], env['globals'])
        assert is_expr(result), "Can only splice expressions currently"

    assert isinstance(result, ast.AST), result
    return result

def escape(tree, env=None, **kwds):
    """
    Escape operator. This evaluates in the local scope at the time it is
    encountered in a quotation statement. Additionally the escape may be
    used outside of a quotation to splice in an expression.
    """
    if env is not None:
        return ct_escape(tree, env, **kwds)
    else:
        # runtime, verify escaped result
        if isinstance(tree, ast.Expression):
            tree = tree.body
        return wrap(tree)

def run(result, globals=None, locals=None):
    """Run a quotation and return the result"""
    if globals is None:
        globals = sys._getframe(1).f_globals
    elif locals is None:
        locals = globals

    if locals is None:
        locals = sys._getframe(1).f_locals

    code = astcompile(result)
    if is_expr(result):
        return eval(code, globals, locals)
    else:
        assert is_stmt(result)
        exec code in globals, locals
        return globals, locals

def string(expr):
    """Stringify an ast"""
    import meta
    return meta.dump_python_source(expr).strip()

# ______________________________________________________________________
# Rewriting utilities

# compile() does not accept ast.Suite()
suite = lambda body: ast.If(ast.Num(1), body, [])

def preprocess(tree, env):
    """Pre-process a quoted tree"""
    if env['auto_escape']:
        bindingmap = bindings(tree, env)
        bindfree(tree, env, bindingmap)

def process(tree, env, quotes=None, escapes=None):
    """
    Rewrite quotes in an AST. Returns a transformed AST and a set of new nodes.
    """
    replacements = {}
    globals = env['globals']
    if quotes is None:
        quotes, escapes = findquotes(tree, env)

    # Process quotes and escaped and build replacement map
    for node in quotes | escapes:
        if isinstance(node, ast.Subscript):
            replacements[node] = globals[node.value.id](node.slice.value, env)
        else:
            metasuite = globals['quote'](suite(node.body), env)
            replacements[node] = ast.Assign(
                [ast.Name(node.optional_vars.id, ast.Store())], metasuite)

    tree = replace(tree, replacements)
    return tree, set(replacements.itervalues())

def postprocess(tree, env, exclude=None):
    """Post-process a quoted tree"""
    if env['hygienic']:
        bindingmap = bindings(tree, exclude)
        refreshbound(tree, env, bindingmap)

# ______________________________________________________________________

def bindfree(tree, env, bindings):
    """Resolve freevars from bindings or environment and splice in result"""
    replacements = {}
    for node, (bound, free) in bindings.iteritems():
        for name, nodes in free.iteritems():
            if name in env['locals']:
                for node in nodes:
                    replacements[node] = ast.Subscript(
                        value=ast.Name(id='escape', ctx=ast.Load()),
                        slice=ast.Index(value=node), ctx=ast.Load())

    replace(tree, replacements)

def refreshbound(tree, env, bindings):
    """Refresh bound variables for hygiene"""
    for node, (bound, free) in bindings.iteritems():
        for name, nodes in bound.iteritems():
            if not name.startswith('staged.temp'):
                name = temp(name)
                for node in nodes:
                    node.id = name

# ______________________________________________________________________
# -*- coding: utf-8 -*-

"""
AST utilities:

    - parse
    - compile
    - stringify
    - wrap
    - escape
"""

from __future__ import print_function, division, absolute_import

import ast
import sys
from functools import partial

from pystaging.utils import hashable

# ______________________________________________________________________

is_expr = lambda tree: isinstance(tree, (ast.Expression, ast.expr))
is_stmt = lambda tree: isinstance(tree, (ast.stmt, ast.Suite, ast.Module))

def astcompile(tree, filename="<string>", flags=0):
    """Compile an AST"""
    env = sys._getframe(1).f_globals
    if "print_function" in env and env["print_function"].compiler_flag:
        flags |= env["print_function"].compiler_flag

    if is_stmt(tree):
        return _compilestmt(tree, filename, flags)
    else:
        assert is_expr(tree), tree
        return _compileexpr(tree, filename, flags)

def _compilestmt(tree, filename, flags):
    if not isinstance(tree, ast.Module):
        tree = ast.Module([tree])
    ast.fix_missing_locations(tree)
    return compile(tree, filename, 'exec', flags, True)

def _compileexpr(tree, filename, flags):
    if not isinstance(tree, ast.Expression):
        tree = ast.Expression(tree)
    ast.fix_missing_locations(tree)
    return compile(tree, filename, 'eval', flags, True)


def astparse(tree, filename="<string>", flags=0):
    pass

def wrap(obj):
    """Wrap an object in an AST"""
    if isinstance(obj, ast.AST):
        return obj
    elif isinstance(obj, (list, dict, tuple, int, float, basestring)):
        return escape_ast(obj)
    else:
        raise TypeError(
            "Cannot wrap objects of type %s into an AST" % (type(obj),))

# ______________________________________________________________________
# Heavily based on basil.lang.mython.ASTUtils.mk_escaper
import _ast
def mk_escaper(ast_module):
    def escape_ast(obj, exclude=frozenset()):
        """Translate the given AST into a Python AST
        that can be evaluated to construct the given AST (a meta-ast)."""
        if hashable(obj) and obj in exclude:
            return obj

        escape = partial(escape_ast, exclude=exclude)
        if isinstance(obj, ast_module.AST):
            ast_type = type(obj)
            esc_args = [escape(getattr(obj, ctor_arg))
                        for ctor_arg in ast_type._fields]
            ctor = ast_module.Attribute(
                ast_module.Name('ast', ast_module.Load()),
                ast_type.__name__, ast_module.Load())
            ret_val = ast_module.Call(ctor, esc_args, [], None, None)
        elif isinstance(obj, dict):
            keyobjs = obj.keys()
            ret_val = ast_module.Dict(
                [escape(keyobj) for keyobj in keyobjs],
                [escape(obj[keyobj]) for keyobj in keyobjs])
        elif isinstance(obj, list):
            ret_val = ast_module.List([escape(subobj) for subobj in obj],
                                      ast_module.Load())
        elif isinstance(obj, tuple):
            ret_val = ast_module.Tuple([escape(subobj) for subobj in obj],
                                        ast_module.Load())
        elif isinstance(obj, int):
            ret_val = ast_module.Num(obj)
        elif isinstance(obj, float):
            ret_val = ast_module.Num(obj)
        elif isinstance(obj, str):
            ret_val = ast_module.Str(obj)
        elif obj is None:
            ret_val = ast_module.Name("None", ast_module.Load())
        else:
            raise NotImplementedError("Don't know how to escape '%r'!" % (obj))
        return ret_val

    return escape_ast

escape_ast = mk_escaper(ast)
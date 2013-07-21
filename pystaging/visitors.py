# -*- coding: utf-8 -*-

"""
Support for multi-stage programming.
"""

from __future__ import print_function, division, absolute_import

import collections
import ast
from functools import partial

from pystaging.astutils import is_stmt, is_expr

dict_of_list = partial(collections.defaultdict, list)

def exclude_subtrees(visitor, exclude=None):
    exclude = exclude or frozenset()

    def visit(node):
        """Visit a node, skip excluded subtrees."""
        if node not in exclude:
            method = 'visit_' + node.__class__.__name__
            method = getattr(visitor, method, visitor.generic_visit)
            return method(node)

    visitor.visit = visit
    return visitor

#===------------------------------------------------------------------===
# Transformers
#===------------------------------------------------------------------===

def replace(tree, replacements):
    """Replace nodes in an AST according to a replacements dict"""
    return Replacer(replacements).visit(tree)

class Replacer(ast.NodeTransformer):
    def __init__(self, replacements):
        self.replacements = replacements

    def visit(self, node):
        if node in self.replacements:
            return self.replacements[node]
        return super(Replacer, self).visit(node)

class ExprKill(ast.NodeTransformer):
    """
    Remove expressions that wrap statements, e.g. for when escape[expr]
    returns a statement.
    """

    def visit_Expr(self, node):
        node.value = self.visit(node.value)
        if is_stmt(node.value):
            return node.value
        return node

#===------------------------------------------------------------------===
# Visitors
#===------------------------------------------------------------------===

def bindings(ast, exclude=None):
    """Find bindings of variables, returns { FunctionNode : (bound, free) }"""
    v = exclude_subtrees(BindingVisitor(), exclude)
    v.collect(ast)
    return v.bindings

class BindingVisitor(ast.NodeVisitor):

    def __init__(self):
        self.bindings = {} # Node -> (bound, free)
        self.bound, self.free = None, None

    def visit_FunctionDef(self, node):
        self.boundvar(node.name, node)
        self.collect(node, self.generic_visit)

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Param, ast.Store)):
            self.boundvar(node.id, node)
        else:
            self.freevar(node.id, node)

    # __________________________________________________________________

    def collect(self, node, visit=None):
        """Collect the bound and free sets"""
        bound, free = self.bound, self.free
        self.bound, self.free = dict_of_list(), dict_of_list()
        self.bindings[node] = (self.bound, self.free)
        (visit or self.visit)(node)
        self.bound, self.free = bound, free

    def boundvar(self, name, node):
        self.bound[name].append(node)
        self.bound[name].extend(self.free.pop(name, []))

    def freevar(self, name, node):
        if name not in self.bound:
            self.free[node.id].append(node)

# ______________________________________________________________________

def findquotes(ast, env):
    """Find quotations and escapes"""
    v = QuoteFinder()
    v.visit(ast)
    return v.quotes, v.escapes

class QuoteFinder(ast.NodeVisitor):

    def __init__(self):
        self.quotes = set()
        self.escapes = set()

    def visit_Subscript(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == 'quote':
            self.quotes.add(node)
        elif isinstance(node.value, ast.Name) and node.value.id == 'escape':
            self.escapes.add(node)
        else:
            self.generic_visit(node)

    def visit_With(self, node):
        ctx, dst = node.context_expr, node.optional_vars
        if isinstance(ctx, ast.Name) and ctx.id == 'quote':
            assert isinstance(dst, ast.Name), dst
            self.quotes.add(node)
        else:
            self.generic_visit(node)
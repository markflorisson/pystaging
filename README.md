pystaging
=========

pystaging provides support for staged code using quotation and
anti-quotation. This allows users to quickly assemble syntactically
safe programs using python syntax.

This has many applications, such as a staged interpreter for a DSL:

```python
    def translate_Add(left, right):
        return quote[escape[left] + escape[right]]
```

Another example is domain-specific optimizations, e.g. when combined
with an external translator. Languages like Terra make extensive use
of this. Here's an example to generate arbitrary binary ufuncs:

```
    import ast
    import numpy as np
    from pystaging import *

    def make_ufunc(op):
        @staging(debug=True)
        def ufunc(A, B):
            out = np.empty_like(A)
            for i in range(A.shape[0]):
                # Evaluate operation inline
                out[i] = escape[op(quote[A[i]], quote[B[i]])]
            return out
        return ufunc

    @staging
    def add(a, b):
        return quote[escape[a] + escape[b]]

    def build_ufunc():
        ufunc = make_ufunc(add)
        A = np.arange(10)
        B = np.arange(10)
        print(ufunc(A, B))

    op = add # doesn't understand cell variables yet :(
    build_ufunc()
```

Since we had debugging on, it prints:

```
    def ufunc(A, B):
        out = np.empty_like(A)
        for i in range(A.shape[0]):
            out[i] = (A[i] + B[i])
        return out
```

And the output of the generated ufunc application:

```
    [ 0  2  4  6  8 10 12 14 16 18]
```


Supported Features:
===================

Syntactic well-formedness:

    pystaging makes sure the programs generated have a valid syntactic
    structure.

Custom stagers:

    quote and escape can be overridden to produce different code fragments
    than Python ASTs. These overrides can also perform type checking or
    verification where desired.

Missing Features:
=================

Well-typedness:

    Typing that ensured generated code is well-typed if the code generator
    is well-typed.

Elegance:

    The elegance to override Python syntax and use custom quote and escape
    syntax operators.

Cross-stage persistence:

    Persist objects across stages, e.g. persist a compile time constant object
    to runtime. Only string, int, float, list, dict and AST objects (and compositions
    thereof) can be persisted.

Common subexpression elimination:

    def square(x):
        return quote[x * x]

    square(quote[a + 2]) # produces ((a + 2) * (a + 2))

Rewrites and optimizations:

    No built-in support for rewrites or domain-specific optimizations. However, one
    can take the AST or Python code object and apply these later.


Credits and Literature
======================

None of the ideas in pystaging are new, and can be found in many other languages.

- [Multi-Stage Programming: Its Theory and Applications](http://www.cs.rice.edu/~taha/publications/thesis/thesis.pdf)
- [A Gentle Introduction to Multi-stage Programming](http://www.cs.rice.edu/~taha/publications/journal/dspg04a.pdf)
- [Lightweight Modular Staging: A Pragmatic Approach to Runtime Code Generation and Compiled DSLs](http://infoscience.epfl.ch/record/150347/files/gpce63-rompf.pdf)
- [Terra: A Multi-Stage Language for High-Performance Computing](http://terralang.org/pldi071-devito.pdf)
- [REFLECTIVE TECHNIQUES IN EXTENSIBLE LANGUAGES](http://people.cs.uchicago.edu/~jriehl/dissertation.pdf)
- [Metaprogramming in Julia](http://docs.julialang.org/en/release-0.1/manual/metaprogramming/)


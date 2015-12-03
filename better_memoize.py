""" Fastest memoization decorator available for functions with more than one argument.
    This pattern dynamically concatenates custom code which is then executed.
    The memoized arguments match the arguments of the original function.
    No more costly conversions to and from (*args, **kwargs)

    By using the inspect module, we can piece together code which
    allows the memoized decorator to take the same argument format
    as the original function.
"""
__all__ = ['memoize']

def memoize(func):
    template  = '''if True:
    def wrapper(func):
        cache = {}
        @wraps(func)
        def _memoize(%(top_args)s):
            key = (%(middle_args)s)
            try:
                return cache[key]
            except KeyError:
                pass
            val = func(%(bottom_args)s)
            cache[key] = val
            return val
        return _memoize
    ''' % arg_formatter(func)

    from functools import wraps
    namespace = {'wraps': wraps}
    exec(template, namespace)
    return namespace['wrapper'](func)

def arg_formatter(func):
    """ Helper function to help parse together a string to execute code to create
        the custom memoizing wrapper.  Some sample output is below:

        top_args:
            Example: (x, y, z=-1, *varargs, **keywords)
            returns the arg format for the wrapped function.  It should be
            identical to the format for the original function.

        middle_args:
            Example: (x, y, z, varargs, frozenset(keywords.items()))
            This is a lightweight tuple used to make the memoizing key.
            We don't care about default arguments anymore, nor do we care
            about the single "*" and double "**" splat operators.

        bottom_args:
            Example: (x, y, z, *varargs, **keywords)
            We don't care about default arguments, but we do care
            about the single "*" and double "**" splat operators.
            This the lines used to invoke our original function.
    """
    import inspect
    spec = inspect.getargspec(func)
    spec = spec._replace(defaults = spec.defaults or ())

    c = len(spec.args) - len(spec.defaults)
    top_required = [', '.join(spec.args[:c])] if c else []

    if spec.defaults:
        defaults = zip(spec.args[c:], spec.defaults)
        top_defaults = [', '.join('%s=%r' % i for i in defaults)]
    else:
        top_defaults = []

    field_names = list(spec.args)
    if spec.varargs:
        field_names.append(spec.varargs)
        top_varargs = ["*%s" % spec.varargs]
        middle_varargs = [spec.varargs]
    else:
        top_varargs = []
        middle_varargs = []

    if spec.keywords:
        field_names.append(spec.keywords)
        top_keywords = ["**%s" % spec.keywords]
        middle_keywords = ["frozenset(%s.items())" % spec.keywords]
    else:
        top_keywords = []
        middle_keywords = []

    top_args = ', '.join(top_required + top_defaults + top_varargs + top_keywords)
    middle_args = ', '.join(spec.args + middle_varargs + middle_keywords)
    bottom_args = ", ".join(spec.args + top_varargs + top_keywords)
    return {'top_args': top_args, 'middle_args': middle_args, 'bottom_args': bottom_args}

def private_cache(func):
    """ Lightning fast way to memoize properties of objects.
        Use in place of a property decorator.  130 ns per lookup
        Even works to memoize properties where __slots__ = ()

        class Person:
            @private_cache
            def full_name(self):
                return self.first_name + '_' + self.last_name

        We create a dict subclass where we define __missing__.
        Missing makes a fresh call of the unbound function, passing
        in the instance as a key.  Then during all the other hits,
        we're calling property on the dictionary.__getitem__ method.
    """
    class Cache(dict):
        __slots__ = ()
        def __missing__(self, key):
            val = func(key)
            self[key] = val
            return val
    fget = Cache().__getitem__
    return property(fget, doc=func.__doc__)
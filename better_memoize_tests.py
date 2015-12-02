import unittest
from better_memoize import memoize, private_cache

from collections import namedtuple, OrderedDict
from operator import itemgetter

########################################################
#  Template for creating multiple unit tests per item  #
########################################################

class bulk_test(object):
    """ Class decorator which allows for the setting of of bulk unit testing.
        The original class should NOT inherit from unittest.TestCase.  Just 
        inherit from object.

        This class decorator will then deconstruct the class, find the methods
        that are decorated with @bulk_test.template, then it will apply that 
        template to all the items.

        Then the class will be rebuilt from scratch, this time inheriting from
        unittest.TestCase.  Everything works fine after that.
    """

    def items(me):
        msg = "Please define a sequence of items over which each of the tests will be written"
        raise NotImplementedError(msg)

    @classmethod
    def template(me, func):
        """ This meorator is used to itentify bulk tests when the test class is created. """
        func.__bulktemplate__ = True
        func.__module__ = me.__module__
        return func

    @classmethod
    def apply_template(me, template, dct, items):
        for item in items:
            def test(self):
                return template(self, item)
            test.__name__ = '%s_for_%s' % (template.__name__, item.signature)
            test.__module__ = me.__module__
            test.__doc__ = template.__doc__
            dct[test.__name__] = test
        return dct

    @classmethod
    def extract_templates(me, dct, items):
        for name, value in dct.items():
            if getattr(value, '__bulktemplate__', False):
                me.apply_template(value, dct, items)
                del dct[name]
        return dct

    def __new__(me, cls):
        name = cls.__name__
        bases = cls.__bases__
        dct = dict(cls.__dict__)
        dct = me.extract_templates(dct, dct['items'])
        if unittest.TestCase not in cls.__mro__:
            bases = (unittest.TestCase,) + bases
        return type(name, bases, dct)

########################################################
#     Testing for the 'cached_property' features       #
########################################################

class Incrementer:
    def __init__(self):
        self.value = 0

    def __iter__(self):
        return self

    def next(self):
        self.value += 1
        return self.value
    __next__ = next

class Person(object):
    def __init__(self, first_name, last_name):
        self.first_name = first_name
        self.last_name = last_name
        self.x_id = Incrementer()
        self.y_id = Incrementer()
        self.z_id = Incrementer()
        self.name_id = Incrementer()

    @property
    def signature(self):
        return self.first_name + '_' + self.last_name

    def __hash__(self):
        return hash(tuple([self.first_name, self.last_name]))

    def __eq__(self, other):
        t_self = (self.first_name, self.last_name)
        if t_self == other:
            return True
        elif t_self == (other.first_name, other.last_name):
            return True
        return NotImplemented

    @private_cache
    def full_name(self):
        return self.first_name + '_' + self.last_name + '_' + next(self.name_id)

    @private_cache
    def x(self):
        return "XXX_%d_%d" % (id(self), next(self.x_id))

    @private_cache
    def y(self):
        return "YYY_%d_%d" % (id(self), next(self.y_id))

    @property
    def z(self):
        return "ZZZ_%d_%d" % (id(self), next(self.z_id))

@bulk_test
class test_cached_property(object):
    items = [
        Person('Steve', 'Zelaznik'),
        Person('Barack','Obama'),
        Person('Michael','Zelaznik'),
        Person('Donald','Trump')
    ]

    @bulk_test.template
    def test_native_method_z_increments_up_each_time(self, item):
        last_z = next(item.z_id)
        self.assertEqual(item.z, "ZZZ_%d_%d" % (id(item),last_z+1))
        item.z
        item.z
        item.z
        self.assertEqual(item.z, "ZZZ_%d_%d" % (id(item),last_z+5))

    @bulk_test.template
    def test_cached_method_y_returns_id_1_each_time(self, item):
        for _ in range(10):
            item.y
        self.assertEqual(item.y, "YYY_%d_1" % id(item))

    def test_same_method_returns_different_values_for_each_item(self):
        item_a, item_b = self.items[:2]
        self.assertNotEqual(item_a.x, item_b.x)

########################################################
#     Testing for the 'better_memoize' features        #
########################################################

keys = ('required_ct','arg_ct','default_ct','varargs','keywords','args_passed')
class Item(namedtuple('BaseItem',keys)):
    __slots__ = ()
    source = OrderedDict([('x',3),('y',4),('z',5),('a',0)])
    max_args = len(source)
    required = tuple(source.keys())
    defaults = tuple(['%s=%r' % i for i in source.items()])
    extra_keys = tuple(['n','o','r','t','h'])
    extra_values = tuple(ord(k) for k in extra_keys)

    @classmethod
    def base_args(cls, varargs = None, keywords = None, args_passed = ()):
        from random import random
        for arg_ct in range(cls.max_args+1):
            for default_ct in range(arg_ct+1):
                required_ct = arg_ct - default_ct
                for n in range(required_ct, arg_ct+1):
                    args_passed = tuple([random() for _ in range(n)])
                    item = Item(required_ct, arg_ct, default_ct, varargs, keywords, args_passed)
                    assert required_ct + default_ct == arg_ct, "Inconsistent counting: %r" % (item,)
                    yield item

    @classmethod
    def all_args(cls):
        for keywords in (None, 'keywords'):
            for varargs in (None, 'varargs'):
                for item in cls.base_args(keywords, varargs):
                    yield item

    @classmethod
    def all_values_passed(cls):
        for item in cls.all_args():
            for n in range(item.required_ct, item.arg_ct+1):
                args = [random() for _ in range(n)]

    @staticmethod
    def make_func(args, varargs = None, keywords = None):
        top_args = list(args)
        if varargs: top_args += ['*%s' % (varargs,)]
        if keywords: top_args += ['**%s' % (keywords,)]
        top_args = ', '.join(top_args)
        template = """if True:
        def orig_func(%(top_args)s):
            return locals()
        """ % {'top_args': top_args}
        namespace = {}
        exec(template, namespace)
        return namespace['orig_func']

    @private_cache
    def args(self):
        required, defaults = self.required, self.defaults
        required_ct, arg_ct, default_ct, varargs, keywords, args_passed = self
        return required[:required_ct] + defaults[arg_ct-default_ct:arg_ct]

    @private_cache
    def signature(self):
        d = self.__dict__
        d['varargs'] = '__varargs' if d['varargs'] else ''
        d['keywords'] = '__keywords' if d['keywords'] else ''
        return 'required_ct_%(required_ct)s__arg_ct_%(arg_ct)s__default_ct_%(default_ct)s%(varargs)s%(keywords)s' % d

    @private_cache
    def memoized(self):
        return memoize(self.func)

    @private_cache
    def func(self):
        return self.make_func(self.args, self.varargs, self.keywords)

from inspect import getargspec
@bulk_test
class test_better_memoize(object):
    items = tuple(Item.all_args())

    @bulk_test.template
    def test_argspecs_equal(self, item):
        orig_spec = getargspec(item.func)
        memoized_spec = getargspec(item.memoized)
        args = (orig_spec, memoized_spec)
        msg = """\nOriginal: %(orig_spec)s\nMemoized: %(memoized_spec)s"""
        self.assertEqual(orig_spec, memoized_spec, msg % locals())

if __name__ == '__main__':
    unittest.main()
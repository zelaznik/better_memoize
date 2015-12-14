from __future__ import division, print_function, absolute_import

import unittest
from main import memoize, private_cache
from bulk_tests import bulk_test

from collections import namedtuple, OrderedDict
from operator import itemgetter

########################################################
#     Testing for the 'cached_property' features       #
########################################################

from collections import defaultdict
class Enumerator(object):
    def __init__(self, name):
        self.name = name
        self.values = defaultdict(int)

    def __call__(self, obj):
        self.values[id(obj)] += 1
        return self.values[id(obj)]

class Person(namedtuple('BasePerson',('first_name','last_name'))):
    __slots__ = ()
    x_id = property(Enumerator('x_id'))
    y_id = property(Enumerator('y_id'))
    z_id = property(Enumerator('z_id'))
    name_id = property(Enumerator('name_id'))

    @property
    def signature(self):
        return self.first_name + '_' + self.last_name

    @private_cache
    def full_name(self):
        return '%s_%s_%s' % (self.first_name , self.last_name, self.name_id)

    @private_cache
    def x(self):
        return "XXX_%d_%d" % (id(self), self.x_id)

    @private_cache
    def y(self):
        return "YYY_%d_%d" % (id(self), self.y_id)

    @property
    def z(self):
        return "ZZZ_%d_%d" % (id(self), self.z_id)

p = Person('Steve','Zelaznik')
m = Person('Michael','Zelaznik')

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
        last_z = item.z_id
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

    def __repr__(self):
        c = self.__class__.__name__
        items = zip(self._fields, self)
        r = ', '.join(['%s=%r' % i for i in items])
        return '%s(%s)' % (c, r)

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

    @bulk_test.template
    def test_memoized_and_orig_return_equal_values(self, item):
        orig_result = item.func(*item.args_passed)
        memoized_result = item.memoized(*item.args_passed)
        args = (orig_result, memoized_result)
        msg = """\nOriginal: %(orig_result)s\nMemoized: %(memoized_result)s"""
        self.assertEqual(orig_result, memoized_result, msg % locals())

if __name__ == '__main__':
    unittest.main()

# Better Memoize Library

## Overview
  - A set of functions which improve the performance of Python's memoize pattern.
  - Gets rid of unnecessary nested function calls.
  - Eliminates unnecessary variable packing and unpacking.

## Functions Included:
  - **better_memoize**
    - Uses custom executed code which preserve original function arguments.
    - Eliminates costly argument unpacking and repacking.

  - **private_cache**
    - For custom on-the-fly calculated properties.
    - Performance as good as Python's namedtuple.
    - Memory efficient.  One cache dictionary per attribute, not class instance.

## How to use "better_memoize.memoize" in code:

```python
from better_memoize import memoize

@memoize
def magnitude(x, y, z):
    return (x**2 + y**2 + z**2) ** 0.5

  [in] >>> import inspect
  [in] >>> inspect.getargspec(magnitude)
 [out] >>> ArgSpec(args=['x', 'y', 'z'], varargs=None, keywords=None, defaults=None)
```
## How to use "better_memoize.private_cache" in code:

```python
from better_memoize import private_cache
from operator import itemgetter
class Person(tuple):
    __slots__ = ()
    first_name = property(itemgetter(0))
    last_name  = property(itemgetter(1))

    def __new__(cls, first_name, last_name):
        return tuple.__new__(cls, (first_name, last_name))

    ''' Combines the property and memoize decorators. '''
    @private_cache
    def full_name(self):
        return '%s_%s' % (self.first_name, self.last_name)

  [in] >>> p = Person('Steve','Zelaznik')
  [in] >>> p.full_name
 [out] >>> 'Steve_Zelaznik'
```

## Installation Guide:
  - Browse to the directory you want in the terminal
  - Clone the Git Repo in your computer
  - Make sure to have the colorize gem

  ```bash
  $ cd '/users/zMac/desktop'
  $ git clone https://github.com/zelaznik/better_memoize.git
  $ cd 'better_memoize'
  $ python setup.py install
  ```

## Private Cache - Design Choices Explained

I’ll admit it. I hate meta programming. Don’t get me wrong, I like to use it, but only after somebody else has slaved away create all that darkroom magic that makes my life so seamless. Even so, every once in a while I too get caught deep in the metaprogramming rabbit hole. Usually after I’ve grown sick of typing the same boiler plate patterns over and over again. Most of the time there’s nothing to brag about. Every once in a while I feel like I’ve at least struck silver. So here goes. I’m presenting what may be the fastest way to memoize property decorators in Python. Necessity is the mother of invention, and I stumbled across this problem after writing and rewriting this same pattern.

```python
class Person:
    @property
    def full_name(self):
        try:
            return self.__full_name
        except AttributeError:
            val = '%s_%s' % (self.first_name, self.last_name)
            self.__full_name = val
            return val
```

This is a lot of boilerplate code. It would be nice to be able to repeat the pattern like this:

```python
class Person:
    @cached_property
    def full_name(self):
        return '%s_%s' % (self.first_name, self.last_name)
```

I looked up some memoizing patterns, and this patten seems to be the standard way to do things.

```python
def cache_property_standard(fget):
    private_template = '_%%s__%s' % fget.__name__
    from functools import wraps
    @wraps(fget)
    def fget_memoized(self):
        attr_name = private_template % self.__class__.__name__
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fget(self))
        return getattr(self, attr_name)
    return property(fget_memoized)
```

This seems to be the most common pattern, but it’s really slow. This is where I’m offering my alternative implementation.

```python
class Person(namedtuple('BasePerson', ('first_name','last_name'))):
    def __repr__(self):
        c = self.__class__.__name__
        items = ['%s: %r' % i for i in zip(self._fields, self)]
        return '%s(%s)' % (c, ', '.join(items))

class SlowPerson(Person):
    @cache_property_standard
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

s = SlowPerson('Steve','Zelaznik')

In [94]: s.full_name
Out[94]: 'Steve Zelaznik'

In [95]: timeit s.full_name
1000000 loops, best of 3: 805 ns per loop
1000000 loops, best of 3: 790 ns per loop
1000000 loops, best of 3: 781 ns per loop
1000000 loops, best of 3: 789 ns per loop
```

We can do a lot better. This is the solution I’ve proposed for the same problem. Notice the order of magnitude difference in speed. It’s also more efficient with memory as well. It requires one new dictionary for each field that is memoized, as opposed to a new dictionary for each object that’s instantiated.

```python
def lightning_speed_cache(func):
    class Cache(dict):
        __slots__ = ()
        def __missing__(self, key):
            val = func(key)
            self[key] = val
            return val
    fget = Cache().__getitem__
    return property(fget, doc=func.__doc__)

class Sprinter(Person):
    __slots__ = ()
    @lightning_speed_cache
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])
t = Sprinter('Steve','Zelaznik')

t.full_name
Out[131]: 'Steve Zelaznik'

timeit t.full_name
10000000 loops, best of 3: 150 ns per loop
10000000 loops, best of 3: 152 ns per loop
10000000 loops, best of 3: 150 ns per loop
10000000 loops, best of 3: 150 ns per loop
```

This solution is as good as we’re going to get for anything that’s wrapped with a “property” decorator. **These are the same benchmarks that Python’s namedtuple attributes achieve.** It doesn’t The first thing we can do is start to use exceptions. Python is a “Better to ask forgiveness than permission,” language. This contrasts with lower level languages which follow a “Look before you leap,” approach. Here’s our first improvement. Baby steps, baby steps…

```python
def cache_property_use_exceptions(fget):
    private_template = '_%%s__%s' % fget.__name__
    from functools import wraps
    @wraps(fget)
    def fget_memoized(self):
        attr_name = private_template % self.__class__.__name__
        try:
            return getattr(self, attr_name)
        except AttributeError:
            val = fget(self)
            setattr(self, attr_name, val)
            return val
    return property(fget_memoized)

class MediumPerson(Person):
    @cache_property_use_exceptions
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

m = MediumPerson('Steve','Zelaznik')
m.full_name
Out[116]: 'Steve Zelaznik'
timeit m.full_name
1000000 loops, best of 3: 678 ns per loop
```

The big bottleneck is when we’re setting attributes by their private name. For those of you who don’t already know, **Python stores “private” attributes in an obscure way. They’re not really private, they’ve just garbled up the naming convention.** Not that different from trying to watch HBO as a kid without a subscription. You would still make out what’s going on if you’re willing to put in the effort. So “full_name” is officially a private attribute. That means the dictionary that stores the instance attributes for a person looks like this:

```python
m2 = MediumPerson('Steve','Zelaznik')
m2.full_name
Out[121]: 'Steve Zelaznik'
m2.__dict__
Out[122]: {'_MediumPerson__full_name': 'Steve Zelaznik'}
```

Getting rid of this will shave a lot of time off. Let’s take a look. Just to show that my computer didn’t suddenly speed up as I have been writing this post, I went back and benchmarked an earlier class instance:

```python
def cache_property_semipublic_names(fget):
    attr_name = '_%s' % fget.__name__
    from functools import wraps
    @wraps(fget)
    def fget_memoized(self):
        try:
            return getattr(self, attr_name)
        except AttributeError:
            val = fget(self)
            setattr(self, attr_name, val)
            return val
    return property(fget_memoized)


class SemiPublicAttributes(Person):
    @cache_property_semipublic_names
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

i = SemiPublicAttributes('Steve','Zelaznik')
i.full_name
Out[127]: 'Steve Zelaznik'

timeit i.full_name
1000000 loops, best of 3: 321 ns per loop
# Whoa!  Did my computer speed up suddenly?
# Let's run the old class instance just to be sure...
timeit m.full_name
1000000 loops, best of 3: 695 ns per loop
```

We’re almost there, but we can STILL shave off more than half the runtime we’re currently occupying. We’ve got two more steps to go. First, let’s get rid of the attribute getting. It’s far more efficient simply to store the caches inside a closure. This is also more memory efficient. We need one dictionary per field memoized, as opposed one dictionary per item. Hash tables waste space, so a field based storage system makes more sense in this case. In addition, it allows us to add attributes to classes where **\_\_slots\_\_ = ()**. The namedtuple in particular comes to mind.

```python
def caches_stored_per_field_not_instance(func):
    from functools import wraps
    cache = {}
    @property
    @wraps(func)
    def decorated(self):
        try:
            return cache[self]
        except KeyError:
            value = func(self)
            cache[self] = value
            return value
    return decorated

class Jogger(Person):
    @caches_stored_per_field_not_instance
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])

j = Jogger('Steve','Zelaznik')

j.full_name
Out[152]: 'Steve Zelaznik'

timeit j.full_name
1000000 loops, best of 3: 263 ns per loop
1000000 loops, best of 3: 266 ns per loop
1000000 loops, best of 3: 262 ns per loop
1000000 loops, best of 3: 266 ns per loop
```

One step left before we’re done. This is probably the most “Python magic” of any of the steps so far. **Function calls in Python are expensive. So whenever we are writing programming, it’s nice to be able to delegate those calls to builtin methods, which are written in C.** What we’re doing here is making a special subclass of a dictionary. When the item is missing, that’s when we go ahead and make the original function call. Again, Python is “ask forgiveness and not permission.” Then we instantiate this dictionary subclass. This subclass is a singleton. The clever thing that we do is we return the **\_\_getitem\_\_** method of the singleton. A property getter object only expects one argument “self”, and the **\_\_getitem\_\_** method only expects one key, so this works out perfectly.

```python
def lightning_speed_cache(func):
    class Cache(dict):
        __slots__ = ()
        def __missing__(self, key):
            val = func(key)
            self[key] = val
            return val
    fget = Cache().__getitem__
    return property(fget, doc=func.__doc__)

class Sprinter(Person):
    __slots__ = ()
    @lightning_speed_cache
    def full_name(self):
        return ' '.join([self.first_name, self.last_name])
t = Sprinter('Steve','Zelaznik')

t.full_name
Out[131]: 'Steve Zelaznik'

timeit t.full_name
10000000 loops, best of 3: 150 ns per loop
10000000 loops, best of 3: 152 ns per loop
10000000 loops, best of 3: 150 ns per loop
10000000 loops, best of 3: 150 ns per loop
```

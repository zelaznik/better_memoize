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
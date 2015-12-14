from __future__ import division, print_function
from __future__ import absolute_import

import sys, os
base_folder = os.path.split(__file__)[0]
sys.path.insert(0, base_folder)

import unittest
from .tests import *

if __name__ == '__main__':
    unittest.main()

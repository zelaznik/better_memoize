import sys, os
base_folder = os.path.split(__file__)[0]
os.chdir(base_folder)
from tests import *

if __name__ == '__main__':
    unittest.main()

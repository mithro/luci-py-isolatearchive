# appengine_config.py
from google.appengine.ext import vendor

# Add any libraries install in the "lib" folder.
import os.path
vendor.add(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib'))

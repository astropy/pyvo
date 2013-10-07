# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os

def get_package_data():
    paths = [ os.path.join('data', '*.xml') ]
    return { 'pyvo.registry.tests': paths}

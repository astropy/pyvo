# Licensed under a 3-clause BSD style license - see LICENSE.rst
import os


def get_package_data():
    paths = [
        os.path.join('data/query', '*.xml'),
        os.path.join('data/querydata', 'image.fits'),
        os.path.join('data/querydata', '*.xml'),
        os.path.join('data/querydata', '*.xml'),
        os.path.join('data/tap', '*.xml'),
        os.path.join('data/scs', '*.xml'),
        os.path.join('data/sia', '*.xml'),
        os.path.join('data/sla', '*.xml'),
        os.path.join('data/ssa', '*.xml'),
        os.path.join('data/datalink', '*.xml'),
        os.path.join('data', '*.xml'),
    ]
    return {'pyvo.dal.tests': paths}

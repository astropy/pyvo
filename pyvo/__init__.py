# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
PyVO is a package providing access to remote data and services of the 
Virtual observatory (VO) using Python.  

The pyvo module currently provides these main capabilities:
* find archives that provide particular data of a particular type and/or 
  relates to a particular topic
  *  regsearch()
* search an archive for datasets of a particular type
  *  imagesearch(), spectrumsearch()
* do simple searches on catalogs or databases
  *  conesearch(), linesearch()
* get information about an object via its name
  *  resolve(), object2pos(), object2sexapos()

Submodules provide additional functions and classes for greater control over
access to these services.

This module also exposes the exception classes raised by the above functions, 
of which DALAccessError is the root parent exception. 
"""

#this indicates whether or not we are in the pyvo's setup.py
try:
    _ASTROPY_SETUP_
except NameError:
    from sys import version_info
    if version_info[0] >= 3:
        import builtins
    else:
        import __builtin__ as builtins
    builtins._ASTROPY_SETUP_ = False
    del version_info

try:
    from .version import version as __version__
except ImportError:
    __version__ = '0.0.dev'
try:
    from .version import githash as __githash__
except ImportError:
    __githash__ = ''

if not _ASTROPY_SETUP_:

    import os
    from warnings import warn
    from astropy import config

    # add these here so we only need to cleanup the namespace at the end
    config_dir = None

    if not os.environ.get('ASTROPY_SKIP_CONFIG_UPDATE', False):
        config_dir = os.path.dirname(__file__)
        try:
            config.configuration.update_default_config(__package__, config_dir)
        except config.configuration.ConfigurationDefaultMissingError as e:
            wmsg = (e.args[0] + " Cannot install default profile. If you are "
                    "importing from source, this is expected.")
            warn(config.configuration.ConfigurationDefaultMissingWarning(wmsg))
            del e

    del os, warn, config_dir  # clean up namespace

# make sure we have astropy
import astropy.io.votable
from . import registry
from .dal import ssa, sia, sla, scs

from .registry import search as regsearch
from .dal import imagesearch, spectrumsearch, conesearch, linesearch
from .dal import DALAccessError, DALProtocolError, DALFormatError,   \
                 DALServiceError, DALQueryError

from .nameresolver import *

__all__ = [ "imagesearch", "spectrumsearch", "conesearch", "linesearch", 
            "regsearch", "resolve", "object2pos", "object2sexapos" ]

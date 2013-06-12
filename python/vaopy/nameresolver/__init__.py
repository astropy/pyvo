"""
This module provides access to astronomical name resolvers available
as web services.  A name resolver service, in its most basic form, is
one that can return a source's position in the sky given a recognized
name.  Such a service may also be able to provide other metadata as
well given a name.  

The default resolver, accessible via the lookup() function, defaults
to the CDS Sesame resolver. 
"""
# __all__ = [ "lookup" ]

import sys, os


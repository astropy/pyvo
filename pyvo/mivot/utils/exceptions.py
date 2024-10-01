"""
MIVOT Exceptions

3 exception classes
- AstropyVersionException that prevent to use the package
- MappingException if the annotation cannot be processed (e.g. no MIVOT block)
  but the VOtable parsing can continue
- MivotException in any other case (block the processing)
"""


class MivotException(Exception):
    """
    The annotation block is there but something went wrong with its processing
    """


class MappingException(Exception):
    """
    Exception raised if a Resource or MIVOT element can't be mapped for one of these reasons:
    - It doesn't match with any Resource/MIVOT element expected.
    - It matches with too many Resource/MIVOT elements than expected.
    This exception is trapped by the Viewer so that the processing can continue by ignoring
    the annotations
    """


class NoMatchingDMTypeError(Exception):
    """
    Exception thrown when some PyVO code misses MIVOT element:
    - When trying to build a SkyCoord while there is no position in the annotations
    - is mapped to a model unknown to the PyVO code.
    This exception is never caught by the mivot package.
    It must be handled by the calling code.
    """


class AstropyVersionException(Exception):
    """
    Exception raised if the version of astropy is not compatible with MIVOT.
    """

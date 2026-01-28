.. _pyvo-utils:

*******************************
pyVO utilities (``pyvo.utils``)
*******************************

This subpackage collects a few packages intended to help developing
and maintaining pyVO.  Almost all of this is not part of pyVO's public API and
may change at any time.   It is documented here for the convenience
of the maintainers and to help users when the effects of this code
becomes user-visible.

There is one piece of public API here:
`pyvo.utils.http.setup_user_agent`.  This can be used at the beginning
of a program to mark pyVO requests as comming from a specific client,
e.g.,::

  >>> from pyvo.utils.http import setup_user_agent
  >>> setup_user_agent(primary_component="clusterfinder")

Code doing bulk downloads (e.g., for mirroring or archiving) should use::

  >>> setup_user_agent(purpose="copy")

Finally, code running for validation or testing should do before making
such requests::

  >>> setup_user_agent(purpose="test")

See `Operational Identification of Software Components`_ for the
background of this.

.. _Operational Identification of Software Components: https://ivoa.net/documents/Notes/softid/


Reference/API
=============

.. automodapi:: pyvo.utils.http
.. automodapi:: pyvo.utils.xml.elements
    :no-inheritance-diagram:

.. toctree::
  :maxdepth: 1

  prototypes

.. doctest-skip-all

.. _vo-samp-example_hub:

Starting and Stopping a SAMP Hub Server
***************************************

There are several ways you can start up a SAMP hub:

Using an Existing Hub
=====================

You can start up another application that includes a hub, such as
`TOPCAT <https://www.star.bristol.ac.uk/mbt/topcat>`_, `SAO DS9 <http://ds9.si.edu/>`_, or
`Aladin Desktop <https://aladin.unistra.fr>`_.


Starting a Hub Programmatically
===============================

You can start up a hub by creating a `pyvo.samp.SAMPHubServer` instance and starting it,
either from the interactive Python prompt, or from a Python script::

    >>> from pyvo.samp import SAMPHubServer
    >>> hub = SAMPHubServer()
    >>> hub.start()

You can then stop the hub by calling::

    >>> hub.stop()

However, this method is generally not recommended for average users because it
does not work correctly when web SAMP clients try to connect. Instead, this
should be reserved for developers who want to embed a SAMP hub in a GUI, for
example. For more information, see :doc:`advanced_embed_samp_hub`.

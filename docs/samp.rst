.. _pyvo-samp:

******************
SAMP (`pyvo.samp`)
******************

SAMP, the Simple Application Messaging Protocol, lets you send and
receive tables, datasets, or points of interest between various clients
on a desktop.

While the main SAMP support still resides in astropy (it might be moved
over to pyvo in later versions), there are a few wrapper functions in
pyvo that make a few common SAMP tasks simpler or more robust.

Most importantly, pyvo lets you manage the SAMP connection in a context
manager, which means you will not have to remember to close your
connections to avoid ugly artefacts in the SAMP hub.

In addition, there are convenience functions for sending out data; in all
cases, you can pass a ``client_name`` to only send a message to the
specific client; a simple way to obtain client names is to inspect
TOPCAT's SAMP status if you use TOPCAT's built-in SAMP hub.  If, on the
other hand, you pass ``None`` as ``client_name`` (or omit the
parameter), you will send a broadcast.

Sending tables has the additional difficulty over sending other datasets
that you will have to make the table data accessible to the receiving
client.  The solution chosen by pyvo.samp at this time will only work if
the sending and receiving applications share a file system.  This seems
a reasonable expectation and saves a bit of a potential security headache.

Using pyvo.samp, sending an astropy table ``t`` to TOPCAT would look
like this::


  import pyvo

  with pyvo.samp.connection(client_name="pyvo magic") as conn:
    pyvo.samp.send_table_to(
      conn,
      t,
      name="my-results",
      client_name="topcat")

Reference/API
=============

.. automodapi:: pyvo.samp
  :no-inheritance-diagram:

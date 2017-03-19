.. _about-vo:

**********************************
About the Virtual Observatory (VO)
**********************************

The Virtual Observatory refers to a web of data, services,
technologies, and software that together create an environment for
conducting astronomical research on the network.  In particular, it
takes advantage of the wealth of data available on-line from
astronomical archives around the world.  This web is held together
through a set of open standards that give application common ways of
doing things, such as discovering and retrieving data.  

PyVO has been developed to understand the VO standards, allowing one
to interact with the VO using Python.  The initial focus of PyVO is on
data discovery and retrieval.  

It is typically not necessary to understand the details of the VO
standards or the underlying architecture of the VO in order to use PyVO
and access remote data; feel free to skip to the section on
:ref:`getting-started`. However, if you are completely new to the concepts of
the VO, or you encounter something you don't understand, you can read on
for an overview of VO services.  

.. _about-data-disc:

=========================
Data Discovery and Access
=========================

An archive can expose its data to VO by providing standard data access
services.  Each major class of astronomical data (images, spectra,
catalogs, etc.) have its own standard service protocol that allows
users to discover what data they have and to download it.   (The full
set of data access standards is often referred to as the VO's *Data
Access Layer* or DAL.)  These protocols are all similar, sharing a
largely common query interface, dataset metadata and query response.
Typically, queries are formed by a set of keyword=value parameters
appended onto a base URL.  Responses come in the form of a table, in
VOTable format (an XML format).   

There are two basic kinds of data access services, dataset services
and catalog services.  With a dataset service, one sends a query that
asks what datasets the archive has of a particular type and that match
the user's constraints.  Currently, PyVO supports querying two types
of dataset services: 

* `Simple Image Access (SIA) <http://www.ivoa.net/documents/SIA/>`_ -- 
  a service for finding images
* `Simple Spectral Access (SSA) <http://www.ivoa.net/documents/SSA/>`_
  -- a service for finding spectra

The response is a table where each row is describes a single
downloadable dataset (an image or a spectrum) available in the archive
that matches the input query.   The columns contain metadata
describing the dataset.  One of the columns gives the format of the
image (in the format of a MIME-type, such as "image/fits"), and
another provides a URL that can be used to download that image.
Typically, users will ask for data that over lap some region of the
sky; however, other constraints on the query (such as waveband) can be
set to further restrict the search results.  

With a catalog service, there is no dataset to download; instead one
is simply searching a catalog for its records.  Currently, PyVO
supports querying three types of catalog services: 

* `Simple Cone Search (SCS) <http://www.ivoa.net/documents/latest/ConeSearch.html>`_ 
  -- a service for positional searching a source catalog or an observation log.
* `Simple Line Access (SLAP) <http://www.ivoa.net/documents/SLAP/>`_ 
  -- a service for finding data about spectral lines, including their
  rest frequencies. 
* `Table Access Protocol (TAP) <http://www.ivoa.net/documents/TAP/>`_
  -- a service for flexible access to source catalogs using custom search
  parameters.

In all DAL search results, the archive can provide a rich set of
metadata that describe whatever it is that is being searched for.  The
DAL call for the columns for the results table to be tagged with
special labels that allow applications pick out particular kinds of
information.  These labels are separate from the column names, so
while different archives may give their right ascension columns
different names, they will share a common label, allowing an
application to properly interpret the table.  

====================
Discovering Archives
====================

If you don't know what archive or archives to search, you can discover
them by searching what is called a VO Registry.  This is a special
database containing descriptions of all archives, services, and other
resources known to the VO.  Queries to a registry are good for finding
services of a particular type (like image services or source catalog
services) or have data related to a particular science topic.  

The registry is important for finding new data that you might not be
aware exists or is available.  Imagine for example that you want to
find all image data available of your favorite source.  You would
first query the registry to find all image archives; you could
then systematically search all of those archive for images overlapping
the position of your source.  You might further downselect the list of
images based on the image metadata returned.  

.. _getting-started:

*************************
Getting Started With PyVO
*************************

PyVO lets your find and download astronomical data available from
archives that support standard VO service protocols.   The different
types of services that are supported will access different types of
data.  Nevertheless, these services have similar interfaces:

position and size parameters are named `pos` and `size` and accept instances of
`~astropy.coordinates.SkyCoord` or `~astropy.units.Quantity` with any appropiate
unit as well as scalar or sequences of floats in the default unit,
and results are returned as a `~astropy.io.votable.tree.VOTableFile` instance
encapsulated in a `~pyvo.dal.query.DALResults` subclass.

.. _getting-started-examples:

==============
A Few Examples
==============

As a quick overview, we start with an example that illustrates a
number of the key features of the PyVO's data discovery capabilities.
Here, we are interested in X-ray images of our favorite source,
supernova remnant, Cas A.  This examples finds out where X-ray images
can be found and saves references to those images to a simple CSV
file (a table with comma-separated values):

.. code-block:: python
    :linenos:

    from csv import writer
    import pyvo as vo
    from astropy.coordinates import SkyCoord

    # find archives with x-ray images
    archives = vo.regsearch(servicetype='image', waveband='x-ray')

    # position of my favorite source
    pos = SkyCoord.from_name('Cas A')

    # find images and list in a CSV file
    with open('cas-a.csv', 'w') as csvfile:
        csv = writer(csvfile)
        csv.writerow([
            "Archive", "title", "Image title", "format",
            "RA", "Dec", "URL"])
        for arch in archives:
            print "searching {0}...".format(arch.res_title)

            try:
                matches = arch.search(pos=pos, size=0.25)
            except vo.DALAccessError as ex:
                print "Trouble accessing {0} archive {1}".format(
                    arch.res_title, str(ex))
                continue

            print "...found {0} images".format(len(matches))
            for image in matches:
                csv.writerow([
                    arch.res_title, image.title,
                    str(image.ra), str(image.dec), image.format,
                    image.getdataurl()])

You might notice a few things in this example at the labeled line
numbers: 

2.  Most of the time, you can what you will need from the top ``pyvo``
    module; just import it.  

6.  The first step is to find archives that might have data were
    interested in.  To do this, we use the ``regsearch()`` function to search
    the VO registry for relevent archives given the type of data were
    interested (images) and our waveband of interest.  

9.  We look up the source position using
    the `~astropy.coordinates.SkyCoord.from_name` function.

17. The results we got back from our registry query behaves like a
    list--in particular, we can iterate through each of the archives that
    were returned.  

18. A registry query will return a variety of information about each
    service it finds, like its "res_title".  These are accessible as
    properties.  

21. Each item returned by the registry search represents a service at
    some archive that can return images.  (This is because we said
    ``servicetype='image'`` in line 5.)  We can find out what images the
    archive has via its ``search()`` function by giving it a "rectangular"
    region of the sky.  Our search region is a square that is 0.25 degrees
    on a side, centered on the position of Cas A.  

23. Sometimes, services are not up or working properly.   The
    ``DALAccessError`` exception is a base class for the various things
    that can go wrong when querying a service (including the registry).
    If one of our searches fail, we are noting it and going on to the next
    one.  PyVO provides more detailed exception classes if you want to
    distinguish betweeen different types of errors (like input errors).  

28. Calling ``len`` with the result object as argument tells the number of items
    returned in the results (the ``archives`` list has this property, too).
    Each represents an image that overlaps our search region.

29. As with the registry search results, we can iterate through the
    images that were matched.  

30  . For each image found, we will write out a row into our output
    list, copying data about both the image and the archive it came from.
    One of the important pieces of information we want about the image is
    where to get it:  the ``image.getdataurl()`` function returns a URL
    that can be used to retrieve the data.  

There are five different kind of VO search services supported by PyVO 
and they all work the same way:  

* you can execute search via a search function to which you pass in
  search constraints as keyword arguments,
* you get back a list of items that match your constraints which you
  can iterate through,
* catchable exceptions will be thrown if anything goes wrong, 
* each returned record will have properties holding metadata that
  describe that item, and 
* when searching for a dataset, the record will include a URL for
  downloading the dataset.  

Here's another example searching for images.  In this example, we want
to download cutout images for the NVSS survey for a list of sources.
We already know what archive we want to go to for images; that is, we
already know the NVSS image service URL we need to use.  In this
example, we show a slightly different way to pass search parameters as well as
how to download the images. 

.. code-block:: python
    :linenos:

    import pyvo as vo
    from astropy.coordinates import SkyCoord

    # obtain your list of positions from somewhere
    sourcenames = ["ngc4258", "m101", "m51"]
    mysources = {}
    for src in sourcenames:
        mysources[src] = SkyCoord.from_name(src)

    # create an output directory for cutouts
    import os
    if not os.path.exists("NVSSimages"):
        os.mkdir("NVSSimages")

    nvss = "http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&"

    for name, pos in mysources.items():
        query = vo.sia.SIAQuery(
            nvss, pos=(pos.ra.deg, pos.dec.deg), # degrees
            format='image/fits')
        results = query.execute()
        for image in results:
            print "Downloading {0}...".format(name)
            image.cachedataset(filename="NVSSimages/{0}.fits".format(name))

You might notice:

5.  We created a simple list of three sources, but you might load them in
    from a catalog our your own table.  

18. Instead of passing a `~astropy.coordinates.SkyCoord` instance to specify
    the search position, we instantiate a `~pyvo.dal.sia.SIAQuery` instance with
    a tuple of icrs decimal degrees as the pos parameter.

20. We'll ask only for FITS images.

21. We iterate through sources in our list, setting the query
    position to that of the source and executing it.  

24. We can download each image to a directory via the
    ``cachedataset()`` function.  

.. _getting-started-pyvo:

===================================
What's available in the pyvo Module
===================================

The :py:mod:`pyvo` module is organized such that most of what might need is
available at the top of the module; that is, simply importing this
module is sufficient for most uses:

.. code-block:: python

   import pyvo as vo

The module's search capabilities are available through top-level
functions.  Four of the functions represent what's referred to as the
*VO Data Access Layer* (DAL):

* :py:func:`~pyvo.conesearch` -- search a remote catalog for data
  about sources or observations located within some radius of a given
  position.  
* :py:func:`~pyvo.imagesearch` -- search an image archive for images
  that overlap a region of the sky
* :py:func:`~pyvo.spectrumsearch` -- search an image archive for spectra
  observed within some radius of a given position.
* :py:func:`~pyvo.linesearch` -- search a remote spectral line database
  for data about emission lines.  
* :py:func:`~pyvo.tablesearch` -- search a remote database for generic data.

We'll show you how to use these in the next chapter,
:ref:`data-access`.  

All the DAL search functions require a URL that represents the
location of the service as its first argument.  If you don't know the URL,
you can look it up through a search of the VO Registry:

* :py:func:`~pyvo.regsearch` -- search the VO Registry to find
  services and archives.  

The Registry is discussed more in a subsequent chapter,
:ref:`registry-access`. 

The :py:mod:`pyvo` module also makes available a set of exceptions
that are thrown by the above functions when things go wrong.  These
are described in the :ref:`data-access` chapter under the section,
:ref:`data-access-exceptions`: 

============================================  ===================================================================================
:py:class:`~pyvo.dal.query.DALAccessError`    a base class for all failures while accessing a DAL service
:py:class:`~pyvo.dal.query.DALProtocolError`  a base exception indicating that a DAL service responded in an erroneous way.  
:py:class:`~pyvo.dal.query.DALFormatError`    an exception indicating that a DAL response contains fatal format errors.
:py:class:`~pyvo.dal.query.DALServiceError`   an exception indicating a failure communicating with a DAL service.
:py:class:`~pyvo.dal.query.DALQueryError`     an exception indicating an error by a working DAL service while processing a query.  
============================================  ===================================================================================

.. raw:: html

   <br>

Finally, we will see in the next chapter that additional features are
available in sub-modules, each associated with a different type of
services.  This includes:

===========================  ====================================================
:py:mod:`pyvo.dal.sia`       Classes for accessing image services
:py:mod:`pyvo.dal.ssa`       Classes for accessing spectrum services
:py:mod:`pyvo.dal.scs`       Classes for accessing catalog services
:py:mod:`pyvo.dal.sla`       Classes for accessing spectral line catalog services
:py:mod:`pyvo.dal.tap`       Classes for accessing table access services
:py:mod:`pyvo.registry`      Classes for accessing the registry
===========================  ====================================================

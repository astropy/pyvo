
************************
Data Discovery With PyVO
************************

PyVO lets your find and download astronomical data available from
archives that support standard VO service protocols.   The different
types of services that are supported will access different types of
data.  Nevertheless, these services have similar interfaces:  Queries
are formed via a set of name=value parameters, and results are
returned as a table in VOTable format.   

===============================
Getting Started: A Few Examples
===============================

As a quick overview, we start with an example that illustrates a
number of the key features of the PyVO's data discovery capabilities.
Here, we are interested in X-ray images of our favorite source,
supernova remnant, Cas A.  This examples finds out where X-ray images
can be found and saves references to those images to a simple CSV
file (a table with comma-separated values):

.. code-block:: python
   :linenos:

   import pyvo as vo

   # find archives with x-ray images
   archives = vo.regsearch(servicetype='image', waveband='xray')
                           
   # position of my favorite source
   pos = vo.object2pos('Cas A')

   # find images and list in a CSV file
   with open('cas-a.csv', 'w') as csv:
       print >> csv, "Archive short name,Archive title,Image", \
                     "title,format,RA,Dec,URL"
       for arch in archives:
           print "searching %s..." % arch.shortname

           try:
                matches = arch.search(pos=pos, size=0.25)
           except vo.DALAccessError, ex:
                print "Trouble accessing %s archive (%s)"\
                      % (arch.shortname, str(ex))
                continue

           print "...found %d images" % matches.nrecs
           for image in matches:
                print >> csv, ','.join( 
                    (arch.shortname, arch.title, image.title, 
                     str(image.ra), str(image.dec), image.format,
                     image.getdataurl()) )

You might notice a few things in this example at the labeled line
numbers: 

1.  Most of the time, you can what you will need from the top ``pyvo``
    module; just import it.  

4.  The first step is to find archives that might have data were
    interested in.  To do this, we use the ``regsearch()`` function to search
    the VO registry for relevent archives given the type of data were
    interested (images) and our waveband of interest.  

7.  A little later, we'll ask each archive what data they have at the
    position of our source, but for now we can look up that position using
    the ``object2pos()`` function.  

13. The results we got back from our registry query behaves like a
    list--in particular, we can iterate through each of the archives that
    were returned.  

14. A registry query will return a variety of information about each
    service it finds, like its "short name".  These are accessible as
    properties.  

17. Each item returned by the registry search represents a service at
    some archive that can return images.  (This is because we said
    ``servicetype='image'`` in line 5.)  We can find out what images the
    archive has via its ``search()`` function by giving it a "rectangular"
    region of the sky.  Our search region is a square that is 0.25 degrees
    on a side, centered on the position of Cas A.  

18. Sometimes, services are not up or working properly.   The
    ``DALAccessError`` exception is a base class for the various things
    that can go wrong when querying a service (including the registry).
    If one of our searches fail, we are noting it and going on to the next
    one.  PyVO provides more detailed exception classes if you want to
    distinguish betweeen different types of errors (like input errors).  

23. The ``nrecs`` property tells the number of items returned in the
    results (the ``archives`` list has this property, too).  Each
    represents an image that overlaps our search region.  ``len(matches)``
    returns the same number.  

24. As with the registry search results, we can iterate through the
    images that were matched.  

25. For each image found, we will write out a row into our output
    list, copying data about both the image and the archive it came from.
    One of the important pieces of information we want about the image is
    where to get it:  the ``image.getdataurl()`` function returns a URL
    that can be used to retrieve the data.  

There are five different kind of VO search services supported by PyVO 
and they all work the same way:  

* you can execute search via a search function to which you pass in
  search constraints as keyword=value arguments,
* you get back a list of items that match your constraints which you
  can iterate through,
* catchable exceptions will be thrown if anything goes wrong, 
* each returned record will have properties that describe that item,
  and 
* when searching for a dataset, the record will include a URL for
  downloading the dataset.  

Here's another example searching for images.  In this example, we want
to download cutout images for the NVSS survey for a list of sources.
We already know what archive we want to go to for images; that is, we
already know the NVSS image service URL we need to use.  In this
example, we show a slightly different way to submit queries as well as
how to download the images. 

.. code-block:: python
   :linenos:

   import pyvo as vo

   # obtain your list of positions from somewhere
   sourcenames = ["ngc4258", "m101", "m51"]
   mysources = {}
   for src in sourcenames:
       mysources[src] = vo.object2pos(src)

   # create an output directory for cutouts
   import os
   if not os.path.exists("NVSSimages"):
       os.mkdir("NVSSimages")

   # setup a query object for NVSS
   nvss = "http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&"
   query = vo.sia.SIAQuery(nvss)
   query.size = 0.2                 # degrees
   query.format = 'image/fits'

   for name, pos in mysources.items():
       query.pos = pos
       results=query.execute()
       for image in results:
           print "Downloading %s..." % name
           image.cachedataset(filename="NVSSimages/%s.fits" % name)

You might notice:

4.  We created a simple list of three sources, but you might load them in
    from a catalog our your own table.  

16. Instead of using a function to send a query, we will create a
    query object by wrapping it around the service URL.  Its properties
    are constraints on the queries we want to send.  We can reuse this
    instance changing only the parameters that need changing along the
    way.  

18. We'll ask only for FITS images.

20. We iterate through sources in our list, setting the query
    position to that of the source and executing it.  

25. We can download each image to a directory via the
    ``cachedataset()`` function.  


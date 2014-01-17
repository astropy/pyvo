
.. _resolve-names:

*****************************************************
Object Name Resolution: Finding Positions of Sources
*****************************************************

Sometimes, you would like find data of or near well-known objects in
the sky--that is, for objects that you know by name.  The 
:ref:`simple data access services <data-access>` tend to find data by
position.  Thus, looking up the position of an object by its name can
be handy.  The :py:mod:`pyvo.nameresolver` module supports this.  

.. note:: the Astropy package provides object-to-position resolution,
          so future versions of PyVO will migrate to use the Astropy
          implementation.  Thus, *the* :py:mod:`pyvo.nameresolver`
          *module will be deprecated*.  Here's how you can use Astropy
          (as of v0.3) to resolve an object name to an ICRS position,
          suitable for use with PyVO data access services:

          >>> from astropy.coordinates.builtin_systems import ICRSCoordinates as ICRS
          >>> m42 = ICRS.from_name("M42")
          >>> pos = (m42.ra.degrees, m42.dec.degrees)
          >>> pos
          (83.82208, -5.3911100000000003)
          >>> nvss = "http://skyview.gsfc.nasa.gov/cgi-bin/vo/sia.pl?survey=nvss&"
          >>> cutouts = pyvo.imagesearch(nvss, pos=pos, size=0.2, format="image/fits")

          Direct support for Astropy coordinate types by the data
          access services is also planned for future versions of
          PyVO.  

          The support for the CDS Sesame Service within the 
          :py:mod:`pyvo.nameresolver.sesame` will be evolved
          appropriately for accessing other source information
          available from the service.  

The primary function for resolving names, 
:py:func:`~pyvo.nameresolver.sesame.object2pos`, is available in top
:py:mod:`pyvo` module:

>>> import pyvo as vo
>>> vo.object2pos('M81')
(148.88822108299999, 69.065294722000004)
>>> vo.object2pos(['M81', 'M82'])
[(148.88822107999999, 69.065294719999997), (148.96845833, 69.67970278)]

:py:func:`~pyvo.nameresolver.sesame.object2pos` function returns an
ICRS right ascension and declination as required by VO services.  This
implementation uses the 
`CDS Sesame web service <http://cds.u-strasbg.fr/cgi-bin/Sesame>`_ 
to look up object names.  As you can see from the example above, the
function can take either a single name or a list to resolve several
names in a single call to the Sesame service.

The :py:func:`~pyvo.nameresolver.sesame.resolve` function is a more
generic function that returns all of the information about the object
available from the Sesame service in an 
:py:class:`~pyvo.nameresolver.sesame.ObjectData` container.  This can
be useful for obtaining other names that the object is known by.
Here's an example where we figure out what M81's associated IRAS names
are.  

>>> m81data = vo.resolve('m81', include="aliases")
>>> len(m81data.aliases) # aliases contains the list of other names
69
>>> [alias for alias in m81data.aliases if "IRAS" in alias]
['IRAS F09517+6954', 'IRAS 09517+6954']

The Sesame service is hosted at two locations: one in Strasbourg,
France and one in Cambridge, MA in the United States.  The 
:py:mod:`~pyvo.nameresolver.sesame` module and functions allow you to
control which service is used.  (Note that they don't always return
identical results.)  See the :py:mod:`pyvo.nameresolver.sesame`
reference documentation for more details.  

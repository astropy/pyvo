#! /usr/bin/env python
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

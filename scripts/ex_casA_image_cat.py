#! /usr/bin/env python
from __future__ import print_function
import pyvo as vo

# find archives with x-ray images
archives = vo.regsearch(servicetype='image', waveband='xray')

# position of my favorite source
pos = vo.object2pos('Cas A')

# find images and list in a file
with open('cas-a.csv', 'w') as csv:
    print("Archive short name,Archive title,Image"
          "title,RA,Dec,format,URL", file=csv)
    for arch in archives:
        print("searching %s..." % arch.shortname)
        try:
            matches = arch.search(pos=pos, size=0.25)
        except vo.DALAccessError as ex:
            print("Trouble accessing %s archive (%s)"
                  % (arch.shortname, str(ex)))
            continue
        print("...found %d images" % matches.nrecs)
        for image in matches:
            print(','.join(
             (arch.shortname, arch.title, image.title,
              str(image.ra), str(image.dec), image.format,
              image.getdataurl())), file=csv)

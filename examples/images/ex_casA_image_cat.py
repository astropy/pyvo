#! /usr/bin/env python
import pyvo as vo
from astropy.coordinates import SkyCoord

import warnings
warnings.filterwarnings('ignore', module="astropy.io.votable.*")

# find archives with x-ray images
archives = vo.regsearch(servicetype='image', waveband='x-ray')
# position of my favorite source
pos = SkyCoord.from_name('Cas A')

# find images and list in a file
with open('cas-a.csv', 'w') as csv:
    print("Archive short name,Archive title,Image"
          "title,RA,Dec,format,URL", file=csv)
    for arch in archives:
        print("searching {}...".format(arch.short_name))
        try:
            matches = arch.search(pos=pos, size=0.25)
        except vo.DALAccessError as ex:
            print("Trouble accessing {} archive ({})".format(
                  arch.short_name, str(ex)))
            continue
        print("...found {} images.".format(len(matches)))
        for image in matches:
            print(','.join(
             (arch.short_name, arch.res_title, image.title,
              str(image.pos), image.format,
              image.getdataurl())), file=csv)

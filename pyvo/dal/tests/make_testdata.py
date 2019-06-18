from pathlib import Path

import numpy as np

from astropy.table import Table
from astropy.io.votable.tree import VOTableFile, Info
from astropy.io.fits import ImageHDU


def _votablefile():
    table = Table([
        [23, 42, 1337],
        [b'Illuminatus', b"Don't panic, and always carry a towel", b'Elite']
    ], names=('1', '2'))

    table['1'].meta['ucd'] = 'foo;bar'

    table['2'].meta['utype'] = 'foobar'

    votablefile = VOTableFile.from_table(table)

    info = Info(name='QUERY_STATUS', value='OK')
    info.content = 'OK'
    votablefile.resources[0].infos.append(info)

    return votablefile


def votablefile():
    votablefile = _votablefile()
    return votablefile


def votablefile_errorstatus():
    votablefile = _votablefile()

    info = Info(name='QUERY_STATUS', value='ERROR')
    info.content = 'ERROR'
    votablefile.resources[0].infos[0] = info

    return votablefile


def votablefile_missingtable():
    votablefile = _votablefile()
    del votablefile.resources[0].tables[0]
    return votablefile


def votablefile_missingresource():
    votablefile = _votablefile()
    del votablefile.resources[0]
    return votablefile


def votablefile_missingcolumns():
    votablefile = _votablefile()
    del votablefile.resources[0].tables[0].fields[:]
    return votablefile


def votablefile_firstresource():
    votablefile = _votablefile()
    votablefile.resources[0]._type = ''
    return votablefile


def votablefile_tableinfo():
    votablefile = _votablefile()
    votablefile.resources[0].tables[0].infos[:] = (
        votablefile.resources[0].infos[:])

    del votablefile.resources[0].infos[:]

    return votablefile


def votablefile_rootinfo():
    votablefile = _votablefile()
    votablefile.infos[:] = (
        votablefile.resources[0].infos[:])

    del votablefile.resources[0].infos[:]

    return votablefile


def votablefile_dataset():
    table = Table([
        [
            'image/fits',
            'application/x-votable+xml',
            'application/x-votable+xml;content=datalink'
        ],
        [
            b'http://example.com/querydata/image.fits',
            b'http://example.com/querydata/votable.xml',
            b'http://example.com/querydata/votable-datalink.xml'
        ]
    ], names=('dataformat', 'dataurl'))

    table['dataformat'].meta['ucd'] = 'meta.code.mime'
    table['dataurl'].meta['utype'] = 'Access.Reference'
    table['dataurl'].meta['ucd'] = 'meta.dataset;meta.ref.url'

    votablefile = VOTableFile.from_table(table)

    info = Info(name='QUERY_STATUS', value='OK')
    info.content = 'OK'
    votablefile.resources[0].infos.append(info)

    return votablefile


def dataset_fits():
    hdu = ImageHDU(np.random.random((256, 256)))
    return hdu


def main():
    dirname = Path(__file__).parent / 'data'

    votablefile().to_xml(
        str(dirname / 'query/basic.xml'), tabledata_format='tabledata')

    votablefile_errorstatus().to_xml(
        str(dirname / 'query/errorstatus.xml'), tabledata_format='tabledata')

    votablefile_missingtable().to_xml(
        str(dirname / 'query/missingtable.xml'), tabledata_format='tabledata')

    votablefile_missingresource().to_xml(
        str(dirname / 'query/missingresource.xml'),
        tabledata_format='tabledata')

    votablefile_missingcolumns().to_xml(
        str(dirname / 'query/missingcolumns.xml'),
        tabledata_format='tabledata')

    votablefile_firstresource().to_xml(
        str(dirname / 'query/firstresource.xml'), tabledata_format='tabledata')

    votablefile_tableinfo().to_xml(
        str(dirname / 'query/tableinfo.xml'), tabledata_format='tabledata')

    votablefile_rootinfo().to_xml(
        str(dirname / 'query/rootinfo.xml'), tabledata_format='tabledata')

    votablefile_dataset().to_xml(
        str(dirname / 'query/dataset.xml'), tabledata_format='tabledata')

    dataset_fits().writeto(
        str(dirname / 'querydata/image.fits'), overwrite=True)


if __name__ == '__main__':
    main()

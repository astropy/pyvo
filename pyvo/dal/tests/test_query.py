#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.query
"""
from functools import partial

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from os import listdir

import pytest

import numpy as np

from pyvo.dal.query import DALService, DALQuery, DALResults, Record
from pyvo.dal.exceptions import DALServiceError, DALQueryError, DALFormatError
from pyvo.version import version
from pyvo.utils.compat import ASTROPY_LT_4_1

from astropy.table import Table
from astropy.io.votable.tree import VOTableFile, Table as VOTable
from astropy.io.fits import HDUList

from astropy.utils.data import get_pkg_data_contents

get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')


@pytest.fixture()
def register_mocks(mocker):
    with ExitStack() as stack:
        matchers = [
            stack.enter_context(mocker.register_uri(
                'GET', '//example.com/query/basic',
                content=get_pkg_data_contents('data/query/basic.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/missingtable',
                content=get_pkg_data_contents('data/query/missingtable.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/missingresource',
                content=get_pkg_data_contents('data/query/missingresource.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/missingcolumns',
                content=get_pkg_data_contents('data/query/missingcolumns.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/firstresource',
                content=get_pkg_data_contents('data/query/firstresource.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/rootinfo',
                content=get_pkg_data_contents('data/query/rootinfo.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/tableinfo',
                content=get_pkg_data_contents('data/query/tableinfo.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/dataset',
                content=get_pkg_data_contents('data/query/dataset.xml')
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/querydata/image.fits',
                content=get_pkg_data_contents('data/querydata/image.fits')
            )),
            # mocker.register_uri(
            #     'GET', 'http://example.com/querydata/votable.xml',
            #     content=get_pkg_data_contents('data/querydata/votable.xml')
            # ),
            # mocker.register_uri(
            #     'GET', 'http://example.com/querydata/votable-datalink.xml',
            #     content=get_pkg_data_contents('data/querydata/votable-datalink.xml')
            # ),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/nonexistant',
                text='Not Found', status_code=404
            )),
            stack.enter_context(mocker.register_uri(
                'GET', '//example.com/query/errornous',
                text='Error', status_code=500
            )),
            stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/query/errorstatus',
                content=get_pkg_data_contents('data/query/errorstatus.xml')
            )),
        ]

        def verbosetest_callback(request, context):
            assert 'VERBOSE' in request.qs and '1' in request.qs['VERBOSE']
            return get_pkg_data_contents('data/query/basic.xml')

        matchers.append(stack.enter_context(mocker.register_uri(
            'GET', 'http://example.com/query/verbosetest',
            content=verbosetest_callback
        )))

        def useragent_callback(request, context):
            assert 'User-Agent' in request.headers
            assert request.headers['User-Agent'] == 'python-pyvo/{}'.format(
                version)
            return get_pkg_data_contents('data/query/basic.xml')

        matchers.append(stack.enter_context(mocker.register_uri(
            'GET', 'http://example.com/query/useragent',
            content=useragent_callback
        )))

        yield matchers


def _test_results(results):
    """Regression test result columns for correctnes"""
    assert len(results) == 3

    assert results['1', 0] == 23
    assert results['1', 1] == 42
    assert results['1', 2] == 1337

    truth = b'Illuminatus' if ASTROPY_LT_4_1 else 'Illuminatus'
    assert results['2', 0] == truth
    truth = b"Don't panic, and always carry a towel" \
        if ASTROPY_LT_4_1 else "Don't panic, and always carry a towel"
    assert results['2', 1] == truth
    truth = b'Elite' if ASTROPY_LT_4_1 else 'Elite'
    assert results['2', 2] == truth


def _test_records(records):
    """ Regression test dal records for correctness"""
    assert len(records) == 3

    assert all([isinstance(record, Record) for record in records])

    assert records[0]['1'] == 23

    truth = b'Illuminatus' if ASTROPY_LT_4_1 else 'Illuminatus'
    assert records[0]['2'] == truth

    assert records[1]['1'] == 42
    truth = b"Don't panic, and always carry a towel" \
        if ASTROPY_LT_4_1 else "Don't panic, and always carry a towel"
    assert records[1]['2'] == truth

    assert records[2]['1'] == 1337
    truth = b'Elite' if ASTROPY_LT_4_1 else 'Elite'
    assert records[2]['2'] == truth


@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
@pytest.mark.usefixtures('register_mocks')
class TestDALService:
    def test_init(self):
        """Test if baseurl if passed correctly"""
        service = DALService('http://example.com/query/basic')
        assert service.baseurl == 'http://example.com/query/basic'

    def test_search(self):
        """
        Test (in conjunction with mocker) that parameters arrive serverside,
        while also ensuring data consistency
        """
        service = DALService('http://example.com/query/verbosetest')
        dalresults = service.search(VERBOSE=1)

        _test_results(dalresults)
        _test_records(dalresults)

    def test_useragent(self):
        service = DALService('http://example.com/query/useragent')
        service.search()

    def test_http_exception_404(self):
        service = DALService('http://example.com/query/nonexistant')

        try:
            service.search()
        except DALServiceError as exc:
            assert exc.code == 404
        else:
            assert False

    def test_http_exception_500(self):
        service = DALService('http://example.com/query/errornous')

        try:
            service.search()
        except DALServiceError as exc:
            assert exc.code == 500
        else:
            assert False

    def test_query_exception(self):
        service = DALService('http://example.com/query/errorstatus')

        with pytest.raises(DALQueryError):
            service.search()

    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W53")
    def test_format_exception(self):
        with pytest.raises(DALFormatError):
            service = DALService('http://example.com/query/missingtable')
            service.search()

        with pytest.raises(DALFormatError):
            service = DALService('http://example.com/query/missingresource')
            service.search()

        with pytest.raises(DALFormatError):
            service = DALService('http://example.com/query/missingcolumns')
            service.search()


@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
@pytest.mark.usefixtures('register_mocks')
class TestDALQuery:
    def test_url(self):
        queries = (
            DALQuery('http://example.com/query/basic'),
            DALQuery(b'http://example.com/query/basic'),
        )

        assert all(
            q.queryurl == 'http://example.com/query/basic' for q in queries
        )

    def test_params(self):
        query = DALQuery(
            'http://example.com/query/basic', verbose=1, foo='BAR')

        assert query['VERBOSE'] == 1
        assert query['FOO'] == 'BAR'

    def test_execute(self):
        query = DALQuery('http://example.com/query/basic')
        dalresults = query.execute()

        assert dalresults.queryurl == 'http://example.com/query/basic'

        _test_results(dalresults)
        _test_records(dalresults)

    def test_execute_raw(self):
        query = DALQuery('http://example.com/query/basic')
        raw = query.execute_raw()

        assert raw.startswith(b'<?xml')
        assert raw.strip().endswith(b'</VOTABLE>')


@pytest.mark.filterwarnings('ignore::astropy.io.votable.exceptions.W03')
@pytest.mark.filterwarnings('ignore::astropy.io.votable.exceptions.W06')
@pytest.mark.usefixtures('register_mocks')
class TestDALResults:
    def test_init(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        assert dalresults.queryurl == 'http://example.com/query/basic'
        assert isinstance(dalresults.votable, VOTableFile)
        assert isinstance(dalresults.resultstable, VOTable)

        assert dalresults.fieldnames == ('1', '2')
        assert (
            dalresults.fielddescs[0].name, dalresults.fielddescs[1].name
        ) == ('1', '2')

        assert dalresults.status == ('OK', 'OK')

    def test_from_result_url(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')
        assert dalresults.status == ('OK', 'OK')

    def test_init_errorstatus(self):
        with pytest.raises(DALQueryError):
            DALResults.from_result_url('http://example.com/query/errorstatus')

    def test_init_missingtable(self):
        with pytest.raises(DALFormatError):
            DALResults.from_result_url('http://example.com/query/missingtable')

    @pytest.mark.filterwarnings('ignore::astropy.io.votable.exceptions.W53')
    def test_init_missingresource(self):
        with pytest.raises(DALFormatError):
            DALResults.from_result_url(
                'http://example.com/query/missingresource')

    @pytest.mark.xfail()
    def test_init_missingcolumns(self):
        with pytest.raises(DALFormatError):
            DALResults.from_result_url(
                'http://example.com/query/missingcolumns')

    def test_init_firstresource(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/firstresource')
        assert dalresults.status == ('OK', 'OK')

    def test_init_tableinfo(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/tableinfo')
        assert dalresults.status == ('OK', 'OK')

    def test_init_rootinfo(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/rootinfo')
        assert dalresults.status == ('OK', 'OK')

    @pytest.mark.xfail(reason="ID lookup does not work")
    def test_repr(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        assert repr(dalresults) == repr(dalresults.table())

    def test_iter(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        records = list(iter(dalresults))

        _test_results(dalresults)
        _test_records(records)

    def test_dataconsistency(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        assert isinstance(dalresults['1'], np.ndarray)
        assert isinstance(dalresults['2'], np.ndarray)

        _test_results(dalresults)
        _test_records(dalresults)

    @pytest.mark.xfail(reason="ID lookup does not work")
    def test_table_conversion(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        assert isinstance(dalresults.table(), Table)
        assert len(dalresults) == len(dalresults.table())

    def test_id_over_name(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        assert isinstance(dalresults['_1'], np.ndarray)
        assert isinstance(dalresults['_2'], np.ndarray)

        table = dalresults.to_table()
        with pytest.raises(KeyError):
            assert table['_1']
        with pytest.raises(KeyError):
            assert table['_2']

    def test_nosuchcolumn(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        with pytest.raises(KeyError):
            dalresults['nosuchcolumn']

        with pytest.raises(KeyError):
            dalresults.getdesc('nosuchcolumn')

    def test_columnaliases(self):
        dalresults = DALResults.from_result_url(
            'http://example.com/query/basic')

        assert dalresults.fieldname_with_ucd('foo') == '1'
        assert dalresults.fieldname_with_ucd('bar') == '1'

        assert dalresults.fieldname_with_utype('foobar') == '2'

        assert dalresults.fieldname_with_ucd('baz') is None
        assert dalresults.fieldname_with_utype('foobaz') is None


@pytest.mark.filterwarnings('ignore::astropy.io.votable.exceptions.W03')
@pytest.mark.filterwarnings('ignore::astropy.io.votable.exceptions.W06')
@pytest.mark.usefixtures('register_mocks')
class TestRecord:
    def test_itemaccess(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]

        assert record['1'] == 23
        truth = b'Illuminatus' if ASTROPY_LT_4_1 else 'Illuminatus'
        assert record['2'] == truth

        assert record['_1'] == 23
        assert record['_2'] == truth

    def test_nosuchcolumn(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]

        with pytest.raises(KeyError):
            record['nosuchcolumn']

    def test_iter(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]

        record = list(iter(record))

        assert record[0] == '1'
        assert record[1] == '2'

    def test_len(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]

        assert len(record) == 2

    def test_repr(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]
        truth = b'Illuminatus' if ASTROPY_LT_4_1 else 'Illuminatus'
        assert repr(record) == repr((23, truth))

    def test_get(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]

        assert record.get('2', decode=True) == 'Illuminatus'

    def test_columnaliases(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]

        assert record.getbyucd('foo') == 23
        assert record.getbyucd('bar') == 23

        truth = b'Illuminatus' if ASTROPY_LT_4_1 else 'Illuminatus'
        assert record.getbyutype('foobar') == truth

        record.getbyucd('baz') is None
        record.getbyutype('foobaz') is None

    def test_datasets(self):
        records = DALResults.from_result_url(
            'http://example.com/query/dataset')

        record = records[0]
        assert record.getdataurl() == 'http://example.com/querydata/image.fits'
        dataset = record.getdataset()
        HDUList.fromstring(dataset.read())

    def test_nodataset(self):
        record = DALResults.from_result_url(
            'http://example.com/query/basic')[0]

        assert record.getdataurl() is None

        with pytest.raises(KeyError):
            record.getdataset().read()

    def test_cachedataset(self, tmpdir):
        tmpdir = str(tmpdir)

        record = DALResults.from_result_url(
            'http://example.com/query/dataset')[0]

        record.cachedataset(dir=tmpdir)

        assert "dataset.dat" in listdir(tmpdir)


class TestUpload:
    pass

# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.tap
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

from functools import partial

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

import re
from io import BytesIO

from six.moves.urllib.parse import parse_qsl
import pytest
import requests_mock

from pyvo.dal.tap import escape, search, TAPService
from pyvo.io.uws import JobFile
from pyvo.io.uws.tree import Parameter, Result

from astropy.time import Time, TimeDelta

from astropy.utils.data import get_pkg_data_contents

get_pkg_data_contents = partial(
    get_pkg_data_contents, package=__package__, encoding='binary')

job_re_path_full = re.compile('^http://example.com/tap/async/([0-9]+)')
job_re_path = re.compile('^/tap/async/([0-9]+)')

job_re_phase_full = re.compile('^http://example.com/tap/async/([0-9]+)/phase')

job_re_result_full = re.compile(
    '^http://example.com/tap/async/([0-9]+)/results/result')


def _test_image_results(results):
    assert len(results) == 10


@pytest.fixture()
def sync(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/tap/obscore-image.xml')

    with mocker.register_uri(
        'POST', 'http://example.com/tap/sync', content=callback
    ) as matcher:
        yield matcher


@pytest.fixture()
def async(mocker):
    class Callback(object):
        def __init__(self):
            self._jobs = dict()

        def create(self, request, context):
            newid = max(list(self._jobs.keys()) or [0]) + 1
            data = dict(parse_qsl(request.body))

            job = JobFile()
            job.version = "1.1"
            job.jobid = newid
            job.phase = 'PENDING'
            job.quote = Time.now() + TimeDelta(1, format='sec')
            job.creationtime = Time.now()
            job.executionduration = TimeDelta(3600, format='sec')
            job.destruction = Time.now() + TimeDelta(3600, format='sec')

            for key, value in data.items():
                param = Parameter(id=key.lower())
                param.content = value
                job.parameters.append(param)

            context.status_code = 303
            context.reason = 'See other'
            context.headers['Location'] = (
                'http://example.com/tap/async/{}'.format(newid))

            self._jobs[newid] = job

        def job(self, request, context):
            jobid = int(job_re_path.match(request.path).group(1))

            if request.method == 'GET':
                job = self._jobs[jobid]
                io = BytesIO()
                job.to_xml(io)
                return io.getvalue()
            elif request.method == 'POST':
                data = dict(parse_qsl(request.body))
                action = data.get('ACTION')

                if action == 'DELETE':
                    del self._jobs[jobid]

        def phase(self, request, context):
            jobid = int(job_re_path.match(request.path).group(1))

            if request.method == 'GET':
                phase = self._jobs[jobid].phase
                return phase
            elif request.method == 'POST':
                newphase = request.body.split('=')[-1]
                job = self._jobs[jobid]
                result = get_pkg_data_contents('data/tap/obscore-image.xml')

                if newphase == 'RUN':
                    newphase = 'COMPLETED'
                    result = Result(**{
                        'id': 'result',
                        'size': len(result),
                        'mime-type': 'application/x-votable+xml',
                        'xlink:href': (
                            'http://example.com/tap/async/{}/results/result'
                        ).format(jobid)
                    })

                    try:
                        job.results[0] = result
                    except (IndexError, TypeError):
                        job.results.append(result)

                job.phase = newphase

        def result(self, request, context):
            # jobid = int(job_re_path.match(request.path)[1])
            return get_pkg_data_contents('data/tap/obscore-image.xml')

    callback = Callback()

    with ExitStack() as stack:
        matchers = {
            'create': stack.enter_context(mocker.register_uri(
                'POST', 'http://example.com/tap/async',
                content=callback.create
            )),
            'job': stack.enter_context(mocker.register_uri(
                requests_mock.ANY, job_re_path_full, content=callback.job
            )),
            'phase': stack.enter_context(mocker.register_uri(
                requests_mock.ANY, job_re_phase_full, content=callback.phase
            )),
            'result': stack.enter_context(mocker.register_uri(
                'GET', job_re_result_full, content=callback.result
            ))
        }

        yield matchers


@pytest.fixture()
def tables(mocker):
    def callback_tables(request, context):
        return get_pkg_data_contents('data/tap/tables.xml')

    def callback_table1(request, context):
        return get_pkg_data_contents('data/tap/lazy-table1.xml')

    def callback_table2(request, context):
        return get_pkg_data_contents('data/tap/lazy-table2.xml')

    with ExitStack() as stack:
        matchers = {
            'tables': stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/tap/tables', content=callback_tables
            )),
            'table1': stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/tap/tables/test.table1',
                content=callback_table1
            )),
            'table2': stack.enter_context(mocker.register_uri(
                'GET', 'http://example.com/tap/tables/test.table2',
                content=callback_table2
            )),
        }

        yield matchers


@pytest.fixture()
def capabilities(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/tap/capabilities.xml')

    with mocker.register_uri(
        'GET', 'http://example.com/tap/capabilities', content=callback
    ) as matcher:
        yield matcher


def test_escape():
        query = 'SELECT * FROM ivoa.obscore WHERE dataproduct_type = {}'
        query = query.format(escape("'image'"))
        assert query == (
            "SELECT * FROM ivoa.obscore WHERE dataproduct_type = ''image''")


@pytest.mark.usefixtures('sync')
def test_search():
    results = search('http://example.com/tap', "SELECT * FROM ivoa.obscore")

    _test_image_results(results)


class TestTAPService(object):
    def test_init(self):
        service = TAPService('http://example.com/tap')

        assert service.baseurl == 'http://example.com/tap'

    def _test_tables(self, table1, table2):
        assert table1.description == 'Lazy Test Table 1'
        assert table1.title == 'Test table 1'

        assert table2.description == 'Lazy Test Table 2'
        assert table2.title == 'Test table 2'

    @pytest.mark.usefixtures('tables')
    def test_tables(self):
        service = TAPService('http://example.com/tap')
        tables = service.tables

        assert list(tables.keys()) == ['test.table1', 'test.table2']

        table1, table2 = list(tables.iter_tables())
        self._test_tables(table1, table2)

    @pytest.mark.usefixtures('capabilities')
    def test_maxrec(self):
        service = TAPService('http://example.com/tap')

        assert service.maxrec == 20000

    @pytest.mark.usefixtures('capabilities')
    def test_hardlimit(self):
        service = TAPService('http://example.com/tap')

        assert service.hardlimit == 10000000

    @pytest.mark.usefixtures('capabilities')
    def test_upload_methods(self):
        service = TAPService('http://example.com/tap')
        upload_methods = service.upload_methods

        assert upload_methods[0].ivo_id == (
            'ivo://ivoa.net/std/TAPRegExt#upload-https')
        assert upload_methods[1].ivo_id == (
            'ivo://ivoa.net/std/TAPRegExt#upload-ftp')
        assert upload_methods[2].ivo_id == (
            'ivo://ivoa.net/std/TAPRegExt#upload-inline')
        assert upload_methods[3].ivo_id == (
            'ivo://ivoa.net/std/TAPRegExt#upload-http')

    @pytest.mark.usefixtures('sync')
    def test_run_sync(self):
        service = TAPService('http://example.com/tap')
        results = service.run_sync("SELECT * FROM ivoa.obscore")
        _test_image_results(results)

    @pytest.mark.usefixtures('sync')
    def test_search(self):
        service = TAPService('http://example.com/tap')
        results = service.search("SELECT * FROM ivoa.obscore")
        _test_image_results(results)

    @pytest.mark.usefixtures('async')
    def test_run_async(self):
        service = TAPService('http://example.com/tap')
        results = service.run_async("SELECT * FROM ivoa.obscore")
        _test_image_results(results)

    @pytest.mark.usefixtures('async')
    def test_submit_job(self):
        service = TAPService('http://example.com/tap')
        job = service.submit_job(
            'http://example.com/tap', "SELECT * FROM ivoa.obscore")

        assert job.url == 'http://example.com/tap/async/' + job.job_id
        assert job.phase == 'PENDING'
        assert job.execution_duration == TimeDelta(3600, format='sec')
        assert isinstance(job.destruction, Time)
        assert isinstance(job.quote, Time)

        job.run()
        job.wait()
        job.delete()

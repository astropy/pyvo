# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
Tests for pyvo.dal.tap
"""
from functools import partial
from contextlib import ExitStack
import datetime
import re
from io import BytesIO
from urllib.parse import parse_qsl

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

job_re_parameters_full = re.compile(
    '^http://example.com/tap/async/([0-9]+)/parameters')

job_re_result_full = re.compile(
    '^http://example.com/tap/async/([0-9]+)/results/result')


def _test_image_results(results):
    assert len(results) == 10


@pytest.fixture()
def sync_fixture(mocker):
    def callback(request, context):
        return get_pkg_data_contents('data/tap/obscore-image.xml')

    with mocker.register_uri(
        'POST', 'http://example.com/tap/sync', content=callback
    ) as matcher:
        yield matcher


class MockAsyncTAPServer:
    def __init__(self):
        self._jobs = dict()

    def validator(self, request):
        pass

    def use(self, mocker):
        with ExitStack() as stack:
            matchers = {
                'create': stack.enter_context(mocker.register_uri(
                    'POST', 'http://example.com/tap/async',
                    content=self.create
                )),
                'job': stack.enter_context(mocker.register_uri(
                    requests_mock.ANY, job_re_path_full, content=self.job
                )),
                'phase': stack.enter_context(mocker.register_uri(
                    requests_mock.ANY, job_re_phase_full, content=self.phase
                )),
                'parameters': stack.enter_context(mocker.register_uri(
                    requests_mock.ANY, job_re_parameters_full,
                    content=self.parameters
                )),
                'result': stack.enter_context(mocker.register_uri(
                    'GET', job_re_result_full, content=self.result
                )),
                'get_job': stack.enter_context(mocker.register_uri(
                    'GET', 'http://example.com/tap/async/111',
                    content=self.get_job
                )),
                'get_job_list': stack.enter_context(mocker.register_uri(
                    'GET', 'http://example.com/tap/async',
                    content=self.get_job_list
                ))
            }
            yield matchers

    def create(self, request, context):
        if request.method == 'GET':
            return self.get_job_list(request, context)
        self.validator(request)
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
        self.validator(request)
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
        self.validator(request)
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

    def parameters(self, request, context):
        self.validator(request)
        jobid = int(job_re_path.match(request.path).group(1))
        job = self._jobs[jobid]

        if request.method == 'GET':
            pass
        elif request.method == 'POST':
            data = dict(parse_qsl(request.body))

            if 'QUERY' in data:
                assert data['QUERY'] == 'SELECT TOP 42 * FROM ivoa.obsCore'
                for param in job.parameters:
                    if param.id_ == 'query':
                        param.content = data['QUERY']
            if 'UPLOAD' in data:
                for param in job.parameters:
                    if param.id_ == 'upload':
                        uploads1 = {data[0]: data[1] for data in [
                            data.split(',') for data
                            in data['UPLOAD'].split(';')
                        ]}

                        uploads2 = {data[0]: data[1] for data in [
                            data.split(',') for data
                            in param.content.split(';')
                        ]}

                        uploads1.update(uploads2)

                        param.content = ';'.join([
                            '{}={}'.format(key, value) for key, value
                            in uploads1.items()
                        ])

    def result(self, request, context):
        self.validator(request)
        return get_pkg_data_contents('data/tap/obscore-image.xml')

    def get_job(self, request, context):
        self.validator(request)
        jobid = int(job_re_path.match(request.path).group(1))

        job = JobFile()
        job.jobid = jobid
        job.phase = 'EXECUTING'
        job.ownerid = '222'
        job.creationtime = Time.now()
        io = BytesIO()
        job.to_xml(io)
        return io.getvalue()

    def _get_jobref_rep(self, jobid, phase, runid, ownerid, creation_time):
        doc = ('    <uws:jobref id="{}">\n'
               '        <uws:phase>{}</uws:phase>\n'
               '        <uws:runId>{}</uws:runId>\n'
               '        <uws:ownerId>{}</uws:ownerId>\n'
               '        <uws:creationTime>{}</uws:creationTime>\n'
               '    </uws:jobref>\n')
        return doc.format(jobid, phase, runid, ownerid, creation_time)

    def get_job_list(self, request, context):
        self.validator(request)
        fields = parse_qsl(request.query)
        phases = []
        last = None
        after = None
        for arg, val in fields:
            if arg == 'PHASE':
                phases.append(val)
            elif arg == 'LAST':
                last = int(val)
            elif arg == 'AFTER':
                after = val

        doc = '<?xml version="1.0" encoding="UTF-8"?>\n' +\
              '<uws:jobs xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" ' +\
              'xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1">\n'

        if phases:
            doc += self._get_jobref_rep('abc1', 'EXECUTING', 'def1', '21',
                                        '2018-12-20T00:23:15.79')
            doc += self._get_jobref_rep('abc2', 'EXECUTING', 'def2', '21',
                                        '2018-12-20T00:23:15.79')

        if after:
            doc += self._get_jobref_rep('abc3', 'EXECUTING', 'def3', '21',
                                        '2018-12-20T00:23:15.79')

        if last:
            doc += self._get_jobref_rep('abc4', 'EXECUTING', 'def4', '21',
                                        '2018-12-20T00:23:15.79')
            doc += self._get_jobref_rep('abc5', 'EXECUTING', 'def5', '21',
                                        '2018-12-20T00:23:15.79')
            doc += self._get_jobref_rep('abc6', 'EXECUTING', 'def6', '21',
                                        '2018-12-20T00:23:15.79')
        doc += '</uws:jobs>'

        return doc.encode('UTF-8')


@pytest.fixture()
def async_fixture(mocker):
    mock_server = MockAsyncTAPServer()
    yield from mock_server.use(mocker)


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
def examples(mocker):
    def callback_examplesXHTML(request, context):
        return get_pkg_data_contents('data/tap/examples.htm')

    with mocker.register_uri(
        'GET', 'http://example.com/tap/examples', content=callback_examplesXHTML
    ) as matcher:
        yield matcher


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


@pytest.mark.usefixtures('sync_fixture')
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
@pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
def test_search():
    results = search('http://example.com/tap', "SELECT * FROM ivoa.obscore")

    _test_image_results(results)


class TestTAPService:
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

        table1, table2 = list(tables)
        self._test_tables(table1, table2)

    def _test_examples(self, exampleXHTML):
        assert "SELECT * FROM rosmaster" in exampleXHTML[0]['QUERY']

    @pytest.mark.usefixtures('examples')
    def test_examples(self):
        service = TAPService('http://example.com/tap')
        examples = service.examples

        self._test_examples(examples)

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

    @pytest.mark.usefixtures('sync_fixture')
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
    def test_run_sync(self):
        service = TAPService('http://example.com/tap')
        results = service.run_sync("SELECT * FROM ivoa.obscore")
        _test_image_results(results)

    @pytest.mark.usefixtures('sync_fixture')
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
    def test_search(self):
        service = TAPService('http://example.com/tap')
        results = service.search("SELECT * FROM ivoa.obscore")
        _test_image_results(results)

    @pytest.mark.usefixtures('async_fixture')
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W27")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W48")
    @pytest.mark.filterwarnings("ignore::astropy.io.votable.exceptions.W06")
    def test_run_async(self):
        service = TAPService('http://example.com/tap')
        results = service.run_async("SELECT * FROM ivoa.obscore")
        _test_image_results(results)

    @pytest.mark.usefixtures('async_fixture')
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

    @pytest.mark.usefixtures('async_fixture')
    def test_modify_job(self):
        service = TAPService('http://example.com/tap')
        job = service.submit_job(
            "SELECT * FROM ivoa.obscore", uploads={
                'one': 'http://example.com/uploads/one'
            })
        job.query = "SELECT TOP 42 * FROM ivoa.obsCore"
        job.upload(two='http://example.com/uploads/two')

        for parameter in job._job.parameters:
            if parameter.id_ == 'query':
                assert parameter.content == 'SELECT TOP 42 * FROM ivoa.obsCore'
                break
            elif parameter.id_ == 'upload':
                assert (
                    'one=http://example.com/uploads/one' in parameter.content)
                assert (
                    'two=http://example.com/uploads/two' in parameter.content)

    @pytest.mark.usefixtures('async_fixture')
    def test_get_job(self):
        service = TAPService('http://example.com/tap')
        job = service.get_job('111')
        assert job.jobid == '111'
        assert job.phase == 'EXECUTING'
        assert job.ownerid == '222'

    @pytest.mark.usefixtures('async_fixture')
    def test_get_job_list(self):
        service = TAPService('http://example.com/tap')
        # server returns:
        #       - 3 jobs for last atribute
        #       - 2 jobs for phase attribute
        #       - 1 job for after attribute
        # Tests consists in counting the cumulative number of jobs as per
        # above rules
        after = datetime.datetime.now()
        assert len(service.get_job_list()) == 0
        assert len(service.get_job_list(last=3)) == 3
        assert len(service.get_job_list(after='2018-04-25T17:46:01Z')) == 1
        assert len(service.get_job_list(phases=['EXECUTING'])) == 2
        assert len(service.get_job_list(after=after,
                                        phases=['EXECUTING'])) == 3
        assert len(service.get_job_list(after='2018-04-25T17:46:01.123Z',
                                        last=3)) == 4
        assert len(service.get_job_list(phases=['EXECUTING'], last=3)) == 5
        assert len(service.get_job_list(phases=['EXECUTING'], last=3,
                                        after=datetime.datetime.now())) == 6

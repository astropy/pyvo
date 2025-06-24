******************************************
Universal Worker Service (``pyvo.io.uws``)
******************************************

.. currentmodule:: pyvo.io.uws

Introduction
============

The Universal Worker Service (UWS) is an IVOA Recommendation that defines a protocol for managing asynchronous jobs in IVOA services
through a RESTful API that can be used to submit, monitor and control asynchronous operations.

Getting Started
===============

UWS job documents can be parsed directly from URLs, files, or strings using the parsing functions provided by this module:

.. doctest-remote-data::

    >>> import pyvo as vo
    >>> from pyvo.io.uws import parse_job, parse_job_list
    >>> tap_service = vo.dal.TAPService("http://dc.g-vo.org/tap")
    >>> ex_query = """
    ...     SELECT TOP 5
    ...     source_id, ra, dec, phot_g_mean_mag
    ...     FROM gaia.dr3lite
    ...     WHERE phot_g_mean_mag BETWEEN 19 AND 20
    ...     ORDER BY phot_g_mean_mag
    ...     """
    >>> async_job = tap_service.submit_job(ex_query)
    >>> async_job.run().wait() # doctest: +ELLIPSIS
    <pyvo.dal.tap.AsyncTAPJob object at 0x...>
    >>>
    >>> # Parse a single job from a UWS service
    >>> job = parse_job(async_job.url)
    >>>
    >>> print(f"Job {job.jobid} is {job.phase}")
    Job ... is COMPLETED
    >>> jobs = parse_job_list('http://dc.g-vo.org/tap/async')
    >>> # Show jobs
    >>> if len(jobs) >= 1:
    ...     print(f"Example job: {jobs[0].jobid} is {jobs[0].phase}") # doctest: +ELLIPSIS
    Example job: ... is ...
    >>>
    >>> print(f"Successfully parsed {len(jobs)} jobs") # doctest: +SKIP

UWS is most commonly encountered when working with :ref:`TAP services <pyvo_tap>`
in asynchronous mode.
The :class:`pyvo.dal.AsyncTAPJob` class provides a higher-level interface that
uses the UWS parsing functions internally.

UWS Job Lifecycle
==================

A UWS job progresses through several phases. Most jobs follow the standard progression through the five common states, while the additional states handle special circumstances:

**Common Job States**:

* **PENDING**: The job is accepted by the service but not yet committed for execution by the client. In this state, the job quote can be read and evaluated. This is the state into which a job enters when it is first created.
* **QUEUED**: The job is committed for execution by the client but the service has not yet assigned it to a processor. No results are produced in this phase.
* **EXECUTING**: The job has been assigned to a processor. Results may be produced at any time during this phase.
* **COMPLETED**: The execution of the job is over. The results may be collected.
* **ERROR**: The job failed to complete. No further work will be done nor results produced. Results may be unavailable or available but invalid; either way the results should not be trusted.

**Special States**:

* **ABORTED**: The job has been manually aborted by the user, or the system has aborted the job due to lack of or overuse of resources.
* **HELD**: The job is HELD pending execution and will not automatically be executed (cf. PENDING).
* **SUSPENDED**: The job has been suspended by the system during execution. This might be because of temporary lack of resources. The UWS will automatically resume the job into the EXECUTING phase without any intervention when resource becomes available.
* **UNKNOWN**: The job is in an unknown state.
* **ARCHIVED**: At destruction time the results associated with a job have been deleted to free up resource, but the metadata associated with the job is retained.


Core Components
===============

Jobs and Job Lists
------------------

The fundamental UWS concepts are represented by these classes:

:class:`~pyvo.io.uws.tree.JobSummary`
    Represents a single UWS job with all its metadata, parameters, and results.

:class:`~pyvo.io.uws.tree.Jobs`
    Represents a list of jobs, typically returned when querying a job list endpoint.

:class:`~pyvo.io.uws.endpoint.JobFile`
    Represents a complete UWS job XML document.

Job Parameters and Results
--------------------------

:class:`~pyvo.io.uws.tree.Parameters`
    Container for job input parameters.

:class:`~pyvo.io.uws.tree.Parameter`
    Individual parameter with an ID and value, optionally referenced by URL.

:class:`~pyvo.io.uws.tree.Results`
    Container for job output results.

:class:`~pyvo.io.uws.tree.Result`
    Individual result with metadata like size and MIME type.

What is JobInfo?
================

The :class:`~pyvo.io.uws.tree.JobInfo` element is an extensible container
that allows UWS implementations to include arbitrary, service-specific information
about a job. This for example can be used to provide:

* **Implementation-specific metadata** about job execution like progress info
* **Service-specific configuration** or diagnostic information
* **Extended error details** or debugging information

JobInfo exposes this information in a possibly hierarchical dictionary.

Working with UWS Jobs
=====================

Setting Up Examples
-------------------

For the following examples, we'll use a sample UWS job document:

>>> import pyvo.io.uws
>>> from io import BytesIO
>>>
>>> # Load sample UWS job from Appendix A
>>> sample_job_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
... <job xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1">
...   <jobId>async-query-12345</jobId>
...   <runId>query-run-id</runId>
...   <ownerId>user-1</ownerId>
...   <phase>COMPLETED</phase>
...   <quote>2025-06-19T14:35:00.000Z</quote>
...   <creationTime>2025-06-19T14:30:00.000Z</creationTime>
...   <startTime>2025-06-19T14:30:05.123Z</startTime>
...   <endTime>2025-06-19T14:32:18.456Z</endTime>
...   <executionDuration>600</executionDuration>
...   <destruction>2025-06-26T14:30:00.000Z</destruction>
...   <parameters>
...     <parameter id="LANG">ADQL</parameter>
...     <parameter id="QUERY">SELECT obj_id, ra, dec, magnitude FROM catalog.objects WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 180.0, 45.0, 1.0))</parameter>
...     <parameter id="FORMAT">votable</parameter>
...     <parameter id="MAXREC">10000</parameter>
...   </parameters>
...   <results>
...     <result id="result" xlink:href="http://example.com/tap/async/async-query-12345/results/result"/>
...   </results>
...   <jobInfo>
...     <rowsReturned>1234</rowsReturned>
...     <executionTime>133.333</executionTime>
...     <cpuTime>98.765</cpuTime>
...     <queuePosition>0</queuePosition>
...     <estimatedDuration>120</estimatedDuration>
...     <nodeId>compute-node-03</nodeId>
...     <serviceVersion>1.1</serviceVersion>
...   </jobInfo>
... </job>'''
>>>
>>> job = pyvo.io.uws.parse_job(BytesIO(sample_job_xml))

Parsing and Basic Access
------------------------

>>> # Access basic job information (job created in testsetup above)
>>> print(f"Job ID: {job.jobid}")
Job ID: async-query-12345
>>> print(f"Phase: {job.phase}")
Phase: COMPLETED
>>> print(f"Owner: {job.ownerid}")
Owner: user-1
>>> print(f"Run ID: {job.runid}")
Run ID: query-run-id

Timing and Duration Analysis
----------------------------

UWS jobs include comprehensive timing information automatically parsed as
:class:`astropy.time.Time` and :class:`astropy.time.TimeDelta` objects:

>>> # Job times are automatically parsed as astropy Time objects
>>> print(f"Created: {job.creationtime}")
Created: 2025-06-19T14:30:00.000
>>> print(f"Started: {job.starttime}")
Started: 2025-06-19T14:30:05.123
>>> print(f"Completed: {job.endtime}")
Completed: 2025-06-19T14:32:18.456
>>>
>>> # Calculate actual execution time
>>> if job.starttime and job.endtime:
...     duration = job.endtime - job.starttime
...     print(f"Job took {duration.to('second').value:.1f} seconds")
Job took 133.3 seconds
>>>
>>> # Check execution limits
>>> if job.executionduration:
...     print(f"Max allowed: {job.executionduration.to('minute').value:.1f} minutes")
Max allowed: 10.0 minutes

Parameter Inspection
--------------------

Job parameters include both the query itself and configuration options:

>>> # Iterate through all parameters
>>> for param in job.parameters:
...     if param.byreference:
...         print(f"Parameter {param.id_}: Referenced from {param.content}")
...     else:
...         print(f"Parameter {param.id_}: {param.content}")
Parameter LANG: ADQL
Parameter QUERY: SELECT obj_id, ra, dec, magnitude FROM catalog.objects WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 180.0, 45.0, 1.0))
Parameter FORMAT: votable
Parameter MAXREC: 10000

Result Access and Download
--------------------------

Results include the actual data products and associated metadata:

>>> # Access all results
>>> for result in job.results:
...     print(f"Result '{result.id_}':")
...     print(f"  URL: {result.href}")
Result 'result':
  URL: http://example.com/tap/async/async-query-12345/results/result

Working with JobInfo
====================

JobInfo provides access to service-specific metadata about job execution.

Basic JobInfo Access
--------------------

>>> if job.jobinfo:
...     # RECOMMENDED: Dict-like access for expected elements
...     try:
...         rows_returned = job.jobinfo['rowsReturned']
...         execution_time = job.jobinfo['executionTime']
...         print(f"Query returned {rows_returned.value:,} rows in {execution_time.value:.1f} seconds")
...     except KeyError as e:
...         print(f"Missing expected element: {e}")
...
...     # Use .get() with defaults for optional elements
...     queue_pos = job.jobinfo.get('queuePosition', None)
...     node_id = job.jobinfo.get('nodeId', None)
...
...     if queue_pos:
...         print(f"Final queue position: {queue_pos.value}")
...
...     if node_id:
...         print(f"Executed on: {node_id.text}")
Query returned 1,234 rows in 133.3 seconds
Final queue position: 0
Executed on: compute-node-03

.. note::
   **API Usage Recommendation**: When accessing jobInfo elements, prefer dict-like
   access (``job.jobinfo['element']``) for expected elements, as this provides
   clearer error handling with KeyError exceptions. Use ``.get()`` with default
   values for optional elements. See the jobInfo examples for detailed patterns.

Understanding .value vs .text
-----------------------------

JobInfo elements provide two ways to access their content:

>>> if job.jobinfo:
...     duration_elem = job.jobinfo['estimatedDuration']
...
...     # .text returns the raw string content
...     print(f"Raw text: '{duration_elem.text}'")
...
...     # .value attempts automatic type conversion (int, float, or string)
...     print(f"Converted value: {duration_elem.value}")
...     print(f"Type: {type(duration_elem.value)}")
...
...     # For elements with string content that shouldn't be converted
...     node_elem = job.jobinfo['nodeId']
...     print(f"Node ID text: {node_elem.text}")
...     print(f"Node ID value: {node_elem.value}")
Raw text: '120'
Converted value: 120
Type: <class 'int'>
Node ID text: compute-node-03
Node ID value: compute-node-03

Best Practices for JobInfo Access
---------------------------------

>>> def safe_jobinfo_access(job):
...     """Demonstrates safe jobInfo access patterns"""
...     if not job.jobinfo:
...         print("No jobInfo available")
...         return
...
...     # Pattern 1: Expected elements with error handling
...     try:
...         rows = job.jobinfo['rowsReturned']
...         exec_time = job.jobinfo['executionTime']
...         print(f"Processed {rows.value:,} rows in {exec_time.value:.1f} seconds")
...     except KeyError as e:
...         print(f"Required statistics missing: {e}")
...
...     # Pattern 2: Optional elements with defaults
...     queue_pos = job.jobinfo.get('queuePosition', 'unknown')
...     priority = job.jobinfo.get('priority', 'normal')
...
...     # Pattern 3: Check existence before accessing
...     if 'nodeId' in job.jobinfo:
...         node = job.jobinfo['nodeId']
...         print(f"Executed on node: {node.text}")
...
...     # Pattern 4: Iterate through all available elements
...     print("All jobInfo elements:")
...     for key in job.jobinfo.keys():
...         element = job.jobinfo[key]
...         print(f"  {key}: {element.text}")
>>> safe_jobinfo_access(job)
Processed 1,234 rows in 133.3 seconds
Executed on node: compute-node-03
All jobInfo elements:
  rowsReturned: 1234
  executionTime: 133.333
  cpuTime: 98.765
  queuePosition: 0
  estimatedDuration: 120
  nodeId: compute-node-03
  serviceVersion: 1.1

Job Status Monitoring
=====================

Checking Completion Status
--------------------------

>>> # Check if job completed successfully
>>> if job.phase == 'COMPLETED':
...     print("Job completed successfully!")
...
...     # Show summary information
...     total_time = (job.endtime - job.creationtime).to('minute').value
...     print(f"Total job runtime: {total_time:.1f} minutes")
...
...     # Access jobInfo safely
...     if job.jobinfo:
...         try:
...             rows = job.jobinfo['rowsReturned']
...             print(f"Total rows returned: {rows.value:,}")
...         except KeyError:
...             print("Row count not available")
... elif job.phase == 'ERROR' and job.errorsummary and job.errorsummary.message:
...     print(f"Job failed: {job.errorsummary.message.content}")
... else:
...     print(f"Job is currently: {job.phase}")
Job completed successfully!
Total job runtime: 2.3 minutes
Total rows returned: 1,234

Working with Job Lists
======================

Parsing Job Lists
-----------------

While the examples above focus on individual jobs, you can also parse job lists:

.. doctest-remote-data::

    >>> from pyvo.io.uws import parse_job_list
    >>>
    >>> # Parse a job list from a UWS service endpoint
    >>> jobs = parse_job_list('http://dc.g-vo.org/tap/async')
    >>>
    >>> # Or from a local file
    >>> # jobs = parse_job_list('job_list.xml')
    >>>
    >>> # Iterate through jobs (each is a JobSummary object)
    >>> for job in jobs:  # doctest: +ELLIPSIS
    ...     print(f"Job {job.jobid}: {job.phase}")
    Job ...: COMPLETED


Error Handling
==============

When working with failed jobs, check the error summary:

    >>> # Example of handling a job with errors
    >>> def check_job_status(job_file):
    ...     job = parse_job(job_file)
    ...
    ...     if job.phase == 'ERROR':
    ...         print(f"Job {job.jobid} failed!")
    ...         if job.errorsummary:
    ...             print(f"Error type: {job.errorsummary.type_}")
    ...             if job.errorsummary.message and job.errorsummary.message.content:
    ...                 print(f"Message: {job.errorsummary.message.content}")


Reference/API
=============

.. automodapi:: pyvo.io.uws.tree

.. automodapi:: pyvo.io.uws.endpoint

Appendix A: Example UWS Job Document
====================================

All examples in this documentation reference this sample UWS job XML document.

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <job xmlns:uws="http://www.ivoa.net/xml/UWS/v1.0" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1">
      <jobId>async-query-12345</jobId>
      <runId>query-run-id</runId>
      <ownerId>user-1</ownerId>
      <phase>COMPLETED</phase>
      <quote>2025-06-19T14:35:00.000Z</quote>
      <creationTime>2025-06-19T14:30:00.000Z</creationTime>
      <startTime>2025-06-19T14:30:05.123Z</startTime>
      <endTime>2025-06-19T14:32:18.456Z</endTime>
      <executionDuration>600</executionDuration>
      <destruction>2025-06-26T14:30:00.000Z</destruction>

      <parameters>
        <parameter id="LANG">ADQL</parameter>
        <parameter id="QUERY">SELECT obj_id, ra, dec, magnitude FROM catalog.objects WHERE 1=CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', 180.0, 45.0, 1.0))</parameter>
        <parameter id="FORMAT">votable</parameter>
        <parameter id="MAXREC">10000</parameter>
      </parameters>

      <results>
        <result id="result"
                xlink:href="http://example.com/tap/async/async-query-12345/results/result"/>
      </results>

      <jobInfo>
        <rowsReturned>1234</rowsReturned>
        <executionTime>133.333</executionTime>
        <cpuTime>98.765</cpuTime>
        <queuePosition>0</queuePosition>
        <estimatedDuration>120</estimatedDuration>
        <nodeId>compute-node-03</nodeId>
        <serviceVersion>1.1</serviceVersion>
      </jobInfo>
    </job>

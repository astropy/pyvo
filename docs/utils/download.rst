.. _pyvo-download:

**************************************************
Download Utilities (`pyvo.utils.download`)
**************************************************

The download utilities provide methods for downloading data once a link to it
it obtained. These can be considered an advanced version of `~pyvo.dal.Record.getdataset` that can handle
data from standard on-prem servers as well as cloud data. For now only AWS is supported.

There two methods with the same call signature: `~pyvo.utils.download.http_download` and `~pyvo.utils.download.aws_download`. The first handles standard links from on-prem servers, while the second downloads data from the `Amazon S3 storage`_.


.. _pyvo-download-examples:

Example Usage
==============
This is an example of downloading data when an URL or URI are available:

.. doctest-remote-data::

    >>> from pyvo.utils import aws_download, http_download
    >>> data_url = 'https://heasarc.gsfc.nasa.gov/FTP/chandra/data/byobsid/2/3052/primary/acisf03052N004_cntr_img2.jpg'
    >>> image_file = http_download(url=data_url)
    >>> s3_uri = 's3://nasa-heasarc/chandra/data/byobsid/2/3052/primary/acisf03052N004_cntr_img2.jpg'
    >>> image2_file = aws_download(uri=s3_uri)
    Downloading chandra/data/byobsid/2/3052/primary/acisf03052N004_cntr_img2.jpg to acisf03052N004_cntr_img2.jpg ... [Done]


A bucket name and a key can also be passed to `~pyvo.utils.download.aws_download` instead of an URI:

.. doctest-remote-data::
    >>> from pyvo.utils import aws_download 
    >>> s3_key = 'chandra/data/byobsid/2/3052/primary/acisf03052N004_cntr_img2.jpg'
    >>> s3_bucket = 'nasa-heasarc'
    >>> image2_file = aws_download(bucket_name=s3_bucket, key=s3_key)
    Downloading chandra/data/byobsid/2/3052/primary/acisf03052N004_cntr_img2.jpg to acisf03052N004_cntr_img2.jpg ... [Done]


If the aws data requires authentication, a credential profile (e.g. ``aws_user`` profile in ``~/.aws/credentials``) can be passed:

.. doctest-skip::
    >>> image2_file = aws_download(bucket=s3_bucket, key=s3_key, aws_profile='aws_user')


A session (instance of ``boto3.session.Session``) can also be passed instead (see detials in `AWS session documentation`_):

.. doctest-skip::
    >>> s3_session = boto3.session.Session(aws_access_key_id, aws_secret_access_key)
    >>> image2_file = aws_download(bucket=s3_bucket, key=s3_key, session=s3_session)


.. _pyvo-download-api:

Reference/API
=============

.. automodapi:: pyvo.utils.download


.. _Amazon S3 storage: https://aws.amazon.com/s3/
.. _AWS session documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html
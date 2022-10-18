.. pyvo-cloud_access:

.. doctest-skip-all


Cloud Access
************

Services can return a ``cloud_access`` column in their responses, with a valid JSON string content.

.. Note::
  The current prototype implementation support AWS holdings only, but the example below shows how
that this could work universally, for other cloud providers, too.

.. code-block::

{"aws": [{ "bucket_name": "irsa-mast-tike-spitzer-data",
           "region": "us-east-1",
           "access": "restricted",
           "key": "data/COSMOS/irac_ch1_go2_sci_10.fits" }],
"google": [{...}],
"azure": [{...}]
}


A Simple User Case
------------------

The service returns addresses for both on premisses and cloud holdings of a particular file
where user manually specifies to get file from cloud, and downloads/reads it::

>>> import sys
>>> import os
>>> import astropy.coordinates as coord
>>> import pyvo
>>> pos = coord.SkyCoord.from_name("ngc 4151")

>>> query_url = 'https://mast.stsci.edu/portal_vo/Mashup/VoQuery.asmx/SiaV1?MISSION=HST&'
>>> query_result = pyvo.dal.sia.search(query_url, pos=pos, size=0.0)
>>> table_result = query_result.to_table()
>>> col_name = query_result.fieldname_with_ucd('VOX:Image_AccessReference')
>>> data_product = table_result[0]

To manually access the on-premises data::

>>> prem_handle = pyvo.utils.cloud_access.get_data_product(data_product, access_url_column=col_name)
>>> prem_handle.download()

To  manually access the cloud hosted data::

>>> aws_handle = pyvo.utils.cloud_access.get_data_product(data_product, 'aws', access_url_column=col_name)
>>> aws_handle.download()

Automated decision between on-premisses vs cloud versions
---------------------------------------------------------

Depending on the access model of the given data (specified in the ``cloud_access`` column),
and location of the client a decision is

>>> query_url = 'https://mast.stsci.edu/portal_vo/Mashup/VoQuery.asmx/SiaV1?MISSION=HST&'
>>> query_result = pyvo.dal.sia.search(query_url, pos=pos, size=0.0)
>>> table_result = query_result.to_table()
>>> col_name = query_result.fieldname_with_ucd('VOX:Image_AccessReference')
>>> data_product = table_result[0]

>>> pyvo.utils.cloud_access.get_data_product(data_product, 'aws', access_url_column=col_name)

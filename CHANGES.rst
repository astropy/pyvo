1.4.1 (2023-03-07)
==================

- registry.regsearch now accepts an optional maxrec argument rather than
  automatically passing the service's hard limit. [#375]

- fixed the RegTAP fragment for the discovery of EPN-TAP tables. [#395]

- Removing defaults for optional SIAv1 and SSA query parameters to avoid
  unnecessarily overriding the server-side defaults. [#367]

- Error messages from uws jobs are now in job.errorsummary.message
  rather than job.message (where one wouldn't expect them given the UWS
  schema). [#432]

- Avoid raising ``AttributeError`` for None responses. [#392]


1.4 (2022-09-26)
================

- Added the TAP Table Manipulation prototype (cadc-tb-upload). [#274]

- More explicit exception messages where the payload is
  sometimes considered if it can be presented properly (simple
  body text or job error message). [#355]

- we now ignore namespaces in xsi-type attributes; this is a lame fix
  for services like ESO's and MAST's TAP, which do not use canonical
  prefixes while astropy.utils.xml ignores namespaces. [#323]

- Overhaul of the registry.regsearch as discussed in
  https://blog.g-vo.org/towards-data-discovery-in-pyvo.html.  This
  should be backwards-compatible. [#289]

- Versions of astropy <4.1 are no longer supported. [#289]

- pyvo.dal warns on results with overflow status. [#329]

- Allow session to be passed through in SSA and DataLink. [#327]

- pyvo.dal.tap.AsyncTAPJob treats parameter names as case-insensitive when
  retrieving the query from the job record. [#357]

- Adding support for prototype features via the ``prototype_feature``
  decorator . [#309]

- No longer formatting microseconds into SSA time literals. [#351]

- Adding operating system to User-Agent. [#344]


1.3 (2022-02-19)
==================

- pyvo deals with non-core terms in datalink.bysemantics again. [#299]

- Versions of Python <3.8 are no longer supported. [#290]


1.2.1 (2022-01-12)
==================

- Get wraps decorator from functools instead of astropy. [#283]


1.2 (2021-12-17)
================

- Make .bysemantics expand its terms to the entire branch by default [#241]

- Added optional includeaux flag for regTAP search() [#258]

- Added VOResource 1.1 mirrorurl and testquerystring to vosi.Interface [#269]

- Versions of Python <3.7 are no longer supported. [#255]


1.1 (2020-06-26)
================

- Added TAP examples function. [#220]

- Add default for UWS version. [#199]

- Handle description of None when describing a TAP service's tables. [#197]

- Properly handle single string keywords value for regsearch(). [#201]

- Add support for SIAv2. [#206]

- Add kwargs to sia2. [#222]

- Fix handling relative result URLs. [#192]


1.0 (2019-09-20)
================

- Fix pedantic table parsing not throwing exception. [#140]

- Drop support for legacy Python 2.7. [#153]

- Sphinx 1.7 or higher is needed to build the documentation. [#160]

- Add support for authenticated requests. [#157]

- Add a get_job_list method to the TAPService class. [#169]

- Replace example's usage of pyvo.object2pos() with SkyCoord.from_name() [#171]

- Stop installing files from scripts to /usr/local/bin. Move them to
  examples/images instead. [#166]

- Update ex_casA_image_cat example. [#172]

- Fix waveband option in registry.regsearch [#175]

- Fix to regtap.ivoid2service(), few decode()'s, para_format_desc  was moved
  to utils. [#177]

- Fix default result id for fetch_results of async TAP. [#148]


0.9.3 (2019-05-30)
==================

- Fix parsing of SecurityMethod in capabilities. [#114]

- Keep up to date with upstream astropy changes.

- Move into astropy GitHub organization and README updates. [#133]

- Replace mimetype functions with library-based ones.


0.9.2 (2018-10-05)
==================

- Fix typo fornat -> format. [#106]


0.9.1 (2018-10-02)
==================

- Don't use OR's in RegTAP queries.

- Add a timeout to job wait.


0.9 (2018-09-18)
================

- Add a describe method to services to print a human-readable description.

- Use a customized user agent in http requests.

- Fix some python2/3 issues.

- Add general datalink processing method. [#103]


0.8.1 (2018-06-27)
==================

- Pass use_names_over_ids=True to astropy's to_table.


0.8 (2018-06-07)
================

- Make XML handling more generic.


0.7rc1 (2018-02-18)
===================

- Rework VOSI parsing using astropy xml handling. [#88]

- Describe service object bases on vosi capabilities.

- Add SODA functionallity.

- Fixes and Improvements.


0.6.1 (2017-06-29)
==================

- Add Datalink interface.

- Put some common functionallity in Mixins.

- Minor fixes and improvements.


0.6 (2017-04-17)
================

- Using RegTAP as the only registry interface.

- Added a datamodel keyword to registry search.

- Using the six libray to address Python 2/3 compatibility issues.

- AsyncTAPJob is now context aware.

- Improvement upload handling; it is no longer necessary to specifiy the type
  of upload.

- Allow astropy's SkyCoord and Quantity as input parameters.


0.5.2 (2017-02-09)
==================

- Remove trailing ? from query urls. [#78]

- VOTable fieldnames are now gathered from names only instead of ID and name.


0.5.1 (2017-02-02)
==================

- Fix content decoding related error in async result handling.


0.5 (2017-01-13)
================

- Added a RegTAP interface. [#73]

- Removed urllib in favor of the requests library. [#74]

- Deprecated vao registry interface.

- Minor improvements and fixes.


0.4.1 (2016-12-02)
==================

- Fix a bug where maxrec wasn't send to the server.


0.4 (2016-12-02)
================

- Use astropy tables for table metadata. [#71]

- Fix another content encoding error. [#72]


0.3.2 (2016-12-02)
==================

- Adding table property to DALResults. This is a shortcut to access the
  astropy table.

- Improved Error Handling.

- Adding ``upload_methods`` to TAPService. [#69]


0.3.1 (2016-12-02)
==================

- Fix an error where the content wasn't decoded properly. [#67]

- Fix a bug where POST parameters are submitted as GET parameters.


0.3 (2016-12-02)
================

- Adding TAP API. [#58, #66]


0.1 (2016-12-02)
================

- This is the last release that supports Python 2.6. [#62]

- This release only contains bug fixes beyond 0.0beta2.

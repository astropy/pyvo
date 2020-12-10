1.2 (unreleased)
================


1.1 (2020-06-26)
================

- Added TAP examples function. [#220]

- Add default for UWS version. [#199]

- Handle description of None when describing a TAP service's tables. [#197]

- Properly handle single string keywords value for regsearch(). [#201]

- Add support for SIAv2. [#206]

- Add kwargs to sia2. [#222]


1.0 (2019-09-20)
================

- Fix pedantic table parsing not throwing exception. [#140]

- Drop support for legacy Python 2.7. [#153]

- Sphinx 1.7 or higher is needed to build the documentation. [#160]

- Add support for authenticated requests. [#157]

- Add a get_job_list method to the TAPService class. [#169]

- Replace example's usage of pyvo.object2pos() with SkyCoord.from_name() [#171]

- Stop installing files from scripts to /usr/local/bin. Move them to examples/images instead. [#166]

- Update ex_casA_image_cat example. [#172]

- Fix waveband option in registry.regsearch [#175]

- Fix to regtap.ivoid2service(), few decode()'s, para_format_desc  was moved to utils.  [#177]


0.9.3 (2019-05-30)
==================

- Fix parsing of SecurityMethod in capabilities.

- Keep up to date with upstream astropy changes.

- Move into astropy GitHub organization and README updates.

- Replace mimetype functions with library-based ones.


0.9.2
=====

- Fix typo fornat -> format.


0.9.1
=====

- Don't use OR's in RegTAP queries.

- Add a timeout to job wait.


0.9
===

- Add a describe method to services to print a human-readable description.

- Use a customized user agent in http requests.

- Fix some python2/3 issues.

- Add general datalink processing method.


0.8.1
=====

- Pass use_names_over_ids=True to astropy's to_table.


0.8
===

- Make XML handling more generic.


0.7rc1
======

- Rework VOSI parsing using astropy xml handling.

- Describe service object bases on vosi capabilities.

- Add SODA functionallity.

- Fixes and Improvements.


0.6.1
=====

- Add Datalink interface.

- Put some common functionallity in Mixins.

- Minor fixes and improvements.


0.6
===

- Using RegTAP as the only registry interface.

- Added a datamodel keyword to registry search.

- Using the six libray to address Python 2/3 compatibility issues.

- AsyncTAPJob is now context aware.

- Improvement upload handling; it is no longer necessary to specifiy the type
  of upload.

- Allow astropy's SkyCoord and Quantity as input parameters.


0.5.2
=====

- Remove trailing ? from query urls.

- VOTable fieldnames are now gathered from names only instead of ID and name.


0.5.1
=====

- Fix content decoding related error in async result handling.

0.5
===

- Added a RegTAP interface.

- Removed urllib in favor of the requests library.

- Deprecated vao registry interface.

- Minor improvements and fixes.

0.4.1
=====

- Fix a bug where maxrec wasn't send to the server.


0.4
===

- Use astropy tables for table metadata.

- Fix another content encoding error.


0.3.2
=====

- Adding table property to DALResults. This is a shortcut to access the
  astropy table.

- Improved Error Handling.


0.3.1
=====

- Fix an error where the content wasn't decoded properly.

- Fix a bug where POST parameters are submitted as GET parameters.


0.3
===

- Adding TAP API.


0.1
===

- This is the last release that supports Python 2.6.

- This release only contains bug fixes beyond 0.0beta2.

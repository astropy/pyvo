1.0
----------------

* Fix #130 pedantic table parsing not throwing exception.

0.9.3
----------------
* Fix parsing of SecurityMethod in capabilities

* Keep up to date with upstream astropy changes

* Move into astropy GitHub organization and README updates

* Replace mimetype functions with library-based ones

0.9.2
----------------
* Fix typo fornat -> format

0.9.1
----------------
* Don't use OR's in RegTAP queries

* Add a timeout to job wait

0.9
----------------
* add a describe method to services to print a human-readable description

* use a customized user agent in http requests

* fix some python2/3 issues

* add general datalink processing method

0.8.1
----------------
pass use_names_over_ids=True to astropy's to_table

0.8
----------------
* Make XML handling more generic

0.7rc1
----------------
* Rework VOSI parsing using astropy xml handling

* Describe service object bases on vosi capabilities

* Add SODA functionallity

* Fixes and Improvements

0.6.1
----------------
* Add Datalink interface

* Put some common functionallity in Mixins

* Minor fixes and improvements

0.6
----------------
* Using RegTAP as the only registry interface

* Added a datamodel keyword to registry search

* Using the six libray to address Python 2/3 compatibility issues

* AsyncTAPJob is now context aware

* Improvement upload handling; it is no longer necessary to specifiy the type
  of upload

* Allow astropy's SkyCoord and Quantity as input parameters

0.5.2
----------------
Remove trailing ? from query urls
VOTable fieldnames are now gathered from names only instead of ID and name

0.5.1
----------------
* fix content decoding related error in async result handling

0.5
----------------
* added a RegTAP interface
* removed urllib in favor of the requests library
* deprecated vao registry interface
* minor improvements and fixes

0.4.1
------------------
* fix a bug where maxrec wasn't send to the server

0.4
----------------
* Use astropy tables for table metadata

* fix another content encoding error

0.3.2
------------------
* Adding table property to DALResults. This is a shortcut to access the astropy table

* Improved Error Handling

0.3.1
------------------
* fix an error where the content wasn't decoded properly

* fix a bug where POST parameters are submitted as GET parameters

0.3
----------------
Adding TAP API

0.1
----------------

This is the last release that supports Python 2.6.

This release only contains bug fixes beyond 0.0beta2.


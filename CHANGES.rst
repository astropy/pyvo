0.6 (unreleased)
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


Release Procedure for pyvo
==========================

These steps are intended to help guide a developer into
making a new release.  For these instructions, version
is to be replaced by the version number of the release.

1. Edit setup.cfg and remove .dev from the version number

2. Edit CHANGES.rst to change unreleased to the date of the release.

3. Commit and push

4. git tag -a version -m "releasing new version version" (this makes a release tag)

5. git push origin version

6. python setup.py sdist (this makes a .tar.gz of the package in dist)

7. twine upload sdist/* (this uploads the output of the previous step to pypi)

8. Edit setup.cfg and set the version to the next release number and add .dev after the version number.  Add a new section at the top for the next release number

9. Commit and push.  This begins the new release

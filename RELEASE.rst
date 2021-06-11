Release Procedure for pyvo
==========================

These steps are intended to help guide a developer into
making a new release.  For these instructions, version
is to be replaced by the version number of the release.

1. Make a PR with the following changes to publish a release:

- Edit setup.cfg and remove .dev from the version number
- Edit CHANGES.rst to change unreleased to the date of the release

2. Use the GitHub releases to draft a new release, and put the version
number in for the tag.  This tag must match what is in the setup.cfg
(without the dev).  This will trigger a github action that builds
the release and uploads it to pypi.

3. Make a PR with the following changes to begin the new release cycle:

- Edit setup.cfg and set the version to the next release number plus ".dev"
- Add a new section at the top of CHANGES.rst for the next release number

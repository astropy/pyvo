.. _pyvo-testing:

******************************************
Helpers for Testing (`pyvo.utils.testing`)
******************************************

This package contains a few helpers to make testing pyvo code simpler.
This is *not* intended to be used by user code or other libraries at
this point; the API might change at any time depending on the testing
needs of pyVO itself, and this documentation (mainly) addresses pyVO
developers.


The LearnableRequestMocker
--------------------------

By its nature, much of pyVO is about talking to remote services.
Talking to these remote services in order to test pyVO code
makes test runs dependent on the status of external resources and may be
slow.  It is therefore desirable to “can” responses to a large extent,
i.e., use live responses to define the test fixture.  This is what
`pyvo.utils.testing.LearnableRequestMocker` tries to support.

To use it, define a fixture for the mocker, somewhat like this::

  @pytest.fixture
  def _all_constraint_responses(requests_mock):
      matcher = LearnableRequestMocker("image-with-all-constraints")
      requests_mock.add_matcher(matcher)

The first constructor argument is a fixture name that should be unique
among all the fixtures in a given subdirectory.

When “training“ your mocker, run ``pytest --remote-data=any``.  This
will create one or more pairs of files in the cache directory, which is
a sibling of the current file called ``data/<fixture-name>``.  Each
request produces two files:

* <base-name>.meta: a pickle of the request and selected response
  metadata.  You probably do not want to edit this.
* <base-name>: the resonse body, which you may very well want to edit.

All these must become part of the package for later tests to run without
network interaction.  The <base-name> is intended to facilitate figuring
out which response belongs to which request; it consists of the method,
the host, the start of the payload (if any), and hashes of the full URL
and a payload.

When the upstream response (or whatever request pyvo produces) changes,
remove the
cached files and re-run test with ``--remote-data=any``.

We do not yet have a good plan for how to preserve edits made to the
test files.  For now, commit the original responses, do any changes, and
do a commit encompassing only these changes.

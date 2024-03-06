.. _pyvo-prototypes:

**************************************************
Prototype Implementations (`pyvo.utils.prototype`)
**************************************************

This subpackage provides support for prototype standard implementations.

``PyVO`` implements the IVOA standards. As part of the standard approval process, new features
are proposed and need to be demonstrated before the standard may be approved. ``PyVO``
may implement features that are not yet part of an approved standard.
Such features are unstable, as the standard may be subject to reviews and significant changes, until it's finally
approved.

The ``prototype`` package provides support for such prototypes by means of a decorator
for implementations that are still unstable. The expectation is that they will eventually become
standard at which time the decorator will be removed.

Users of ``pyvo`` need to explicitly opt-in in order to use such features. If prototype
implementations are accessed without the user explicitly opting in, an exception will be raised.

.. _pyvo-prototypes-users:

Activating Prototype Implementations
====================================

In order to activate a feature, users need to call the function::

   activate_features('feature_one', 'feature_two')

Where the arguments are names of prototype features. If a feature name does not exist, a `~pyvo.utils.prototype.PrototypeWarning`
will be issued, but the call will not fail. If no arguments are provided, then all features are enabled.

.. _pyvo-prototypes-developers:

Marking Features as Experimental
================================
The design restricts the possible usage of the decorator, which needs to always be called
with a single argument being the name of the corresponding feature. More arguments are allowed
but will be ignored. If the decorator is not used with the correct
``@prototype_feature("feature-name")`` invocation, the code will error as soon as the class is
imported.

The decorator can be used to tag individual functions or methods::

   @prototype_feature('a-feature')
   def i_am_a_prototype(*arg, **kwargs):
      pass

In this case, a single function or method is tagged as part of the ``a-feature`` prototype feature. If the feature
has a URL defined (see :ref:`pyvo-prototypes-registry` below).

Alternatively, a class can be marked as belonging to a feature. All public methods will be marked as part of the
prototype implementation. Protected, private, and *dunder* methods (i.e. any method starting with
an underscore) will be ignored. The reason is that the class might be instantiated by some mediator before the
user can call (and more importantly not call) a higher level facade::

   @prototype_feature('a-feature')
   class SomeFeatureClass:
       def method(self):
           pass

       @staticmethod
       def static():
           pass

       def __ignore__(self):
           pass

Any number of classes and functions can belong to a single feature, and individual methods can be tagged
in a class rather than the class itself.

.. _pyvo-prototypes-registry:

Feature Registry
================

The feature registry is a static ``features`` dictionary in the `~pyvo.utils.prototype` package. The key is the name
of the feature and the value is an instance of the `~pyvo.utils.protofeature.Feature` class. This class is responsible for determining
whether an instance should error or not, and to format an error message if it's not. While the current implementation
of the ``Feature`` class is simple, future requirements might lead to other implementations with more complex logic or
additional documentation elements.

.. _pyvo-prototypes-api:

Reference/API
=============

.. automodapi:: pyvo.utils.prototype
.. automodapi:: pyvo.utils.protofeature


Existing Prototypes
===================

.. _cadc-tb-upload:

CADC Table Manipulation (cadc-tb-upload)
----------------------------------------

This is a proposed extension to the TAP protocol to allow users to manipulate
tables (https://wiki.ivoa.net/twiki/bin/view/IVOA/TAP-1_1-Next). The
`~pyvo.dal.tap.TAPService` has been extended with methods that allow for:

* table creation
* column index creation
* table content upload
* table removal

More details at: :ref:`table manipulation`

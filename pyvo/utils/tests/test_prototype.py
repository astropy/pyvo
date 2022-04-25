import warnings
from copy import deepcopy
from unittest import mock

import pytest

from pyvo.utils import prototype_feature, activate_features, prototype
from pyvo.utils.prototype import PrototypeError, PrototypeWarning, Feature


@pytest.fixture
def prototype_function(features):
    features({
        'my-feature': Feature('my-feature', url='http://somewhere/else')
    })

    @prototype_feature('my-feature')
    def i_am_prototype(arg):
        arg('called')

    return i_am_prototype


@pytest.fixture
def features():
    previous_available = deepcopy(prototype.features)
    prototype.features.clear()

    def add(features):
        prototype.features.update(features)

    yield add

    prototype.features.clear()
    prototype.features.update(previous_available)


def test_feature_turned_off_by_default(prototype_function):
    with pytest.raises(PrototypeError) as e:
        prototype_function(None)

    assert str(e.value) == 'i_am_prototype is part of a prototype feature (my-feature) that has not been activated. ' \
                           'For more information please visit http://somewhere/else'


def test_activate_feature(prototype_function):
    probe = mock.Mock()

    activate_features('my-feature')

    try:
        prototype_function(probe)
    except Exception as exc:
        assert False, f"Should not have raised {exc}"

    probe.assert_called_once_with('called')


def test_non_existent_feature_warning():
    with pytest.warns(PrototypeWarning) as w:
        activate_features('i dont exist')

    assert len(w) == 1
    assert str(w[0].message) == 'No such feature "i dont exist"'


def test_activate_all_features(features):
    features({
        'feat-one': Feature('feat-one'),
        'feat-two': Feature('feat-two')
    })

    activate_features()

    assert set(prototype.features.keys()) == {'feat-one', 'feat-two'}
    assert prototype.features['feat-one'].on
    assert prototype.features['feat-two'].on


def test_decorate_class(features, recwarn):
    features({
        'class': Feature('class')
    })
    probe = mock.Mock()

    @prototype_feature('class')
    class FeatureClass:
        def method(self):
            probe('method')

        @staticmethod
        def static():
            probe('static')

        def __ignore__(self):
            probe('ignore')

    with pytest.raises(PrototypeError):
        FeatureClass.static()

    with pytest.raises(PrototypeError):
        FeatureClass().method()

    FeatureClass().__ignore__()
    probe.assert_called_once_with('ignore')
    probe.reset_mock()

    activate_features('class')

    FeatureClass.static()
    probe.assert_called_once_with('static')
    probe.reset_mock()

    FeatureClass().method()
    probe.assert_called_once_with('method')
    probe.reset_mock()

    FeatureClass().__ignore__()
    probe.assert_called_once_with('ignore')


def test_decorator_without_call_errors_out():
    with pytest.raises(PrototypeError) as e:
        @prototype_feature
        def function():
            pass

    assert str(e.value) == "The `prototype_feature` decorator must always be called with the feature name as an " \
                           "argument"


def test_decorator_without_call_around_class():
    with pytest.raises(PrototypeError) as e:
        @prototype_feature
        class Class:
            pass

    assert str(e.value) == "The `prototype_feature` decorator must always be called with the feature name as an " \
                           "argument"


def test_decorator_with_no_arguments_and_class():
    with pytest.raises(PrototypeError) as e:
        @prototype_feature()
        class Class:
            pass

    assert str(e.value) == "The `prototype_feature` decorator must always be called with the feature name as an " \
                           "argument"

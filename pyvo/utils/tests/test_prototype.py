import warnings
from copy import deepcopy
from unittest import mock

import pytest

from pyvo.utils import prototype_feature, turn_off_features, prototype, prototype_warnings_off
from pyvo.utils.prototype import PrototypeError, PrototypeWarning


@pytest.fixture(autouse=True, scope='function')
def prototype_function():
    previous_available = deepcopy(prototype.features)
    prototype.features.clear()

    @prototype_feature('my-feature', url='https:/somewhere/else')
    def i_am_prototype(arg):
        arg('called')

    yield i_am_prototype

    prototype.features.update(previous_available)


def test_warns(prototype_function):
    probe = mock.Mock()
    with pytest.warns(PrototypeWarning) as w:
        prototype_function(probe)

    assert len(w) == 1
    assert str(w[0].message) == 'i_am_prototype is part of the my-feature prototype feature an may ' \
                                'change in the future. Please refer to https:/somewhere/else for details. Use ' \
                                'prototype_warnings_off(my-feature) to mute this warning.'
    probe.assert_called_once_with('called')


def test_turn_off_feature(prototype_function):
    turn_off_features('my-feature')

    with pytest.raises(PrototypeError) as e:
        prototype_function(None)

    assert str(e.value) == 'i_am_prototype is part of an prototype feature (my-feature) that has been turned off.'


def test_non_existent_feature_warning():
    with pytest.warns(PrototypeWarning) as w:
        turn_off_features('i dont exist')

    assert len(w) == 1
    assert str(w[0].message) == 'No such feature "i dont exist"'


def test_turn_off_all_features():
    @prototype_feature
    def func_one():
        pass

    @prototype_feature('feat-one')
    def func_two():
        pass

    turn_off_features()

    # my-feature comes from fixture
    assert set(prototype.features.keys()) == {'feat-one', 'generic', 'my-feature'}
    assert prototype.features['feat-one'].off
    assert prototype.features['my-feature'].off
    assert prototype.features['generic'].off


def test_decorate_class(recwarn):
    probe = mock.Mock()

    @prototype_feature('class')
    class Feature:
        def method(self):
            probe('method')

        @staticmethod
        def static():
            probe('static')

        def __ignore__(self):
            probe('ignore')

    with pytest.warns(PrototypeWarning):
        Feature.static()

    probe.assert_called_once_with('static')
    probe.reset_mock()

    with pytest.warns(PrototypeWarning):
        Feature().method()

    probe.assert_called_once_with('method')
    probe.reset_mock()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Feature().__ignore__()
    probe.assert_called_once_with('ignore')


def test_turn_off_warnings(prototype_function):
    probe = mock.Mock()

    prototype_warnings_off('my-feature')

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        prototype_function(probe)

    probe.assert_called_once_with('called')


def test_decorator_with_no_arguments():
    probe = mock.Mock()

    @prototype_feature
    def function():
        probe('called')

    function()

    probe.assert_called_once_with('called')
    assert prototype.features['generic'].url == ''

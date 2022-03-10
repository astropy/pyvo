import warnings
from copy import deepcopy
from unittest import mock

import pytest

from pyvo.utils import experimental_feature, turn_off_features, experimental, experimental_warnings_off
from pyvo.utils.experimental import ExperimentalError, ExperimentalWarning


@pytest.fixture(autouse=True, scope='function')
def experimental_function():
    previous_available = deepcopy(experimental.features)
    experimental.features.clear()

    @experimental_feature('my-feature', url='https:/somewhere/else')
    def i_am_experimental(arg):
        arg('called')

    yield i_am_experimental

    experimental.features.update(previous_available)


def test_warns(experimental_function):
    probe = mock.Mock()
    with pytest.warns(ExperimentalWarning) as w:
        experimental_function(probe)

    assert len(w) == 1
    assert str(w[0].message) == 'i_am_experimental is part of the my-feature experimental feature an may ' \
                                'change in the future. Please refer to https:/somewhere/else for details. Use ' \
                                'experimental_warnings_off(my-feature) to mute this warning.'
    probe.assert_called_once_with('called')


def test_turn_off_feature(experimental_function):
    turn_off_features('my-feature')

    with pytest.raises(ExperimentalError) as e:
        experimental_function(None)

    assert str(e.value) == 'i_am_experimental is part of an experimental feature (my-feature) that has been turned off.'


def test_non_existent_feature_warning():
    with pytest.warns(ExperimentalWarning) as w:
        turn_off_features('i dont exist')

    assert len(w) == 1
    assert str(w[0].message) == 'No such feature "i dont exist"'


def test_turn_off_all_features():
    @experimental_feature
    def func_one():
        pass

    @experimental_feature('feat-one')
    def func_two():
        pass

    turn_off_features()

    # my-feature comes from fixture
    assert set(experimental.features.keys()) == {'feat-one', 'generic', 'my-feature'}
    assert experimental.features['feat-one'].off
    assert experimental.features['my-feature'].off
    assert experimental.features['generic'].off


def test_decorate_class(recwarn):
    probe = mock.Mock()

    @experimental_feature('class')
    class Feature:
        def method(self):
            probe('method')

        @staticmethod
        def static():
            probe('static')

        def __ignore__(self):
            probe('ignore')

    with pytest.warns(ExperimentalWarning):
        Feature.static()

    probe.assert_called_once_with('static')
    probe.reset_mock()

    with pytest.warns(ExperimentalWarning):
        Feature().method()

    probe.assert_called_once_with('method')
    probe.reset_mock()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Feature().__ignore__()
    probe.assert_called_once_with('ignore')


def test_turn_off_warnings(experimental_function):
    probe = mock.Mock()

    experimental_warnings_off('my-feature')

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        experimental_function(probe)

    probe.assert_called_once_with('called')


def test_decorator_with_no_arguments():
    probe = mock.Mock()

    @experimental_feature
    def function():
        probe('called')

    function()

    probe.assert_called_once_with('called')
    assert experimental.features['generic'].url == ''

import inspect
import warnings
from dataclasses import dataclass
from functools import wraps
from typing import Dict

from pyvo.dal.exceptions import PyvoUserWarning

features: Dict[str, "Feature"] = {}


def experimental_feature(*args, **kwargs):
    """
    docs stub: the decorator, to use with functions or classes to decorate all the "public" methods.
    If given with arguments, the first one is the name of the feature the function belongs to. The keyword
    arguments are passed to the Feature object initializer.
    If given without arguments, the function is added to the 'generic' feature.
    """
    feature_name, decorated = _parse_args(*args)
    features[feature_name] = Feature(name=feature_name, **kwargs)
    decorator = _make_decorator(feature_name)
    return decorator(decorated) if decorated is not None else decorator


def turn_off_features(*feature_names):
    """turn off one or more features. Calls to experimental features will raise an Error. If no arguments are given
    all experimental features are turned off."""
    names = feature_names or set(features.keys())
    for name in names:
        if not _validate(name):
            continue
        features[name].off = True


def experimental_warnings_off(*feature_names):
    """turn off warnings for one or more features. If no arguments are provided all warnings are turned off."""
    names = feature_names or set(features.keys())
    for name in names:
        if not _validate(name):
            continue
        features[name].warn = False


@dataclass
class Feature:
    name: str
    url: str = ''
    off: bool = False
    warn: bool = True

    def warning(self, function_name):
        base = f'{function_name} is part of the {self.name} experimental feature an may change in the future.'
        if self.url:
            base = f'{base} Please refer to {self.url} for details.'
        return f'{base} Use experimental_warnings_off({self.name}) to mute this warning.'

    def error(self, function_name):
        return f'{function_name} is part of an experimental feature ({self.name}) that has been turned off.'


class ExperimentalError(Exception):
    pass


class ExperimentalWarning(PyvoUserWarning):
    pass


def _parse_args(*args):
    if callable(args[0]):
        return 'generic', args[0]
    return args[0], None


def _make_decorator(feature_name):

    def decorator(decorated):
        if inspect.isfunction(decorated):
            return _make_wrapper(feature_name, decorated)

        if inspect.isclass(decorated):
            method_infos = inspect.getmembers(decorated, predicate=_should_wrap)
            _wrap_class_methods(decorated, method_infos, feature_name)

        return decorated

    return decorator


def _validate(feature_name):
    if feature_name not in features:
        warnings.warn(f'No such feature "{feature_name}"', category=ExperimentalWarning)
        return False
    return True


def _warn_or_raise(function, feature_name):
    _validate(feature_name)
    feature = features[feature_name]

    if feature.off:
        raise ExperimentalError(feature.error(function.__name__))
    if feature.warn:
        warnings.warn(feature.warning(function.__name__), category=ExperimentalWarning)


def _should_wrap(member):
    return inspect.isfunction(member) and not member.__name__.startswith('_')


def _wrap_class_methods(decorated_class, method_infos, feature_name):
    for method_info in method_infos:
        setattr(decorated_class, method_info[0], _make_wrapper(feature_name, method_info[1]))


def _make_wrapper(feature_name, function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        _warn_or_raise(function, feature_name)
        return function(*args, **kwargs)
    return wrapper

import inspect
import warnings
from dataclasses import dataclass
from functools import wraps
from typing import Dict

from pyvo.dal.exceptions import PyvoUserWarning

features: Dict[str, "Feature"] = {}


def prototype_feature(*args):
    """
    docs stub: the decorator, to use with functions or classes to decorate all the "public" methods.
    If given with arguments, the first one is the name of the feature the function belongs to. The keyword
    arguments are passed to the Feature object initializer.
    If given without arguments, the function is added to the 'generic' feature.
    """
    feature_name = _parse_args(*args)
    decorator = _make_decorator(feature_name)
    return decorator


def activate_features(*feature_names):
    """activate one or more features. If no arguments are given
    all prototype features are activated."""
    names = feature_names or set(features.keys())
    for name in names:
        if not _validate(name):
            continue
        features[name].on = True


@dataclass
class Feature:
    name: str
    url: str = ''
    on: bool = False

    def should_error(self):
        return not self.on

    def error(self, function_name):
        return f'{function_name} is part of a prototype feature ({self.name}) that has not been activated.'


class PrototypeError(Exception):
    pass


class PrototypeWarning(PyvoUserWarning):
    pass


def _parse_args(*args):
    if not args or callable(args[0]):
        raise PrototypeError("The `prototype_feature` decorator must always be called with the feature name as an "
                             "argument")
    return args[0]


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
        warnings.warn(f'No such feature "{feature_name}"', category=PrototypeWarning)
        return False
    return True


def _warn_or_raise(function, feature_name):
    _validate(feature_name)
    feature = features[feature_name]

    if feature.should_error():
        raise PrototypeError(feature.error(function.__name__))


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

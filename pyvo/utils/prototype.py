import inspect
import warnings
from dataclasses import dataclass
from functools import wraps
from typing import Dict, Iterable

from pyvo.dal.exceptions import PyvoUserWarning

__all__ = ['features', 'prototype_feature', 'activate_features', 'Feature', 'PrototypeWarning', 'PrototypeError']

features: Dict[str, "Feature"] = {

}


def prototype_feature(*args):
    """
    Decorator for functions and classes that implement unstable standards which haven't been approved yet.
    The decorator can be used to tag individual functions or methods::

    Please refer to the user documentation for details.

    Parameters
    ----------
    args: iterable of arguments.
        Currently, the decorator must always be called with one and only one argument, a string representing
        the feature's name associated with the decorated class or functions. Additional arguments will be ignored,
        while using the decorator without any arguments will result in a ``PrototypeError`` error.

    Returns
    -------
    The class or function it decorates, which will be associated to the feature provided as argument.

    """
    feature_name = _parse_args(*args)
    decorator = _make_decorator(feature_name)
    return decorator


def activate_features(*feature_names: Iterable[str]):
    """
    Activate one or more prototype features.

    Parameters
    ----------
    feature_names: Iterable[str]
        An arbitrary number of feature names. If a feature with that name does not exist, a `PrototypeWarning` will
        be issued. If no arguments are provided, all features will be activated

    Returns
    -------

    """
    names = feature_names or set(features.keys())
    for name in names:
        if not _validate(name):
            continue
        features[name].on = True


@dataclass
class Feature:
    """
    A prototype feature implementing a standard that is currently in the process of being approved, but that might
    change as a result of the approval process. A Feature must have a name. Optionally, a feature may have a *url*
    that is displayed to the user in case a feature is used without the user explicitly opting in on its usage.
    The URL is expected to contain more information about the standard and its state in the approval process.
    """
    name: str
    url: str = ''
    on: bool = False

    def should_error(self):
        """
        Should accessing this feature fail?

        Returns
        -------
        bool Whether accessing this feature should result in an error.
        """
        return not self.on

    def error(self, function_name):
        """
        Format an error message when the feature is being accesses without the user having opted in its usage.

        This function will be used as a callback when an error message needs to be displayed to the user, with the
        function name that was accessed as an argument. Extensions of this class may have additional information to
        display.

        Parameters
        ----------
        function_name: str
            The name of the function associated to this feature and that the user called.

        Returns
        -------
        str: The error message to be displayed to the user.

        """
        message = f'{function_name} is part of a prototype feature ({self.name}) that has not been activated. ' \
                  f'For information about prototype features please refer to ' \
                  f'https://pyvo.readthedocs.io/en/latest/prototypes .'
        if self.url:
            message += f' For more information about the {self.name} feature please visit {self.url}.'
        message += f' To suppress this error and enable the feature use `pyvo.utils.activate_features(\'{self.name}\')`'
        return message


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

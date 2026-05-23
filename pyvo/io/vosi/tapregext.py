# Licensed under a 3-clause BSD style license - see LICENSE.rst
from astropy.utils.collections import HomogeneousList
from textwrap import indent

from astropy.io.votable.exceptions import vo_raise, warn_or_raise

from ...utils.xml.elements import (
    Element, ContentMixin, xmlelement, xmlattribute)
from . import voresource as vr
from .exceptions import (
    W05, W06, W19, W20, W21, W26, W27, W28, W29, W30, W31, W38, W39, W40, W41,
    E06, E08, E09, VOSIError)

__all__ = [
    "TAPCapRestriction", "TableAccess", "DataModelType", "Language", "Version",
    "LanguageFeatureList", "LanguageFeature", "OutputFormat", "UploadMethod",
    "TimeLimits", "DataLimits", "DataLimit"]


INDENT = 4 * " "


######################################################################
# ELEMENT CLASSES
class DataModelType(ContentMixin, Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        ivo_id = kwargs.get('ivo-id', None)
        if ivo_id is None:
            warn_or_raise(W26, W26, config=config, pos=pos)
        self.ivo_id = ivo_id

    def __repr__(self):
        return '<DataModel ivo-id={}>{}</DataModel>'.format(
            self.ivo_id, self.content)

    def describe(self):
        """
        Prints out a human readable description
        """
        print(f"Datamodel {self.content}")
        print(indent(self.ivo_id, INDENT))
        print()

    @xmlattribute(name='ivo-id')
    def ivo_id(self):
        """The IVORN of the data model."""
        return self._ivo_id

    @ivo_id.setter
    def ivo_id(self, ivo_id):
        self._ivo_id = ivo_id


class OutputFormat(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        ivo_id = kwargs.get('ivo-id')

        self.mime = None
        self._aliases = HomogeneousList(str)
        self.ivo_id = ivo_id

    def __repr__(self):
        return '<OutputFormat ivo-id={}>{}</OutputFormat>'.format(
            self.ivo_id, self.mime)

    def describe(self):
        """
        Prints out a human readable description
        """
        print(f'Output format {self.mime}')

        if self.aliases:
            print(indent('Also available as {}'.format(', '.join(self.aliases)),
                         INDENT))

        print()

    @xmlelement(plain=True, multiple_exc=W28)
    def mime(self):
        return self._mime

    @mime.setter
    def mime(self, mime):
        self._mime = mime

    @xmlelement(name='alias')
    def aliases(self):
        return self._aliases


class UploadMethod(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        ivo_id = kwargs.get('ivo-id')
        self.ivo_id = ivo_id

    def __repr__(self):
        return f'<UploadMethod ivo-id="{self.ivo_id}"/>'

    def describe(self):
        """
        Prints out a human readable description
        """
        print("Upload method supported")
        print(indent(self.ivo_id, INDENT))
        print()

    @xmlattribute(name='ivo-id')
    def ivo_id(self):
        """The IVORN of the upload model."""
        return self._ivo_id

    @ivo_id.setter
    def ivo_id(self, ivo_id):
        self._ivo_id = ivo_id


class TimeLimits(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        self._default = None
        self._hard = None
        self.for_mode = kwargs.get('forMode', None)

    def __repr__(self):
        mode = f' forMode={self.for_mode}' if self.for_mode else ''
        return '<TimeLimits{} default={} hard={}/>'.format(
            mode, self.default, self.hard)

    @xmlelement(plain=True, multiple_exc=W29)
    def default(self):
        return self._default

    @default.setter
    def default(self, default):
        self._default = int(default)

    @xmlelement(plain=True, multiple_exc=W30)
    def hard(self):
        return self._hard

    @hard.setter
    def hard(self, hard):
        self._hard = int(hard)

    @xmlattribute(name='forMode')
    def for_mode(self):
        return self._for_mode

    @for_mode.setter
    def for_mode(self, for_mode):
        self._for_mode = for_mode


class LanguageFeature(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        self.form = None
        self.description = None

    @xmlelement(plain=True, multiple_exc=W27)
    def form(self):
        return self._form

    @form.setter
    def form(self, form):
        self._form = form

    @xmlelement(plain=True, multiple_exc=W06)
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    def parse(self, iterator, config):
        super().parse(iterator, config)

        if not self.form:
            vo_raise(E09, self._element_name, config=config, pos=self._pos)


class LanguageFeatureList(Element, HomogeneousList):
    def __init__(
        self, config=None, pos=None, _name='languageFeatures', **kwargs
    ):
        Element.__init__(self, config, pos, _name, **kwargs)
        HomogeneousList.__init__(self, LanguageFeature)

        self.type = kwargs.get('type')
        self._features = HomogeneousList(LanguageFeature)

    @xmlattribute
    def type(self):
        return self._type

    @type.setter
    def type(self, type_):
        self._type = type_

    @xmlelement(name='feature', cls=LanguageFeature)
    def features(self):
        return self


class Version(ContentMixin, Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        ivo_id = kwargs.get('ivo-id')
        self.ivo_id = ivo_id

    def __repr__(self):
        return '<Version ivo-id={}>{}</Version>'.format(
            self.ivo_id, self.content)

    @xmlattribute(name='ivo-id')
    def ivo_id(self):
        """The IVORN of the version."""
        return self._ivo_id

    @ivo_id.setter
    def ivo_id(self, ivo_id):
        self._ivo_id = ivo_id


class Language(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        self.name = None
        self._versions = HomogeneousList(Version)
        self.description = None
        self._languagefeaturelists = HomogeneousList(LanguageFeatureList)

    def __repr__(self):
        return f'<Language>{self.name}</Language>'

    def describe(self):
        """
        Prints out a human readable description
        """
        print(f"Language {self.name}")

        for languagefeaturelist in self.languagefeaturelists:
            print(indent(languagefeaturelist.type, INDENT))

            for feature in languagefeaturelist:
                print(indent(feature.form, 2 * INDENT))

                if feature.description:
                    print(indent(feature.description, 3 * INDENT))

                print()

            print()

    def get_feature_list(self, ivoid):
        """
        returns a list of features groupd with the features id ivoid.

        Parameters
        ----------
        ivoid : the ivoid of a TAPRegExt feature list.  It is compared
            case-insensitively against the service's ivoids.

        Returns
        -------
        A (possibly empty) list of `~pyvo.io.vosi.tapregext.LanguageFeature` elements
        """
        ivoid = ivoid.lower()
        for features in self.languagefeaturelists:
            if features.type.lower() == ivoid:
                return features
        return []

    def get_feature(self, ivoid, form):
        """
        returns the `~pyvo.io.vosi.tapregext.LanguageFeature` with ivoid and form if present.

        We return None rather than raising an error because we expect
        the normal pattern of usage here will be "if feature is present",
        and with None-s this is simpler to write than with exceptions.

        Since it's hard to predict the form of UDFs, for those rather
        use the get_udf method.

        ivoid (regrettably) has to be compared case-insensitively;
        form is compared case-sensitively.

        Parameters
        ----------
        ivoid : str
            The IVOA identifier of the feature group the form is in
        form : str
            The form of the feature requested

        Returns
        -------
        A `~pyvo.io.vosi.tapregext.LanguageFeature` or None.
        """
        for feature in self.get_feature_list(ivoid):
            if feature.form == form:
                return feature

        return None

    def get_udf(self, function_name):
        """
        returns a `~pyvo.io.vosi.tapregext.LanguageFeature` corresponding to an ADQL user defined
        function on the server, on None if the UDF is not available.

        This is a bit heuristic in that it tries to parse the form, which
        is specified only so-so.

        Parameters
        ----------
        function_name : str
            A function name.  This is matched against the server's function
            names case-insensitively, as guided by ADQL's case insensitivity.

        Returns:
            A `~pyvo.io.vosi.tapregext.LanguageFeature` instance or None.
        """
        function_name = function_name.lower()
        for udf in self.get_feature_list(
                "ivo://ivoa.net/std/TAPRegExt#features-udf"):
            this_name = udf.form.split("(")[0].strip()
            if this_name.lower() == function_name:
                return udf

        return None

    @xmlelement(plain=True, multiple_exc=W05)
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @xmlelement(name='version', cls=Version)
    def versions(self):
        return self._versions

    @xmlelement(plain=True, multiple_exc=W06)
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @xmlelement(name='languageFeatures', cls=LanguageFeatureList)
    def languagefeaturelists(self):
        return self._languagefeaturelists

    def parse(self, iterator, config):
        super().parse(iterator, config)

        if not self.name:
            vo_raise(E06, self._element_name, config=config, pos=self._pos)

        if not self.versions:
            vo_raise(E08, self._element_name, config=config, pos=self._pos)


class DataLimit(ContentMixin, Element):
    def __init__(self, unit=None, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        self.unit = unit

    def __str__(self):
        return f"{self.unit}:{self.content}"

    @xmlattribute
    def unit(self):
        return self._unit

    @unit.setter
    def unit(self, unit):
        self._unit = unit

    @property
    def content(self):
        return self._content

    @content.setter
    def content(self, content):
        self._content = int(content)

    def parse(self, iterator, config):
        super().parse(iterator, config)

        if self.unit not in ('byte', 'row'):
            warn_or_raise(W31, W31, config=config, pos=self._pos)


class DataLimits(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super().__init__(config=config, pos=pos, **kwargs)

        self.default = None
        self.hard = None
        self.for_mode = kwargs.get('forMode', None)

    def __repr__(self):
        parts = []
        if self.for_mode is not None:
            parts.append(f"forMode={self.for_mode}")
        if self.default is not None:
            parts.append(f"default={self.default}")
        if self.hard is not None:
            parts.append(f"hard={self.hard}")
        return '<DataLimits {}/>'.format(" ".join(parts))

    @xmlelement(cls=DataLimit, multiple_exc=W29)
    def default(self):
        return self._default

    @default.setter
    def default(self, default):
        self._default = default

    @xmlelement(cls=DataLimit, multiple_exc=W30)
    def hard(self):
        return self._hard

    @hard.setter
    def hard(self, hard):
        self._hard = hard

    @xmlattribute(name='forMode')
    def for_mode(self):
        return self._for_mode

    @for_mode.setter
    def for_mode(self, for_mode):
        self._for_mode = for_mode


class TAPCapRestriction(vr.Capability):
    def __init__(
        self, config=None, pos=None, _name='capability', standardID=None,
        **kwargs
    ):
        if standardID != 'ivo://ivoa.net/std/TAP':
            warn_or_raise(W19, W19, config=config, pos=pos)

        super().__init__(
            config, pos, _name, standardID='ivo://ivoa.net/std/TAP', **kwargs)


@vr.Capability.register_xsi_type('tr:TableAccess')
class TableAccess(TAPCapRestriction):
    def __init__(self, config=None, pos=None, _name='capability', **kwargs):
        super().__init__(config, pos, _name, **kwargs)

        self._datamodels = HomogeneousList(DataModelType)
        self._languages = HomogeneousList(Language)
        self._outputformats = HomogeneousList(OutputFormat)
        self._uploadmethods = HomogeneousList(UploadMethod)
        self._retentionperiods = HomogeneousList(TimeLimits)
        self._executiondurations = HomogeneousList(TimeLimits)
        self._outputlimits = HomogeneousList(DataLimits)
        self._uploadlimits = HomogeneousList(DataLimits)

    @staticmethod
    def _get_limit_for_mode(limits, mode=None):
        """
        Returns the limit for the given mode, or the default if no
        mode-specific limit is found.  If there is no default, returns None.

        Parameters
        ----------
        limits : list of `~pyvo.io.vosi.tapregext.TimeLimits` or
            list of `~pyvo.io.vosi.tapregext.DataLimits`
            The limits to search through
        mode : str or None
            The mode to search for.  If None, return the default limit.
        """
        default = None
        mode_specific = None

        for limit in limits:
            if limit.for_mode is None:
                default = limit
            elif mode is not None and limit.for_mode.lower() == mode.lower():
                mode_specific = limit
        return mode_specific if mode_specific is not None else default

    @staticmethod
    def _check_duplicate_modes(limits, exc_class, config):
        seen = set()
        for limit in limits:
            key = limit.for_mode
            if key in seen:
                warn_or_raise(exc_class, args=(key,), config=config,
                              pos=limit._pos)
            seen.add(key)

    def describe(self):
        """
        Prints out a human readable description
        """
        super().describe()

        for datamodel in self.datamodels:
            datamodel.describe()

        for language in self.languages:
            language.describe()

        for outputformat in self.outputformats:
            outputformat.describe()

        for uploadmethod in self.uploadmethods:
            uploadmethod.describe()

        for limit in self._retentionperiods:
            mode = f" ({limit.for_mode})" if limit.for_mode else ""
            print(f"Time a job is kept (in seconds){mode}")
            print(indent(f"Default {limit.default}", INDENT))
            if limit.hard:
                print(indent(f"Maximum {limit.hard}", INDENT))
            print()

        for limit in self._executiondurations:
            mode = f" ({limit.for_mode})" if limit.for_mode else ""
            print(f"Maximal run time of a job{mode}")
            print(indent(f"Default {limit.default}", INDENT))
            if limit.hard:
                print(indent(f"Maximum {limit.hard}", INDENT))
            print()

        for limit in self._outputlimits:
            mode = f" ({limit.for_mode})" if limit.for_mode else ""
            print(f"Maximum size of resultsets{mode}")
            print(indent(f"Default {limit.default.content} {limit.default.unit}", INDENT))
            if limit.hard:
                print(indent(f"Maximum {limit.hard.content} {limit.hard.unit}", INDENT))
            print()

        for limit in self._uploadlimits:
            if limit.hard:
                mode = f" ({limit.for_mode})" if limit.for_mode else ""
                print(f"Maximal size of uploads{mode}")
                print(indent(f"Maximum {limit.hard.content} {limit.hard.unit}", INDENT))
                print()

    def get_adql(self):
        """
        returns the (first) ADQL language element on this service.

        ADQL support is mandatory for IVOA TAP, so in general you can
        rely on this being present.
        """
        for lang in self.languages:
            if lang.name == "ADQL":
                return lang
        raise VOSIError(
            "Invalid TAP service: Does not declare an ADQL language")

    @xmlelement(name='dataModel', cls=DataModelType)
    def datamodels(self):
        """Identifier of IVOA-approved data model supported by the service."""
        return self._datamodels

    @xmlelement(name='language', cls=Language)
    def languages(self):
        """Languages supported by the service."""
        return self._languages

    @xmlelement(name='outputFormat', cls=OutputFormat)
    def outputformats(self):
        """Output formats supported by the service."""
        return self._outputformats

    @xmlelement(name='uploadMethod', cls=UploadMethod)
    def uploadmethods(self):
        """
        Upload methods supported by the service.

        The absence of upload methods indicates that the service does not
        support uploads at all.
        """
        return self._uploadmethods

    @xmlelement(name='retentionPeriod', cls=TimeLimits)
    def retentionperiods(self):
        """Limits on the time between job creation and destruction time."""
        return self._retentionperiods

    @xmlelement(name='executionDuration', cls=TimeLimits)
    def executiondurations(self):
        """Limits on executionDuration."""
        return self._executiondurations

    @xmlelement(name='outputLimit', cls=DataLimits)
    def outputlimits(self):
        """Limits on the size of data returned."""
        return self._outputlimits

    @xmlelement(name='uploadLimit', cls=DataLimits)
    def uploadlimits(self):
        return self._uploadlimits

    def _get_limit_compat(self, limits):
        """Return the default limit, falling back to the first entry if no
        default exists."""
        result = self._get_limit_for_mode(limits)
        if result is None and limits:
            return limits[0]
        return result

    @property
    def retentionperiod(self):
        """The default retentionPeriod limit."""
        return self._get_limit_compat(self._retentionperiods)

    @property
    def executionduration(self):
        """The default executionDuration limit."""
        return self._get_limit_compat(self._executiondurations)

    @property
    def outputlimit(self):
        """The default outputLimit."""
        return self._get_limit_compat(self._outputlimits)

    @property
    def uploadlimit(self):
        """The default uploadLimit."""
        return self._get_limit_compat(self._uploadlimits)

    def get_retentionperiod(self, mode=None):
        """Get retentionPeriod limit for a specific mode."""
        return self._get_limit_for_mode(self._retentionperiods, mode)

    def get_executionduration(self, mode=None):
        """Get executionDuration limit for a specific mode."""
        return self._get_limit_for_mode(self._executiondurations, mode)

    def get_outputlimit(self, mode=None):
        """Get outputLimit for a specific mode."""
        return self._get_limit_for_mode(self._outputlimits, mode)

    def get_uploadlimit(self, mode=None):
        """Get uploadLimit for a specific mode."""
        return self._get_limit_for_mode(self._uploadlimits, mode)

    def parse(self, iterator, config):
        super().parse(iterator, config)

        if not self.languages:
            warn_or_raise(W20, W20, config=config, pos=self._pos)

        if not self.outputformats:
            warn_or_raise(W21, W21, config=config, pos=self._pos)

        self._check_duplicate_modes(self.retentionperiods, W38, config)
        self._check_duplicate_modes(self.executiondurations, W39, config)
        self._check_duplicate_modes(self.outputlimits, W40, config)
        self._check_duplicate_modes(self.uploadlimits, W41, config)

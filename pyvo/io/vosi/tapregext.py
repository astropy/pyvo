# Licensed under a 3-clause BSD style license - see LICENSE.rst
from astropy.utils.collections import HomogeneousList
from astropy.utils.misc import indent

from astropy.io.votable.exceptions import vo_raise, warn_or_raise

from ...utils.xml.elements import (
    Element, ContentMixin, xmlelement, xmlattribute)
from . import voresource as vr
from .exceptions import (
    W05, W06, W19, W20, W21, W22, W23, W24, W25, W26, W27, W28, W29, W30, W31,
    E06, E08, E09)

__all__ = [
    "TAPCapRestriction", "TableAccess", "DataModelType", "Language", "Version",
    "LanguageFeatureList", "LanguageFeature", "OutputFormat", "UploadMethod",
    "TimeLimits", "DataLimits", "DataLimit"]


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
        print("Datamodel {}".format(self.content))
        print(indent(self.ivo_id))
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
        print('Output format {}'.format(self.mime))

        if self.aliases:
            print(indent('Also available as {}'.format(
                ', '.join(self.aliases))))

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
        return '<UploadMethod ivo-id="{}"/>'.format(self.ivo_id)

    def describe(self):
        """
        Prints out a human readable description
        """
        print("Upload method supported")
        print(indent(self.ivo_id))
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

    def __repr__(self):
        return '<TimeLimits default={} hard={}/>'.format(
            self.default, self.hard)

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
        return '<Language>{}</Language>'.format(self.name)

    def describe(self):
        """
        Prints out a human readable description
        """
        print("Language {}".format(self.name))

        for languagefeaturelist in self.languagefeaturelists:
            print(indent(languagefeaturelist.type))

            for feature in languagefeaturelist:
                print(indent(feature.form, shift=2))

                if feature.description:
                    print(indent(feature.description, shift=3))

                print()

            print()

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

    def __repr__(self):
        return '<DataLimits default={}:{} hard={}:{}/>'.format(
            self.default.unit,
            self.default.content,
            self.hard.unit,
            self.hard.content
        )

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
        self.retentionperiod = None
        self.executionduration = None
        self.outputlimit = None
        self.uploadlimit = None

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

        if self.retentionperiod:
            print("Time a job is kept (in seconds)")
            print(indent("Default {}".format(self.retentionperiod.default)))
            if self.retentionperiod.hard:
                print(indent("Maximum {}".format(self.retentionperiod.hard)))
            print()

        if self.executionduration:
            print("Maximal run time of a job")
            print(indent("Default {}".format(self.executionduration.default)))
            if self.executionduration.hard:
                print(indent("Maximum {}".format(self.executionduration.hard)))
            print()

        if self.outputlimit:
            print("Maximum size of resultsets")
            print(indent("Default {} {}".format(
                self.outputlimit.default.content,
                self.outputlimit.default.unit))
            )
            if self.outputlimit.hard:
                print(indent("Maximum {} {}".format(
                    self.outputlimit.hard.content, self.outputlimit.hard.unit))
                )
            print()

        if self.uploadlimit:
            print("Maximal size of uploads")
            print(indent("Maximum {} {}".format(
                self.uploadlimit.hard.content, self.uploadlimit.hard.unit)))
            print()

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

    @xmlelement(name='retentionPeriod', cls=TimeLimits, multiple_exc=W22)
    def retentionperiod(self):
        """Limits on the time between job creation and destruction time."""
        return self._retentionperiod

    @retentionperiod.setter
    def retentionperiod(self, retentionperiod):
        self._retentionperiod = retentionperiod

    @xmlelement(name='executionDuration', cls=TimeLimits, multiple_exc=W23)
    def executionduration(self):
        """Limits on executionDuration."""
        return self._executionduration

    @executionduration.setter
    def executionduration(self, executionduration):
        self._executionduration = executionduration

    @xmlelement(name='outputLimit', cls=DataLimits, multiple_exc=W24)
    def outputlimit(self):
        """Limits on the size of data returned."""
        return self._outputlimit

    @outputlimit.setter
    def outputlimit(self, outputlimit):
        self._outputlimit = outputlimit

    @xmlelement(name='uploadLimit', cls=DataLimits, multiple_exc=W25)
    def uploadlimit(self):
        return self._uploadlimit

    @uploadlimit.setter
    def uploadlimit(self, uploadlimit, cls=DataLimits):
        self._uploadlimit = uploadlimit

    def parse(self, iterator, config):
        super().parse(iterator, config)

        if not self.languages:
            warn_or_raise(W20, W20, config=config, pos=self._pos)

        if not self.outputformats:
            warn_or_raise(W21, W21, config=config, pos=self._pos)

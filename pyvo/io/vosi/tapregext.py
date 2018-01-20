# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

from astropy.extern import six

from astropy.utils.collections import HomogeneousList
from astropy.utils.xml import check as xml_check
from astropy.utils.misc import indent

from astropy.io.votable.exceptions import vo_raise, vo_warn, warn_or_raise

from .util import (
    make_add_simplecontent, make_add_complexcontent, Element, ValueMixin)
from . import voresource as vr
from .exceptions import (
    W01, W02, W03, W04, W05, W06, W07, W08, W09, W10, W11, W12, W13, W14, W15,
    W16, W17, W18, W19, W20, W21, W22, W23, W24, W25, W26, W27, W28, W29, W30,
    W31,
    E01, E02, E03, E04, E05, E06, E07, E08, E09)

__all__ = [
    "TAPCapRestriction", "TableAccess", "DataModelType", "Language", "Version",
    "LanguageFeatureList", "LanguageFeature", "OutputFormat", "UploadMethod",
    "TimeLimits", "DataLimits", "DataLimit"]

######################################################################
# ELEMENT CLASSES
class TAPCapRestriction(vr.Capability):
    def __init__(self, standardID=None, config=None, pos=None, **kwargs):
        if standardID != 'ivo://ivoa.net/std/TAP':
            warn_or_raise(W19, W19, config=config, pos=pos)

        super(TAPCapRestriction, self).__init__(
            standardID='ivo://ivoa.net/std/TAP')


@vr.Capability.register_xsi_type('tr:TableAccess')
class TableAccess(TAPCapRestriction):
    def __init__(self, config=None, pos=None, **kwargs):
        super(TableAccess, self).__init__(config=config, pos=None, **kwargs)

        self._tag_mapping.update({
            "dataModel": make_add_complexcontent(
                self, "dataModel", "datamodels", DataModelType),
            "language": make_add_complexcontent(
                self, "language", "languages", Language),
            "outputFormat": make_add_complexcontent(
                self, "outputFormat", "outputformats", OutputFormat),
            "uploadMethod": make_add_complexcontent(
                self, "uploadMethod", "uploadmethods", UploadMethod),
            "retentionPeriod": make_add_complexcontent(
                self, "retentionPeriod", "retentionperiod", TimeLimits, W22),
            "executionDuration": make_add_complexcontent(
                self, "executionDuration", "executionduration", TimeLimits,
                W23),
            "outputLimit": make_add_complexcontent(
                self, "outputLimit", "outputlimit", DataLimits, W24),
            "uploadLimit": make_add_complexcontent(
                self, "uploadLimit", "uploadlimit", DataLimits, W25)
        })

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
        super(TableAccess, self).describe()

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
                print(indent("Maximum {}".fornat(self.retentionperiod.hard)))
            print()

        if self.executionduration:
            print("Maximal run time of a job")
            print(indent("Default {}".format(self.executionduration.default)))
            if self.executionduration.hard:
                print(indent("Maximum {}".fornat(self.executionduration.hard)))
            print()

        if self.outputlimit:
            print("Maximum size of resultsets")
            print(indent("Default {} {}".format(
                self.outputlimit.default.value, self.outputlimit.default.unit)))
            if self.outputlimit.hard:
                print(indent("Maximum {} {}".format(
                    self.outputlimit.hard.value, self.outputlimit.hard.unit)))
            print()

        if self.uploadlimit:
            print("Maximal size of uploads")
            print(indent("Maximum {} {}".format(
                self.uploadlimit.hard.value, self.uploadlimit.hard.unit)))
            print()

    @property
    def datamodels(self):
        """Identifier of IVOA-approved data model supported by the service."""
        return self._datamodels

    @property
    def languages(self):
        """Languages supported by the service."""
        return self._languages

    @property
    def outputformats(self):
        """Output formats supported by the service."""
        return self._outputformats

    @property
    def uploadmethods(self):
        """
        Upload methods supported by the service.

        The absence of upload methods indicates that the service does not
        support uploads at all.
        """
        return self._uploadmethods

    @property
    def retentionperiod(self):
        """Limits on the time between job creation and destruction time."""
        return self._retentionperiod

    @retentionperiod.setter
    def retentionperiod(self, retentionperiod):
        self._retentionperiod = retentionperiod

    @property
    def executionduration(self):
        """Limits on executionDuration."""
        return self._executionduration

    @executionduration.setter
    def executionduration(self, executionduration):
        self._executionduration = executionduration

    @property
    def outputlimit(self):
        """Limits on the size of data returned."""
        return self._outputlimit

    @outputlimit.setter
    def outputlimit(self, outputlimit):
        self._outputlimit = outputlimit

    @property
    def uploadlimit(self):
        return self._uploadlimit

    @uploadlimit.setter
    def uploadlimit(self, uploadlimit):
        self._uploadlimit = uploadlimit

    def parse(self, iterator, config):
        super(TableAccess, self).parse(iterator, config)

        if not self.languages:
            warn_or_raise(W20, W20, config=config, pos=self._pos)

        if not self.outputformats:
            warn_or_raise(W21, W21, config=config, pos=self._pos)


class DataModelType(ValueMixin, Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(DataModelType, self).__init__(config=config, pos=pos, **kwargs)

        ivo_id = kwargs.get('ivo-id', None)
        if ivo_id is None:
            warn_or_raise(W26, W26, config=config, pos=pos)
        self.ivo_id = ivo_id

    def __repr__(self):
        return '<DataModel ivo-id={}>{}</DataModel>'.format(
            self.ivo_id, self.value)

    def describe(self):
        """
        Prints out a human readable description
        """
        print("Datamodel {}".format(self.value))
        print(indent(self.ivo_id))
        print()

    @property
    def ivo_id(self):
        """The IVORN of the data model."""
        return self._ivo_id

    @ivo_id.setter
    def ivo_id(self, ivo_id):
        self._ivo_id = ivo_id


class Language(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(Language, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "name": make_add_simplecontent(self, "name", "name", W05),
            "version": make_add_complexcontent(
                self, "version", "versions", Version),
            "description": make_add_simplecontent(
                self, "description", "description", W06),
            "languageFeatures": make_add_complexcontent(
                self, "languageFeatures", "languagefeaturelists",
                LanguageFeatureList)
        })

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

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def versions(self):
        return self._versions

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    @property
    def languagefeaturelists(self):
        return self._languagefeaturelists

    def parse(self, iterator, config):
        super(Language, self).parse(iterator, config)

        if not self.name:
            vo_raise(E06, self._element_name, config=config, pos=self._pos)

        if not self.versions:
            vo_raise(E08, self._element_name, config=config, pos=self._pos)


class Version(ValueMixin, Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(Version, self).__init__(config=config, pos=pos, **kwargs)

        ivo_id = kwargs.get('ivo-id')
        self.ivo_id = ivo_id

    def __repr__(self):
        return '<Version ivo-id={}>{}</Version>'.format(self.ivo_id, self.value)

    @property
    def ivo_id(self):
        """The IVORN of the data model."""
        return self._ivo_id

    @ivo_id.setter
    def ivo_id(self, ivo_id):
        self._ivo_id = ivo_id


class LanguageFeatureList(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(LanguageFeatureList, self).__init__(
            config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "feature": make_add_complexcontent(
                self, "feature", "features", LanguageFeature)
        })

        self.type = kwargs.get('type')
        self._features = HomogeneousList(LanguageFeature)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, index):
        return self.features[index]

    def __iter__(self):
        return iter(self.features)

    def __repr__(self):
        return (
            '<LanguageFeatureList>'
            '... {} features ...'
            '</LanguageFeatureList'
        ).format(len(self.features))

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, type_):
        self._type = type_

    @property
    def features(self):
        return self._features


class LanguageFeature(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(LanguageFeature, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "form": make_add_simplecontent(self, "form", "form", W27),
            "description": make_add_simplecontent(
                self, "description", "description", W06)
        })

        self.form = None
        self.description = None

    @property
    def form(self):
        return self._form

    @form.setter
    def form(self, form):
        self._form = form

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, description):
        self._description = description

    def parse(self, iterator, config):
        super(LanguageFeature, self).parse(iterator, config)

        if not self.form:
            vo_raise(E09, self._element_name, config=config, pos=self._pos)


class OutputFormat(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(OutputFormat, self).__init__(config=config, pos=pos, **kwargs)
        
        ivo_id = kwargs.get('ivo-id')

        self._tag_mapping.update({
            "mime": make_add_simplecontent(self, "mime", "mime", W28),
            "alias": make_add_simplecontent(self, "alias", "aliases")
        })

        self.mime = None
        self._aliases = HomogeneousList(six.text_type)
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

    @property
    def mime(self):
        return self._mime

    @mime.setter
    def mime(self, mime):
        self._mime = mime

    @property
    def aliases(self):
        return self._aliases


class UploadMethod(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(UploadMethod, self).__init__(config=config, pos=pos, **kwargs)

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

    @property
    def ivo_id(self):
        """The IVORN of the upload model."""
        return self._ivo_id

    @ivo_id.setter
    def ivo_id(self, ivo_id):
        self._ivo_id = ivo_id


class TimeLimits(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(TimeLimits, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "default": make_add_simplecontent(
                self, "default", "default", W29, data_func=int),
            "hard": make_add_simplecontent(
                self, "hard", "hard", W30, data_func=int)
        })

        self.default = None
        self.hard = None

    def __repr__(self):
        return '<TimeLimits default={} hard={}/>'.format(
            self.default, self.hard)

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, default):
        self._default = default

    @property
    def hard(self):
        return self._hard

    @hard.setter
    def hard(self, hard):
        self._hard = hard


class DataLimits(Element):
    def __init__(self, config=None, pos=None, **kwargs):
        super(DataLimits, self).__init__(config=config, pos=pos, **kwargs)

        self._tag_mapping.update({
            "default": make_add_complexcontent(
                self, "default", "default", DataLimit, W29),
            "hard": make_add_complexcontent(
                self, "hard", "hard", DataLimit, W30)
        })

        self.default = None
        self.hard = None

    def __repr__(self):
        return '<DataLimits default={}:{} hard={}:{}/>'.format(
            self.default.unit,
            self.default.value,
            self.hard.unit,
            self.hard.value
        )

    @property
    def default(self):
        return self._default

    @default.setter
    def default(self, default):
        self._default = default

    @property
    def hard(self):
        return self._hard

    @hard.setter
    def hard(self, hard):
        self._hard = hard


class DataLimit(ValueMixin, Element):
    def __init__(self, unit=None, config=None, pos=None, **kwargs):
        super(DataLimit, self).__init__(config=config, pos=pos, **kwargs)

        self.unit = unit

    def _value_parse(self, value):
        return int(value)

    def parse(self, iterator, config):
        super(DataLimit, self).parse(iterator, config)

        if self.unit not in ('byte', 'row'):
            warn_or_raise(W31, W31, config=config, pos=self._pos)

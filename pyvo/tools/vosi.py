# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import unicode_literals
from . import plainxml
import datetime
from collections import OrderedDict
from astropy.table import Table, Column
from astropy.io.votable.converters import get_converter
import numpy as np

class _CapabilitiesParser(plainxml.StartEndHandler):
# VOSI; each capability is a dict with at least a key interfaces.
# each interface is a dict with key type (namespace prefix not expanded;
# change that?), accessURL, and use.
	def __init__(self):
		plainxml.StartEndHandler.__init__(self)
		self.capabilities = []

	def _start_capability(self, name, attrs):
		self.curCap = {
			"interfaces": [],
			"dataModels": [],
			"languages": [],
			"outputFormats": [],
			"uploadMethods": [],
			"retentionPeriod": {},
			"executionDuration": {}
		}
		self.curCap["standardID"] = attrs.get("standardID")

	def _end_capability(self, name, attrs, content):
		self.capabilities.append(self.curCap)
		self.curCap = None

	def _start_interface(self, name, attrs):
		attrs = plainxml._pruneAttrNS(attrs)
		self.curInterface = {"type": attrs.get("type"), "role": attrs.get("role")}

	def _end_interface(self,name, attrs, content):
		self.curCap["interfaces"].append(self.curInterface)
		self.curInterface = None

	def _start_dataModel(self, name, attrs):
		pass

	def _end_dataModel(self, name, attrs, content):
		self.curCap["dataModels"].append(content)

	def _start_language(self, name, attrs):
		self.curLang = {
			"name": "",
			"version": "",
			"description": "",
			"languageFeatures": []
		}

	def _end_language(self, name, attrs, content):
		self.curCap["languages"].append(self.curLang)
		self.curLang = None

	def _start_languageFeatures(self, name, attrs):
		attrs = plainxml._pruneAttrNS(attrs)
		self.curLanguageFeatures = {
			"type": attrs["type"],
			"features": []
		}

	def _end_languageFeatures(self, name, attrs, content):
		self.curLang["languageFeatures"] = self.curLang.get(
			"languageFeatures", []) + [self.curLanguageFeatures]
		self.curLanguageFeatures = None

	def _start_feature(self, name, attrs):
		self.curFeature = {
			"form": "",
			"description": ""
		}

	def _end_feature(self, name, attrs, content):
		self.curLanguageFeatures["features"].append(self.curFeature)
		self.curFeature = None

	def _start_outputFormat(self, name, attrs):
		self.curOutputFormat = {
			"mime": "",
			"alias": ""
		}

	def _end_outputFormat(self, name, attrs, content):
		self.curCap["outputFormats"].append(self.curOutputFormat)
		self.curOutputFormat = None

	def _start_uploadMethod(self, name, attrs):
		attrs = plainxml._pruneAttrNS(attrs)
		self.curCap["uploadMethods"].append(attrs["ivo-id"])

	def _end_uploadMethod(self, name, attrs, content):
		pass

	def _start_retentionPeriod(self, name, attrs):
		self.curRetentionPeriod = {
			"default": ""
		}

	def _end_retentionPeriod(self, name, attrs, content):
		self.curCap["retentionPeriod"] = self.curRetentionPeriod
		self.curRetentionPeriod = None

	def _start_executionDuration(self, name, content):
		self.curExecutionDuration = {
			"default": 0
		}

	def _end_executionDuration(self, name, attrs, content):
		self.curCap["executionDuration"] = self.curExecutionDuration
		self.curExecutionDuration = None

	def _start_outputLimit(self, name, attrs):
		self.curOutputLimit = {
			"default": {},
			"hard": {}
		}

	def _end_outputLimit(self, name, attrs, content):
		self.curCap["outputLimit"] = self.curOutputLimit
		self.curOutputLimit = None

	def _start_uploadLimit(self, name, attrs):
		self.curUploadLimit = {
			"hard": {}
		}

	def _end_uploadLimit(self, name, attrs, content):
		self.curCap["uploadLimit"] = self.curUploadLimit
		self.curUploadLimit = None

	def _end_accessURL(self, name, attrs, content):
		self.curInterface["accessURL"] = content.strip()
		self.curInterface["use"] = attrs.get("use")

	def _end_name(self, name, attrs, content):
		if self.curLang is not None:
			self.curLang["name"] = content.strip()

	def _end_version(self, name, attrs, content):
		if self.curLang is not None:
			self.curLang["version"] = content.strip()

	def _end_description(self, name, attrs, content):
		if getattr(self, "curFeature", None) is not None:
			self.curFeature["description"] = content.strip()
		elif self.curLang is not None:
			self.curLang["description"] = content.strip()

	def _end_form(self, name, attrs, content):
		if self.curFeature is not None:
			self.curFeature["form"] = content.strip()

	def _end_mime(self, name, attrs, content):
		if self.curOutputFormat is not None:
			self.curOutputFormat["mime"] = content.strip()

	def _end_alias(self, name, attrs, content):
		if self.curOutputFormat is not None:
			self.curOutputFormat["alias"] = content.strip()

	def _end_default(self, name, attrs, content):
		if getattr(self, "curRetentionPeriod", None) is not None:
			self.curRetentionPeriod["default"] = int(content.strip())
		elif getattr(self, "curExecutionDuration", None) is not None:
			self.curExecutionDuration["default"] = int(content.strip())
		elif getattr(self, "curOutputLimit", None) is not None:
			self.curOutputLimit["default"] = {
				"unit": attrs["unit"],
				"value": int(content.strip())
			}

	def _end_hard(self, name, attrs, content):
		if getattr(self, "curOutputLimit", None) is not None:
			self.curOutputLimit["hard"] = {
				"unit": attrs["unit"],
				"value": int(content.strip())
			}
		elif getattr(self, "curUploadLimit", None) is not None:
			self.curUploadLimit["hard"] = {
				"unit": attrs["unit"],
				"value": int(content.strip())
			}

	def getResult(self):
		return self.capabilities

def parse_capabilities(stream):
	parser = _CapabilitiesParser()
	parser.parse(stream)
	return parser.getResult()


class _TablesParser(plainxml.StartEndHandler):
	def __init__(self):
		plainxml.StartEndHandler.__init__(self)
		self.tables = OrderedDict()

	def _start_schema(self, name, attrs):
		self.curSchema = ""

	def _end_schema(self, name, attrs, content):
		self.curSchema = None

	def _start_table(self, name, attrs):
		self.curTable = Table()

	def _end_table(self, name, attrs, content):
		table_name = self.curTable.meta["name"]
		self.tables[table_name] = self.curTable
		self.curTable = None

	def _start_column(self, name, attrs):
		self.inColumn = True

	def _end_column(self, name, attrs, content):
		column = Column(
			name = self.curColumn, dtype = self.curDtype,
			description = self.curDescription,
			unit = getattr(self, "curUnit", None))
		column.meta["ucd"] = self.curUcd
		column.meta["datatype"] = self.curDatatype
		column.meta["arraysize"] = self.curArraysize
		self.curTable[self.curColumn] = column
		self.inColumn = False

	def _end_name(self, name, attrs, content):
		content = content.strip()

		if getattr(self, "inColumn", False):
			self.curColumn = content
		elif getattr(self, "curTable", None) is not None:
			self.curTable.meta["name"] = content

	def _end_description(self, name, attrs, content):
		content = content.strip()

		if getattr(self, "inColumn", False):
			self.curDescription = content

	def _end_ucd(self, name, attrs, content):
		content = content.strip()

		if getattr(self, "inColumn", False):
			self.curUcd = content

	def _end_dataType(self, name, attrs, content):
		content = content.strip()

		class _values(object):
			null = None

		class _field(object):
			datatype = content
			arraysize = attrs.get("arraysize") if content in (
				"char", "unicodeChar") else None
			precision = None
			width = None
			values = _values()


		converter = get_converter(_field())
		self.curDtype = np.dtype(converter.format)
		self.curDatatype = content
		self.curArraysize = attrs.get("arraysize")

	def _end_unit(self, name, attrs, content):
		content = content.strip()

		if getattr(self, "inColumn", False):
			self.curUnit = content

	def getResult(self):
		return self.tables


def parse_tables(stream):
	parser = _TablesParser()
	parser.parse(stream)
	return parser.getResult()


class _AvailabiliyParser(plainxml.StartEndHandler):
	def __init__(self):
		plainxml.StartEndHandler.__init__(self)

		self.available = False
		self.up_since = None

	def _end_available(self, name, attrs, content):
		content = content.strip()
		self.available = content == "true"

	def _end_upSince(self, name, attrs, content):
		content = content.strip()

		self.up_since = datetime.datetime.strptime(
			content, "%Y-%m-%dT%H:%M:%SZ")

	def getResult(self):
		return (self.available, self.up_since)

def parse_availability(stream):
	parser = _AvailabiliyParser()
	parser.parse(stream)
	return parser.getResult()

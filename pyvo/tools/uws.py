# Licensed under a 3-clause BSD style license - see LICENSE.rst
import dateutil.parser
from . import plainxml

class _JobParser(plainxml.StartEndHandler):
	def __init__(self):
		plainxml.StartEndHandler.__init__(self)
		self.job = {}

	def _end_jobId(self, name, attrs, content):
		self.job["jobId"] = content.strip()

	def _end_ownerId(self, name, attrs, content):
		self.job["ownerId"] = content.strip()

	def _end_phase(self, name, attrs, content):
		self.job["phase"] = content.strip()

	def _end_quote(self, name, attrs, content):
		self.job["quote"] = content.strip()

	def _end_startTime(self, name, attrs, content):
		self.job["startTime"] = content.strip()

	def _end_endTime(self, name, attrs, content):
		self.job["endTime"] = content.strip()

	def _end_executionDuration(self, name, attrs, content):
		self.job["executionDuration"] = content.strip()

	def _end_destruction(self, name, attrs, content):
		self.job["destruction"] = dateutil.parser.parse(content.strip())

	def _end_message(self, name, attrs, content):
		self.job["message"] = content.strip()

	def _start_results(self, name, attrs):
		if not self.job.get("results", None):
			self.job["results"] = dict()

	def _start_result(self, name, attrs):
		id = attrs["id"]
		href = attrs["xlink:href"]
		self.job["results"][id] = href

	def getResult(self):
		return self.job

def parse_job(stream):
	parser = _JobParser()
	parser.parse(stream)
	return parser.getResult()

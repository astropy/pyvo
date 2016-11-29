import contextlib
import os
import sys
import tempfile
import time

import astropy
from astropy.vo.samp import SAMPIntegratedClient
from pyvo.dal import scs
from pyvo.registry import regtap


@contextlib.contextmanager
def samp_accessible(astropy_table):
	"""a context manager making astroy_table available under a (file)
	URL for the controlled section.

	This is useful with uploads.
	"""
	handle, f_name = tempfile.mkstemp(suffix=".xml")
	with os.fdopen(handle, "w") as f:
		astropy_table.write(output=f,
			format="votable")
	try:
		yield "file://"+f_name
	finally:
		os.unlink(f_name)


@contextlib.contextmanager
def SAMP_conn():
	"""a context manager to give the controlled block a SAMP connection.

	The program will disconnect as the controlled block is exited.
	"""
	client = SAMPIntegratedClient(name="serialquery", 
		description="A serial SCS querier.")
	client.connect()
	try:
		yield client
	finally:
		client.disconnect()


def broadcast(astropy_table):
	"""broadcasts an astropy table object to all SAMP clients on the local
	bus.
	"""
	with SAMP_conn() as client:
		with samp_accessible(astropy_table) as table_url:
			client.notify_all(
				{
					"samp.mtype": "table.load.votable",
					"samp.params": {
						"url": table_url,
					}})
			time.sleep(2)  # hack: give other clients time to pick our table up


def main(ra, dec, sr):
	for resource in regtap.search(
		keywords=["standard stars"], servicetype="image"
	):
		print(resource.res_title)
		result = resource.service.search((ra, dec), sr)
		print(len(result))
		if result:
			break
	else:
		sys.exit("No service has results for CIRCLE({0}, {1}, {2})".format(
			ra, dec, sr))
	broadcast(result.table)


if __name__=="__main__":
	# serialquery.py RA DEC SR
	main(*[float(v) for v in sys.argv[1:]])


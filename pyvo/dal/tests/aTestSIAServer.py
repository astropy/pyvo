#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a test DAL server for testing pyvo.dal
"""
from __future__ import print_function, division

# this gets around a bug in astropy 0.2.4 (needed for python3 support)
from ... import dal

import os
import sys
import shutil
import re
import threading
import socket
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from astropy.utils.data import get_pkg_data_filename

siaresult = "data/neat-sia.xml"
scsresult = "data/twomass-cs.xml"
errresult = "data/error-sia.xml"
ssaresult = "data/jhu-ssa.xml"
slaresult = "data/nrao-sla.xml"

class TestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        path = re.split(r'\?', self.path, 1)[0]

        if path.startswith("/path"):
            self.send_path()
        elif path.startswith("/dal/"):
            self.send_file(path[len("/dal/"):])
        elif path.startswith("/err"):
            self.send_err()
        elif path == "/sia":
            self.send_sia()
        elif path == "/cs":
            self.send_scs()
        elif path == "/ssa":
            self.send_ssa()
        elif path == "/sla":
            self.send_sla()
        elif path == "/shutdown":
            self.send_empty()
            # self.shutdown()
        else:
            try:
                self.send_error(404)
                self.end_headers()
            except socket.error as ex:
                if ex.errno != 104:
                    print("Test Server: Detected socket error while serving "+
                          path+": " + str(ex))
                

    def send_path(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Content-Length", len(self.path)+1)
        self.end_headers()
        self.wfile.write(self.path+"\n")

    def send_err(self):
        self.send_file(errresult)

    def send_sia(self):
        self.send_file(siaresult)

    def send_scs(self):
        self.send_file(scsresult)

    def send_ssa(self):
        self.send_file(ssaresult)

    def send_sla(self):
        self.send_file(slaresult)

    def send_file(self, filename):
        path = get_pkg_data_filename(filename)
        f = open(path,'rb')

        self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.send_header("Content-Length", os.fstat(f.fileno())[6])
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)

    def send_empty(self):
        self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.send_header("Content-Length", 0)
        self.end_headers()

    def log_message(format, *args):
        pass

class TestServer(threading.Thread):

    def __init__(self, port=8081, timeout=5):
        threading.Thread.__init__(self)
        self._port = port
        self._timeout = timeout
        self.httpd = None


    def run(self):
        self.httpd = HTTPServer(('', self._port), TestHandler)
        self.httpd.timeout = self._timeout
        self.httpd.serve_forever()

    def shutdown(self, timeout=None):
        if not timeout:
            timeout = self._timeout+1
        if self.httpd:  
            self.httpd.shutdown()
            self.join(timeout)
            self.httpd = None

def run():
    httpd = HTTPServer(('', 8081), TestHandler)
    httpd.timeout = 12
    httpd.handle_request()
    # httpd.serve_forever()
    # os.sleep(12)
    # httpd.shutdown()

if __name__ == "__main__":
    run()



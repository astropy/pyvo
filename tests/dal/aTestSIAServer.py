#!/usr/bin/env python
"""
a test DAL server for testing dal.query
"""
import os
import sys
import shutil
import re
import threading
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

testdir = os.path.dirname(sys.argv[0])
if not testdir:
    testdir = "tests"
siaresult = "neat-sia.xml"
scsresult = "twomass-cs.xml"
errresult = "error-sia.xml"
ssaresult = "jhu-ssa.xml"
slaresult = "nrao-sla.xml"


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
        else:
            self.send_error(404)
            self.end_headers()

    def send_path(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Content-Length", len(self.path)+1)
        self.end_headers()
        self.wfile.write(self.path+"\n")

    def send_err(self):
        self.send_file(os.path.join(testdir,errresult))

    def send_sia(self):
        self.send_file(os.path.join(testdir,siaresult))

    def send_scs(self):
        self.send_file(os.path.join(testdir,scsresult))

    def send_ssa(self):
        self.send_file(os.path.join(testdir,ssaresult))

    def send_sla(self):
        self.send_file(os.path.join(testdir,slaresult))

    def send_file(self, filename):
        f = open(filename)

        self.send_response(200)
        self.send_header("Content-type", "text/xml")
        self.send_header("Content-Length", os.fstat(f.fileno())[6])
        self.end_headers()
        shutil.copyfileobj(f, self.wfile)

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

    def shutdown(self):
        if self.httpd:
            self.httpd.shutdown()
            self.join(self._timeout+1)
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

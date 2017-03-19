#!/usr/bin/env python
# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
a test DAL server for testing pyvo.dal
"""
from __future__ import (
    absolute_import, division, print_function, unicode_literals)

import os
import multiprocessing
import requests
from flask import Flask, render_template, request, redirect

try:
    from astropy.tests.disable_internet import (turn_on_internet,
                                                turn_off_internet, INTERNET_OFF)
except:
    # for astropy ver < 0.4
    def turn_on_internet(verbose=False): pass
    def turn_off_internet(verbose=False): pass
    INTERNET_OFF = False

template_folder = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "data"
)
app = Flask(__name__, template_folder=template_folder)

@app.route("/err")
def send_err():
    return render_template("error-sia.xml")

@app.route("/sia")
def send_sia():
    return render_template("neat-sia.xml")

@app.route("/cs")
def send_scs():
    return render_template("twomass-cs.xml")

@app.route("/ssa")
def send_ssa():
    return render_template("jhu-ssa.xml")

@app.route("/sla")
def send_sla():
    return render_template("nrao-sla.xml")

@app.route("/tap/sync", methods=["POST"])
def send_tap():
    return render_template("arihip-tap.xml")

@app.route("/tap/async", methods=["POST"])
def send_tap_async_redir():
    return redirect("/tap/async/3bLj5O")

@app.route("/tap/async/3bLj5O", methods=["GET", "POST"])
def send_tap_async():
    if request.method == "GET":
        return render_template("arihip-tap-async-get.xml")
    elif request.method == "POST":
        return render_template("arihip-tap-async.xml")

@app.route("/tap/async/3bLj5O/results/result")
def send_tap_async_result():
    return render_template("arihip-tap-async-result.xml")

@app.route("/tap/async/3bLj5O/phase", methods=["POST"])
def send_tap_async_phase():
    return redirect("/tap/async/3bLj5O")


class PortProcess(multiprocessing.Process):
    port = None


def server_running(port=8081):
    url = "http://localhost:{0}/path".format(port)
    try:
        r = requests.get(url)
        return True
    except requests.exceptions.ConnectionError:
        return False

def find_available_port(baseport=8081, limit=8181, step=1):
    port = baseport
    while port < limit:
        if not server_running(port):
            return port
        port += step
    raise RuntimeError("No port available!")

def get_server(baseport=8081, limit=8181, step=1):
    port = find_available_port(baseport, limit, step)
    process = multiprocessing.Process(target=app.run, kwargs={
        "port": port
    })
    process.port = port

    return process

if __name__ == "__main__":
    app.run()

# Licensed under a 3-clause BSD style license - see LICENSE.rst

import os
import sys

import pytest

# By default, tests should not use the internet.
from pyvo.samp import SAMPWarning, conf
from pyvo.samp.client import SAMPClient
from pyvo.samp.constants import SAMP_STATUS_OK, SAMP_STATUS_WARNING
from pyvo.samp.errors import SAMPClientError
from pyvo.samp.hub import SAMPHubServer
from pyvo.samp.hub_proxy import SAMPHubProxy
from pyvo.samp.integrated_client import SAMPIntegratedClient


CI = os.environ.get("CI", "false") == "true"
IS_MACOS = sys.platform == "darwin"


def setup_module(module):
    conf.use_internet = False


# ---------------------------------------------------------------------------
# Existing tests (unchanged)
# ---------------------------------------------------------------------------


def test_SAMPHubProxy():
    """Test that SAMPHubProxy can be instantiated"""
    SAMPHubProxy()


@pytest.mark.slow
def test_SAMPClient():
    """Test that SAMPClient can be instantiated"""
    proxy = SAMPHubProxy()
    SAMPClient(proxy)


def test_SAMPIntegratedClient():
    """Test that SAMPIntegratedClient can be instantiated"""
    SAMPIntegratedClient()


@pytest.fixture
def samp_hub():
    """A fixture that can be used by client tests that require a HUB."""
    my_hub = SAMPHubServer()
    my_hub.start()
    yield
    my_hub.stop()


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
@pytest.mark.filterwarnings("ignore:unclosed <socket:ResourceWarning")
def test_SAMPIntegratedClient_notify_all(samp_hub):
    """Test that SAMP returns a warning if no receiver got the message."""
    client = SAMPIntegratedClient()
    client.connect()
    message = {"samp.mtype": "coverage.load.moc.fits"}
    with pytest.warns(SAMPWarning):
        client.notify_all(message)
    client.disconnect()


@pytest.mark.skipif(IS_MACOS and CI, reason="This test hangs on MacOS GHA.")
def test_reconnect(samp_hub):
    """Test that SAMPIntegratedClient can reconnect.

    This is a regression test for bug [#2673]
    https://github.com/astropy/astropy/issues/2673
    """
    my_client = SAMPIntegratedClient()
    my_client.connect()
    my_client.disconnect()
    my_client.connect()


# ---------------------------------------------------------------------------
# New: a stub hub proxy so client logic can be tested without a live hub
# ---------------------------------------------------------------------------


class StubHubProxy:
    """
    Minimal stand-in for `~pyvo.samp.SAMPHubProxy`.

    `SAMPClient` only ever touches a handful of attributes and methods on the
    hub proxy, so a stub lets us exercise the client's own logic (bindings,
    dispatch, registration bookkeeping) without starting a hub or touching a
    socket.
    """

    def __init__(self, is_connected=True):
        self.is_connected = is_connected
        self.lockfile = {"samp.secret": "a-secret"}
        self.register_result = {
            "samp.self-id": "public-id",
            "samp.private-key": "private-key",
            "samp.hub-id": "hub-id",
        }
        # Recorded interactions
        self.replies = []
        self.subscriptions = None
        self.metadata = None
        self.xmlrpc_callback = None
        self.unregistered = []

    def register(self, secret):
        self.secret_used = secret
        return self.register_result

    def unregister(self, private_key):
        self.unregistered.append(private_key)

    def set_xmlrpc_callback(self, private_key, xmlrpc_addr):
        self.xmlrpc_callback = (private_key, xmlrpc_addr)

    def declare_subscriptions(self, private_key, subscriptions):
        self.subscriptions = subscriptions

    def declare_metadata(self, private_key, metadata):
        self.metadata = metadata

    def reply(self, private_key, msg_id, reply):
        self.replies.append((private_key, msg_id, reply))


@pytest.fixture
def stub_hub():
    return StubHubProxy()


@pytest.fixture
def quiet_client(stub_hub):
    """A non-callable client: no XML-RPC server, no sockets, no threads."""
    return SAMPClient(stub_hub, name="quiet", callable=False)


@pytest.fixture
def callable_client(stub_hub):
    client = SAMPClient(stub_hub, name="loud", callable=True)
    client.register()
    try:
        yield client
    finally:
        if client.is_running:
            client.stop()
        else:
            client.client.server_close()


# ---------------------------------------------------------------------------
# New: construction and metadata assembly
# ---------------------------------------------------------------------------


def test_metadata_built_from_name_and_description(stub_hub):
    client = SAMPClient(
        stub_hub, name="My App", description="Does things", callable=False
    )
    assert client._metadata["samp.name"] == "My App"
    assert client._metadata["samp.description.text"] == "Does things"


def test_explicit_metadata_is_extended_not_replaced(stub_hub):
    client = SAMPClient(
        stub_hub,
        name="My App",
        metadata={"author.name": "Someone"},
        callable=False,
    )
    assert client._metadata["author.name"] == "Someone"
    assert client._metadata["samp.name"] == "My App"


def test_no_metadata_by_default(stub_hub):
    client = SAMPClient(stub_hub, callable=False)
    assert client._metadata == {}


def test_non_callable_client_has_no_xmlrpc_address(quiet_client):
    assert quiet_client._xmlrpcAddr is None
    assert quiet_client.client is None


def test_callable_client_picks_a_free_port(callable_client):
    """With port=0 the OS assigns a port, which the client must read back."""
    assert callable_client._port != 0
    assert callable_client._xmlrpcAddr.startswith("http://127.0.0.1:")
    assert str(callable_client._port) in callable_client._xmlrpcAddr


# ---------------------------------------------------------------------------
# New: registration and its error branches
# ---------------------------------------------------------------------------


def test_keys_are_none_before_registration(quiet_client):
    assert quiet_client.get_private_key() is None
    assert quiet_client.get_public_id() is None
    assert not quiet_client.is_registered


def test_register_and_unregister(quiet_client, stub_hub):
    quiet_client.register()

    assert quiet_client.is_registered
    assert quiet_client.get_public_id() == "public-id"
    assert quiet_client.get_private_key() == "private-key"
    assert quiet_client._hub_id == "hub-id"
    # Metadata was non-empty, so it should have been declared.
    assert stub_hub.metadata["samp.name"] == "quiet"

    quiet_client.unregister()

    assert not quiet_client.is_registered
    assert quiet_client.get_private_key() is None
    assert quiet_client.get_public_id() is None
    assert quiet_client._hub_id is None
    assert stub_hub.unregistered == ["private-key"]


def test_register_callable_declares_callback_and_subscriptions(
    callable_client, stub_hub
):
    assert stub_hub.xmlrpc_callback == ("private-key", callable_client._xmlrpcAddr)
    # The two built-in call bindings are always declared.
    assert "samp.app.ping" in stub_hub.subscriptions
    assert "client.env.get" in stub_hub.subscriptions


def test_register_twice_raises(quiet_client):
    quiet_client.register()
    with pytest.raises(SAMPClientError, match="already registered"):
        quiet_client.register()


def test_register_without_connected_hub_raises(stub_hub):
    stub_hub.is_connected = False
    client = SAMPClient(stub_hub, callable=False)
    with pytest.raises(SAMPClientError, match="Hub proxy not connected"):
        client.register()


def test_unregister_without_connected_hub_raises(quiet_client, stub_hub):
    quiet_client.register()
    stub_hub.is_connected = False
    with pytest.raises(SAMPClientError, match="Hub proxy not connected"):
        quiet_client.unregister()


@pytest.mark.parametrize(
    "missing_key,expected",
    [
        ("samp.self-id", "samp.self-id was not set"),
        ("samp.private-key", "samp.private-key was not set"),
    ],
)
def test_register_rejects_empty_hub_response(stub_hub, missing_key, expected):
    stub_hub.register_result[missing_key] = ""
    client = SAMPClient(stub_hub, callable=False)
    with pytest.raises(SAMPClientError, match=expected):
        client.register()


# ---------------------------------------------------------------------------
# New: "Client not callable." branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,args",
    [
        ("bind_receive_notification", ("table.load.votable", lambda *a: None)),
        ("bind_receive_call", ("table.load.votable", lambda *a: None)),
        ("bind_receive_response", ("tag", lambda *a: None)),
        ("unbind_receive_notification", ("table.load.votable",)),
        ("unbind_receive_call", ("table.load.votable",)),
        ("unbind_receive_response", ("tag",)),
        ("declare_subscriptions", ()),
    ],
)
def test_non_callable_client_rejects_binding_operations(quiet_client, method, args):
    with pytest.raises(SAMPClientError, match="Client not callable"):
        getattr(quiet_client, method)(*args)


# ---------------------------------------------------------------------------
# New: binding, unbinding and subscription declaration
# ---------------------------------------------------------------------------


def test_bind_receive_message_binds_both_call_and_notification(callable_client):
    def handler(private_key, sender_id, msg_id, mtype, params, extra):
        pass

    callable_client.bind_receive_message("table.load.votable", handler)

    assert callable_client._call_bindings["table.load.votable"][0] is handler
    assert callable_client._notification_bindings["table.load.votable"][0] is handler


def test_binding_declares_subscriptions_to_hub(callable_client, stub_hub):
    stub_hub.subscriptions = None
    callable_client.bind_receive_notification(
        "table.load.votable", lambda *a: None, metadata={"x": "y"}
    )

    assert "table.load.votable" in stub_hub.subscriptions
    assert stub_hub.subscriptions["table.load.votable"] == {"x": "y"}


def test_binding_with_declare_false_does_not_contact_hub(callable_client, stub_hub):
    stub_hub.subscriptions = None
    callable_client.bind_receive_call(
        "table.load.votable", lambda *a: None, declare=False
    )

    assert stub_hub.subscriptions is None
    assert "table.load.votable" in callable_client._call_bindings


def test_unbinding_removes_bindings(callable_client, stub_hub):
    def handler(*args):
        pass

    callable_client.bind_receive_message("table.load.votable", handler)
    callable_client.bind_receive_response("my-tag", handler)

    callable_client.unbind_receive_notification("table.load.votable")
    callable_client.unbind_receive_call("table.load.votable")
    callable_client.unbind_receive_response("my-tag")

    assert "table.load.votable" not in callable_client._notification_bindings
    assert "table.load.votable" not in callable_client._call_bindings
    assert "my-tag" not in callable_client._response_bindings
    assert "table.load.votable" not in stub_hub.subscriptions


def test_declare_subscriptions_merges_optional_map(callable_client, stub_hub):
    callable_client.declare_subscriptions({"extra.mtype": {"note": "hi"}})

    assert stub_hub.subscriptions["extra.mtype"] == {"note": "hi"}
    # Built-in bindings are still declared alongside the optional map.
    assert "samp.app.ping" in stub_hub.subscriptions


def test_declare_subscriptions_deep_copies_metadata(callable_client, stub_hub):
    metadata = {"mutable": ["a"]}
    callable_client.bind_receive_call("table.load.votable", lambda *a: None,
                                      metadata=metadata)
    metadata["mutable"].append("b")

    assert stub_hub.subscriptions["table.load.votable"]["mutable"] == ["a"]


def test_declare_subscriptions_requires_registration(stub_hub):
    client = SAMPClient(stub_hub, callable=True)
    try:
        with pytest.raises(SAMPClientError, match="Unable to declare subscriptions"):
            client.declare_subscriptions()
    finally:
        client.client.server_close()


# ---------------------------------------------------------------------------
# New: metadata declaration
# ---------------------------------------------------------------------------


def test_declare_metadata_updates_and_sends(quiet_client, stub_hub):
    quiet_client.register()
    quiet_client.declare_metadata({"author.email": "someone@example.org"})

    assert stub_hub.metadata["author.email"] == "someone@example.org"
    # Pre-existing metadata is preserved.
    assert stub_hub.metadata["samp.name"] == "quiet"


def test_declare_metadata_requires_registration(quiet_client):
    with pytest.raises(SAMPClientError, match="Unable to declare metadata"):
        quiet_client.declare_metadata({"a": "b"})


# ---------------------------------------------------------------------------
# New: built-in call bindings (samp.app.ping, client.env.get)
# ---------------------------------------------------------------------------


def test_ping_replies_with_ok_status(quiet_client, stub_hub):
    quiet_client.register()
    quiet_client.receive_call(
        "private-key",
        "sender-id",
        "msg-id",
        {"samp.mtype": "samp.app.ping", "samp.params": {}},
    )

    private_key, msg_id, reply = stub_hub.replies[0]
    assert private_key == "private-key"
    assert msg_id == "msg-id"
    assert reply["samp.status"] == SAMP_STATUS_OK


def test_client_env_get_returns_existing_variable(quiet_client, stub_hub, monkeypatch):
    monkeypatch.setenv("PYVO_SAMP_TEST_VAR", "hello")
    quiet_client.register()
    quiet_client.receive_call(
        "private-key",
        "sender-id",
        "msg-id",
        {
            "samp.mtype": "client.env.get",
            "samp.params": {"name": "PYVO_SAMP_TEST_VAR"},
        },
    )

    _, _, reply = stub_hub.replies[0]
    assert reply["samp.status"] == SAMP_STATUS_OK
    assert reply["samp.result"]["value"] == "hello"


def test_client_env_get_warns_for_missing_variable(quiet_client, stub_hub, monkeypatch):
    monkeypatch.delenv("PYVO_SAMP_TEST_VAR", raising=False)
    quiet_client.register()
    quiet_client.receive_call(
        "private-key",
        "sender-id",
        "msg-id",
        {
            "samp.mtype": "client.env.get",
            "samp.params": {"name": "PYVO_SAMP_TEST_VAR"},
        },
    )

    _, _, reply = stub_hub.replies[0]
    assert reply["samp.status"] == SAMP_STATUS_WARNING
    assert reply["samp.result"]["value"] == ""
    assert "samp.error" in reply


# ---------------------------------------------------------------------------
# New: message dispatch (notifications, calls, responses)
# ---------------------------------------------------------------------------


def test_receive_notification_dispatches_to_five_argument_handler(callable_client):
    received = {}

    def handler(private_key, sender_id, mtype, params, extra):
        received.update(
            private_key=private_key,
            sender_id=sender_id,
            mtype=mtype,
            params=params,
            extra=extra,
        )

    callable_client.bind_receive_notification("table.load.votable", handler)
    result = callable_client.receive_notification(
        "private-key",
        "sender-id",
        {
            "samp.mtype": "table.load.votable",
            "samp.params": {"url": "http://example.org/t.xml"},
            "samp.extra": "kept",
        },
    )

    assert result == ""
    assert received["private_key"] == "private-key"
    assert received["sender_id"] == "sender-id"
    assert received["mtype"] == "table.load.votable"
    assert received["params"] == {"url": "http://example.org/t.xml"}
    # mtype and params are stripped from the message; anything else is "extra".
    assert received["extra"] == {"samp.extra": "kept"}


def test_receive_notification_dispatches_to_six_argument_handler(callable_client):
    received = {}

    def handler(private_key, sender_id, msg_id, mtype, params, extra):
        received.update(msg_id=msg_id, mtype=mtype)

    callable_client.bind_receive_notification("table.load.votable", handler)
    callable_client.receive_notification(
        "private-key",
        "sender-id",
        {"samp.mtype": "table.load.votable", "samp.params": {}},
    )

    # Notifications have no message id, so the six-argument form gets None.
    assert received["msg_id"] is None
    assert received["mtype"] == "table.load.votable"


def test_notification_matches_wildcard_subscription(callable_client):
    """A binding on a parent MType must catch its subtypes."""
    assert "table.*" in SAMPHubServer.get_mtype_subtypes("table.load.votable")

    calls = []
    callable_client.bind_receive_notification(
        "table.*", lambda *args: calls.append(args)
    )
    callable_client.receive_notification(
        "private-key",
        "sender-id",
        {"samp.mtype": "table.load.votable", "samp.params": {}},
    )

    assert len(calls) == 1


def test_receive_notification_ignores_wrong_private_key(callable_client):
    calls = []
    callable_client.bind_receive_notification(
        "table.load.votable", lambda *args: calls.append(args)
    )
    result = callable_client.receive_notification(
        "wrong-key",
        "sender-id",
        {"samp.mtype": "table.load.votable", "samp.params": {}},
    )

    assert result == ""
    assert calls == []


def test_receive_notification_ignores_message_without_mtype(callable_client):
    calls = []
    callable_client.bind_receive_notification(
        "table.load.votable", lambda *args: calls.append(args)
    )
    result = callable_client.receive_notification(
        "private-key", "sender-id", {"samp.params": {}}
    )

    assert result == ""
    assert calls == []


def test_receive_notification_ignores_unbound_mtype(callable_client):
    result = callable_client.receive_notification(
        "private-key",
        "sender-id",
        {"samp.mtype": "image.load.fits", "samp.params": {}},
    )
    assert result == ""


def test_receive_call_dispatches_with_message_id(callable_client):
    received = {}

    def handler(private_key, sender_id, msg_id, mtype, params, extra):
        received.update(msg_id=msg_id, mtype=mtype, params=params)

    callable_client.bind_receive_call("table.load.votable", handler)
    result = callable_client.receive_call(
        "private-key",
        "sender-id",
        "msg-id",
        {"samp.mtype": "table.load.votable", "samp.params": {"n": 1}},
    )

    assert result == ""
    assert received["msg_id"] == "msg-id"
    assert received["params"] == {"n": 1}


def test_receive_call_ignores_wrong_private_key(callable_client):
    calls = []
    callable_client.bind_receive_call(
        "table.load.votable", lambda *args: calls.append(args)
    )
    result = callable_client.receive_call(
        "wrong-key",
        "sender-id",
        "msg-id",
        {"samp.mtype": "table.load.votable", "samp.params": {}},
    )

    assert result == ""
    assert calls == []


def test_receive_response_dispatches_by_tag(callable_client):
    received = {}

    def handler(private_key, responder_id, msg_tag, response):
        received.update(responder_id=responder_id, msg_tag=msg_tag, response=response)

    callable_client.bind_receive_response("my-tag", handler)
    result = callable_client.receive_response(
        "private-key", "responder-id", "my-tag", {"samp.status": SAMP_STATUS_OK}
    )

    assert result == ""
    assert received["responder_id"] == "responder-id"
    assert received["msg_tag"] == "my-tag"
    assert received["response"] == {"samp.status": SAMP_STATUS_OK}


@pytest.mark.parametrize(
    "private_key,msg_tag", [("wrong-key", "my-tag"), ("private-key", "other-tag")]
)
def test_receive_response_ignores_unmatched_messages(
    callable_client, private_key, msg_tag
):
    calls = []
    callable_client.bind_receive_response("my-tag", lambda *args: calls.append(args))
    result = callable_client.receive_response(private_key, "responder-id", msg_tag, {})

    assert result == ""
    assert calls == []


# ---------------------------------------------------------------------------
# New: start/stop lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.filterwarnings("ignore:unclosed <socket:ResourceWarning")
def test_start_and_stop_callable_client(callable_client):
    assert not callable_client.is_running

    callable_client.start()
    assert callable_client.is_running
    assert callable_client._thread.is_alive()

    callable_client.stop()
    assert not callable_client.is_running
    assert not callable_client._thread.is_alive()


def test_start_is_a_no_op_for_non_callable_client(quiet_client):
    quiet_client.start()
    assert not quiet_client.is_running


@pytest.mark.filterwarnings("ignore:unclosed <socket:ResourceWarning")
def test_stop_raises_if_thread_does_not_terminate(callable_client, monkeypatch):
    """The timeout branch in stop() should surface as a SAMPClientError."""
    callable_client.start()

    # Simulate a thread that refuses to die: join() returns without stopping it.
    monkeypatch.setattr(callable_client._thread, "join", lambda timeout=None: None)

    with pytest.raises(SAMPClientError, match="not shut down successfully"):
        callable_client.stop(timeout=0.1)

    # Let the real thread wind down so the socket is released.
    monkeypatch.undo()
    callable_client._thread.join(10)

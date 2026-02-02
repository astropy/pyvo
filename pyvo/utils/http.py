# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""
HTTP utils
"""
import platform
import requests
from ..version import version

__all__ = ["setup_user_agent"]


_USER_AGENT_TEMPLATE = ("pyVO/{pyvo_version} Python/{python_version}"
    " ({system}) (IVOA-{purpose})")


def setup_user_agent(*, purpose="science", primary_component=""):
    """
    Sets up a user agent for http requests made by pyVO.

    This respects the IVOA Note "Operational Identification of Software
    Components", https://ivoa.net/documents/Notes/softid/ ("softid").
    If you do not want this, perhaps for privacy reasons, you can put an
    arbitrary string into pyvo.utils.http.USER_AGENT.

    Parameters
    ----------
    purpose : str
        The function of the current user agent in the VO: Usually "science",
        but infrastructure code might use test or copy as per the softid
        Note.

    primary_component : str
        An custom identifier for your particular program, preferably in the
        form "myProgram/0.2".
    """
    global USER_AGENT
    USER_AGENT = _USER_AGENT_TEMPLATE.format(
        pyvo_version=version,
        python_version=platform.python_version(),
        system=platform.system(),
        purpose=purpose)

    if primary_component:
        USER_AGENT = primary_component+" "+USER_AGENT


def use_session(session):
    """
    Return the session passed in, or create a default
    session to use for this network request.
    """
    if session:
        return session
    else:
        return create_session()


def create_session():
    """
    Create a new empty requests session with a pyvo
    user agent.
    """
    session = requests.Session()
    session.headers['User-Agent'] = USER_AGENT
    return session


setup_user_agent()

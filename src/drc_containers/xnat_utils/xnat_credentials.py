import os
from dataclasses import dataclass

import xnat


@dataclass
class XnatCredentials:
    username: str
    password: str
    host: str

    # Whether the server's SSL certificate should be verified.
    # Always set to True for production servers. May be necessary to set to
    # False if using a test server with a self-signed certificate
    verify_ssl: bool = True


class XnatContainerCredentials(XnatCredentials):
    """Obtain XNAT credentials when running in the XNAT container service.
    The credentials are set in environment variables by XNAT when running the
    container"""

    def __init__(self):
        username = os.getenv("XNAT_USER")
        if not username:
            raise ValueError("No username in environment variable XNAT_USER")
        password = os.getenv("XNAT_PASS")
        if not password:
            raise ValueError("No password in environment variable XNAT_PASS")
        host = os.getenv("XNAT_HOST")
        if not host:
            raise ValueError("No host in environment variable XNAT_HOST")
        super().__init__(username=username, password=password, host=host)


def open_xnat_session(credentials: XnatCredentials):
    """Initiate XNAT session using credentials set by XNAT container service

    Args:
        credentials: server credentials. Use XnatContainerCredentials if running
            using XNAT container service

    """
    return xnat.connect(
        server=credentials.host,
        user=credentials.username,
        password=credentials.password,
        extension_types=True,
        verify=credentials.verify_ssl,
    )

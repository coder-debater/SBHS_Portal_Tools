"""
sbhsauth library

50% less code
(probably)

Copyright Wensen D 2022. All rights reserved.
also what does all rights reserved even mean?
o-oo
"""

import base64
import hashlib
import itertools
import requests
import secrets

class SessionBase(object):
    """OAuth 2.0 Wrapper for SBHS Portal API"""
    _id: str
    _redir_uri: str
    access_token: str
    refresh_token: str
    _state: str
    _scope: str
    def __init__(self) -> None:
        """OAuth 2.0 Wrapper for SBHS Portal API"""
        self._state = secrets.token_urlsafe()
        self.access_token = ''
        self.refresh_token = ''
    def reset(self) -> None:
        """Reset session to be used again"""
        self.__init__()
    def auth_and_reset(self, *args) -> str:
        """
        Reset session to be used again
        Returns authentication link
        """
        self.reset()
        return self.auth(*args)
    def auth(self, *args) -> str:
        """
        Return authentication link.
        Stores information for later access token retrieval
        """
        raise NotImplementedError
    def token(self, auth_code: str, returned_state: str) -> bool:
        """
        Attempt to retrieve access token
        Requires that session.auth() is already called
        If the state was wrong, returns False immediately
        Upon success, returns True and stores token info
        Upon failure, returns False
        """
        raise NotImplementedError
    def __bool__(self) -> bool:
        if not hasattr(self, 'access_token'):
            return False
        return bool(self.access_token)
    def call_api(self, path: str, auth: bool = True) -> tuple[bytes, int] | bool:
        """
        Call the Student Portal API.
        If access token is gone, return False (if authorisation required)
        If response is empty, return True
        Otherwise, return content
        """
        path: str = f"https://student.sbhs.net.au/api/{path.lstrip('/')}"
        headers: dict = {}
        if auth and self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
            headers['Authorisation'] = f"Bearer {self.access_token}"
        elif auth:
            return False
        resp: requests.Response = requests.get(
            path, headers = headers
        )
        content: bytes = resp.content
        if content:
            return content, resp.status_code
        return True
    def _token(self, data: dict, extras: dict = {}) -> bool:
        try:
            resp: requests.Response = requests.post(
                "https://student.sbhs.net.au/api/token",
            data = data, headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                **extras
            })
            token = resp.json()
            self.access_token = token['access_token']
            self.refresh_token = token['refresh_token']
            return True
        except Exception:
            return False
    def _check(self, returned_state: str) -> bool:
        return self._state != returned_state
    def refresh(self) -> bool:
        """
        Attempt to refresh the access token
        Returns True on success, False if otherwise
        """
        if not hasattr(self, 'refresh_token'):
            return False
        if not self.refresh_token:
            return False
        try:
            x = self._refresh_data()
            if not isinstance(x, dict):
                return False
            return self._token({
                'grant_type': "refresh_token",
                'redirect_uri': self._redir_uri,
                'scope': self._scope,
                'refresh_token': self.refresh_token,
                'client_id': self._id,
                **x
            }, self._refresh_extras())
        except Exception:
            return False
    def _refresh_extras(self) -> dict[str, str]:
        raise NotImplementedError
    def _refresh_data(self) -> dict[str, str]:
        raise NotImplementedError
class PkceSession(SessionBase):
    """OAuth 2.0 Wrapper for SBHS Portal API (PKCE)"""
    _code_verifier: str
    _code_challenge: str
    def __init__(self) -> None:
        """OAuth 2.0 Wrapper for SBHS Portal API (PKCE)"""
        super(PkceSession, self).__init__()
        self._code_verifier: str = secrets.token_urlsafe()
        hashed: bytes = hashlib.sha256(
            self._code_verifier.encode('utf-8')
        ).digest()
        encoded: bytes = base64.urlsafe_b64encode(hashed)
        self._code_challenge: str = encoded.decode('utf-8').rstrip('=')
    def auth(
        self,
        id_: str,
        redir_uri: str,
        scope: str = 'all-ro'
    ) -> str:
        """
        Return authentication link.
        Stores information for later access token retrieval
        """
        self._id = id_
        self._redir_uri = redir_uri
        self._scope = scope
        return f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={id_}&redirect_uri={redir_uri}&scope={scope}&state={self._state}&code_challenge={self._code_challenge}&code_challenge_method=S256"
    def token(self, auth_code: str, returned_state: str) -> bool:
        """
        Attempt to retrieve access token
        Requires that session.auth() is already called
        If the state was wrong, returns False immediately
        Upon success, returns True and stores token info
        Upon failure, returns False
        """
        if self._check(returned_state):
            return False
        return self._token({
            'grant_type': "authorization_code",
            'code': auth_code,
            'redirect_uri': self._redir_uri,
            'client_id': self._id,
            'code_challenge': self._code_challenge,
            'code_verifier': self._code_verifier
        })
    def _refresh_extras(self) -> dict[str, str]:
        raise NotImplementedError
    def _refresh_data(self) -> dict[str, str]:
        raise NotImplementedError
def auth_pkce(id_: str, redir_uri: str, scope: str = 'all-ro') -> tuple[PkceSession, str]:
    """Generate an authentication link using PKCE"""
    pkce_session = PkceSession()
    return pkce_session, pkce_session.auth(id_, redir_uri, scope)

class SecretSession(SessionBase):
    """OAuth 2.0 Wrapper for SBHS Portal API (App Secret)"""
    __secret: str
    def __init__(self) -> None:
        """OAuth 2.0 Wrapper for SBHS Portal API (App Secret)"""
        super(SecretSession, self).__init__()
    def reset(self) -> None:
        self.__init__()
    def auth(
        self,
        id_: str,
        secret: str,
        redir_uri: str,
        scope: str = 'all-ro'
    ) -> str:
        """
        Return authentication link.
        Stores information for later access token retrieval
        """
        self._id = id_
        self._redir_uri = redir_uri
        self.__secret = secret
        self._scope = scope
        return f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={id_}&redirect_uri={redir_uri}&state={self._state}&scope={scope}"
    def token(self, auth_code: str, returned_state: str) -> bool:
        """
        Attempt to retrieve access token
        Requires that session.auth() is already called
        If the state was wrong, returns False immediately
        Upon success, returns True and stores token info
        Upon failure, returns False
        """
        if self._check(returned_state):
            return False
        return self._token({
            'grant_type': "authorization_code",
            'code': auth_code,
            'client_id': self._id,
            'redirect_uri': self._redir_uri,
            'client_secret': self.__secret,
        })
    def _refresh_extras(self) -> dict[str, str]:
        return {'client_secret': self.__secret}
    def _refresh_data(self) -> dict[str, str]:
        x = f'Basic {self.__secret}'
        return {
            'Authorisation': x,
            'Authorization': x,
            'scope': self._scope
        }
def auth_secret(id_: str, secret: str, redir_uri: str, scope: str = 'all-ro') -> tuple[SecretSession, str]:
    """Generate an authentication link using a client secret"""
    secret_session = SecretSession()
    return secret_session, secret_session.auth(id_, secret, redir_uri, scope = 'all-ro')

function = type(auth_secret)

def _func() -> list[function, function, function]:
    default: list | None = None
    def init(*args) -> None:
        nonlocal default
        default = args
    def deinit() -> None:
        nonlocal default
        default = None
    def parse(args) -> list:
        return [
            arg if arg else default_
            for arg, default_
            in itertools.zip_longest(
                args, default
            )
        ]
    def pkce(*args) -> PkceSession:
        args = parse(args)
        return auth_pkce(args)
    def secret(*args) -> SecretSession:
        args = parse(args)
        return auth_secret(args)
    return init, deinit, pkce, secret
init: function
init, deinit, pkce, secret = _func()
del _func

if __name__ == "__main__":
    my_hand = "nonexistent"
    raise my_hand

"""
Preview the portal, written using my sbhsauth library
Less than half of lines needed
"""

# ! TODO: Update this for the new previewer

import flask
import webbrowser
from sbhsauth import PkceSession as Session

app: flask.Flask = flask.Flask('SBHS_Portal_Tools')
CLIENT_ID: str = "SBHS_Portal_Tools"
MAIN: str = f"http://localhost:5050/"
session: Session = Session()

@app.route('/')
def root() -> flask.Response:
    if session:
        return flask.Response('Authenticated')
    elif flask.request.args.get('error') or flask.request.args.get('reset'):
        pass
    elif flask.request.args.get('code') and session.token(
        flask.request.args.get('code'),
        flask.request.args.get('state')
    ):
        return flask.redirect(MAIN)
    return flask.redirect(session.auth_and_reset(CLIENT_ID, MAIN))

@app.errorhandler(404)
def handle_404(e) -> tuple[bytes, int]:
    resp: tuple[bytes, int] | bool = session.call_api(flask.request.full_path)
    if resp is True:
        return b"No content :(", 204
    elif resp is False:
        return b"Not authenticated", 401
    return resp

@app.route('/favicon.ico')
def favicon() -> flask.Response:
    return flask.redirect('http://localhost:5050/static/favicon.ico')

webbrowser.open(session.auth_and_reset(CLIENT_ID, MAIN))
if __name__ == "__main__":
    app.run(host = '127.0.0.1', port = 5050)
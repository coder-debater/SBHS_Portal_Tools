"""
Get daytimetable, written using my sbhsauth library
Output in ./daytimetable.json
"""

import flask
import webbrowser
from sbhsauth import PkceSession as Session

app: flask.Flask = flask.Flask('SBHS_Portal_Tools')
CLIENT_ID: str = "SBHS_Portal_Tools"
MAIN: str = f"http://localhost:5050/"
session: Session = Session()

@app.route('/')
def root() -> flask.Response:
    if flask.request.args.get('error') or flask.request.args.get('reset'):
        pass
    elif flask.request.args.get('code') and session.token(
        flask.request.args.get('code'),
        flask.request.args.get('state')
    ):
        return flask.Response(f"Access token: {session.access_token}<br>Refresh token: {session.refresh_token}")
    return flask.redirect(session.auth_and_reset(CLIENT_ID, MAIN))

@app.route('/refresh')
@app.route('/refresh/')
@app.route('/refresh.html')
def refresh() -> flask.Response:
    if session.refresh():
        return flask.redirect(MAIN)
    return flask.Response("Cannot refresh (500)", 500)

@app.route('/favicon.ico')
def favicon() -> flask.Response:
    return flask.redirect('http://localhost:5050/static/favicon.ico')

webbrowser.open('http://localhost:5050/')
if __name__ == "__main__":
    app.run(host = '127.0.0.1', port = 5050)
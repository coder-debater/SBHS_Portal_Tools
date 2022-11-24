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
def root() -> flask.Response | tuple[str, int]:
    if flask.request.args.get('error') or flask.request.args.get('reset'):
        pass
    elif flask.request.args.get('code') and session.token(
        flask.request.args.get('code'),
        flask.request.args.get('state')
    ):
        resp: tuple[bytes, int] | bool = session.call_api('timetable/daytimetable.json')
        if resp is True:
            resp = b"No content :("
        elif resp is False:
            resp = b"Not authenticated :("
        else:
            resp = resp[0]
        with open('daytimetable.json', 'wb') as file:
            file.write(resp)
        return "All done", 200
    return flask.redirect(session.auth_and_reset(CLIENT_ID, MAIN))

@app.route('/favicon.ico')
def favicon() -> flask.Response:
    return flask.redirect('http://localhost:5050/static/favicon.ico')

webbrowser.open('http://localhost:5050/')
if __name__ == "__main__":
    app.run(host = '127.0.0.1', port = 5050)
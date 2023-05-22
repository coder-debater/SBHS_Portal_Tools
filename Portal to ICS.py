"""
Convert Student Portal to an ICS (calendar) file
Output in ./output.ics
"""

import base64
from datetime import datetime as DT, timedelta as TD
import hashlib
import json
import webbrowser
import flask
import secrets
import requests

class Calendar(object):
    def __init__(self, version: str = None, attrs: dict = None, subcomponents: list = None):
        self._attrs: dict = attrs or {}
        if version is not None:
            self.version: str = version
        self._sub: str = subcomponents or []
    def _attrs_repr(self) -> list[str]:
        return [':'.join([k, v]) for k, v in self._attrs.items() if v is not None]
    def __repr__(self) -> str:
        return '\n'.join([
            f"BEGIN:VCALENDAR",
            *self._attrs_repr(),
            *map(self._sub_repr, self._sub),
            f"END:VCALENDAR"
        ])
    @classmethod
    def _sub_repr(cls, self) -> str:
        return '\n'.join(self._attrs_repr()).join([
            f"BEGIN:VEVENT\n", f"\nEND:VEVENT"
        ])
    def __setitem__(self, k, v) -> None:
        self._attrs[str(k).upper()] = str(v)
    def __setattr__(self, name: str, val) -> None:
        if (name in dir(self)) or name.startswith('_'):
            return object.__setattr__(self, name, val)
        self[name] = val
    def format_dt(self, dt: DT) -> str:
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    def add_class(self,
        class_name: str, teacher: str, room: str,
        day: DT, start_time: TD, end_time: TD
    ) -> None:
        start: str = self.format_dt(day + start_time)
        formatted: str = day.strftime('%A')[:2].upper()
        self._sub.append(type(self)(attrs = {
            'SUMMARY': class_name,
            'DESCRIPTION': f"{class_name} in {room} with {teacher}",
            "LOCATION": f"{room} with {teacher}",
            "DTSTART": start,
            "DTEND": self.format_dt(day + end_time),
            "DTSTAMP": start,
            "RRULE": f"FREQ=WEEKLY;INTERVAL=3;BYDAY={formatted}"
        }))
    # def add_classes(self, classes):
    #     for class_info in classes: self.add_class(*class_info)
    def write_to(self, filename: str, mode: str = 'w') -> None:
        r: str = repr(self)
        with open(filename, mode) as file:
            file.write(r)

app: flask.Flask = flask.Flask('SBHS_Portal_Tools')
CLIENT_ID: str = "SBHS_Portal_Tools"
access_token: str = ""
code_verifier: str = ""
code_challenge: str = ""
state: str = ""
generated: bool = False

def auth():
    global state, code_verifier, code_challenge
    state = secrets.token_urlsafe()
    code_verifier = secrets.token_urlsafe()
    hashed: bytes = hashlib.sha256(
        code_verifier.encode('utf-8')
    ).digest()
    encoded: bytes = base64.urlsafe_b64encode(hashed)
    code_challenge = encoded.decode('utf-8').rstrip('=')
    return f"http://student.sbhs.net.au/api/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri=http://localhost:5050/&scope=all-ro&state={state}&code_challenge={code_challenge}&code_challenge_method=S256"

def parseTime(time: str) -> TD:
    # convert HH:MM, H:MM, HH:MM:SS, H:MM:SS
    # to timedelta from midnight
    # includes am, pm

    time = time.strip().lower()
    if time.endswith('am'):
        return parseTime(time[:-2])
    elif time.endswith('pm'):
        return parseTime(time[:-2]) + TD(hours = 12)
    time = time.split(':')
    td: TD = TD(hours = int(time[0]), minutes = int(time[1]))
    if len(time) == 3:
        td += TD(seconds = int(time[-1]))
    return td

@app.route('/')
def root() -> flask.Response | str:
    global access_token, generated
    if (( flask.request.args.get('state')) and
          ( flask.request.args.get('state') != state)):
        # Wrong state
        return flask.redirect('http://localhost:5050/')
    elif (flask.request.args.get('error')):
        # Denied, re-authenticate
        pass
    elif flask.request.args.get('reset'):
        # RESET EVERYTHING!!!!!!!
        access_token = ''
        generated = False
    elif flask.request.args.get('code'):
        # Authenticated
        try:
            assert flask.request.args.get('state') == state
            resp: requests.Response = requests.post(
                "https://student.sbhs.net.au/api/token",
            data = {
                'grant_type': "authorization_code",
                'code': flask.request.args.get('code'),
                'redirect_uri': 'http://localhost:5050/',
                'client_id': CLIENT_ID,
                'code_challenge': code_challenge,
                'code_verifier': code_verifier
            }, headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            }).json()
            access_token = str(resp['access_token'])
            return flask.redirect('http://localhost:5050/')
        except Exception:
            pass
    if access_token:
        # Yay timetable :D
        if generated:
            return "Already generated"
        generated = True
        calendar = Calendar('2.0')
        now = DT.now()
        curr_day = DT(year = int(now.year), month = int(now.month), day = int(now.day))
        day = TD(days = 1)
        curr_day -= day
        for _ in range(21):
            curr_day += day
            try:
                content = requests.get(''.join([
                    "http://student.sbhs.net.au",
                    "/api/timetable/daytimetable.json",
                    "?date=",
                    str(curr_day.year),
                    "-",
                    str(curr_day.month).zfill(2),
                    "-",
                    str(curr_day.day).zfill(2)
                ]), headers = {
                    'Authorization': f"Bearer {access_token}",
                }).content
                print(len(content))
                timetable = json.loads(content)
                bells = timetable.get('bells', timetable.get('bell', None))
                if not bells:
                    continue
                timetable_classes = timetable['timetable']
                daytimetable = timetable_classes['timetable']
                periods = daytimetable['periods']
                classes = timetable_classes.get('subjects', timetable_classes.get('classes', None))
                if isinstance(bells, dict):
                    bells = bells.values()
                bells = {v['period']: v for v in bells}
                if not isinstance(periods, dict):
                    break
                for name, info in periods.items():
                    bell = bells.get(str(name), None)
                    if bell is None:
                        bell = bells[int(name)]
                    start = parseTime(
                        bell.get('startTime',
                        bell.get('start',
                        bell.get('time', None)))
                    )
                    end = parseTime(
                        bell.get('endTime',
                        bell.get('end', None))
                    )
                    if ((end - start) >= TD(minutes = 10)):
                        short_title = info['title']
                        possible_class_key = ''.join([info['year'], short_title])
                        possible_class = classes.get(short_title, None)
                        this_class = classes.get(possible_class_key, possible_class)
                        class_name = this_class.get('title', this_class.get('longTitle', None))
                        teacher = this_class.get('fullTeacher', this_class.get('teacher', None))
                        calendar.add_class(
                            class_name,
                            teacher,
                            info['room'],
                            curr_day,
                            start,
                            end
                        )
                print("All classes added", curr_day)
            except Exception:
                pass
        calendar.write_to('output.ics')
        return 'All done!'
    return flask.redirect(auth())

@app.errorhandler(404)
def handle_404(e) -> flask.Response:
    return flask.redirect('http://localhost:5050/')

@app.route('/favicon.ico')
def favicon() -> flask.Response:
    return flask.redirect('http://localhost:5050/static/favicon.ico')

webbrowser.open(auth())
if __name__ == "__main__":
    app.run(host = '127.0.0.1', port = 5050)
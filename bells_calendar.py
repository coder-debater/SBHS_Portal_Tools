from datetime import datetime as DT, timedelta as TD
import flask
import secrets
import requests

class Calendar(object):
    def __init__(self, version = None, attrs = None, subcomponents = None):
        self._attrs = attrs or {}
        if version is not None:
            self.version = version
        self._sub = subcomponents or []
    def _attrs_repr(self):
        return [':'.join([k, v]) for k, v in self._attrs.items()]
    def __repr__(self):
        return '\n'.join([
            f"BEGIN:VCALENDAR",
            *self._attrs_repr(),
            *map(self._sub_repr, self._sub),
            f"END:VCALENDAR"
        ])
    @classmethod
    def _sub_repr(cls, self):
        return '\n'.join(self._attrs_repr()).join([
            f"BEGIN:VEVENT\n", f"\nEND:VEVENT"
        ])
    def __setitem__(self, k, v):
        self._attrs[str(k).upper()] = str(v)
    def __setattr__(self, name, val):
        if (name in dir(self)) or name.startswith('_'):
            return object.__setattr__(self, name, val)
        self[name] = val
    def format_dt(self, dt: DT):
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    def add_class(self,
        class_name: str, teacher: str, room: int,
        day: DT, start_time: TD, end_time: TD
    ):
        start = self.format_dt(day + start_time)
        formatted = day.strftime('%A')[:2].upper()
        self._sub.append(type(self)(attrs = {
            'SUMMARY': class_name,
            'DESCRIPTION': f"{class_name} class - {teacher}",
            "LOCATION": str(room),
            "DTSTART": start,
            "DTEND": self.format_dt(day + end_time),
            "DTSTAMP": start,
            "RRULE": f"FREQ=WEEKLY;INTERVAL=3;BYDAY={formatted}"
        }))
    def add_classes(self, classes):
        for class_info in classes: self.add_class(*class_info)
    def write_to(self, filename, mode = 'w'):
        r = repr(self)
        with open(filename, mode) as file:
            file.write(r)

"""
cal = Calendar('2.0')
cal.add(Event(
    attrs = {
        'SUMMARY': 'Halloween',
        'DESCRIPTION': 'Halloween class - Mr. T Rick and Mr. T Reat',
        'LOCATION': '666',
    },
    start = datetime(2022, 10, 31, 9),
    end = datetime(2022, 10, 31, 15, 15),
    rrday = 'Monday'
))
# ========== SEP ========== #
cal = Calendar('2.0')
cal.add_class("Halloween", "Mr. T Rick and Mr. T Reat", 666, DT(2022, 10, 31), TD(hours = 9), TD(hours = 15, minutes = 15))
cal.add_classes([
    ("Halloween + 1", "Teacher #1", 6661, DT(2022, 11, 1), TD(hours = 9), TD(hours = 15, minutes = 15)),
    ("Halloween + 2", "Teacher #2", 6662, DT(2022, 11, 2), TD(hours = 9), TD(hours = 15, minutes = 15)),
    ("Halloween + 3", "Teacher #3", 6663, DT(2022, 11, 3), TD(hours = 9), TD(hours = 15, minutes = 15))
])
cal.write_to('aaa.ics')
"""

app = flask.Flask('Portal to ICS')

code = [(True, secrets.token_hex())]

def _reset():
    code[0] = (True, secrets.token_hex())

@app.route('/')
def index():
    if code[0][0]:
        return flask.redirect(''.join([
            "https://student.sbhs.net.au/api/authorize"
            "?response_type=code&client_id=dinnerjacket_plus&scope=all-ro&state=",
            code[0][1]
        ]))
    resp = requests.post(
        "https://" "student.sbhs"
        ".net.au/api/token",
    data = {
        'grant_type': '12524',
        'code': code[0][1],
        'redirect_uri': 'http://localhost:5500/callback.html',
        'client_id': ''

# Why are you looking at this?
# Stop trying to steal my Client ID!
# >:( >:( >:( >:( >:( >:( >:( >:( >:(

    })
    return flask.render_template('index.html', code = code[0][1])

@app.route('/callback.html')
def callback():
    if code[0][1] == flask.request.args.get('state'):
        code[0] = (False, flask.request.args.get('code'))
    else:
        _reset()
    return flask.redirect('/')

@app.route('/reset')
def reset():
    _reset()
    return flask.redirect('/')

app.run(host = '127.0.0.1', port = 5500)

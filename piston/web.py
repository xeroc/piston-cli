from flask import Flask, redirect, url_for, session, current_app
from flask_assets import Environment
from flask_bootstrap import Bootstrap
from flaskext.markdown import Markdown
from .utils import strfdelta, strfage
from flask_socketio import SocketIO


app = Flask(__name__)
socketio = SocketIO(app)
Bootstrap(app)
webassets = Environment(app)
markdown = Markdown(
    app,
    extensions=['meta',
                'tables'
                ],
    safe_mode=True,
    output_format='html4',
)

from . import web_assets, web_views


@app.template_filter('datetime')
def _jinja2_filter_datetime(date, fmt=None):
    if fmt:
        return strfdelta(date, fmt)
    else:
        return strfdelta(date, '{days} days {hours} hours')


@app.template_filter('age')
def _jinja2_filter_age(date, fmt=None):
    return strfage(date, fmt)


@app.template_filter('excert')
def _jinja2_filter_datetime(data):
    words = data.split(" ")
    return " ".join(words[:100])


def run():
    socketio.run(app, debug=True, port=app.config.get("PORT", 5054))

    # FIXME: Don't use .run()
    # from gevent.wsgi import WSGIServer
    # from yourapplication import app
    # http_server = WSGIServer(('', 5000), app)
    # http_server.serve_forever()

app.config["GOOGLE_ANALYTICS_ID"] = ""

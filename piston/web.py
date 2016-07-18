from flask import Flask, redirect, url_for, session, current_app
from flask_assets import Environment
from flask_bootstrap import Bootstrap
from flaskext.markdown import Markdown
from .utils import strfdelta

# https://github.com/acoomans/flask-autodoc

app = Flask(__name__)
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

###############################################################################
# Extras
###############################################################################
@app.template_filter('datetime')
def _jinja2_filter_datetime(date, fmt=None):
    if fmt:
        return strfdelta(date, fmt)
    else:
        return strfdelta(date, '{days} days {hours} hours')

###############################################################################
# Run webserver
###############################################################################
def run():
    app.run(debug=True, port=app.config.get("PORT", 5054))

    # FIXME: Don't use .run()
    # from gevent.wsgi import WSGIServer
    # from yourapplication import app
    # http_server = WSGIServer(('', 5000), app)
    # http_server.serve_forever()

app.config["GOOGLE_ANALYTICS_ID"] = ""

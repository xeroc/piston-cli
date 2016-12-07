from flask import Flask
from flask_assets import Environment
from flask_bootstrap import Bootstrap
from flaskext.markdown import Markdown
from flask_socketio import SocketIO

# Flask APP
app = Flask(__name__)

# Define some parameters for flask
app.config["GOOGLE_ANALYTICS_ID"] = ""
app.config["SECRET_KEY"] = "abcdefghijklmnopqrstuvwxyz"

# SocketIO for realtime data transmission to interface
socketio = SocketIO(app)

# Bootstrap templating
Bootstrap(app)

# Web assets to manage JS and CSS
webassets = Environment(app)

# Markdown for formating content
markdown = Markdown(
    app,
    extensions=['meta',
                'tables',
                'admonition',
                'extra',
                'toc',
                ],
    # disable safe mode since private keys
    # are not in the browser
    safe_mode=False,
    output_format='html4'
)

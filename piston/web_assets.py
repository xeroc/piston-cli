from flask_assets import Bundle
from .web_app import app, webassets

# Javascript Libraries
js_libs = Bundle("libs/bootstrap-notify/js/bootstrap-notify.js",
                 "libs/sliptree-bootstrap-tokenfield/dist/bootstrap-tokenfield.min.js",
                 output="js/libs.js")

# CSS libraries
css_libs = Bundle("libs/bootstrap-notify/css/bootstrap-notify.css",
                  "libs/bootstrap-notify/css/styles/alert-bangtidy.css",
                  "libs/sliptree-bootstrap-tokenfield/dist/css/bootstrap-tokenfield.min.css",
                  output="css/libs.css")

# JS main script
js_main = Bundle("js/src/main.js",
                 output="js/main.js")

# CSS main style
css_main = Bundle("css/src/main.css",
                  output="css/main.css")

webassets.manifest = 'cache' if not app.debug else False
webassets.cache = not app.debug
webassets.debug = app.debug

webassets.register('js_libs', js_libs)
webassets.register('css_libs', css_libs)
webassets.register('js_main', js_main)
webassets.register('css_main', css_main)

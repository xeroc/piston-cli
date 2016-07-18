from flask_assets import Bundle
from .web import app, webassets

js_main = Bundle("js/src/main.js",
                 output="js/main.js")

css_less = Bundle("css/src/styles.less",
                  output="css/styles.css",
                  debug=False)

css_main = Bundle(css_less,
                  output="css/main.css")


webassets.manifest = 'cache' if not app.debug else False
webassets.cache = not app.debug
webassets.debug = app.debug

webassets.register('js_main', js_main)
webassets.register('css_main', css_main)

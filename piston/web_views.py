from jinja2 import Template, Markup, Environment, PackageLoader, FileSystemLoader
from flask import render_template, redirect, request, session, flash, url_for, make_response, jsonify, abort
from .steem import Steem, Post
from .web import app, auth
from .storage import configStorage as config

# Connect to Steem network
steem = Steem(
    node=app.config.get("STEEM_NODE", config["node"]),
    rpcuser=app.config.get("STEEM_RPCUSER", config["rpcuser"]),
    rpcpassword=app.config.get("STEEM_RPCPASS", config["rpcpassword"]),
    nobroadcast=app.config.get("STEEM_NOBROADCAST", False)
)

from . import web_socketio


@app.route('/')
@auth.login_required
def index():
    accounts = steem.wallet.getAccountsWithPermissions()
    return render_template('index.html', **locals())


@app.route('/browse', defaults={"category": "", "sort": "hot"})
@app.route('/browse/<sort>/<category>')
def browse(category, sort):
    accounts = steem.wallet.getAccountsWithPermissions()
    posts = steem.get_posts(limit=10, category=category, sort=sort)
    tags = steem.get_categories("trending", limit=25)
    return render_template('browse.html', **locals())


@app.route('/read/<path:identifier>')
def read(identifier):
    post = Post(steem, identifier)
    if not post:
        abort(400)
    else:
        comments = 
    tags = steem.get_categories("trending", limit=25)
    return render_template('browse.html', **locals())


@app.route('/post')
def post():
    pass


@app.route('/transfer')
def transfer():
    pass


@app.route('/trade')
def trade():
    pass

# http://www.vermilion.com/responsive-comparison/?framework=bootstrap
# http://v4-alpha.getbootstrap.com/

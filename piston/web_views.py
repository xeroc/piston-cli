from jinja2 import Template, Markup, Environment, PackageLoader, FileSystemLoader
from flask import render_template, redirect, request, session, flash, url_for, make_response, jsonify, abort
from .utils import resolveIdentifier
from .steem import Steem, Post
from .web import app, auth
from .storage import configStorage as config
from .web_forms import NewPostForm
from textwrap import indent

# Connect to Steem network
steem = Steem(
    node=config["WEB_STEEM_NODE"],
    rpcuser=config["WEB_STEEM_RPCUSER"],
    rpcpassword=config["WEB_STEEM_RPCPASS"],
    nobroadcast=config["WEB_STEEM_NOBROADCAST"]
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
    return render_template('read.html', **locals())


@app.route('/post', defaults={"identifier": ""}, methods=["GET", "POST"])
@app.route('/post/<path:identifier>', methods=["GET", "POST"])
def post(identifier):
    if identifier:
        post = Post(steem, identifier)
        if not post:
            abort(400)
        postForm = NewPostForm(
            category=post.category,
            body=indent(post.body, "> "),
            title="Re: " + post.title
        )
    else:
        postForm = NewPostForm()

    if steem.wallet.locked():
        flash("Wallet is locked!")
    else:
        if postForm.validate_on_submit():
            steem.post(
                postForm.title.data,
                postForm.body.data,
                author=config["web.user"],
                category=postForm.category.data
            )
            return url_for(
                "browse",
                category=postForm.category.data,
                sort="created"
            )
    return render_template('post.html', **locals())


@app.route('/transfer')
def transfer():
    pass


@app.route('/trade')
def trade():
    pass

# http://www.vermilion.com/responsive-comparison/?framework=bootstrap
# http://v4-alpha.getbootstrap.com/

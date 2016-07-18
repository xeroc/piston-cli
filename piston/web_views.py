from jinja2 import Template, Markup, Environment, PackageLoader, FileSystemLoader
from flask import render_template, redirect, request, session, flash, url_for, make_response, jsonify, abort
from .steem import Steem
from .web import app
from .storage import configStorage as config

# Connect to Steem network
steem = Steem(
    node=app.config.get("STEEM_NODE", config["node"]),
    rpcuser=app.config.get("STEEM_RPCUSER", config["rpcuser"]),
    rpcpassword=app.config.get("STEEM_RPCPASS", config["rpcpassword"]),
    nobroadcast=app.config.get("STEEM_NOBROADCAST", False)
)


@app.route('/')
def index():
    accounts = steem.wallet.getAccountsWithPermissions()
    return render_template('index.html', **locals())

###############################################################################
# Views
###############################################################################
# steemit compatiblilty!
##############################
# /@user
# /@user/transfer
# /@user/market
# /@user/post
# /replies/@user
# /blog/@user
# /recommended/@user
# /created/<category>
# /hot/<category>


# http://www.vermilion.com/responsive-comparison/?framework=bootstrap
# http://v4-alpha.getbootstrap.com/

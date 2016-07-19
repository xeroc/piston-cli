from .steem import Steem
from .web import socketio as io
from .storage import configStorage as config
from flask_socketio import send, emit
from .steem import Post
from .web_views import steem
import traceback


def success(msg):
    data = {"status": "success",
            "message": msg}
    emit("log", data, json=True)
    print(data)


def error(msg):
    data = {"status": "danger",
            "message": msg}
    emit("log", data, json=True)


def error_locked(msg="Wallet is locked"):
    data = {"status": "warning",
            "message": msg}
    emit("log", data, json=True)


def error_exc(msg=None):
    data = {"status": "danger",
            "message": traceback.format_exc()}
    emit("log", data, json=True)


@io.on('test')
def test():
    print("test")
    success("test")


@io.on('changeAccount')
def changeAccount(account):
    config["default_author"] = account
    config["default_voter"] = account
    success("changeAccount to " + account)


@io.on('vote')
def vote(identifier, weight):
    if steem.wallet.locked():
        return error_locked()

    print(steem.wallet.locked())
    try:
        post = Post(steem, identifier)
        post.vote(weight=weight,
                  voter=config["default_voter"])
        success("voted post %s with account %s" %
                (identifier, config["default_voter"]))
    except:
        error_exc()

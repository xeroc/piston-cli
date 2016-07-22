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


def warning(msg):
    data = {"status": "warning",
            "message": msg}
    emit("log", data, json=True)


def error_exc(msg=None):
    data = {"status": "danger",
            "message": traceback.format_exc()}
    emit("log", data, json=True)


def error_locked():
    warning("Wallet is locked")


@io.on('test')
def test():
    print("test")
    success("test")


@io.on('getWebUser')
def getWebUser():
    if "web.user" in config:
        emit("web.user", {
             "name": config["web.user"]
             })
    else:
        warning("Please pick an account!")


@io.on('changeAccount')
def changeAccount(account):
    config["web.user"] = account
    success("changeAccount to " + account)


@io.on('unlock')
def unlock(password):
    try:
        steem.wallet.unlock(password)
        emit("unlocked")
    except:
        error("Couldn't unlock wallet. Wrong Password?")
        emit("notunlocked")


@io.on('vote')
def vote(identifier, weight):
    if steem.wallet.locked():
        return error_locked()

    print(steem.wallet.locked())
    try:
        post = Post(steem, identifier)
        post.vote(weight=weight,
                  voter=config["web.user"])
        success("voted post %s with account %s" %
                (identifier, config["web.user"]))
    except:
        error_exc()

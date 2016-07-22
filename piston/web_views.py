from pprint import pprint
from jinja2 import Template, Markup, Environment, PackageLoader, FileSystemLoader
from flask import render_template, redirect, request, session, flash, url_for, make_response, jsonify, abort
from .utils import resolveIdentifier
from .steem import Steem, Post
from .web import app
from .storage import configStorage as configStore
from . import web_forms
from textwrap import indent

# Connect to Steem network
steem = Steem(
    node=configStore["WEB_STEEM_NODE"],
    rpcuser=configStore["WEB_STEEM_RPCUSER"],
    rpcpassword=configStore["WEB_STEEM_RPCPASS"],
    nobroadcast=configStore["WEB_STEEM_NOBROADCAST"]
)

from . import web_socketio


@app.context_processor
def inject_dict_for_all_templates():
    accounts = steem.wallet.getAccountsWithPermissions()

    def checkvotes(post):
        myaccount = configStore["web.user"]
        for v in post.active_votes:
            if v["voter"] == myaccount and v["percent"] > 0:
                return True, False
            elif v["voter"] == myaccount and v["percent"] < 0:
                return False, True
        return False, False

    return dict(
        accounts=accounts,
        wallet=steem.wallet,
        checkvotes=checkvotes
    )


@app.route('/')
def index():
    return render_template('index.html', **locals())


@app.route('/@<user>')
@app.route('/@<user>/blog')
def user_blog(user):
    try:
        user = steem.rpc.get_account(user)
        if not user:
            raise
    except:
        abort(404)
    posts = steem.get_blog(user["name"])
    return render_template('user-blog.html', **locals())


@app.route('/@<user>/recommended')
def user_recommended(user):
    try:
        user = steem.rpc.get_account(user)
        if not user:
            raise
    except:
        abort(404)
    posts = steem.get_recommended(user["name"])
    return render_template('user-recommended.html', **locals())


@app.route('/@<user>/replies')
def user_replies(user):
    try:
        user = steem.rpc.get_account(user)
        if not user:
            raise
    except:
        abort(404)
    posts = steem.get_replies(user["name"])
    return render_template('user-replies.html', **locals())


@app.route('/@<user>/funds')
def user_funds(user):
    try:
        user = steem.rpc.get_account(user)
        if not user:
            raise
    except:
        abort(404)
    info = steem.rpc.get_dynamic_global_properties()
    median_price = steem.rpc.get_current_median_history_price()
    steem_per_mvest = (
        float(info["total_vesting_fund_steem"].split(" ")[0]) /
        (float(info["total_vesting_shares"].split(" ")[0]) / 1e6)
    )
    price = (
        float(median_price["base"].split(" ")[0]) /
        float(median_price["quote"].split(" ")[0])
    )
    vesting_shares = float(user["vesting_shares"].split(" ")[0]) / 1e6 * steem_per_mvest
    vets_shares = float(user["vesting_shares"].split(" ")[0])
    steem_balance = float(user["balance"].split(" ")[0])
    sbd_balance = float(user["sbd_balance"].split(" ")[0])
    transactions = steem.get_account_history(user["name"], end=99999999, limit=10)
    return render_template('user-funds.html', **locals())


@app.route('/wallet/remove/<account>')
def removeAccount(account):
    steem.wallet.removeAccount(account)
    return redirect(url_for("wallet"))


@app.route('/wallet/privatekeys/<account>')
def showPrivateKeys(account):
    if steem.wallet.locked():
        flash("Wallet is locked!")
        return redirect(url_for("wallet"))

    from steembase import PrivateKey

    posting_key = steem.wallet.getPostingKeyForAccount(account)
    memo_key = steem.wallet.getMemoKeyForAccount(account)
    active_key = steem.wallet.getActiveKeyForAccount(account)
    owner_key = steem.wallet.getOwnerKeyForAccount(account)

    posting_key_pub = None
    memo_key_pub = None
    active_key_pub = None
    owner_key_pub = None
    if posting_key:
        posting_key_pub = format(PrivateKey(posting_key).pubkey, "STM")
    if memo_key:
        memo_key_pub = format(PrivateKey(memo_key).pubkey, "STM")
    if active_key:
        active_key_pub = format(PrivateKey(active_key).pubkey, "STM")
    if owner_key:
        owner_key_pub = format(PrivateKey(owner_key).pubkey, "STM")

    return render_template('wallet-keys.html', **locals())


@app.route('/wallet', methods=["GET", "POST"])
def wallet():
    import_wifForm = web_forms.ImportWifKey()
    import_accountpwd = web_forms.ImportAccountPassword()

    if request.method == 'POST' and steem.wallet.locked():
        flash("Wallet is locked!")

    elif request.method == 'POST' and "import_wif" in request.form:
        if import_wifForm.validate():
            steem.wallet.addPrivateKey(import_wifForm.wif.data)

    elif request.method == 'POST' and "import_accountpwd" in request.form:
        if import_accountpwd.validate():
            from graphenebase.account import PasswordKey
            keyImported = False
            for role in ["active", "posting", "memo"]:
                priv = PasswordKey(
                    import_accountpwd.accountname.data,
                    import_accountpwd.password.data,
                    role
                ).get_private_key()
                pub = format(priv.pubkey, "STM")
                importName = steem.wallet.getAccountFromPublicKey(pub)
                if importName:
                    configStore["web.user"] = importName
                    try:
                        steem.wallet.addPrivateKey(str(priv))
                    except:
                        flash("Key seems to be installed already!", "error")

                    keyImported = True
            if not keyImported:
                flash("The account could not be imported. "
                      "Verify your password!", "error")

    return render_template('wallet.html', **locals())


@app.route('/browse', defaults={"category": "", "sort": "hot"})
@app.route('/browse/<sort>', defaults={"category": ""})
@app.route('/browse/<sort>/<category>')
def browse(category, sort):
    posts = steem.get_posts(limit=10, category=category, sort=sort)
    tags = steem.get_categories("trending", limit=25)
    return render_template('browse.html', **locals())


@app.route('/read/<path:identifier>')
def read(identifier):
    post = Post(steem, identifier)
    if not post:
        abort(400)
    return render_template('read.html', **locals())


@app.route('/post/', defaults={"identifier": ""}, methods=["GET", "POST"])
@app.route('/post/<path:identifier>', methods=["GET", "POST"])
def post(identifier):
    if identifier:
        try:
            post = Post(steem, identifier)
        except:
            abort(400)
        if not post:
            abort(400)
        postForm = web_forms.NewPostForm(
            category=post.category,
            body=indent(post.body, "> "),
            title="Re: " + post.title
        )
    else:
        postForm = web_forms.NewPostForm()

    if postForm.validate_on_submit():
        if steem.wallet.locked():
            flash("Wallet is locked!")
        else:
            try:
                if identifier:
                    tx = steem.post(
                        postForm.title.data,
                        postForm.body.data,
                        author=configStore["web.user"],
                        reply_identifier=identifier,
                    )
                    return redirect(url_for(
                        "read",
                        identifier=identifier
                    ))
                else:
                    tx = steem.post(
                        postForm.title.data,
                        postForm.body.data,
                        author=configStore["web.user"],
                        category=postForm.category.data,
                    )
                    return redirect(url_for(
                        "browse",
                        category=postForm.category.data,
                        sort="created"
                    ))
            except Exception as e:
                flash(str(e))
    return render_template('post.html', **locals())


@app.route('/transfer')
def transfer():
    pass


@app.route('/trade')
def trade():
    pass

# http://www.vermilion.com/responsive-comparison/?framework=bootstrap
# http://v4-alpha.getbootstrap.com/

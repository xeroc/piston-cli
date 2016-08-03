import re
from sys import exit
from pprint import pprint
from flask import (
    render_template,
    redirect,
    request,
    flash,
    url_for,
    abort
)
from .utils import resolveIdentifier
from .steem import Post
from .web_app import app
from .web_steem import WebSteem
from .storage import configStorage as configStore
from . import web_forms
from textwrap import indent
import logging
log = logging.getLogger(__name__)
steem = WebSteem().getSteem()


@app.context_processor
def inject_dict_for_all_templates():
    accounts = steem.wallet.getAccountsWithPermissions()
    current_user = {
        "name": configStore["web:user"]
    }

    def checkvotes(post):
        myaccount = configStore["web:user"]
        for v in post.active_votes:
            if v["voter"] == myaccount and v["percent"] > 0:
                return True, False
            elif v["voter"] == myaccount and v["percent"] < 0:
                return False, True
        return False, False

    return dict(
        accounts=accounts,
        wallet=steem.wallet,
        checkvotes=checkvotes,
        current_user=current_user
    )


@app.route('/')
def index():
    posts = steem.get_posts(
        limit=10,
        category="piston",
        sort="created",
    )
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


@app.route('/@<user>/funds', methods=["POST", "GET"])
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

    latestOp = request.args.get('latestOp')
    if latestOp:
        latestOp = int(latestOp) - 1
    else:
        lastTx = steem.get_account_history(user["name"], end=99999999, limit=1)
        latestOp = lastTx[-1][0]

    transactionFilterForm = web_forms.TransactionFilterForm()
    if transactionFilterForm.validate_on_submit():
        ops = transactionFilterForm.operations.data
    else:
        ops = None

    transactions = steem.get_account_history(
        user["name"],
        end=latestOp,
        limit=10,
        only_ops=ops
    )
    transactions = sorted(transactions, key=lambda x: x[0], reverse=True)
    interest = steem.interest(user["name"])
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

    from steembase.account import PrivateKey

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
            from steembase.account import PasswordKey
            keyImported = False
            for role in ["active", "posting", "memo"]:  # do not add owner key!
                priv = PasswordKey(
                    import_accountpwd.accountname.data,
                    import_accountpwd.password.data,
                    role
                ).get_private_key()
                pub = format(priv.pubkey, "STM")
                importName = steem.wallet.getAccountFromPublicKey(pub)
                if importName:
                    configStore["web:user"] = importName
                    try:
                        steem.wallet.addPrivateKey(str(priv))
                    except:
                        flash("Key seems to be installed already!", "error")

                    keyImported = True
            if not keyImported:
                flash("The account could not be imported. "
                      "Verify your password!", "error")

    return render_template('wallet.html', **locals())


@app.route('/browse', defaults={"category": "", "sort": "trending"})
@app.route('/browse/<sort>', defaults={"category": ""})
@app.route('/browse/<sort>/<category>')
def browse(category, sort):
    start = request.args.get('start')
    posts = steem.get_posts(
        # 10 are displyed, the 11th is to pick ?start=
        # for the next page
        limit=11,
        category=category,
        sort=sort,
        start=start
    )
    tags = steem.get_categories("trending", limit=25)
    return render_template('browse.html', **locals())


@app.route('/read/<path:identifier>')
def read(identifier):
    identifier = re.sub(r'.*@', '@', identifier)
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
            title="Re: " + post.title,
            reply=identifier,
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
                        reply_identifier=postForm.reply.data,
                        author=configStore["web:user"],
                    )
                    return redirect(url_for(
                        "read",
                        identifier=identifier
                    ))
                else:
                    tx = steem.post(
                        postForm.title.data,
                        postForm.body.data,
                        author=configStore["web:user"],
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


@app.route('/settings', methods=["GET", "POST"])
def settings():
    global steem
    settingsForm = web_forms.SettingsForm(
        node=configStore["node"],
        rpcuser=configStore["rpcuser"],
        rpcpass=configStore["rpcpass"],
        webport=configStore["web:port"]
    )
    if settingsForm.validate_on_submit():
        oldSteemUrl = steem.rpc.url
        configStore["node"] = settingsForm.node.data
        configStore["rpcuser"] = settingsForm.rpcuser.data
        configStore["rpcpass"] = settingsForm.rpcpass.data
        configStore["web:port"] = settingsForm.webport.data
        if settingsForm.node.data != oldSteemUrl:
            steem = WebSteem().connect()

    return render_template('settings.html', **locals())


@app.route('/transfer')
def transfer():
    pass


@app.route('/trade')
def trade():
    pass

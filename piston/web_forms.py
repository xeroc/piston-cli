import re
from flask_wtf import Form
from wtforms import (
    TextField,
    PasswordField,
    ValidationError,
    StringField,
    BooleanField,
    SubmitField,
    TextAreaField,
    HiddenField,
    IntegerField,
    SelectMultipleField
)
from wtforms.validators import (
    Required,
    DataRequired,
    Email,
    Length,
    Regexp,
    EqualTo,
    Optional,
    NumberRange
)


class SteemNodeAvailable(object):
    def __init__(self, message="Steem node not available"):
        self.message = message

    def __call__(self, form, field):
        from steemapi.steemnoderpc import SteemNodeRPC
        try:
            SteemNodeRPC(field.data, num_retries=0)
        except:
            raise ValidationError(self.message)


class WifPrivateKey(object):
    def __init__(self, message="Improperly formatted private key"):
        self.message = message

    def __call__(self, form, field):
        from steembase.account import PrivateKey
        try:
            PrivateKey(field.data)
        except:
            raise ValidationError(self.message)


class PostCategory(object):
    def __init__(self, message="Category may not contain spaces"):
        self.message = message

    def __call__(self, form, field):
        if(re.search("[\t\n\v\f\r ]", field.data)):
            raise ValidationError(self.message)


validators = {
    'postText': [
        Required(),
    ],
    'postTitle': [
        Optional(),
    ],
    'postCategory': [
        Required(),
        PostCategory()
    ],
    'wif' : [
        Required(),
        WifPrivateKey()
    ],
    'steemnode': [
        Required(),
        SteemNodeAvailable()
    ]
}


class NewPostForm(Form):
    reply = HiddenField()
    category = TextField(
        "Tags",
        validators['postCategory'],
        render_kw={"id": "tokenfield"},
    )
    title = TextField("Title", validators['postText'])
    body = TextAreaField('Body', validators['postText'])
    Submit = SubmitField("Post")


class ImportWifKey(Form):
    wif = PasswordField("Private Key", validators['wif'])
    import_wif = SubmitField("Import Key")


class ImportAccountPassword(Form):
    accountname = TextField("Account", [Required()])
    password = PasswordField("Password", [Required()])
    import_accountpwd = SubmitField("Import")


class SettingsForm(Form):
    node = TextField("API Node", [Required()],
                     render_kw={"list": "apiNodes"})
    rpcuser = TextField("API User", [Optional()])
    rpcpass = TextField("API Password", [Optional()])
    webport = IntegerField("Web Port (requires restart)", [Required(), NumberRange(min=1025)])
    import_accountpwd = SubmitField("Save")

    def validate(self):
        from steemapi.steemnoderpc import SteemNodeRPC
        if not Form.validate(self):
            return False
        try:
            SteemNodeRPC(self.node.data,
                         user=self.rpcuser.data,
                         password=self.rpcpass.data,
                         num_retries=0)
        except:
            self.node.errors.append('Unable to connect')
            return False
        return True


class TransactionFilterForm(Form):
    operations = SelectMultipleField(
        "Types",
        choices=[
            ("vote", "Votes"),
            ("comment", "Comments"),
            ("transfer", "Transfers"),
            ("transfer_to_vesting", "PowerUp"),
            ("withdraw_vesting", "PowerDown"),
            ("limit_order_create", "Create order"),
            ("limit_order_cancel", "Cancel order"),
            ("convert", "Settle/Convert SteemDollars"),
            ("fill_convert_request", "Fill Settlement/Convert"),
            ("comment_reward", "Comment Reward"),
            ("curate_reward", "Curation Reward"),
            ("liquidity_reward", "Liquidity Reward"),
            ("interest", "Interest"),
            ("fill_vesting_withdraw", "Execute PowerDown"),
            ("fill_order", "Order filled"),
            ("account_create", "Account create"),
            ("account_update", "Account update")
        ],
    )
    submit = SubmitField("filter")

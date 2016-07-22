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
    HiddenField
)
from wtforms.validators import (
    Required,
    DataRequired,
    Email,
    Length,
    Regexp,
    EqualTo,
    Optional
)


class WifPrivateKey(object):
    def __init__(self, message="Improperly formatted private key"):
        self.message = message

    def __call__(self, form, field):
        from steembase import PrivateKey
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
    ]
}


class NewPostForm(Form):
    reply = HiddenField()
    category = TextField("Category", validators['postCategory'])
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

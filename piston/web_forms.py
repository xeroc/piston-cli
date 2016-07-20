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
    ]
}


class NewPostForm(Form):
    category = TextField("Category", validators['postCategory'])
    title = TextField("Title", validators['postText'])
    body = TextAreaField('Body', validators['postText'])
    Submit = SubmitField("Post")

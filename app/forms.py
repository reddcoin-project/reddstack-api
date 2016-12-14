from flask_wtf import FlaskForm
from wtforms import TextField, IntegerField, TextAreaField, SubmitField, RadioField, SelectField, StringField, BooleanField
from wtforms.validators import DataRequired

class LookupForm(FlaskForm):
    nameid = TextField('nameid', validators=[DataRequired()])

class PriceForm(FlaskForm):
    username = TextField('username', validators=[DataRequired()])

class LookupAllnamesForm(FlaskForm):
    namespace = TextField('namespace', validators=[DataRequired()])

class NamespaceLookupForm(FlaskForm):
    namespace = TextField('namespace', validators=[DataRequired()])

class NamespacePriceForm(FlaskForm):
    namespace = TextField('namespace', validators=[DataRequired()])
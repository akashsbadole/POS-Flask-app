from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember me')
    submit = SubmitField('Sign In')
    user = None
    
    def validate_username(self, username):
        user = User.get_by_username(username.data)
        if not user:
            raise ValidationError('Username does not exist')
        self.user = user
    
    def validate_password(self, password):
        if self.user and not self.user.check_password(password.data):
            raise ValidationError('Password is incorrect')

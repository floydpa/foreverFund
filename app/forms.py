
import sys

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, RadioField, DecimalField, HiddenField
from wtforms import BooleanField, SelectField, DateField, IntegerField
from wtforms.widgets import TextArea
from wtforms.validators import Required, DataRequired, AnyOf, Optional

from . import uport


class PieChartForm(FlaskForm):
    # submit = SubmitField('OK')
    pass

class AccountNameForm(FlaskForm):
    choicelist = []
    for u in uport.users():
        l = (u,u)
        choicelist.append(l)
    choicelist.append(('ALL','ALL'))
    username = RadioField('Select individual or ALL', choices=choicelist, default='ALL')
    submit  = SubmitField('OK')

class AccountTypeForm(FlaskForm):
    acctype = RadioField('Select type or ALL', choices=[('Pens','Pension Accounts'),
                                                        ('ISA','ISA Accounts'),
                                                        ('Trd','Trading Accounts'),
                                                        ('SavTrdISA', 'Non-Pension Accounts'),
                                                        ('ALL','ALL')], default='ALL')
    submit  = SubmitField('OK')

class PlatformNameForm(FlaskForm):
    pltname = RadioField('Select type or ALL', choices=[('AJB','AJ Bell'),
                                                        ('II','Interactive Investor'),
                                                        ('BI','Tilney BestInvest'),
                                                        ('AV', 'Aviva'),
                                                        ('HL', 'Hargreaves Lansdown'),
                                                        ('ALL','ALL')], default='ALL')
    submit  = SubmitField('OK')

class UpdateAccountForm(FlaskForm):
    account  = StringField(u'Account', validators=[DataRequired()])
    filename = StringField(u'Download File', validators=[DataRequired()])
    formname = StringField(u'Update Form', validators=[DataRequired()])
    submit   = SubmitField('OK')

class FileDownloadCashForm(FlaskForm):
    account  = StringField(u'Account', validators=[DataRequired()])
    filename = StringField(u'Download File', validators=[DataRequired()])
    cash     = DecimalField(u'Cash Amount', places=2, validators=[DataRequired()])
    submit   = SubmitField('OK')
    
class FileDownloadForm(FlaskForm):
    account  = StringField(u'Account', validators=[DataRequired()])
    filename = StringField(u'Download File', validators=[DataRequired()])
    submit   = SubmitField('OK')

class CashForm(FlaskForm):
    account  = StringField(u'Account', validators=[DataRequired()])
    filename = StringField(u'Current File', validators=[DataRequired()])
    cash     = DecimalField(u'Cash Amount', places=2, validators=[DataRequired()])
    submit   = SubmitField('OK')

def getPositionsForm(positions):

    class DynamicForm(FlaskForm):
        submit = SubmitField('OK')
        cancel = SubmitField('Cancel')

    # Extend Dynamic form with fields matching each position
    idx = 1
    for pos in positions:
        sname = "sname%03d" % (idx)
        lname = "lname%03d" % (idx)
        qty   = "qty__%03d" % (idx)
        price = "price%03d" % (idx)
        value = "value%03d" % (idx)

        setattr(DynamicForm, sname, HiddenField(pos.sname()))
        setattr(DynamicForm, lname, StringField("Fund", validators=[DataRequired()], default=pos.lname()))
        setattr(DynamicForm, qty,   DecimalField("Quantity", places=2, validators=[DataRequired()], default=pos.quantity()))
        setattr(DynamicForm, price, DecimalField("Price", places=2, validators=[DataRequired()], default=pos.price()))
        setattr(DynamicForm, value, DecimalField("Value", places=2, validators=[DataRequired()], default=pos.value()))

        idx += 1

    # Create an instance of the form
    form = DynamicForm()

    return form

class SimulationForm(FlaskForm):
    CPI             = DecimalField(u'CPI', places=2, validators=[DataRequired()], default=0.025)
    RPI             = DecimalField(u'RPI', places=2, validators=[DataRequired()], default=0.035)
    portfolioGrowth = growth   = DecimalField(u'Portfolio Growth', places=2, validators=[DataRequired()], default=0.040)
    livingExpenses1 = DecimalField(u'Early Retirement Expenditure', places=2, validators=[DataRequired()], default=60000.00)
    livingExpenses2 = DecimalField(u'Later Retirement Expenditure', places=2, validators=[DataRequired()], default=50000.00)
    expensiveYears  = IntegerField(u'Expensive Years', validators=[DataRequired()], default=5)
    simYears        = IntegerField(u'Length of Simulation', validators=[DataRequired()], default=20)

    submit   = SubmitField('OK')

import sys, logging
from flask import Flask

from flask_script import Manager

from flask_bootstrap import Bootstrap
from flask_moment import Moment

from SecurityClasses import SecurityUniverse
from PortfolioClasses import UserPortfolioGroup

from config import HMRC_PARAMS, SIM_PARAMS


app = Flask(__name__)
app.config.from_object('config')

manager = Manager(app)

bootstrap = Bootstrap(app)
moment = Moment(app)

loglevel = 'DEBUG'

numeric_level = getattr(logging, loglevel.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % args.loglevel)
logging.basicConfig(stream=sys.stderr, format='%(levelname)s:%(message)s', level=numeric_level)

# --- Initialise list of securities
secu = SecurityUniverse(app.config['SECURITYINFO'])

# --- Initialise user portfolios
uport = UserPortfolioGroup(secu, app.config['ACCOUNTINFO'])

logging.debug("User Portfolios for %s", uport.users())

# --- Initialise simulation configuations
class SimConfig:
    def __init__(self):

        # HMRC Configuration
        self.taxrateBasic = HMRC_PARAMS['taxrateBasic']
        self.taxrateHigh = HMRC_PARAMS['taxrateHigh']
        self.taxFreeAmount = HMRC_PARAMS['personalAllowance']
        self.basicRateAmount = HMRC_PARAMS['basicRateLimit']
        self.dividendAllowance = HMRC_PARAMS['dividendAllowance']
        self.fullStatePension = HMRC_PARAMS['fullStatePension']

        self.tuiPension = 1700.0 # Amount age 60

        # Growth rates and inflation
        self._CPI = SIM_PARAMS['CPI']
        self._RPI = SIM_PARAMS['RPI']
        self._portfolioGrowth = SIM_PARAMS['portfolioGrowth']

        # Income required in retirement
        self._livingExpenses1 = SIM_PARAMS['livingExpenses1']     # Net amount needed per annum for first N years of retirement
        self._livingExpenses2 = SIM_PARAMS['livingExpenses2']     # Net amount needed in second stage of retirement
        self._expensiveYears  = SIM_PARAMS['expensiveYears']      # Number of years for which higher living expenses are needed

    def get_CPI(self,amount):
        return self._CPI
    def get_RPI(self,amount):
        return self._RPI
    def get_portfolioGrowth(self,amount):
        return self._portfolioGrowth
    def get_livingExpenses1(self,amount):
        return self._livingExpenses1
    def get_livingExpenses2(self,amount):
        return self._livingExpenses2
    def get_expensiveYears(self,amount):
        return self._expensiveYears

    def set_CPI(self,amount):
        self._CPI = amount
    def set_RPI(self,amount):
        self._RPI = amount
    def set_portfolioGrowth(self,amount):
        self._portfolioGrowth = amount
    def set_livingExpenses1(self,amount):
        self._livingExpenses1 = amount
    def set_livingExpenses2(self,amount):
        self._livingExpenses2 = amount
    def set_expensiveYears(self,amount):
        self._expensiveYears = amount


sim_conf = SimConfig()

from app import views

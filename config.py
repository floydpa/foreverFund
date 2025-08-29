import os

# CSRF_ENABLED = True
SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'

OPENID_PROVIDERS = [
    {'name': 'Google', 'url': 'https://www.google.com/accounts/o8/id'},
    {'name': 'Yahoo', 'url': 'https://me.yahoo.com'},
    {'name': 'AOL', 'url': 'http://openid.aol.com/<username>'},
    {'name': 'Flickr', 'url': 'http://www.flickr.com/<username>'},
    {'name': 'MyOpenID', 'url': 'https://www.myopenid.com'}
]

MAIL_SERVER = 'localhost'
MAIL_PORT = 25
MAIL_SENDER = 'Portfolio Tracker <somename@somedomain.com>'

ITEMS_PER_PAGE = 10

ACCOUNT_NAME = 'ALL'    # Or something like 'User1'
ACCOUNT_TYPE = 'ALL'    # Or something like 'ISA'
PLATFORM_NAME = 'ALL'   # Or something like 'AJB'

LOGLEVEL = 'DEBUG'
# LOGLEVEL = 'INFO'

HOME = os.getenv('HOME')
if HOME is None:
    HOME = os.path.join('c:\\','Users','paulf')

USERDATA     = os.path.join(HOME, 'UserData')
SECURITYINFO = os.path.join(HOME, 'SecurityInfo')
ACCOUNTINFO  = os.path.join(HOME, 'AccountInfo')

# 2022-23
HMRC_PARAMS = {
    'taxrateBasic': 0.2,
    'taxrateHigh': 0.4,
    'personalAllowance': 12570.0,
    'basicRateLimit': 37700.0,
    'dividendAllowance': 2000.0,
    'fullStatePension': 9630.4      # £185.20 per week
}

SIM_PARAMS = {
    'CPI': 0.025,
    'RPI': 0.035,
    'portfolioGrowth': 0.040,
    'livingExpenses1': 60000.00,
    'livingExpenses2': 50000.00,
    'expensiveYears': 5
}

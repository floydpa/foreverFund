import sys, logging
import pandas as pd
from flask import Flask

from flask_script import Manager

from flask_bootstrap import Bootstrap
from flask_moment import Moment

from SecurityClasses import SecurityUniverse
from PortfolioClasses import UserPortfolioGroup

from config import HMRC_PARAMS, SIM_PARAMS

from wb import WbIncome


app = Flask(__name__)
app.config.from_object('config')

manager = Manager(app)

bootstrap = Bootstrap(app)
moment = Moment(app)

loglevel = 'DEBUG'

numeric_level = getattr(logging, loglevel.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % numeric_level)
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

if __name__ == '__main__':

    from AccountClasses import AccountGroup

    from wb import GspreadAuth, WbIncome, WbSecMaster
    from wb import WS_POSITION_INCOME

    # Initialise 2 Google Workbooks
    gsauth = GspreadAuth()
    ForeverIncome = WbIncome(gsauth)
    SecurityMaster = WbSecMaster(gsauth)

    ag = AccountGroup(uport.accounts(),None,None)
    logging.info("ag.accounts=%s\n"%ag.accounts())
    logging.info("ag.positions=%s\n"%ag.positions())

    pos_list = []

    # Position detail
    # Who	AccType	Platform	AccountId	SecurityId	Name	                        Quantity	Book Cost	Value (£)
    # Paul	ISA	    II	        P_ISA_II	TMPL.L	    Temple Bar Investment Trust plc	11,972	    £20,000	    £31,905
 
    for pos in ag.positions():
        acc = pos.account()
        acc_id = "%s_%s_%s" % (acc.usercode(), pos.platform(), pos.account_type())
        p = {
            'Who':          pos.username(),
            'AccType':      pos.account_type(),
            'Platform':     pos.platform(),
            'AccountId':    acc_id,
            'SecurityId':   pos.sname(),
            'Name':         pos.lname(),
            'Quantity':     pos.quantity(),
            'BookCost':     pos.cost(),
            'Value':        pos.value(),
            'ValueDate':    pos.vdate()
            }
        print(p)
        pos_list.append(p)
    
    df = pd.DataFrame(pos_list).sort_values(['Who','AccType','Platform','Value'],ascending=[True,True,True,False]).reset_index(drop=True)
    # df['VLOOKUP Formula'] = df.index.to_series().apply(lambda x: f"=VLOOKUP(E{x + 2},'By Security'!$A:$B,2,FALSE)")
    
    # Use new df to add/update position income sheet
    ForeverIncome = WbIncome()
    ForeverIncome.df_to_worksheet(df, WS_POSITION_INCOME, 0, 4)

    sheet = ForeverIncome.worksheet(WS_POSITION_INCOME)

    # Add 4 columns of formulas with dividend & income information
    formulas = []
    formulas.append(['Dividend','Unit','Yield','Income'])
    for r in range(2,len(df)+2):
        divi = f"=VLOOKUP($E{r},'By Security'!$A:$E,4,FALSE)"
        unit = f"=VLOOKUP($E{r},'By Security'!$A:$E,5,FALSE)"
        yld  = f"=N{r}/I{r}"
        inc  = f'=IF(L{r}="p",G{r},I{r})*K{r}/100'
        row  = [divi,unit,yld,inc]
        # sheet.update_cell(r, 11, f"=VLOOKUP($E{r},'By Security'!$A:$E,4,FALSE)")
        formulas.append(row)

    # Update the range with formulas
    r = len(df)+1
    cell_range = f"K1:N{r}"
    # print(f"range={cell_range}")
    # print(formulas)
    sheet.update(cell_range, formulas, value_input_option='USER_ENTERED')
    
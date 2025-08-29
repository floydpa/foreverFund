# Define classes for handling the different types of securities

import os, logging
from datetime import datetime, timedelta
import time
import json, shutil

from Breakdown import AssetAllocation, Breakdown, RiskAllocation
from Breakdown import truncate_decimal, income_payments_per_year

from wb import GspreadAuth, WbIncome, WbSecMaster
from wb import WS_SECURITY_INFO, WS_SECURITY_URLS

from wb_bysecurity import WsDividendsBySecurity


class SecurityUniverse():
    def __init__(self, SecurityInfoDir):
        self._rootdir = SecurityInfoDir
        logging.debug("SecurityUniverse(%s)"%(SecurityInfoDir))
        self.refresh()

    def refresh(self):
        self._securities = {}
        self._aliases = {}
        for filename in os.listdir(self._rootdir):
            full_path = os.path.join(self._rootdir, filename)
            if os.path.isdir(full_path):
                continue
            sec = self.load_security(full_path)
            self.add_security(sec.sname(), sec)
            if sec.ISIN():
                self.add_alias(sec.ISIN(), sec.sname())
            if sec.SEDOL():
                self.add_alias(sec.SEDOL(),sec.sname())
            if sec.alias():
                self.add_alias(sec.alias(), sec.sname())
        
    def securities(self):    
        return self._securities
    
    def aliases(self):
        return self._aliases

    def add_security(self, name, defn):
        self._securities[name] = defn

    def add_alias(self, alias, name):
        self._aliases[alias] = name

    def security_names(self):
        return self._securities.keys()

    def alias_names(self):
        return self._aliases.keys()

    def load_security(self, full_path):
        with open(full_path, 'r', encoding='utf-8-sig') as fp:
            try:
                data = json.load(fp)
                file_mtime = time.localtime(os.path.getmtime(full_path))
                data['mdate'] = time.strftime('%Y%m%d', file_mtime )
                data['dmdate'] = time.strftime('%d-%b-%Y', file_mtime)
            except:
                print("ERROR:%s" % (full_path))
                exit(1)

        if data["structure"] == "EQ":
            security = Equity(data)
        elif data["structure"] == "IT":
            security = InvTrust(data)
        elif data["structure"] == "OEIC":
            security = OEIC(data)
        elif data["structure"] == "FP":
            security = FP(data)
        elif data["structure"] == "ETF":
            security = ETF(data)
        elif data["structure"] == "ETC":
            security = ETC(data)
        elif data["structure"] == "Cash":
            security = Cash(data)
        else:
            security = None
            assert True, "Unknown security structure (%s)"%(data["structure"])

        return security

    def find_security(self, name):
        if name in self.security_names():
            return (self._securities[name])
        elif name in self.alias_names():
            secname = self._aliases[name]
            return (self._securities[secname])
        else:
            print("security_names=%s"%(self.security_names()))
            print("alias_names=%s"%(self.alias_names()))
            errstr = "ERROR: Security lookup(%s)" % (name)
            assert False, errstr

    def list_securities(self, structure=None):
        seclist = []

        for name in sorted(self.security_names()):
            sec = self._securities[name]
            if structure is None or structure == sec.structure():
                seclist.append(sec.tdl_security())

        return seclist


class Security:
    def __init__(self, data):
        self._data = data
        self.aa = AssetAllocation(self.sector(), 100.0, self.security_aa())
        self.brk = Breakdown(self.sname())
        self.rsk = RiskAllocation(self.sector())
        self._price = 0.0
        self._stale = False

        try:
            now = datetime.now()
            one_year_ago = "%04d%02d%02d" % (now.year-1, now.month, now.day)
            for d in self._data['divis']['prev']:
                if d['payment'] < one_year_ago or d['ex-div'] < one_year_ago:
                    self._stale = True
        except:
            pass

        logging.debug("Security(%s)"%(self.sname()))

    # Optional definition of asset allocation specific to this security
    def security_aa(self):
        try:
            return self._data['asset-allocation']
        except:
            return None
        
    # Return list of recent dividend details. Could be empty.
    # Dummy payments are only generated for monthly frequency
    def recent_divis(self):
        try:
            return self._data['divis']['prev']
        except:
            pass

        # Genenate dummy payments for this month and 11 previous months
        prev = []
        freq = self.payout_frequency()
        paydate = self.divi_paydate()
        if freq != 'M' or paydate == 0:
            return prev
        
        startdate = f"{self.divi_startdate()}"
        lastdate  = f"{self.divi_lastdate()}"

        start_obj = datetime.strptime(startdate, "%Y%m%d").replace(day=paydate)
        last_obj  = datetime.strptime(lastdate, "%Y%m%d").replace(day=paydate)

        # logging.debug(f"recent_divis({self.sname()}): init start_obj={start_obj} last_obj={last_obj}")

        # Reset start to be no more than 12 months ago (Avoid 29-Feb issue)
        yearago_obj = datetime.today().replace(day=paydate)
        try:
            yearago_obj = yearago_obj.replace(year=yearago_obj.year - 1)
        except ValueError:
            yearago_obj = yearago_obj.replace(month=2, day=28, year=yearago_obj.year - 1)

        if start_obj < yearago_obj:
            start_obj = yearago_obj

        # The window goes out to the end date, but no more than 1 year ahead
        yearahead_obj = start_obj
        try:
            yearahead_obj = yearahead_obj.replace(year=yearahead_obj.year + 1)
        except ValueError:
            yearahead_obj = yearahead_obj.replace(month=2, day=28, year=yearahead_obj.year + 1)

        if last_obj > yearahead_obj:
            last_obj = yearahead_obj

        startdate = start_obj.strftime("%Y%m%d")
        lastdate  = last_obj.strftime("%Y%m%d")

        # logging.debug(f"recent_divis({self.sname()}): start={startdate} last={lastdate}")

        # Step forward from the start date, one month at a time, not to exceed end date
        
        dt_obj = start_obj
        for i in range(12):
            # Get paydate and advance date if Sat or Sun
            dt_obj = dt_obj.replace(day=paydate)
            while dt_obj.weekday() >= 5:
                dt_obj = dt_obj + timedelta(days=1)

            year  = dt_obj.year
            month = dt_obj.month
            dt = dt_obj.strftime("%Y%m%d")

            # Include payment in list if not before startdate
            if dt >= lastdate:
                continue

            tag = "month%02d"%(month)
            prev.append({'tag':tag, 'ex-div':dt, 'payment':dt})

            # Step forward one month
            month += 1
            if month > 12:
                month = 1
                year += 1
            dt_obj = dt_obj.replace(year=year,month=month,day=paydate)

        # logging.debug(f"recent_divis({self.sname()}): prev={prev}")

        return prev

    # Return payout frequency if specified otherwise None
    def payout_frequency(self):
        try:
            return self._data['divis']['freq']
        except:
            return None

    def divi_paydate(self):
        try:
            return self._data['divis']['paydate']
        except:
            return 0

    # Optional date when income payments started
    def divi_startdate(self):
        try:
            return self._data['divis']['start-date']
        except:
            # Assume 1 year ago
            start = datetime.today()
            start = start.replace(year=start.year-1)
            return start.strftime("%Y%m%d")
        
    # Optional date when income payments will end
    def divi_lastdate(self):
        try:
            return self._data['divis']['end-date']
        except:
            # Assume end of cemtury
            return "20991231"
        
    # Payout frequency long name
    def freq_fullname(self):
        freq = self.payout_frequency()
        fullnames = {'A':'Annually','S':'Semi-Annually','Q':'Quarterly','M':'Monthly'}
        try:
            return fullnames[freq]
        except:
            return freq

    # Return dict of payment dates with amounts
    def dividend_payments(self):
        payments = {}
        for d in self.recent_divis():
            if 'payment' in d.keys():
                dt = d['payment']
                if dt not in payments.keys():
                    payments[dt] = []
                if 'amount' in d.keys():
                    payments[dt].append(d['amount'])
                else:
                    try:
                        # Securities with 'annual-income' are defined benefit.
                        # Positions in these securities have quantity=100, so need to allow for this
                        # However, dividend payments assumed in pence, so need to allow for this too
                        annual_payout = float(self._data['annual-income']) * 100.0
                        npayments = income_payments_per_year(self.payout_frequency())

                        # add a fraction of a panny before the division to allow for rounding errors
                        # as the number is rounded down by truncate_decimal
                        amount = float((annual_payout + 0.1)/npayments)
                    except:
                        logging.debug("Security.price(%s)=%s"%(self.sname(),self.price()))
                        logging.debug("Security.fund_period_yield(%s)=%s"%(self.sname(),self.fund_period_yield()))
                        amount = self.price() * self.fund_period_yield()

                    # Convert from p to £
                    payments[dt].append(truncate_decimal(amount / 100.0))

        logging.debug("Security.dividend_payments(%s)=%s"%(self.sname(),payments))

        return payments

    # Return dict of projected dividend payments
    def dividend_projections(self, start_projection=None, end_projection=None):
        if start_projection is None:
            start_projection = datetime.today().replace(day=1)
        if end_projection is None:
            end_projection = start_projection + timedelta(weeks=13)
  
        # Reduce to date only by removing any time element
        start_projection = start_projection.replace(hour=0, minute=0, second=0, microsecond=0)
        end_projection   = end_projection.replace(hour=0, minute=0, second=0, microsecond=0)
        logging.debug(f"dividend_projections start={start_projection} end={end_projection}")

        projected = {}
        for divi in self.recent_divis():
            dt = divi['payment']
            # logging.debug(f"dividend_projections dt={dt}")
            dt_obj = datetime.strptime(dt, "%Y%m%d")
            if dt_obj >= start_projection:
                div_status = " * "
                div_date = dt
            else:
                # Assume same dividend will be paid in a year (avoid 29-Feb issue)
                try:
                    dt_obj = dt_obj.replace(year=dt_obj.year + 1)
                except ValueError:
                    dt_obj = dt_obj.replace(month=2, day=28, year=dt_obj.year + 1)
                
                # Advance date if Sat or Sun
                while dt_obj.weekday() >= 5:
                    dt_obj = dt_obj + timedelta(days=1)

                div_status = "Est"
                div_date = dt_obj.strftime("%Y%m%d")

            if dt_obj < start_projection or dt_obj > end_projection:
                continue

            # At this point we have a projected date, so what about the amount?

            # See if a specific amount is defined
            try:
                amount = divi['amount']
                unit   = divi['unit']
            except:
                amount = None
                
            # Work out from fund-yield if possible
            if amount is None:
                try:
                    amount = self._data['fund-yield']
                    unit   = '%'
                except:
                    pass
            
            # Is an annual payout defined?
            if amount is None:
                try:
                    annual_payout = float(self._data['annual-income'])
                    unit = 'p'
                    npayments = income_payments_per_year(self.payout_frequency())
                    amount = float(truncate_decimal(annual_payout/npayments))
                except:
                    pass

            if div_date not in projected.keys():
                 projected[div_date] = []

            projected[div_date].append(
                {
                    'status':div_status, 
                    'amount':amount, 
                    'unit':unit, 
                    'freq': self.payout_frequency()
                }
            )

        return projected

    # Return dict of ex-div dates with amounts
    def dividend_declarations(self):
        payments = {}
        for d in self.recent_divis():
            if 'ex-div' in d.keys():
                dt = d['ex-div']
                if dt not in payments.keys():
                    payments[dt] = []
                if 'amount' in d.keys():
                    payments[dt].append(d['amount'])
                else:
                    payments[dt].append(self.price() * self.fund_period_yield() / 100.0)

        return payments

    # Sum of individual dividend paid in the last yesr
    def annual_dividend_amount(self):
        try:
            # Return the amount from the config (defined in pounds)
            amount = float(self._data['annual-income'])
        except:
            amount = 0.0
            for d in self.recent_divis():
                if 'amount' in d.keys():
                    amount += d['amount']

        return amount

    # Unit of annual dividend, e.g. pence or cents
    def annual_dividend_unit(self):
        unit = ''
        for d in self.recent_divis():
            if 'unit' in d.keys():
                unit = d['unit']
        return unit

    # Annual payout as a percentage of price
    def sec_yield(self):
        annual_amount = self.annual_dividend_amount()
        if annual_amount > 0.0:
            try:
                yld = annual_amount * 100.0 / self.price()
            except:
                yld = 0.0
        elif 'fund-yield' in self._data.keys():
            yld = self._data['fund-yield']
        else:
            yld = 0.0

        return yld

    # Divide annual yield up equally between periods
    def fund_period_yield(self):
        freq = self.payout_frequency()
        np = {'A':1,'S':2,'Q':4,'M':12}
        try:
            nperiods = np[freq]
            return self.sec_yield()/nperiods
        except:
            return 0.0

    # Amount paid out in last year - either sum dividend payments or based on price and yield
    def annual_dividend(self):
        annual_amount = self.annual_dividend_amount()
        if annual_amount <= 0.0:
            annual_amount = self.sec_yield() * self.price() / 100.0
        return annual_amount

    def data(self):
        return self._data
    
    def sname(self):
        return self._data['sname']

    def lname(self):
        return self._data['lname']

    def name(self):
        return self.lname()

    def stype(self):
        return self._data['stype']

    def mdate(self):
        return self._data['mdate']
    
    def dmdate(self):
        return self._data['dmdate']

    def ISIN(self):
        if 'ISIN' in self._data.keys():
            return self._data['ISIN']
        else:
            return None

    def SEDOL(self):
        if 'SEDOL' in self._data.keys():
            return self._data['SEDOL']
        else:
            return None

    def alias(self):
        if 'alias' in self._data.keys():
            return self._data['alias']
        else:
            return None

    def price(self):
        return self._price

    def is_stale(self):
        return self._stale

    def set_price(self, price):
        self._price = price

    def sector(self):
        return self._data['sector']

    def info(self):
        if 'info' in self._data.keys():
            return self._data['info']
        else:
            return None

    def allocation_equity(self):
        return self.aa.allocation_equity()

    def allocation_bond(self):
        return self.aa.allocation_bond()

    def allocation_infrastructure(self):
        return self.aa.allocation_infrastructure()

    def allocation_property(self):
        return self.aa.allocation_property()

    def allocation_commodity(self):
        return self.aa.allocation_commodity()

    def allocation_cash(self):
        return self.aa.allocation_cash()

    def asset_breakdown(self):
        return self.brk.asset_breakdown()

    def region_breakdown(self):
        return self.brk.region_breakdown()

    def risk_bucket(self):
        return self.rsk.risk_bucket()

    def structure(self):
        if 'structure' in self._data.keys():
            return self._data['structure']
        else:
            return None

    def tdl_security(self):
        return { 'id': self.sname(),
                 'name': self.lname(),
                 'structure': self.structure(),
                 'mdate': self.mdate(),
                 'dmdate': self.dmdate(),
                 'stale': 'Yes' if self.is_stale() else 'No'
        }

    def tdl_security_detail(self):
        detail = []
        detail.append({'tag':'Name', 'value': self.name()})
        detail.append({'tag':'Sector', 'value': "%s (%s)" % (self.sector(), self.structure())})
        if self.ISIN():
            detail.append({'tag': 'ISIN', 'value': self.ISIN()})
        if self.SEDOL():
            detail.append({'tag': 'SEDOL', 'value': self.SEDOL()})
        if self.price() > 0.0:
            detail.append({'tag': 'Price (p)', 'value': "%.2f" % (self.price())})

        # Information about the yield
        yld = self.sec_yield()
        if yld > 0.0:
            unit = self.annual_dividend_unit()
            divi_str = "%.2f%s (%.2f%%)" % (self.annual_dividend(), unit, yld)
        else:
            divi_str = "%.2f" % (self.annual_dividend())

        freq = self.freq_fullname()
        if freq is not None:
            divi_str = "%s paid %s" % (divi_str, freq)

        if self.stype() == 'Defined Benefit':
            income = self._data['annual-income']
            growth = "%.2f%%" % (income['growth'] * 100)
            inc_str = "£%.2f starting %s increasing annually %s" % (income['amount'], income['start-date'], growth)
            detail.append({'tag': 'Annual Income', 'value': inc_str})
        else:
            detail.append({'tag': 'Annual Dividend', 'value': divi_str})

        # List of recent dividends if specified
        if self.recent_divis():
            for d in self.recent_divis():
                tag = "%s" % (d['tag'])
                xdate = datetime.strptime(d['ex-div'], '%Y%m%d').strftime('%d-%b-%Y')
                pdate = datetime.strptime(d['payment'], '%Y%m%d').strftime('%d-%b-%Y')
                if 'amount' in d.keys():
                    value = "Ex-Dividend %s Payment %s Amount %.3f%s" % (xdate, pdate, d['amount'], d['unit'])
                else:
                    value = "Ex-Dividend %s Payment %s" % (xdate, pdate)
                detail.append({'tag': tag, 'value': value})

        # Specific asset allocations for this security
        aa = self.security_aa()
        if aa is not None:
            tagstr = "Asset Allocation (%s)" % (aa['asof'])
            value = ""
            for ac in ['equity', 'bond', 'property', 'commodities', 'cash', 'other']:
                if ac in aa.keys() and aa[ac] != 0.0:
                    if len(value) > 0:
                        value += " "
                    value += "%s: %.1f%%" % (ac.title(), aa[ac])

            detail.append({'tag':tagstr, 'value': value})

        # List of URLs for more information
        if self.info():
            urls = []
            for tag in self.info().keys():
                urls.append({'tag': "URL-%s"%(tag), 'value':self.info()[tag]})
            detail.append({'tag': "URL-list", 'value':urls})

        mdate = datetime.strptime(self.mdate(), '%Y%m%d').strftime('%d-%b-%Y')
        detail.append({'tag': 'Last Updated', 'value': mdate})
        detail.append({'tag': 'Stale', 'value': 'Yes' if self.is_stale() else 'No'})

        return detail

        
    def __repr__(self):
        str = "%s %s %s %s %.2f %.2f" % (self.sname(), self.lname(), self.structure(),
                                      self.payout_frequency(), self.annual_dividend(), self.sec_yield())
        return str


class Equity(Security):
    def __init__(self, data):
        Security.__init__(self, data)

    def name(self):
        return "%s (%s)" % (self.lname(), self.sname())

class InvTrust(Security):
    def __init__(self, data):
        Security.__init__(self, data)

    def name(self):
        return "%s (%s)" % (self.lname(), self.sname())


class OEIC(Security):
    def __init__(self, data):
        Security.__init__(self, data)


class FP(Security):
    # Pension Fund
    def __init__(self, data):
        Security.__init__(self, data)
        logging.debug("FP dividend_payments=%s"%(self.dividend_payments()))


class ETF(Security):
    def __init__(self, data):
        Security.__init__(self, data)

    def name(self):
        return "%s (%s)" % (self.lname(), self.sname())


class ETC(Security):
    def __init__(self, data):
        Security.__init__(self, data)

    def sec_yield(self):
        return 0.0


class Cash(Security):
    def __init__(self, data):
        Security.__init__(self, data)

    # Return payout frequency if specified otherwise default to annual
    def payout_frequency(self):
        try:
            return self._data['divis']['freq']
        except:
            return 'A'


#------------------------------------------------------------------------------
# Update a json security file from SecurityMaster workbook
#------------------------------------------------------------------------------

def security_update_json(ForeverIncome, SecurityMaster, SecurityId):
    logging.debug(f"security_update_json({SecurityId})")

    # Base security definition
    df = SecurityMaster.worksheet_to_df(WS_SECURITY_INFO)
    records = df[(df['sname'] == SecurityId)].to_dict('records')
    if len(records) < 1:
        logging.debug(f"security_update_json: '{SecurityId}' not found")
        return
        
    sec_info = records[0]
    freq = sec_info['div-freq']
    sec_info.pop('div-freq')
    for tag in ['alias', 'SEDOL', 'fund-class']:
        if sec_info[tag] is None or sec_info[tag] == "":
            sec_info.pop(tag)

    # Previous dividends
    defn = sec_info
    defn['divis'] = {}
    defn['divis']['freq'] = freq

    bySecurity = WsDividendsBySecurity(ForeverIncome, SecurityMaster)
    prev = bySecurity.json_prev_divis(SecurityId)
    if len(prev) > 0:
        defn['divis']['prev'] = prev

    # Add url information if present
    df = SecurityMaster.worksheet_to_df(WS_SECURITY_URLS)
    sec_urls = df[(df['SecurityId'] == SecurityId)].to_dict('records')
    if len(sec_urls) > 0:
        defn['info'] = {}
        for u in sec_urls:
            defn['info'][u['Platform']] = u['Url']

    # Copy existing file in the Archive directory then recreate original
    sec_dir = f"{os.getenv('HOME')}/SecurityInfo"
    arc_dir = f"{sec_dir}/Archive"
    sec_file = f"{sec_dir}/{SecurityId}.json"
    arc_file = f"{arc_dir}/{SecurityId}.json"

    shutil.copy(sec_file, arc_file)
    with open(sec_file, 'w') as fp:
        json.dump(defn, fp, indent=2)


# =========================================================================================
# Testing
# =========================================================================================

if __name__ == '__main__':

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    
    #---------------------------------------------------------------------------------------------
    # Use (updated) information in SecuityMaster workbook to update specific securities
    #---------------------------------------------------------------------------------------------

    if False:
        # --- Initialise connection to 2 Google Workbooks
        gsauth = GspreadAuth()
        ForeverIncome = WbIncome(gsauth)
        SecurityMaster = WbSecMaster(gsauth)

        for SecurityId in ["BNKR","JCH"]:
            security_update_json(ForeverIncome, SecurityMaster, SecurityId)

    #---------------------------------------------------------------------------------------------
    # Print information from all securities
    #---------------------------------------------------------------------------------------------

    if True:
        secinfo_dir = os.getenv('HOME') + '/SecurityInfo'
        secu  = SecurityUniverse(secinfo_dir)
        # uport = UserPortfolios(secu)

        # defn = secu.find_security("TUI-DB").data()
        # defn = secu.find_security("FSB-3Y110826-595").data()
        # defn = secu.find_security("NW-18m201225-550").data()
        defn = secu.find_security("NW-Loyalty").data()
        sec = Security(defn)

        print(sec.annual_dividend())
        print()
        print(sec.recent_divis())
        print()
        print(sec.dividend_payments())
        print()

        start_date = datetime.today().replace(day=1)
        end_date   = start_date + timedelta(weeks=13)
        print(sec.dividend_projections(start_date, end_date))

    if False:
        entries_to_remove = ('info', 'divis','mdate','annual-income','asset-allocation')
    
        print()
        lk = []
        for sec in secu.securities():
            print("sec=%s" % (sec))
            defn = secu.find_security(sec).data()

            # Get rid of unwanted tags
            for k in entries_to_remove:
                defn.pop(k, None)
        
            for k in defn.keys():
                print("  %s=%s"%(k,defn[k]))
                if k not in lk:
                    lk.append(k)

        print()
        print(lk)



    

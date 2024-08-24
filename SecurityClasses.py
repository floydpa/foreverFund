# Define classes for handling the different types of securities

import os
import datetime
import time
import json
import logging

from Breakdown import AssetAllocation, Breakdown

class SecurityUniverse():
    def __init__(self, SecurityInfoDir):
        # self._rootdir = os.getenv('HOME') + '/SecurityInfo'
        self._rootdir = SecurityInfoDir
        logging.debug("SecurityUniverse(%s)"%(SecurityInfoDir))
        self._securities = {}
        self._aliases = {}
        for name in os.listdir(self._rootdir):
            full_path = self._rootdir + '/' + name
            if os.path.isdir(full_path):
                continue
            s = self.load_security(full_path)
            self.add_security(name, s)
            if s.ISIN():
                self.add_alias(s.ISIN(), name)
            if s.SEDOL():
                self.add_alias(s.SEDOL(), name)
            if s.alias():
                self.add_alias(s.alias(), name)

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
                data['mdate'] = time.strftime('%Y%m%d', time.localtime(os.path.getmtime(full_path)))
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
        self._price = 0.0
        self._stale = False

        try:
            now = datetime.datetime.now()
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
    def recent_divis(self):
        try:
            return self._data['divis']['prev']
        except:
            pass

        # Genenate dummy payments
        prev = []
        freq = self.payout_frequency()
        paydate = self.divi_paydate()
        if freq == 'M' and paydate:
            year = datetime.datetime.today().year
            month = datetime.datetime.today().month
            for i in range(12):
                dt = "%4d%02d%02d"%(year,month,paydate)
                tag = "month%02d"%(month)
                prev.append({'tag':tag, 'ex-div':dt, 'payment':dt})
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1

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

    # Payout frequency long name
    def freq_fullname(self):
        freq = self.payout_frequency()
        fullnames = {'A':'Annually','H':'Half-Yearly','Q':'Quarterly','M':'Monthly'}
        try:
            return fullnames[freq]
        except:
            return freq

    # Return dict of payment dates with amounts
    def dividend_payments(self):
        payments = {}
        for d in self.recent_divis():
            if 'payment' in d.keys():
                if 'amount' in d.keys():
                    payments[d['payment']] = d['amount']
                else:
                    payments[d['payment']] = self.price() * self.fund_period_yield() / 100.0
        return payments

    # Return dict of ex-div dates with amounts
    def dividend_declarations(self):
        payments = {}
        for d in self.recent_divis():
            if 'ex-div' in d.keys():
                if 'amount' in d.keys():
                    payments[d['ex-div']] = d['amount']
                else:
                    payments[d['ex-div']] = self.price() * self.fund_period_yield() / 100.0
        return payments

    # Sum of individual dividend paid in the last yesr
    def annual_dividend_amount(self):
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
            yld = annual_amount * 100.0 / self.price()
        elif 'fund-yield' in self._data.keys():
            yld = self._data['fund-yield']
        else:
            yld = 0.0

        return yld

    # Divide annual yield up equally between periods
    def fund_period_yield(self):
        freq = self.payout_frequency()
        np = {'A':1,'H':2,'Q':4,'M':12}
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
                xdate = datetime.datetime.strptime(d['ex-div'], '%Y%m%d').strftime('%d-%b-%Y')
                pdate = datetime.datetime.strptime(d['payment'], '%Y%m%d').strftime('%d-%b-%Y')
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

        mdate = datetime.datetime.strptime(self.mdate(), '%Y%m%d').strftime('%d-%b-%Y')
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


# =========================================================================================
# Testing
# =========================================================================================

if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    secu  = SecurityUniverse()
    # uport = UserPortfolios(secu)

    for sec in secu.list_securities('IT'):
        print("sec=%s" % (sec))
    print()

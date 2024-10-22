# Platform accounts making up a portfolio

import sys, os
import logging
import pandas as pd

from SecurityClasses import SecurityUniverse
from PlatformClasses import platformCode_to_class


class Account:
    def __init__(self, secu, username, defn):
        self._positions = []
        self._aa = {}
        self._defn = defn
        self._username = username
        self._account_type = defn['acctype']
        self._summary_file = self.userdata_dirname() + '/' + defn['file']
        self._platform = platformCode_to_class(defn['platform'])()
        for pos in self._platform.load_positions(secu, self.usercode(), self._account_type, self._summary_file):
            pos.set_account(self)
            self.add_position(pos)
        self._vdate = self._platform.vdate()

    def __repr__(self):
        s = "ACCOUNT(%s,%s)" % (self.platform(), self.account_type())
        for pos in self.positions():
            s += "\n%s"%(pos)
        return s

    def username(self):
        return self._username

    def usercode(self):
        return self._username[:1]

    def userdata_dirname(self):
        return "%s/UserData" % (os.getenv('HOME'))

    def platform(self, fullname=False):
        return self._platform.name(fullname)

    def positions(self):
        return self._positions

    def add_position(self, pos):
        # logging.debug("add_position(%s)", pos)
        self._positions.append(pos)

    def account_type(self, fullname=False):
        names = {
            'Pens': "Pension",
            'ISA': "ISA",
            'Trd': "Trading",
            'Sav': "Savings"
        }
        return names[self._account_type] if fullname and self._account_type in names.keys() else self._account_type

    def annual_income(self):
        total = 0.0
        for pos in self._positions:
            # print("INCOME pos=%s" % (pos))
            total += pos.annual_income()
        return total

    def dividend_payments(self):
        payments = {}
        for pos in self._positions:
            dp = pos.dividend_payments()
            if dp:
                for dt in dp.keys():
                    if dt not in payments.keys():
                        payments[dt] = []
                    payments[dt].append({'username': self.username(), 'acctype': self.account_type(True), 'platform': self.platform(True),
                                         'secid': pos.sname(), 'secname': pos.lname(), 'amount': dp[dt]})
        return payments

    def dividend_declarations(self):
        payments = {}
        for pos in self._positions:
            dp = pos.dividend_declarations()
            if dp:
                for dt in dp.keys():
                    if dt not in payments.keys():
                        payments[dt] = []
                    payments[dt].append({'username': self.username(), 'acctype': self.account_type(True), 'platform': self.platform(True),
                                         'secid': pos.sname(), 'secname': pos.lname(), 'amount': dp[dt]})
        return payments

    def value(self):
        total = 0.0
        for pos in self._positions:
            total += pos.value()
        return total

    def vdate(self):
        return self._vdate

    def equity_value(self):
        total = 0.0
        for pos in self._positions:
            total += pos.equity_value()
        return total

    def bond_value(self):
        total = 0.0
        for pos in self._positions:
            total += pos.bond_value()
        return total

    def infrastructure_value(self):
        total = 0.0
        for pos in self._positions:
            total += pos.infrastructure_value()
        return total

    def property_value(self):
        total = 0.0
        for pos in self._positions:
            total += pos.property_value()
        return total

    def commodity_value(self):
        total = 0.0
        for pos in self._positions:
            total += pos.commodity_value()
        return total

    def cash_value(self):
        total = 0.0
        for pos in self._positions:
            total += pos.cash_value()
        return total

    def asset_breakdown(self):
        brk = {}
        for pos in self._positions:
            b = pos.asset_breakdown()
            for k in b.keys():
                if k not in brk.keys():
                    brk[k] = 0.0
                brk[k] += b[k]

        return brk

    def region_breakdown(self):
        brk = {}
        for pos in self._positions:
            b = pos.region_breakdown()
            for k in b.keys():
                if k not in brk.keys():
                    brk[k] = 0.0
                brk[k] += b[k]

        return brk

    def sector_breakdown(self):
        brk = {}
        for pos in self._positions:
            sector = pos.sector()
            amount = pos.sector_amount()
            if sector not in brk.keys():
                brk[sector] = 0.0
            brk[sector] += amount

        return brk

    def parent_sector_breakdown(self):
        brk = {}
        for pos in self._positions:
            sector = pos.parent_sector()
            amount = pos.sector_amount()
            if sector not in brk.keys():
                brk[sector] = 0.0
            brk[sector] += amount

        return brk


# ===================================================================================
# Account Group is a temporary object
# It is a filtered set of accounts for a single user
# ===================================================================================

class AccountGroup():
    def __init__(self, accounts, account_type=None, platform_name=None):
        logging.debug("AccountGroup(%s,%s)" % (account_type, platform_name))
        self._accounts = []

        for acct in accounts:
            if account_type is None or acct.account_type() in account_type:
                if platform_name is None or acct.platform() == platform_name:
                    self._accounts.append(acct)

    def accounts(self):
        return self._accounts

    def positions(self):
        poslist = []
        for account in self.accounts():
            for pos in account.positions():
                poslist.append(pos)
        return poslist

    # ====== Assets ======

    def asset_value(self, asset_type):
        total = 0.0
        for account in self.accounts():
            if asset_type == 'ALL':
                total += account.value()
            elif asset_type == 'EQUITY':
                total += account.equity_value()
            elif asset_type == 'BOND':
                total += account.bond_value()
            elif asset_type == 'INFRASTRUCTURE':
                total += account.infrastructure_value()
            elif asset_type == 'PROPERTY':
                total += account.property_value()
            elif asset_type == 'COMMODITY':
                total += account.commodity_value()
            elif asset_type == 'CASH':
                total += account.cash_value()
            else:
                assert True, "Unknown asset type (%s)" % asset_type

        return total

    # ====== Income ======

    def annual_income(self):
        total = 0.0
        for account in self.accounts():
            total += account.annual_income()
        return total

    def dividend_info(self, info):
        payments = {}
        for account in self.accounts():
            if info == 'PAYMENTS':
                dp = account.dividend_payments()
            elif info == 'DECLARATIONS':
                dp = account.dividend_declarations()
            else:
                dp = None
                assert True, "Unknown dividend info (%s)"%(info)

            if dp:
                for dt in dp.keys():
                    if dt not in payments.keys():
                        payments[dt] = []
                    for a in dp[dt]:
                        payments[dt].append(a)
        return payments

    def dividend_payments(self):
        return self.dividend_info('PAYMENTS')

    def dividend_declarations(self):
        return self.dividend_info('DECLARATIONS')

    # ====== Breakdown ======

    def asset_breakdown(self):
        brk = {}
        for account in self.accounts():
            b = account.asset_breakdown()
            for k in b.keys():
                if k not in brk.keys():
                    brk[k] = 0.0
                brk[k] += b[k]
        return brk

    def region_breakdown(self):
        brk = {}
        for account in self.accounts():
            b = account.region_breakdown()
            for k in b.keys():
                if k not in brk.keys():
                    brk[k] = 0.0
                brk[k] += b[k]
        return brk

    def sector_breakdown(self):
        brk = {}
        for account in self.accounts():
            b = account.sector_breakdown()
            for k in b.keys():
                if k not in brk.keys():
                    brk[k] = 0.0
                brk[k] += b[k]
        return brk

    def parent_sector_breakdown(self):
        brk = {}
        for account in self.accounts():
            b = account.parent_sector_breakdown()
            for k in b.keys():
                if k not in brk.keys():
                    brk[k] = 0.0
                brk[k] += b[k]
        return brk


if __name__ == '__main__':
    from PortfolioClasses import UserPortfolioGroup

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    # Load all security information
    secinfo_dir = os.getenv('HOME') + '/SecurityInfo'
    secu = SecurityUniverse(secinfo_dir)

    # Load portfolios for all user accounts
    accinfo_dir = './tmp'
    pgrp = UserPortfolioGroup(secu, accinfo_dir)
    logging.info("\npgrp=%s\n"%pgrp)

    ag = AccountGroup(pgrp.accounts(),None,None)
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
    print(df.dtypes)
    print(df)

# Define classes for handling positions, accounts and portfolios
import logging
from datetime import datetime, timedelta

from Breakdown import SectorAllocation
from Breakdown import truncate_decimal, income_payments_per_year


class Position:
    def __init__(self, security, quantity, price, value, cost, vdate):
        self._account = None
        self._security = security
        self._quantity = quantity
        self._price = price
        self._value = value
        self._cost = cost
        self._vdate = vdate
        self._sa = SectorAllocation(security.sector(), value)
        security.set_price(price)
        logging.debug("Position(%s"%(self))
        logging.debug("dividend_payments=%s"%(self.dividend_payments()))

    def set_account(self, account):
        self._account = account

    def account(self):
        return self._account

    def username(self):
        return self._account.username()

    def account_type(self, fullname=False):
        return self._account.account_type(fullname)

    def platform(self,fullname=False):
        return self._account.platform(fullname)

    def sname(self):
        return self._security.sname()

    def lname(self):
        return self._security.lname()

    def ISIN(self):
        return self._security.ISIN()

    def sector(self):
        return self._security.sector()

    def sector_amount(self):
        return self._sa.amount()

    def parent_sector(self):
        return self._sa.parent_sector()

    def alias(self):
        return self._security.alias()

    def quantity(self):
        return self._quantity

    def price(self):
        return self._price

    def value(self):
        return self._value

    def cost(self):
        return self._cost

    def vdate(self):
        return self._vdate

    def equity_allocation(self):
        return self._security.allocation_equity()

    def equity_value(self):
        return self.equity_allocation() * self.value() / 100.0

    def bond_allocation(self):
        return self._security.allocation_bond()

    def bond_value(self):
        return self.bond_allocation() * self.value() / 100.0

    def infrastructure_allocation(self):
        return self._security.allocation_infrastructure()

    def infrastructure_value(self):
        return self.infrastructure_allocation() * self.value() / 100.0

    def property_allocation(self):
        return self._security.allocation_property()

    def property_value(self):
        return self.property_allocation() * self.value() / 100.0

    def commodity_allocation(self):
        return self._security.allocation_commodity()

    def commodity_value(self):
        return self.commodity_allocation() * self.value() / 100.0

    def cash_allocation(self):
        return self._security.allocation_cash()

    def cash_value(self):
        return self.cash_allocation() * self.value() / 100.0

    def asset_breakdown(self):
        brk = self._security.asset_breakdown().copy()
        for k in brk.keys():
            brk[k] = brk[k] * self.value() / 100.0
        return brk

    def region_breakdown(self):
        brk = self._security.region_breakdown().copy()
        for k in brk.keys():
            brk[k] = brk[k] * self.value() / 100.0
        return brk

    def payout_frequency(self):
        return self._security.payout_frequency()

    def annual_income(self):
        return self.quantity() * self._security.annual_dividend() / 100.0

    def dividend_declarations(self):
        payments = {}
        dp = self._security.dividend_declarations()
        if dp:
            for dt in dp.keys():
                if dt not in payments.keys():
                    payments[dt] = 0.0

                # One or more dividends for a specific date
                for dtdp in dp[dt]:
                    payments[dt] += self.quantity() * dtdp / 100.0

        return payments

    def dividend_payments(self):
        payments = {}
        dp = self._security.dividend_payments()
        logging.debug("dividend_payments(%s)=%s"%(self.sname(),dp))
        if dp:
            for dt in dp.keys():
                if dt not in payments.keys():
                    payments[dt] = 0.0

                # One or more dividends for a specific date
                for dtdp in dp[dt]:
                    payments[dt] += self.quantity() * dtdp / 100.0

        return payments
    
    # Return dict of projected dividend payments
    def dividend_projections(self, start_projection=None, end_projection=None):
        if start_projection is None:
            start_projection = datetime.today().replace(day=1)
        if end_projection is None:
            end_projection = start_projection + timedelta(weeks=13)

        projections = {}
        dp = self._security.dividend_projections(start_projection, end_projection)
        logging.debug("dividend_projections(%s)=%s"%(self.sname(),dp))

        if dp:
            for dt in dp.keys():
                if dt not in projections.keys():
                    projections[dt] = []
                
                for dtdp in dp[dt]:
                    # Calculate the amount for the position
                    if dtdp['unit'] == 'p':
                        amount = float(truncate_decimal(self.quantity() * dtdp['amount'] / 100.0))
                    elif dtdp['unit'] == 'e': 
                        amount = float(truncate_decimal(self.quantity() * dtdp['amount'] / 120.0))
                    elif dtdp['unit'] == '£':
                        amount = float(truncate_decimal(self.quantity() * dtdp['amount']))
                    elif dtdp['unit'] == '%':
                        annual_payout = self.value() * dtdp['amount'] / 100.0
                        npayments = income_payments_per_year(dtdp['freq'])
                        amount = float(truncate_decimal(annual_payout/npayments))
                    else:
                        errstr = f"Bad unit={dtdp['unit']} status={dtdp['status']} amount={dtdp['amount']}"
                        assert False, errstr               

                    projections[dt].append({
                                        'status':dtdp['status'], 
                                        'amount':amount, 
                                        'unit':'£'
                                        })
                
        return projections


    def __repr__(self):
        str = "%s %s %s %.2f %.2f" % (self.sname(), self.lname(), self.payout_frequency(), self.value(), self.annual_income())
        return str


if __name__ == '__main__':
    import os
    from AccountClasses import AccountGroup
    from PortfolioClasses import UserPortfolioGroup
    from SecurityClasses import SecurityUniverse

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    # Load all security information
    secinfo_dir = os.getenv('HOME') + '/SecurityInfo'
    secu = SecurityUniverse(secinfo_dir)

    # Load portfolios for all user accounts
    accinfo_dir = os.getenv('HOME') + '/AccountInfo'
    pgrp = UserPortfolioGroup(secu, accinfo_dir)
    logging.info("\npgrp=%s\n"%pgrp)

    ag = AccountGroup(pgrp.accounts(),None,None)
    logging.info("ag.accounts=%s\n"%ag.accounts())
    logging.info("ag.positions=%s\n"%ag.positions())

    pos_list = []

    # Position detail
    # Who	AccType	Platform	AccountId	SecurityId	Name	                        Quantity	Book Cost	Value (£)
    # Paul	ISA	    II	        P_ISA_II	TMPL.L	    Temple Bar Investment Trust plc	11,972	    £20,000	    £31,905
 
    # sec = "TUI-DB"
    # sec = "FSB-3Y110826-595"
    # sec = "NW-18m201225-550"
    sec = "NW-Loyalty"
    for pos in ag.positions():
        if pos.sname() != sec:
            continue

        if True:
            print("dividend_payments")
            print(pos.dividend_payments())
            print()
            print("dividend_projections")
            print(pos.dividend_projections())

        if False:
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
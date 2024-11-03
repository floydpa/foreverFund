# Define classes for handling positions, accounts and portfolios
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from Breakdown import SectorAllocation

def truncate_decimal(value, decimal_places=2):
    # Create a Decimal object from the input value
    d = Decimal(value)
    
    # Shift decimal point right, truncate, then shift back left
    truncated = d.quantize(Decimal(f'1.{"0" * decimal_places}'), rounding="ROUND_DOWN")
    
    return truncated


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

                payments[dt] += self.quantity() * dp[dt] / 100.0

        return payments

    def dividend_payments(self):
        payments = {}
        dp = self._security.dividend_payments()
        logging.debug("dividend_payments(%s)=%s"%(self.sname(),dp))
        if dp:
            for dt in dp.keys():
                if dt not in payments.keys():
                    payments[dt] = 0.0

                payments[dt] += self.quantity() * dp[dt] / 100.0

        return payments
    
    # Return dict of projected dividend payments
    def dividend_projections(self, end_projection=None):
        if end_projection is None:
            end_projection = datetime.today() + timedelta(weeks=13)

        projections = {}
        dp = self._security.dividend_projections()
        logging.debug("dividend_projections(%s)=%s"%(self.sname(),dp))

        if dp:
            for dt in dp.keys():
                if dt not in projections.keys():
                    projections[dt] = []
                
                # Calculate the amount for the position
                if dp[dt]['unit'] == 'p':
                    amount = float(truncate_decimal(self.quantity() * dp[dt]['amount'] / 100.0))
                elif dp[dt]['unit'] == 'e': 
                    amount = float(truncate_decimal(self.quantity() * dp[dt]['amount'] / 120.0))
                elif dp[dt]['unit'] == '£':
                    amount = float(truncate_decimal(self.quantity() * dp[dt]['amount']))
                elif dp[dt]['unit'] == '%':
                    annual_payout = self.value() * dp[dt]['amount'] / 100.0
                    if dp[dt]['freq'] == 'Q':
                        npayments = 4
                    elif dp[dt]['freq'] == 'S':
                        npayments = 2
                    elif dp[dt]['freq'] == 'A':
                        npayments = 1
                    elif dp[dt]['freq'] == 'M':
                        npayments = 12
                    else:
                        errstr = f"Bad freq={dp[dt]['freq']}"
                        assert False, errstr  

                    amount = float(truncate_decimal(annual_payout/npayments))
                else:
                    errstr = f"Bad unit={dp[dt]['unit']} status={dp[dt]['status']} amount={dp[dt]['amount']}"
                    assert False, errstr               

                projections[dt].append({
                                        'status':dp[dt]['status'], 
                                        'amount':amount, 
                                        'unit':'£'
                                        })
                
        return projections


    def __repr__(self):
        str = "%s %s %s %.2f %.2f" % (self.sname(), self.lname(), self.payout_frequency(), self.value(), self.annual_income())
        return str

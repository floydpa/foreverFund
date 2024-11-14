# User portfolios

import os
import datetime
import json
import logging

from SecurityClasses import SecurityUniverse
from AccountClasses import Account, AccountGroup
from Breakdown import parent_sector_list

class UserPortfolio():
    def __init__(self, secu, username, defn):
        self._username = username
        self._defn = defn
        self._accounts = []
        for accdefn in defn['accounts']:
            self.add_account(secu, accdefn)

    def id(self):
        return self._defn['id']

    def username(self):
        return self._username

    def dob(self):
        return self._defn['dob']

    def rtDate(self):
        try:
            return self._defn['rtDate']
        except:
            return None

    def spDate(self):
        return self._defn['spDate']

    def spRatio(self):
        return self._defn['spRatio']

    def drawdownPens(self):
        return self._defn['drawdownPens']

    def drawdownISA(self):
        return self._defn['drawdownISA']

    def drawdownTrd(self):
        return self._defn['drawdownTrd']

    def spShortfall(self):
        return self._defn['spShortfall']

    def savShortfall(self):
        return self._defn['savShortfall']

    def accounts(self, account_type=None, platform_name=None):
        return AccountGroup(self._accounts, account_type, platform_name).accounts()

    def positions(self, account_type=None, platform_name=None):
        return AccountGroup(self._accounts, account_type, platform_name).positions()

    def add_account(self, secu, defn):
        if defn['status'] == 'active':
            account = Account(secu, self.username(), defn)
            self._accounts.append(account)

    # ====== Assets ======

    def asset_value(self, asset_type, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).asset_value(asset_type)

    # ====== Income ======

    def annual_income(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).annual_income()

    def dividend_payments(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).dividend_payments()
    
    def dividend_projections(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).dividend_projections()

    def dividend_declarations(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).dividend_declarations()

    # ====== Breakdown ======

    def asset_breakdown(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).asset_breakdown()

    def region_breakdown(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).region_breakdown()

    def sector_breakdown(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).sector_breakdown()

    def parent_sector_breakdown(self, account_type=None, platform_name=None):
        return AccountGroup(self.accounts(), account_type, platform_name).parent_sector_breakdown()

    # ====== String representation ======

    def __repr__(self):
        s = "UserPortfolio(%s\n"%self.username()
        for account in self.accounts():
            a = "account(%s)\n" % (account)
            s += a
        s += "\n)\n"
        return s


# ============================================================================================
# Load user portfolios for all accounts
# ============================================================================================

class UserPortfolioGroup():
    def __init__(self, secu, AccountInfo):
        # self._rootdir = os.getenv('HOME') + '/AccountInfo'
        logging.debug('UserPortfolioGroup(%s)'%(AccountInfo))
        self._rootdir = AccountInfo
        self.refresh(secu)

    def refresh(self, secu):
        self._portfolios = {}

        for file in os.listdir(self._rootdir):
            # Name of JSON file with details of user portfolio (set of accounts)
            full_path = self._rootdir + '/' + file
            defn = self.load_definition(full_path)

            # Extract full user name
            username = defn['user']
            self.load_portfolio(secu, username, defn)

    def users(self):
        return self._portfolios.keys()
    
    def portfolio(self, user):
        return self._portfolios[user] if user in self.users() else None

    def get_account(self, user=None, account_type=None, platform_name=None):
        logging.debug("get_account(%s,%s,%s)" % (user, account_type, platform_name))
        for u in self.users():
            if user == u:
                accounts = self.portfolio(u).accounts(account_type, platform_name)
                logging.debug("accounts=%s len=%d" % (accounts, len(accounts)))
                assert (len(accounts) == 1), "get_account() did not return a single account"
                if len(accounts) == 1:
                    return accounts[0]
        return None

    def accounts(self, user=None, account_type=None, platform_name=None):
        acclist = []
        for u in self.users():
            if user is None or user == u:
                for a in self.portfolio(u).accounts(account_type, platform_name):
                    acclist.append(a)
        return acclist

    def positions(self, user=None, account_type=None, platform_name=None):
        poslist = []
        for u in self.users():
            if user is None or user == u:
                for p in self.portfolio(u).positions(account_type,platform_name):
                    poslist.append(p)
        return poslist

    def load_definition(self, full_path):
        with open(full_path, 'r', encoding='utf-8-sig') as fp:
            data = json.load(fp)
        return data

    def load_portfolio(self, secu, username, defn):
        self._portfolios[username] = UserPortfolio(secu, username, defn)

    # ====== Assets ======

    def asset_value(self, asset_type, user=None, account_type=None, platform_name=None):
        total = 0.0
        for u in self.users():
            if user is None or user == u:
                total += self.portfolio(u).asset_value(asset_type, account_type, platform_name)
        return total
    
    def value(self, user=None, account_type=None, platform_name=None):
        return self.asset_value('ALL', user, account_type, platform_name)

    def equity_value(self, user=None, account_type=None, platform_name=None):
        return self.asset_value('EQUITY', user, account_type, platform_name)

    def bond_value(self, user=None, account_type=None, platform_name=None):
        return self.asset_value('BOND', user, account_type, platform_name)

    def infrastructure_value(self, user=None, account_type=None, platform_name=None):
        return self.asset_value('INFRASTRUCTURE', user, account_type, platform_name)

    def property_value(self, user=None, account_type=None, platform_name=None):
        return self.asset_value('PROPERTY', user, account_type, platform_name)

    def commodity_value(self, user=None, account_type=None, platform_name=None):
        return self.asset_value('COMMODITY', user, account_type, platform_name)

    def cash_value(self, user=None, account_type=None, platform_name=None):
        return self.asset_value('CASH', user, account_type, platform_name)

    # ====== Income ======

    def annual_income(self, user=None, account_type=None, platform_name=None):
        total = 0.0
        for u in self.users():
            if user is None or user == u:
                total += self.portfolio(u).annual_income(account_type, platform_name)
        return total

    def dividend_payments(self, user=None, account_type=None, platform_name=None):
        payments = {}
        for u in self.users():
            if user is None or user == u:
                dp = self.portfolio(u).dividend_payments(account_type, platform_name)
                for dt in dp.keys():
                    if dt not in payments.keys():
                        payments[dt] = []
                    for a in dp[dt]:
                        payments[dt].append(a)
        return payments

    def dividend_projections(self, user=None, account_type=None, platform_name=None):
        payments = {}
        for u in self.users():
            if user is None or user == u:
                dp = self.portfolio(u).dividend_projections(account_type, platform_name)
                for dt in dp.keys():
                    if dt not in payments.keys():
                        payments[dt] = []
                    for a in dp[dt]:
                        payments[dt].append(a)
        return payments

    def dividend_declarations(self, user=None, account_type=None, platform_name=None):
        declarations = {}
        for u in self.users():
            if user is None or user == u:
                dp = self.portfolio(u).dividend_declarations(account_type, platform_name)
                for dt in dp.keys():
                    if dt not in declarations.keys():
                        declarations[dt] = []
                    for a in dp[dt]:
                        declarations[dt].append(a)
        return declarations

    # ====== Breakdown ======

    def asset_breakdown(self, user=None, account_type=None, platform_name=None):
        brk = {}
        for u in self.users():
            if user is None or user == u:
                b = self.portfolio(u).asset_breakdown(account_type, platform_name)
                for k in b.keys():
                    if k not in brk.keys():
                        brk[k] = 0.0
                    brk[k] += b[k]
        return brk

    def region_breakdown(self, user=None, account_type=None, platform_name=None):
        brk = {}
        for u in self.users():
            if user is None or user == u:
                b = self.portfolio(u).region_breakdown(account_type, platform_name)
                for k in b.keys():
                    if k not in brk.keys():
                        brk[k] = 0.0
                    brk[k] += b[k]
        return brk

    def sector_breakdown(self, user=None, account_type=None, platform_name=None):
        brk = {}
        for u in self.users():
            if user is None or user == u:
                b = self.portfolio(u).sector_breakdown(account_type, platform_name)
                for k in b.keys():
                    if k not in brk.keys():
                        brk[k] = 0.0
                    brk[k] += b[k]
        return brk

    def parent_sector_breakdown(self, user=None, account_type=None, platform_name=None):
        brk = {}
        for u in self.users():
            if user is None or user == u:
                b = self.portfolio(u).parent_sector_breakdown(account_type, platform_name)
                for k in b.keys():
                    if k not in brk.keys():
                        brk[k] = 0.0
                    brk[k] += b[k]
        return brk


    # ====== Data ======

    def data_asset_class_split(self, user=None, account_type=None):
        data = {}

        data['Asset Allocation'] = 'Value'
        data['Equities'] = self.equity_value(user, account_type)
        data['Bonds'] = self.bond_value(user, account_type)
        data['Infrastructure'] = self.infrastructure_value(user, account_type)
        data['Property'] = self.property_value(user, account_type)
        data['Commodities'] = self.commodity_value(user, account_type)
        data['Cash'] = self.cash_value(user, account_type)

        return data

    def data_sector_split(self, user=None, account_type=None):
        data = {}

        data['Sector Allocation'] = 'Value'
        b = self.sector_breakdown(user, account_type)
        for k in b.keys():
            data[k] = b[k]

        return data

    def data_parent_sector_split(self, user=None, account_type=None):
        data = {}
        sl = parent_sector_list()

        data['Parent Sector Allocation'] = 'Value'
        b = self.parent_sector_breakdown(user, account_type)
        for k in sl:
            if k in b.keys():
                data[k] = b[k]
        for k in b.keys():
            if k not in sl:
                data[k] = b[k]

        return data


    # ====== Template Data List ======

    # General list routine (account level)
    def tdl_account_general(self, fn, username=None, account_type=None, platform_name=None):
        poslist = []
        total = 0.0
        currentUser = currentType = None

        # Process each account meeting the filter criteria
        for account in self.accounts(username, account_type, platform_name):
            if currentUser is None or currentUser != account.username():
                dispuser = currentUser = account.username()
            else:
                dispuser = ""

            if currentType is None or currentType != account.account_type():
                currentType = account.account_type()
                disptype = account.account_type(True)
            else:
                disptype = ""

            if fn == "value":
                value = account.value()
                # Don't include zero value accounts in the list
                if value == 0.0:
                    continue
            elif fn == "income":
                value = account.annual_income()
            else:
                value = 0.0
                assert False, "Unknown value for 'fn' (%s)" % (fn)

            id = "%s_%s_%s" % (currentUser, currentType, account.platform())

            vdate = datetime.datetime.strptime(account.vdate(), '%Y%m%d').strftime('%d-%b-%Y')
            strvalue = "£ %12s" % ("{0:,.2f}".format(value))
            poslist.append({'user': dispuser,
                             'type': disptype,
                             'platform': account.platform(True),
                             'value': strvalue,
                             'vdate': vdate,
                             'id': id})
            total += value

        strvalue = "£ %12s" % ("{0:,.2f}".format(total))
        poslist.append({'user': "", 'type': "", 'platform': 'Total', 'value': strvalue, 'vdate': None, 'id': None})
        return poslist

    # General list routine (position level)
    def tdl_position_general(self, fn, username=None, account_type=None, platform_name=None, asset_class=None):
        logging.debug("tdl_position_general(%s,%s,%s,%s,%s" % (fn, username, account_type, platform_name, asset_class))
        poslist = []
        total = 0.0
        currentUserAccount = None

        for pos in self.positions(username, account_type, platform_name):
            alloc = 1.0
            if fn in ("value","value2"):
                if asset_class is None:
                    value = pos.value()
                elif asset_class == 'equity':
                    alloc = pos.equity_allocation()
                    value = pos.equity_value()
                elif asset_class == 'bond':
                    alloc = pos.bond_allocation()
                    value = pos.bond_value()
                elif asset_class == 'infrastructure':
                    alloc = pos.infrastructure_allocation()
                    value = pos.infrastructure_value()
                elif asset_class == 'property':
                    alloc = pos.property_allocation()
                    value = pos.property_value()
                elif asset_class == 'commodities':
                    alloc = pos.commodity_allocation()
                    value = pos.commodity_value()
                elif asset_class == 'cash':
                    alloc = pos.cash_allocation()
                    value = pos.cash_value()
                else:
                    assert False, "Unknown asset_class (%s)" % (asset_class)
            elif fn == "income":
                value = pos.annual_income()
            else:
                assert False, "Unknown value for 'fn' (%s)" % (fn)

            total += value
            strvalue = "£ %12s" % ("{0:,.2f}".format(value))

            if asset_class is None:
                vdate = datetime.datetime.strptime(pos.vdate(),'%Y%m%d').strftime('%d-%b-%Y')
                poslist.append({'id': pos.sname(), 'name': pos.lname(), 'value': strvalue, 'vdate': vdate})
            elif value != 0.0:
                tmpUserAccount = "%s %s %s" % (pos.username(), pos.platform(), pos.account_type(True))
                if currentUserAccount is None or tmpUserAccount != currentUserAccount:
                    dispUserAccount = currentUserAccount = tmpUserAccount
                else:
                    dispUserAccount = ""

                stralloc = "%6s" % ("{0:,.1f}".format(alloc))
                posname = "%s (%s)" % (pos.lname(), pos.sector())
                poslist.append({'useraccount': dispUserAccount, 'id': pos.sname(), 'name': posname, 'percentage': stralloc, 'value': strvalue})

        if fn != "value2":
            strvalue = "£ %12s" % ("{0:,.2f}".format(total))
            if asset_class is None:
                poslist.append({'id': None, 'name': "Total", 'value': strvalue, 'vdate': None})
            else:
                poslist.append({'id': None, 'name': 'Total', 'percentage': '', 'value': strvalue})

        return poslist


    # General list routine (payment level)
    def tdl_dividend_general(self, fn, username=None, account_type=None, platform_name=None):
        logging.debug("tdl_dividend_general(%s,%s,%s,%s" % (fn, username, account_type, platform_name))

        dlist = []
        ymtotals = {}
        mtotals = {}

        if fn in ("payments", "mpayments"):
            events = self.dividend_payments(username, account_type, platform_name)
        elif fn in ("declarations", "mdeclarations"):
            events = self.dividend_declarations(username, account_type, platform_name)
        elif fn in ("projections"):
            events = self.dividend_projections(username, account_type, platform_name)
        else:
            assert False, "Unknown value for 'fn' (%s)" % (fn)

        ythis = datetime.datetime.today().strftime('%Y')
        total = 0.0

        currentYear = currentMonth = None
        for dt in sorted(events.keys(), reverse=False):
            dispYear = dispMonth = None
            try:
                divYear = datetime.datetime.strptime(dt, '%Y%m%d').strftime('%Y')
            except:
                logging.error("Bad Date '%s'", dt)
                divYear = datetime.datetime.strptime(dt, '%Y%m%d').strftime('%Y')
            if currentYear is None or currentYear != divYear:
                dispYear = currentYear = divYear
            divMonth = datetime.datetime.strptime(dt, '%Y%m%d').strftime('%b')
            if currentMonth is None or currentMonth != divMonth:
                dispMonth = currentMonth = divMonth

            # Total for YYYYMM
            mkey = datetime.datetime.strptime(dt, '%Y%m%d').strftime('%Y%m')
            if mkey not in ymtotals.keys():
                ymtotals[mkey] = 0.0
            if currentMonth not in mtotals.keys():
                mtotals[currentMonth] = {'yprev': 0.0, 'ythis': 0.0, 'ynext': 0.0, 'total': 0.0}

            for p in events[dt]:
                vdate = datetime.datetime.strptime(dt, '%Y%m%d').strftime('%d-%b-%Y')
                strvalue = "£ %12s" % ("{0:,.2f}".format(p['amount']))
                ymtotals[mkey] += p['amount']
                mtotals[currentMonth]['total'] += p['amount']
                total += p['amount']

                if divYear < ythis:
                    mtotals[currentMonth]['yprev'] += p['amount']
                elif divYear > ythis:
                    mtotals[currentMonth]['ynext'] += p['amount']
                else:
                    mtotals[currentMonth]['ythis'] += p['amount']

                if fn in ("payments","declarations","projections"):
                    if 'status' in p.keys():
                        status = p['status']
                    else:
                        status = ' * '

                    if 'unit' in p.keys():
                        unit = p['unit']
                    else:
                        unit = '£'

                    dlist.append({'year': dispYear, 'month': dispMonth,
                              'username': p['username'],
                              'acctype': p['acctype'],
                              'platform': p['platform'],
                              'name': p['secname'], 
                              'id': p['secid'],
                              'value': strvalue, 
                              'status': status,
                              'unit': unit,
                              'date': vdate})

                    dispYear = dispMonth = None

        if fn in ("mpayments", "mdeclarations"):
            currentYear = None
            mdisplayed = {}
            for mkey in sorted(ymtotals.keys(), reverse=False):
                dispMonth = datetime.datetime.strptime(mkey, '%Y%m').strftime('%b')
                dispYear  = datetime.datetime.strptime(mkey, '%Y%m').strftime('%Y')
                if currentYear is None or dispYear != currentYear:
                    currentYear = dispYear
                else:
                    dispYear = None

                # strvalue = "£ %12s" % ("{0:,.2f}".format(ymtotals[mkey]))
                # dlist.append({'year': dispYear, 'month': dispMonth, 'value': strvalue})

                if dispMonth not in mdisplayed.keys():
                    if mtotals[dispMonth]['yprev'] == 0.0:
                        strvalprev = None
                    else:
                        strvalprev = "£ %12s" % ("{0:,.2f}".format(mtotals[dispMonth]['yprev']))

                    if mtotals[dispMonth]['ythis'] == 0.0:
                        strvalthis = None
                    else:
                        strvalthis = "£ %12s" % ("{0:,.2f}".format(mtotals[dispMonth]['ythis']))

                    if mtotals[dispMonth]['ynext'] == 0.0:
                        strvalnext = None
                    else:
                        strvalnext = "£ %12s" % ("{0:,.2f}".format(mtotals[dispMonth]['ynext']))

                    strvalue = "£ %12s" % ("{0:,.2f}".format(mtotals[dispMonth]['total']))
                    dlist.append({'month': dispMonth, 'ynext': strvalnext, 'ythis': strvalthis, 'yprev': strvalprev, 'value': strvalue})
                    mdisplayed[dispMonth] = 1

            strvalue = "£ %12s" % ("{0:,.2f}".format(total))
            dlist.append({'month': "", 'yprev': "", 'ythis': "", 'ynext': 'Total', 'value': strvalue})

        return dlist


    # Asset value for each account meeting the filter criteria
    def tdl_account_asset_value(self, user=None, account_type=None, platform_name=None):
        return self.tdl_account_general("value", user, account_type, platform_name)

    # Annual income for each account meeting the filter criteria
    def tdl_account_annual_income(self, user=None, account_type=None, platform_name=None):
        return self.tdl_account_general("income", user, account_type, platform_name)

    # Asset value at position level
    def tdl_position_asset_value(self, username=None, account_type=None, platform_name=None):
        return self.tdl_position_general("value", username, account_type, platform_name)

    # Asset class value at position level
    def tdl_position_assetclass_value(self, username=None, account_type=None, platform_name=None, asset_class=None):
        return self.tdl_position_general("value", username, account_type, platform_name, asset_class)

    # Asset value at position level without a total
    def tdl_position_list(self, username=None, account_type=None, platform_name=None):
        return self.tdl_position_general("value2", username, account_type, platform_name)

    # Asset value at position level
    def tdl_position_annual_income(self, username=None, account_type=None, platform_name=None):
        return self.tdl_position_general("income", username, account_type, platform_name)

    # Dividend payments
    def tdl_dividend_projections(self, username=None, account_type=None, platform_name=None):
        return self.tdl_dividend_general("projections", username, account_type, platform_name)
    
    # Dividend payments
    def tdl_dividend_payments(self, username=None, account_type=None, platform_name=None):
        return self.tdl_dividend_general("payments", username, account_type, platform_name)

    # Dividend declarations
    def tdl_dividend_declarations(self, username=None, account_type=None, platform_name=None):
        return self.tdl_dividend_general("declarations", username, account_type, platform_name)

    # Dividend payments (monthly)
    def tdl_dividend_mpayments(self, username=None, account_type=None, platform_name=None):
        return self.tdl_dividend_general("mpayments", username, account_type, platform_name)

    # Dividend declarations (monthly)
    def tdl_dividend_mdeclarations(self, username=None, account_type=None, platform_name=None):
        return self.tdl_dividend_general("mdeclarations", username, account_type, platform_name)

    # ====== Representation ======

    def repr_dividend_payments(self, username, account_type):
        s = ""
        payments = self.dividend_payments(username, account_type)
        for dt in sorted(payments.keys()):
            for p in payments[dt]:
                s += "%s £ %8s  %s\n" % (dt, "{0:,.2f}".format(p['amount']), p['secname'])
        return s

    def repr_dividend_declarations(self, username, account_type):
        s= ""
        declarations = self.dividend_declarations(username, account_type)
        for dt in sorted(declarations.keys()):
            for p in declarations[dt]:
                s += "%s £ %8s  %s\n" % (dt, "{0:,.2f}".format(p['amount']), p['secname'])
        return s

    def __repr__(self):
        s = ""
        for user in self.users():
            pfolio = self.portfolio(user)
            a = "UserPortGroup(\nuser=%s; pfolio=%s;\n)\n" % (user, pfolio)
            s += a
        return s

# ===================================================================================================
# TESTING
# ===================================================================================================

if __name__ == '__main__':

    def repr_account_asset_value(pgrp, username, account_type):
        total = 0.0
        s = ""
        for account in pgrp.accounts(username, account_type):
            strvalue = "{0:,.2f}".format(account.value())
            s += "%-10s %-5s %-5s £ %12s\n" % (account.username(), account.account_type(), account.platform(), strvalue)
            total += account.value()

        strvalue = "{0:,.2f}".format(total)
        s += "%22s £ %12s\n" % ("Total", strvalue)
        return s

    def repr_account_annual_income(pgrp, username, account_type):
        total = 0.0
        s = ""
        for account in pgrp.accounts(username, account_type):
            strvalue = "{0:,.2f}".format(account.annual_income())
            s += "%-10s %-5s %-5s £ %12s\n" % (account.username(), account.account_type(), account.platform(), strvalue)
            total += account.annual_income()

        strvalue = "{0:,.2f}".format(total)
        s += "%22s £ %12s\n" % ("Total", strvalue)
        return s

    def repr_asset_class_split(pgrp, username, account_type):
        total = pgrp.value(username, account_type)

        equity_amount = pgrp.equity_value(username, account_type)
        bond_amount = pgrp.bond_value(username, account_type)
        property_amount = pgrp.property_value(username, account_type)
        commodity_amount = pgrp.commodity_value(username, account_type)
        cash_amount = pgrp.cash_value(username, account_type)

        se = "{0:,.2f}".format(equity_amount)
        sb = "{0:,.2f}".format(bond_amount)
        sp = "{0:,.2f}".format(property_amount)
        sc = "{0:,.2f}".format(commodity_amount)
        sh = "{0:,.2f}".format(cash_amount)

        pe = equity_amount * 100.0 / total
        pb = bond_amount * 100.0 / total
        pp = property_amount * 100.0 / total
        pc = commodity_amount * 100.0 / total
        ph = cash_amount * 100.0 / total

        s  = "Equity    £ %10s (%4.1f%%)\n" % (se, pe)
        s += "Bond      £ %10s (%4.1f%%)\n" % (sb, pb)
        s += "Property  £ %10s (%4.1f%%)\n" % (sp, pp)
        s += "Commodity £ %10s (%4.1f%%)\n" % (sc, pc)
        s += "Cash      £ %10s (%4.1f%%)\n" % (sh, ph)

        return (s)

    def repr_asset_breakdown(pgrp, username, account_type):
        total = pgrp.value(username, account_type)
        brk = pgrp.asset_breakdown(username, account_type)
        s = ""
        sbrk = dict(sorted(brk.items(), key=lambda item: -1 * item[1]))
        for k in sbrk:
            amount = sbrk[k]
            a = "{0:,.2f}".format(amount)
            p = amount * 100.0 / total
            s += "%-40s £ %10s (%4.1f%%)\n" % (k, a, p)
        return (s)

    def repr_region_breakdown(pgrp, username, account_type):
        total = pgrp.value(username, account_type)
        brk = pgrp.region_breakdown(username, account_type)
        s = ""
        sbrk = dict(sorted(brk.items(), key=lambda item: -1 * item[1]))
        for k in sbrk:
            amount = sbrk[k]
            a = "{0:,.2f}".format(amount)
            p = amount * 100.0 / total
            s += "%-40s £ %10s (%4.1f%%)\n" % (k, a, p)
        return (s)

    def repr_tdl(tdl):
        s = ""
        for item in tdl:
            s += "%s\n" % (item)
        return s

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    
    # Load details of all securities held in positions
    secinfo_dir = os.getenv('HOME') + '/SecurityInfo'
    secu  = SecurityUniverse(secinfo_dir)

    # Initialise user portfolios
    accinfo_dir = './tmp'
    pgrp = UserPortfolioGroup(secu, accinfo_dir)

    # For each user, the above does:
    # UserPortfolio(secu, username, defn)
    # ... and for each configured account ...
    # Account(secu, self.username(), defn)

    # --- Unit Tests of functions
    print("value=%.02f" % (pgrp.value('Paul','ISA')))
    print("equity=%.02f" % (pgrp.equity_value('Paul','ISA')))
    print("bond=%.02f" % (pgrp.bond_value('Paul', 'ISA')))
    print("property%.02f" % (pgrp.property_value('Paul', 'ISA')))
    print("commodity=%.02f" % (pgrp.commodity_value('Paul', 'ISA')))
    print("cash=%.02f" % (pgrp.cash_value('Paul', 'ISA')))
    print("income=%.02f" % (pgrp.annual_income(None,'ISA')))

    # --- Account level asset/income values
    print(repr_account_asset_value(pgrp, None, None))
    print(repr_account_annual_income(pgrp, None, 'ISA'))
    print(repr_tdl(pgrp.tdl_account_asset_value('Paul', 'ISA')))
    print(repr_tdl(pgrp.tdl_account_annual_income('Paul', 'ISA')))

    # --- Position level asset/income values
    # print(repr_tdl(pgrp.tdl_position_asset_value('User2','ISA')))
    # print(repr_tdl(pgrp.tdl_position_annual_income('User2','ISA')))

    # --- Asset class split
    # print(repr_asset_class_split(pgrp, None, None ))
    # print(pgrp.data_asset_class_split())
    
    # print(repr_asset_breakdown(pgrp, None, None))
    # print(repr_region_breakdown(pgrp, None, None))

    # print(pgrp.repr_dividend_payments('User2', 'ISA'))
    # print(pgrp.repr_dividend_declarations('User2', 'ISA'))
    # for e in pgrp.tdl_dividend_payments('User2','ISA'):
    #     print(e)
    # for e in pgrp.tdl_dividend_declarations('User2','ISA'):
    #    print(e)
    # for e in pgrp.tdl_dividend_mpayments('User2','ISA'):
    #     print(e)

    print("Sector Breakdown")
    b = pgrp.parent_sector_breakdown(None,None)
    for k in b.keys():
        print("%s=%.2f"%(k,b[k]))



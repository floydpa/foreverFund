import os
import re
import json
import logging

from decimal import Decimal

# ASSET CLASS BREAKDOWN (DD/MM/YYYY)
# REGION BREAKDOWN (DD/MM/YYYY)

def income_payments_per_year(freq):
    np = {'A':1,'S':2,'Q':4,'M':12}
    try:
        npayments = np[freq]
    except:
        errstr = f"Bad freq={freq}"
        assert False, errstr

    return npayments

def truncate_decimal(value, decimal_places=2):
    # Create a Decimal object from the input value
    d = Decimal(value)
    
    # Shift decimal point right, truncate, then shift back left
    truncated = d.quantize(Decimal(f'1.{"0" * decimal_places}'), rounding="ROUND_DOWN")
    
    return truncated


class Breakdown():
    def __init__(self,name):
        self._rootdir = os.getenv('HOME') + '/SecurityInfo/Breakdown'
        self._assets = []
        self._regions = []
        full_path = self._rootdir + '/' + name
        in_assets = False
        in_region = False
        if os.path.isfile(full_path):
            with open(full_path, 'r', encoding='utf-8-sig') as fp:
                try:
                    for line in fp:
                        if 'ASSET CLASS BREAKDOWN' in line:
                            in_assets = True
                            in_region = False
                            continue
                        if 'REGION BREAKDOWN' in line:
                            in_assets = False
                            in_region = True
                            continue
                        if 'SECTOR BREAKDOWN' in line:
                            in_assets = False
                            in_region = False
                            continue
                        if in_assets or in_region:
                            a = re.split(r'\t+', line.rstrip())
                            # print(a)
                            if a[0] == 'Rank':
                                continue
                            if in_assets:
                                self._assets.append({'rank':int(a[0]), 'asset':a[1], 'percent':float(a[2])})
                            if in_region:
                                self._regions.append({'rank':int(a[0]), 'region':a[1], 'percent':float(a[2])})
                except:
                    print("ERROR:%s" % (full_path))
                    exit(1)

    def asset_breakdown(self):
        brk = {}
        for a in self._assets:
            brk[a['asset']] = a['percent']
        return brk

    def region_breakdown(self):
        brk = {}
        for a in self._regions:
            brk[a['region']] = a['percent']
        return brk

    def __repr__(self):
        str = "regions=%s\nassets=%s" % (json.dumps(self._regions), json.dumps(self._assets))
        return str


class AssetAllocation:
    def __init__(self, sector, amount, override=None):
        splits = {
            "Asia Pacific Ex Japan": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Asia Pacific Income": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Asia Pacific Smaller Companies": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Banks": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Cash": 
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 100.0 },
            "Commodities & Natural Resources": 
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 100.0, "cash": 0.0 },
            "Debt - Loans & Bonds":
                {"equity": 0.0, "bond": 100.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0},
            "Europe":
                {"equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0},
            "Financials": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Flexible Investment":
                { "equity": 40.0, "bond": 40.0, "infrastructure": 0.0, "property": 10.0, "commodities": 5.0, "cash": 5.0},
            "GBP Strategic Bond":
                { "equity": 0.0, "bond": 100.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Gbl ETF Equity - Europe ex UK":
                {"equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0},
            "Global": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Global Bonds": 
                { "equity": 0.0, "bond": 100.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Global Equities": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Global Equity Income": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Global Property": 
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 100.0, "commodities": 0.0, "cash": 0.0 },
            "Global Smaller Companies":
                {"equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0},
            "Infrastructure":
                {"equity": 0.0, "bond": 0.0, "infrastructure": 100.0, "property": 0.0, "commodities": 0.0, "cash": 0.0},
            "Japanese Smaller Companies":
                {"equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0},
            "Latin America":
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Mixed Investment 0-35% Shares": 
                { "equity": 20.0, "bond": 80.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Mixed Investment 20-60% Shares": 
                { "equity": 40.0, "bond": 60.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Mixed Investment 40-85% Shares": 
                { "equity": 62.5, "bond": 37.5, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Property": 
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 100.0, "commodities": 0.0, "cash": 0.0 },
            "Property Securities": 
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 100.0, "commodities": 0.0, "cash": 0.0 },
            "Property - UK Commercial": 
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 100.0, "commodities": 0.0, "cash": 0.0 },
            "Real Estate Investment Trusts":
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 100.0, "commodities": 0.0, "cash": 0.0},
            "Short Term Money Market": 
                { "equity": 0.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 100.0 },
            "Specialist": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "Technology & Telecommunications": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "UK All Companies": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "UK Equity Income": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "UK Smaller Companies": 
                { "equity": 100.0, "bond": 0.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "USD Index Linked": 
                { "equity": 0.0, "bond": 100.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0 },
            "With Profits":
                # {"equity": 40.0, "bond": 45.0, "infrastructure": 0.0, "property": 15.0, "commodities": 0.0, "cash": 0.0},
                {"equity": 0.0, "bond": 100.0, "infrastructure": 0.0, "property": 0.0, "commodities": 0.0, "cash": 0.0},
            }

        if sector not in splits.keys():
            assert False, "ERROR: AssetAllocation(%s) - sector not defined" % (sector)

        if override is not None:
            logging.debug("AssetAllocation override=%s"%(override))
            ss = override
        else:
            ss = splits[sector]

        self._aa = {}
        self._aa['equity'] = ss['equity'] * amount / 100.0
        self._aa['bond'] = ss['bond'] * amount / 100.0
        self._aa['infrastructure'] = ss['infrastructure'] * amount / 100.0
        self._aa['property'] = ss['property'] * amount / 100.0
        self._aa['commodities'] = ss['commodities'] * amount / 100.0
        self._aa['cash'] = ss['cash'] * amount / 100.0

    def allocation_equity(self):
        return self._aa['equity']

    def allocation_bond(self):
        return self._aa['bond']

    def allocation_infrastructure(self):
        return self._aa['infrastructure']

    def allocation_property(self):
        return self._aa['property']

    def allocation_commodity(self):
        return self._aa['commodities']

    def allocation_cash(self):
        return self._aa['cash']

    def __repr__(self):
        s = "%s" % (self._aa)
        return s


def parent_sector_list():
    return [
        "Global Equity",
        "Asia Pacific Equity",
        "Europe Equity"
        "UK Equity",
        "Mixed Investment",
        "Global Bonds",
        "GBP Strategic Bond",
        "Property",
        "Commodities",
        "Money Market"
    ]

class SectorAllocation():
    def __init__(self, sector, amount):
        super_sector = {
        "Asia Pacific Ex Japan": "Asia Pacific Equity",
        "Asia Pacific Income": "Asia Pacific Equity",
        "Asia Pacific Smaller Companies": "Asia Pacific Equity",
        "Banks": "UK Equity",
        "Cash": "Money Market",
        "Commodities & Natural Resources": "Commodities",
        "Debt - Loans & Bonds": "GBP Strategic Bond",
        "Europe": "Europe Equity",
        "Financials": "Global Equity",
        "Flexible Investment": "Mixed Investment",
        "GBP Strategic Bond": "GBP Strategic Bond",
        "Gbl ETF Equity - Europe ex UK": "Europe Equity",
        "Global": "Global Equity",
        "Global Bonds": "Global Bonds",
        "Global Equities": "Global Equity",
        "Global Equity Income": "Global Equity",
        "Global Property": "Property",
        "Global Smaller Companies": "Global Equity",
        "Infrastructure": "Mixed Investment",
        "Japanese Smaller Companies": "Asia Pacific Equity",
        "Latin America": "Global Equity",
        "Mixed Investment 0-35% Shares": "Mixed Investment",
        "Mixed Investment 20-60% Shares": "Mixed Investment",
        "Mixed Investment 40-85% Shares": "Mixed Investment",
        "Property": "Property",
        "Property Securities": "Property",
        "Property - UK Commercial": "Property",
        "Real Estate Investment Trusts": "Property",
        "Short Term Money Market": "Money Market",
        "Specialist": "Global Equity",
        "Technology & Telecommunications": "Global Equity",
        "UK All Companies": "UK Equity",
        "UK Equity Income": "UK Equity",
        "UK Smaller Companies": "UK Equity",
        "USD Index Linked": "Global Bonds",
        "With Profits": "Mixed Investment"
        }

        if sector not in super_sector.keys():
            assert False, "ERROR: SectorAllocation(%s) - sector not defined" % (sector)

        self._amount = amount
        self._sector = sector
        self._parent_sector = super_sector[sector]

    def amount(self):
        return self._amount

    def sector(self):
        return self._sector

    def parent_sector(self):
        return self._parent_sector

    def __repr__(self):
        s = "%s (%s) = %.2f" % (self.sector(), self.parent_sector(), self.amount())
        return s

class RiskAllocation():
    def __init__(self, sector):
        risk_bucket = {
        "Asia Pacific Ex Japan": "High",
        "Asia Pacific Income": "High",
        "Asia Pacific Smaller Companies": "High",
        "Banks": "High",
        "Cash": "Cash",
        "Commodities & Natural Resources": "High",
        "Debt - Loans & Bonds": "Moderate",
        "Europe": "High",
        "Financials": "High",
        "Flexible Investment": "Moderate",
        "GBP Strategic Bond": "Moderate",
        "Gbl ETF Equity - Europe ex UK": "High",
        "Global": "High",
        "Global Bonds": "Moderate",
        "Global Equities": "High",
        "Global Equity Income": "High",
        "Global Property": "Moderate",
        "Global Smaller Companies": "High",
        "Infrastructure": "Moderate",
        "Japanese Smaller Companies": "High",
        "Latin America": "High",
        "Mixed Investment 0-35% Shares": "Moderate",
        "Mixed Investment 20-60% Shares": "Moderate",
        "Mixed Investment 40-85% Shares": "High",
        "Property": "Moderate",
        "Property Securities": "Moderate",
        "Property - UK Commercial": "Moderate",
        "Real Estate Investment Trusts": "Moderate",
        "Short Term Money Market": "Cash",
        "Specialist": "High",
        "Technology & Telecommunications": "High",
        "UK All Companies": "High",
        "UK Equity Income": "High",
        "UK Smaller Companies": "High",
        "USD Index Linked": "Moderate",
        "With Profits": "Moderate"
        }

        if sector not in risk_bucket.keys():
            errstr = "ERROR: RiskAllocation(%s) - sector not defined" % (sector)
            assert False, errstr

        self._sector = sector
        self._risk_bucket = risk_bucket[sector]

    def sector(self):
        return self._sector

    def risk_bucket(self):
        return self._risk_bucket

    def __repr__(self):
        s = "%s = %s" % (self.sector(), self.risk_bucket())
        return s

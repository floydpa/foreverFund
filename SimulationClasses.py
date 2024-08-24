# Classes for retirement simulation

import pandas as pd
import re
import sys
import os
import logging
import datetime
from dateutil.relativedelta import relativedelta

from AccountClasses import AccountGroup

from app import sim_conf

class Simulation:
    def __init__(self, startYear, nYears, persons):
        self._startYear = startYear
        self._nYears = nYears
        self._persons = persons
        self._years = []
        self._config = sim_conf

        for i in range(0, nYears):
            self._years.append(SimYear(self, startYear + i))

    def firstYear(self):
        return self._startYear

    def lastYear(self):
        return self.firstYear() + self._nYears - 1

    def persons(self):
        return self._persons

    def CPI(self):
        return self._config.get_CPI()

    def RPI(self):
        return self._config.get_RPI()

    def portfolioGrowthRate(self, assetType):
        if assetType in ('aPn','aISA'):
            rate = self._config.get_portfolioGrowth()
        else:
            rate = 0.0

        return 1 + rate

    def livingExpenses1(self):
        return self._config.get_livingExpenses1()

    def livingExpenses2(self):
        return self._config.get_livingExpenses2()

    def fullStatePension(self):
        return self._config.fullStatePension

    def tuiPension(self):
        return self._config.tuiPension

    def expensiveYears(self):
        return self._config.get_expensiveYears()

    def taxFreeAmount(self):
        return self._config.taxFreeAmount

    def basicRateAmount(self):
        return self._config.basicRateAmount

    def taxrateBasic(self):
        return self._config.taxrateBasic

    def taxrateHigh(self):
        return self._config.taxrateHigh

    def yearData(self, year):
        if year < self.firstYear() or year > self.lastYear():
            return None
        else:
            return self._years[year - self.firstYear()]

    def __repr__(self):
        s = "Year,Expenses,TaxFreeAmt,BasicRateAmt,FullStatePens\n"
        for y in self._years:
            line = "%s\n" % (y)
            s += line

        for k in self._persons.keys():
            line = "\n%s\n" % (self._persons[k])
            s += line

        return "Simulation()\n%s" % (s)


class SimYear:
    def __init__(self, simulation, year):

        prev = simulation.yearData(year-1)

        # Start and end of tax year
        dt_start = "06/04/%d" % (year);
        dt_end   = "05/04/%d" % (year + 1);

        self.simulation = simulation
        self.year = year
        self.taxyearStart = datetime.datetime.strptime(dt_start, "%d/%m/%Y").date()
        self.taxyearEnd   = datetime.datetime.strptime(dt_end, "%d/%m/%Y").date()

        #--- Calculate living expenses and full state pension

        if year == simulation.firstYear():
            self.livingExpenses1 = simulation.livingExpenses1()
            self.livingExpenses2 = simulation.livingExpenses2()
            self.fullStatePension = simulation.fullStatePension()
        else:
            self.livingExpenses1 = prev.livingExpenses1 * (1 + simulation.RPI())
            self.livingExpenses2 = prev.livingExpenses2 * (1 + simulation.RPI())
            self.fullStatePension = prev.fullStatePension * (1 + simulation.CPI())

        if year < 2024:
            self.tuiPension = 0.0
        elif year == 2024:
            self.tuiPension = simulation.tuiPension()
        else:
            self.tuiPension = prev.tuiPension * 1.025

        if year < simulation.firstYear() + simulation.expensiveYears():
            self.livingExpenses = self.livingExpenses1
        else:
            self.livingExpenses = self.livingExpenses2

        logging.debug("living expenses %.2f %.2f %.2f"%(self.livingExpenses,self.livingExpenses1,self.livingExpenses2))

        #--- Tax thresholds frozen for a few years then assume increase with CPI

        if year < 2026:
            self.taxFreeAmount = simulation.taxFreeAmount()
            self.basicRateAmount = simulation.basicRateAmount()
        else:
            self.taxFreeAmount = prev.taxFreeAmount * (1 + simulation.CPI())
            self.basicRateAmount = prev.basicRateAmount * (1 + simulation.CPI())

        #--- Determine income for each person
        persons = simulation.persons()
        requiredIncome = self.livingExpenses
        for id in sorted(persons.keys()):
            person = persons[id]
            person.init_simyear(year)
            income = person.netIncome(self, requiredIncome)
            requiredIncome = requiredIncome - income
            logging.debug("--- Income=%.2f leaving required income=%.2f" % (income, requiredIncome))

    def incomePensSP(self, sp_date, spRatio):
        if sp_date > self.taxyearEnd:  # Doesn't reach state pension age until after this year
            amount = 0.0
        elif sp_date < self.taxyearStart:  # Reached state pension age before this year
            amount = self.fullStatePension * spRatio
        else:       # Return a portion of the amount
            d2 = self.taxyearEnd
            d1 = sp_date
            amount = self.fullStatePension * spRatio * (d2-d1).days/365
        logging.debug("incomePensSP(sp_date=%s) end=%s full=%.2f amount=%.2f", sp_date, self.taxyearEnd, self.fullStatePension, amount)
        return amount

    def incomePensTUI(self, tui_date):
        if tui_date > self.taxyearEnd:  # Doesn't reach TUI pension age until after this year
            amount = 0.0
        elif tui_date < self.taxyearStart:  # Reached TUI pension age before this year
            amount = self.tuiPension
        else:       # Return a portion of the amount
            d2 = self.taxyearEnd
            d1 = tui_date
            amount = self.tuiPension * (d2-d1).days/365
        logging.debug("incomePensTUI(tui_date=%s) end=%s full=%.2f amount=%.2f", tui_date, self.taxyearEnd, self.tuiPension, amount)
        return amount

    def incomeTax(self, grossAmount):
        highTax = 0.0
        if grossAmount <= self.taxFreeAmount:
            basicTax = 0.0
        else:
            taxableAmount = grossAmount - self.taxFreeAmount
            if taxableAmount <= self.basicRateAmount:
                basicTax = taxableAmount * self.simulation.taxrateBasic()
            else:
                basicTax = self.basicRateAmount * self.simulation.taxrateBasic()
                highTax = (taxableAmount - self.basicRateAmount) * self.simulation.taxrateHigh()

        totalTax = basicTax + highTax
        logging.debug("incomeTax(gross=%.2f taxFree=%.2f basic=%.2f hig=%.2f", grossAmount, self.taxFreeAmount, basicTax, highTax)
        return totalTax

    def __repr__(self):
        s = "%d,%.0f,%.0f,%.0f,%.0f" % (self.year, self.livingExpenses, self.taxFreeAmount, self.basicRateAmount, self.fullStatePension)
        return s


class SimPerson:
    def __init__(self, portfolio, assets):
        self._portfolio = portfolio
        self._assets = assets.copy()     # Assets at the start of the simulation
        self._simyears = {}

    def init_simyear(self, year):
        ystr = "%d" % (year)
        self._simyears[ystr] = {}

    #--- Configuration

    def id(self):
        return self._portfolio.id()

    def username(self):
        return self._portfolio.username()

    def dob(self):
        return datetime.datetime.strptime(self._portfolio.dob(), "%d/%m/%Y").date()

    def rtDate(self):
        dt = self._portfolio.rtDate()
        if dt is not None:
            dt = datetime.datetime.strptime(dt, "%d/%m/%Y").date()
        return dt

    def spDate(self):
        return datetime.datetime.strptime(self._portfolio.spDate(), "%d/%m/%Y").date()

    def spRatio(self):
        return self._portfolio.spRatio()

    def drawdownPens(self):
        return self._portfolio.drawdownPens()

    def drawdownISA(self):
        return self._portfolio.drawdownISA()

    def drawdownTrd(self):
        return self._portfolio.drawdownTrd()

    def spShortfall(self):
        return self._portfolio.spShortfall()

    def savShortfall(self):
        return self._portfolio.savShortfall()

    #--- Amend assets for this year

    def get_fin(self, simyear, assetType):
        ystr = "%d" % (simyear.year)
        return self._simyears[ystr][assetType]

    def set_fin(self, simyear, assetType, value):
        ystr = "%d" % (simyear.year)
        self._simyears[ystr][assetType] = value

    #--- Income (from drawing down)

    def incomePensDB(self, simyear):
        total = 0.0
        if self.id() == "1":
            tuiDate = "25/10/2024"
            dt = datetime.datetime.strptime(tuiDate, "%d/%m/%Y").date()
            total = simyear.incomePensTUI(dt)
        return total

    def incomePensDC(self, simyear):
        spAmount = self.get_fin(simyear,'pensSP')
        pensionAssets = self.get_fin(simyear,'aPn')

        total = drawdownAmount = self.drawdownPens() * pensionAssets
        spTopUp = 0.0
        if self.spShortfall() == "Yes":
            fullSP = simyear.fullStatePension
            if spAmount < fullSP:
                spTopUp = fullSP - spAmount

        total += spTopUp
        logging.debug("incomePensDC %.2f (DCA=%.2f DD=%.2f SPTU=%.2f)"%(total, pensionAssets, drawdownAmount, spTopUp))

        self.set_fin(simyear, 'pensDC', total)
        self.set_fin(simyear, 'pensDC.DD', drawdownAmount)
        self.set_fin(simyear, 'pensDC.spTU', spTopUp)
        self.set_fin(simyear, 'aPn', pensionAssets - total)

        return total

    def incomeISA(self, simyear):
        isaAssets = self.get_fin(simyear,'aISA')
        drawndownAmount = self.drawdownISA() * isaAssets
        logging.debug("incomeISA %.2f (ISA=%.2f)"%(drawndownAmount,isaAssets))
        self.set_fin(simyear, 'iISA', drawndownAmount)
        self.set_fin(simyear, 'aISA', isaAssets - drawndownAmount)
        return drawndownAmount

    def incomeTrading(self, simyear):
        trdAssets = self.get_fin(simyear, 'aTrd')
        drawndownAmount = self.drawdownTrd() * trdAssets
        logging.debug("incomeTrd %.2f (Trd=%.2f)" % (drawndownAmount, trdAssets))
        self.set_fin(simyear, 'iTrd', drawndownAmount)
        self.set_fin(simyear, 'aTrd', trdAssets - drawndownAmount)
        return drawndownAmount

    def incomeSavings(self, simyear, shortfallAmount):
        topUp = 0.0
        if self.savShortfall() == "Yes" and shortfallAmount > 0:
            savAssets = self.get_fin(simyear, 'aSav')
            if shortfallAmount < savAssets:
                topUp = shortfallAmount
            else:
                topUp = savAssets

            self.set_fin(simyear, 'iSav', topUp)
            self.set_fin(simyear, 'aSav', savAssets - topUp)

        return topUp

    def taxableIncome(self, simyear):
        total = 0.0

        # Amount of State Pension
        spAmount = simyear.incomePensSP(self.spDate(), self.spRatio())
        self.set_fin(simyear,'pensSP',spAmount)
        total += spAmount

        # Amount of any DB Pension
        dbPens = self.incomePensDB(simyear)
        self.set_fin(simyear,'pensDB',dbPens)
        total += dbPens

        # Amount of drawdown from DC Pension accounts
        dcPens = self.incomePensDC(simyear)
        total += dcPens

        self.set_fin(simyear,'taxable',total)
        return total

    def taxfreeIncome(self, simyear, shortfallAmount):
        # Amount of tax-free drawdown from ISA account
        total = 0.0

        isaAmount = self.incomeISA(simyear)
        total += isaAmount
        shortfallAmount -= isaAmount

        # Amount of tax-free income from Trading account
        trdAmount = self.incomeTrading(simyear)
        total += trdAmount
        shortfallAmount -= trdAmount

        # Amount to withdraw from savings to make up shortfall
        savAmount = self.incomeSavings(simyear, shortfallAmount)
        total += savAmount

        self.set_fin(simyear,'taxfree',total)
        return total

    def netIncome(self, simyear, targetIncome):
        # print("netIncome({%s},{%s},%.2f"%(self, simyear, targetIncome))
        thisYear = "%d" % (simyear.year)
        prevYear = "%d" % (simyear.year - 1)

        # assets at start of simulation year
        if simyear.year == simyear.simulation.firstYear():
            self.set_fin(simyear,'aPn',self._assets['Pens'])
            self.set_fin(simyear,'aISA',self._assets['ISA'])
            self.set_fin(simyear,'aTrd',self._assets['Trd'])
            self.set_fin(simyear,'aSav',self._assets['Sav'])
        else:
            self.set_fin(simyear,'aPn', self._simyears[prevYear]['aPn'])
            self.set_fin(simyear,'aISA',self._simyears[prevYear]['aISA'])
            self.set_fin(simyear,'aTrd',self._simyears[prevYear]['aTrd'])
            self.set_fin(simyear,'aSav',self._simyears[prevYear]['aSav'])

        # Taxable income from pensions
        taxableIncome = self.taxableIncome(simyear)

        # Tax to pay on combined pension income
        taxPayable = simyear.incomeTax(taxableIncome)
        self.set_fin(simyear,'tax',taxPayable)

        targetIncome -= (taxableIncome - taxPayable)
        taxfreeIncome = self.taxfreeIncome(simyear, targetIncome)

        logging.debug("%s %d taxfree=%.2f taxable=%.2f tax=%.2f"%(self.username(), simyear.year, taxfreeIncome, taxableIncome, taxPayable))

        # Save the assets at the end of the current year
        logging.debug("%s %d assets=%s"%(self.username(), simyear.year, self._simyears[thisYear]))

        # Allow for growth of each portfolio type to give year-end total
        for ptype in ('aPn','aISA','aTrd','aSav'):
            self.set_fin(simyear,ptype,self.get_fin(simyear,ptype)*simyear.simulation.portfolioGrowthRate(ptype))

        total = taxfreeIncome + taxableIncome - taxPayable
        self.set_fin(simyear,'_income', total)
        return total

    # assets at the end of the previous year of the simulation
    def __repr__(self):
        s = "SimPerson(%s,%s,%s,%s,%.2f)" % (self.id(),self.username(), self.dob(), self.spDate(), self.spRatio())
        for y in sorted(self._simyears.keys()):
            a = self._simyears[y]
            s += "\n%s {" % (y)
            for k in sorted(a.keys()):
                s += "%s: %.2f "%(k, a[k])
            s += "}"
        return s


if __name__ == '__main__':

    from SecurityClasses import SecurityUniverse
    from PortfolioClasses import UserPortfolioGroup
    from config import SECURITYINFO, ACCOUNTINFO

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

    secu = SecurityUniverse(SECURITYINFO)
    pgrp = UserPortfolioGroup(secu, ACCOUNTINFO)

    simYear0  = 2022    # Start year of simulation
    simLength = 12      # Number of years

    persons = {}
    for name in pgrp.users():
        p = pgrp.portfolio(name)
        id = p.id()
        logging.debug("PERSON(%s)=%s"%(id,name))

        assets= {}
        for accountType in ['Pens','ISA','Trd','Sav']:
            assets[accountType] = pgrp.value(name, accountType)

        persons[id] = SimPerson(p, assets)

    # print(persons)

    # Simulate N years starting from a nominated year
    sim = Simulation(simYear0, simLength, persons)

    print(sim)



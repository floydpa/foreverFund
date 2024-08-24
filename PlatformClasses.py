# Platform accounts making up a portfolio

import pandas as pd
import re
import sys
import os

import logging
import datetime

from pathlib import Path

from SecurityClasses import SecurityUniverse
from PositionClasses import Position

def platformCode_to_class(code):
    return getattr(sys.modules[__name__], code)


class Platform:
    def __init__(self):
        self._fullname = None
        self._vdate = None

    def name(self, fullname=False):
        return self._fullname if fullname else self.__class__.__name__

    def vdate(self):
        return self._vdate

    def set_vdate(self, summary_file):
        # filename = os.readlink(self.userdata_dirname() + '/' + summary_file)
        filename = os.readlink(summary_file)
        self._vdate = re.sub('\.csv$','',re.sub('^.*_','',filename))

    def load_positions(self, secu, userCode, accountType, summary_file=None):
        positions = []
        if summary_file is None:
            summary_file = self.latest_file(userCode,accountType)
        self.set_vdate(summary_file)
        df = pd.read_csv(summary_file)
        # print(summary_file)
        # print(df)
        labels = ['Investment', 'Quantity', 'Price', 'Value (£)']
        for n in range(0, len(df)):
            inv = df['Investment'][n]
            sym = inv
            qty = float(re.sub(',', '', str(df['Quantity'][n])))
            price = float(df['Price'][n])
            value = float(re.sub(',', '', str(df['Value (£)'][n])))

            security = secu.find_security(sym)
            pos = Position(security, qty, price, value, self.vdate())

            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions

    def download_dirname(self):
        return "/mnt/chromeos/MyFiles/Downloads"

    def userdata_dirname(self):
        return "%s/UserData" % (os.getenv('HOME'))
    
    def download_filename(self, username, accountType):
        return None

    def current_filename(self, userCode, accountType):
        destlink   = self.latest_file(userCode,accountType)
        return os.readlink(destlink)

    def temp_filename(self, userCode, accountType):
        logging.debug("temp_filename(%s,%s)"%(userCode,accountType))
        return "%s/%s_%s.tmp" % (self.download_dirname(), userCode, accountType)

    def download_formname(self):
        return None

    def dated_file(self, userCode, accountType, dt=None):
        datadir = self.userdata_dirname()
        if dt is None:
            dt = datetime.datetime.now().strftime("%Y%m%d")
        return "%s/%s_%s_%s_%s.csv" % (datadir, userCode, self.name(), accountType, dt)
    
    def latest_file(self, userCode, accountType):
        datadir = self.userdata_dirname()
        return "%s/%s_%s_%s_latest" % (datadir, userCode, self.name(), accountType)

    def update_savings(self, userCode, accountType, cashAmount):
        datadir    = self.userdata_dirname()
        destfile   = self.dated_file(userCode, accountType)
        destlink   = self.latest_file(userCode,accountType)
        sourcefile = "%s/%s" % (datadir, os.readlink(destlink))
        tempfile   = self.temp_filename(userCode, accountType)

        logging.debug("src=%s dest=%s link=%s temp=%s" % (sourcefile,destfile,destlink,tempfile))

        # Create new file in temporary location
        with open(sourcefile, 'r', encoding='utf-8-sig') as fpin:
            lines = fpin.readlines()
            fpin.close()

        security = re.sub(',.*$','',lines[1].rstrip())
        lines[1] = '%s,"%.2f","100","%.2f","%.2f"\n' % (security, cashAmount, cashAmount, cashAmount)

        fpout = open(tempfile, "w")
        fpout.writelines(lines)
        fpout.close()

        # Copy temp file into place
        fpout = open(destfile, "w")
        with open(tempfile, 'r', encoding='utf-8-sig') as fpin:
            for line in fpin:
                fpout.write(line)
        fpout.close()
        fpin.close()

        # Update latest link to point to newly created file
        # Remove the temporary file from the download area
        self.update_latest_link(tempfile, destfile, destlink)

    def update_latest_link(self, downloadFile, destFile, destLink, removeSource=True):
        """Update the 'latest' link to point to the new file and remove downloaded file"""
        os.unlink(destLink)
        os.symlink(destFile, destLink)
        logging.debug("symlink(%s,%s)" % (destFile, destLink))

        # Finally remove the source file which had been downloaded
        if removeSource:
            logging.debug("unlink(%s)" % (downloadFile))
            os.unlink(downloadFile)

    def __repr__(self):
        return "PLATFORM(%s,%s)" % (self.name(), self.name(True))


class AJB(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "AJ Bell Youinvest"

    def download_filename(self, userCode, accountType):
        logging.debug("download_filename(%s,%s)"%(userCode,accountType))
        if userCode == 'C' and accountType == 'ISA':
            filename = "portfolio-AB9F2PI-ISA.csv"
        elif userCode == 'P' and accountType == 'Pens':
            filename = "portfolio-A20782S-SIPP.csv"
        else:
            filename = None
        return "%s/%s" % (self.download_dirname(), filename) if filename else None

    def download_formname(self):
        return "FileDownloadForm"

    def load_positions(self, secu, userCode, accountType, summary_file=None):
        positions = []
        if summary_file is None:
            summary_file = self.latest_file(userCode,accountType)
        self.set_vdate(summary_file)
        df = pd.read_csv(summary_file)
        labels = ['Investment', 'Quantity', 'Price', 'Value (£)']
        for n in range(0, len(df)):
            inv = df['Investment'][n]
            if 'LSE:' in inv:
                sym = re.sub('.*\(LSE:(.*)\).*', '\\1', inv) + ".L"
            elif 'FUND:' in inv:
                sym = re.sub('.*\(FUND:(.*)\).*', '\\1', inv)
            elif 'SEDOL:' in inv:
                sym = re.sub('.*\(SEDOL:(.*)\).*', '\\1', inv)
            else:
                sym = inv

            qty = float(re.sub(',', '', df['Quantity'][n]))
            price = float(df['Price'][n]) * 100.0
            value = float(re.sub(',', '', df['Value (£)'][n]))

            if sym in ('Cash GBP'):
                security = secu.find_security('Cash')
            else:
                security = secu.find_security(sym)

            pos = Position(security, qty, price, value, self.vdate())
            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions

    def update_positions(self, userCode, accountType):
        destfile = self.dated_file(userCode, accountType)
        destlink = self.latest_file(userCode,accountType)
        filename = self.download_filename(userCode,accountType)

        logging.debug("source=%s" % (filename))
        logging.debug("destfile=%s" % (destfile))
        logging.debug("destlink=%s" % (destlink))

        # Copy all lines across
        fpout = open(destfile, "w")
        with open(filename, 'r', encoding='utf-8-sig') as fpin:
            for line in fpin:
                fpout.write(line)
        fpout.close()
        fpin.close()

        # Update latest link to point to newly created file
        # Remove the source file from the download area
        self.update_latest_link(filename, destfile, destlink)


class AV(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Aviva"

    def load_positions(self, secu, userCode, accountType, summary_file=None):
        positions = []
        if summary_file is None:
            summary_file = self.latest_file(userCode,accountType)
        self.set_vdate(summary_file)
        df = pd.read_csv(summary_file)
        labels = ['Symbol', 'Qty', 'Price', 'Market Value']

        for n in range(0, len(df)):
            sym = df['Symbol'][n]
            # print("SYM=%s" % (sym))
            qty = float(re.sub(',', '', str(df['Qty'][n])))
            price = float(re.sub('[,p]', '', str(df['Price'][n])))
            mv = df['Market Value'][n]
            value = float(re.sub('[,£]', '', mv))
            security = secu.find_security(sym)
            pos = Position(security, qty, price, value, self.vdate())
            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions

    def download_formname(self):
        return "getPositionsForm"


class BI(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Bestinvest"

    def load_positions(self, secu, userCode, accountType, summary_file=None):
        positions = []
        if summary_file is None:
            summary_file = self.latest_file(userCode,accountType)
        self.set_vdate(summary_file)
        df = pd.read_csv(summary_file)
        # print(df)
        labels = ['Name', 'Unit', 'Price', 'Change', 'Value']

        for n in range(0, len(df)):
            name = df['Name'][n]
            qty = float(re.sub(',', '', str(df['Unit'][n])))
            price = float(re.sub('[,p]', '', str(df['Price'][n])))
            mv = df['Value'][n]
            value = float(re.sub('[,£�]', '', mv))
            # print("name=%s"%(name))
            security = secu.find_security(name)
            pos = Position(security, qty, price, value, self.vdate())
            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions

    def download_filename(self, username=None, accountType=None):
        return "%s/SIPP_-_NAME_Summary_NAME.csv" % (self.download_dirname())

    def download_formname(self):
        return "FileDownloadCashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        destfile   = self.dated_file(userCode, accountType)
        destlink   = self.latest_file(userCode,accountType)
        sourcefile = self.download_filename(userCode,accountType)

        logging.debug("src=%s dest=%s link=%s" % (sourcefile, destfile, destlink))

        # Copy source excluding some header and footer lines
        fpout = open(destfile, "w")
        with open(sourcefile, 'r', encoding='windows-1252') as fpin:
            outputline = False
            linecount = 0
            for line in fpin:
                if linecount == 0 and "Name,Unit,Price," in line:
                    line = "Name,Unit,Price,Change,Value,Cost,GainLoss,GainLoss%"
                    outputline = True
                if line.rstrip() == '':
                    outputline = False
                if outputline:
                    tmp = "%s\n"%(line.rstrip())
                    outline = re.sub(',,$','',tmp)
                    fpout.write(outline)
                    linecount += 1

        # Finally append the cash amount and close files
        line = 'Cash,%.2f,1,Change,%.2f,%.2f,GainLoss,GainLoss%%\n' % (cashAmount, cashAmount, cashAmount)
        fpout.write(line)

        fpout.close()
        fpin.close()

        # Update latest link to point to newly created file
        # Remove the source file from the download area
        self.update_latest_link(sourcefile, destfile, destlink)


class HL(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Hargreaves Lansdown"

    def load_positions(self, secu, userCode, accountType, summary_file=None):
        positions = []
        if summary_file is None:
            summary_file = self.latest_file(userCode,accountType)
        self.set_vdate(summary_file)
        df = pd.read_csv(summary_file)
        # print(df)
        # labels = ["Code", "Stock", "Units held", "Price (pence)", "Value (£)"]
        for n in range(0, len(df)):
            code = df['Code'][n]
            qty = float(re.sub(',', '', str(df['Units held'][n])))
            price = float(re.sub('[,p]', '', str(df['Price (pence)'][n])))
            mv = df['Value (£)'][n]
            value = float(re.sub('[,£]', '', mv))
            # print("name=%s"%(name))
            security = secu.find_security(code)
            pos = Position(security, qty, price, value,self.vdate())
            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions

    def download_filename(self, username=None, accountType=None):
        return "%s/account-summary.csv" % (self.download_dirname())

    def download_formname(self):
        return "FileDownloadCashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        destfile   = self.dated_file(userCode, accountType)
        destlink   = self.latest_file(userCode,accountType)
        sourcefile = self.download_filename(userCode,accountType)

        logging.debug("src=%s dest=%s link=%s" % (sourcefile, destfile, destlink))

        # Copy source excluding some header and footer lines
        fpout = open(destfile, "w")
        with open(sourcefile, 'r', encoding='windows-1252') as fpin:
            outputline = False
            for line in fpin:
                if "Code,Stock,Units" in line:
                    line='Code,Stock,Units held,Price (pence),Value (£),Cost (£),Gain/loss (£),Gain/loss (%),'
                    outputline = True
                if '","Totals",' in line:
                    outputline = False
                if outputline:
                    # tmp = line.encode('utf-8')
                    # tmp = line.encode('latin-1')
                    # outline = "%s\n"%(tmp.rstrip())
                    outline = "%s\n"%(line.rstrip())
                    fpout.write(outline)

        # Finally append the cash amount and close files
        line = '"Cash","Cash GBP","%.2f","1","%.2f","%.2f","","",""\n' %(cashAmount, cashAmount, cashAmount)
        fpout.write(line)

        fpout.close()
        fpin.close()

        # Update latest link to point to newly created file
        # Remove the source file from the download area
        self.update_latest_link(sourcefile, destfile, destlink)



class II(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Interactive Investor"

    def download_filename(self, userCode, accountType):
        dt = datetime.datetime.now().strftime("%Y%m%d")
        destname = "%s/%s_%s_%s_%s.csv" % (self.download_dirname(), userCode, self.name(), accountType, dt)

        # Get list of files in download directory, newest first
        paths = sorted(Path(self.download_dirname()).iterdir(), key=os.path.getmtime, reverse=True)
        for f in paths:
            print("downloaded file=", f)
            # if re.search('^.*\.csv$', f):
            #     print("csvfile=", f)
            print("destname=", destname)
            os.rename(f, destname)
            break

        return destname

    def download_formname(self):
        return "FileDownloadCashForm"

    def load_positions(self, secu, userCode, accountType, summary_file=None):
        positions = []
        if summary_file is None:
            summary_file = self.latest_file(userCode,accountType)
        self.set_vdate(summary_file)
        df = pd.read_csv(summary_file)
        # print(df.head(5))
        labels = ['Symbol', 'Qty', 'Price', 'Market Value']

        for n in range(0, len(df)):
            sym = df['Symbol'][n]
            # print("Symbol=%s" % (sym))
            qty = df['Qty'][n]
            # print("Qty=%s" % (qty))
            qty = float(re.sub(',', '', str(df['Qty'][n])))
            if '£' in str(df['Price'][n]):
                price = float(re.sub('[,£]', '', str(df['Price'][n]))) * 100.0
            else:
                price = float(re.sub('[,p]', '', str(df['Price'][n])))
            mv = df['Market Value'][n]
            value = float(re.sub('[,£]', '', mv))

            if sym in ('Cash GBP.L'):
                security = secu.find_security('Cash')
            else:
                security = secu.find_security(sym)

            pos = Position(security, qty, price, value, self.vdate())
            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions

    def update_positions(self, userCode, accountType, cashAmount):
        destfile = self.dated_file(userCode, accountType)
        destlink = self.latest_file(userCode,accountType)
        filename = self.download_filename(userCode,accountType)

        logging.debug("source=%s" % (filename))
        logging.debug("destfile=%s" % (destfile))
        logging.debug("destlink=%s" % (destlink))

        # Copy all lines across adding in cash on the final line
        fpout = open(destfile, "w")
        with open(filename, 'r', encoding='utf-8-sig') as fpin:
            for line in fpin:
                # Strip the leading feff characters from header line
                if "Symbol," in line:
                    line = 'Symbol,Name,Qty,Price,Change,Chg %,Market Value £,Market Value,Book Cost,Gain,Gain %,Average Price\n'
                    line = re.sub('^.*Symbol,', 'Symbol,', line)

                # Strip Totals lines at the end
                if not re.match('"",', line):
                    fpout.write(line)

            line = '"Cash","Cash GBP","%.2f","1","","","%.2f","%.2f","","","",""\n' % (cashAmount, cashAmount, cashAmount)
            fpout.write(line)

        fpout.close()
        fpin.close()

        # Update latest link to point to newly created file
        # Remove the source file from the download area
        self.update_latest_link(filename, destfile, destlink)


class CU(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Aviva CU"

    def download_formname(self):
        return "CashForm"
    
    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

class FD(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "First Direct"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

class GSM(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Marcus"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

class FSV(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "First Savings Bank"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

class CSB(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Charter Savings Bank"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)


class NPI(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Phoenix NPI"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

class NSI(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "National Savings & Investments"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

class NW(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Nationwide"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    secu  = SecurityUniverse()
    # uport = UserPortfolios(secu)

    # p = II()
    # print(p.name(True))
    # print(p.latest_file('A','ISA'))
    # p.update_positions('B','ISA',3098.06)
    # p.update_positions('A', 'Pens', 30377.10)
    # p.update_positions('B', 'Trd', 4141.29)
 
    # a = platformCode_to_class('NW')()
    # print(a.name())

    # p = HL()
    # p.update_positions('A','Trd',29.29)
    p = BI()
    p.update_positions('B','Pens',3568.77)


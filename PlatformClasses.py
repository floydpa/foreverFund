# Platform accounts making up a portfolio

import pandas as pd
import re
import sys, os
import glob

import logging
import datetime

from PositionClasses import Position

from wb import GspreadAuth, WbIncome, WbSecMaster


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
        print("SUMMARY FILE %s", summary_file)
        df = pd.read_csv(summary_file)
        print("DATAFRAME:\n%s", df)
        labels = ['Investment', 'Quantity', 'Price', 'Value (£)']
        for n in range(0, len(df)):
            inv = df['Investment'][n]
            sym = inv
            qty = float(re.sub(',', '', str(df['Quantity'][n])))
            price = float(df['Price'][n])
            value = float(re.sub(',', '', str(df['Value (£)'][n])))
            cost  = value

            security = secu.find_security(sym)
            pos = Position(security, qty, price, value, cost, self.vdate())

            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions

    def download_dirname(self):
        return "%s/Downloads" % (os.getenv('HOME'))

    def userdata_dirname(self):
        return "%s/UserData" % (os.getenv('HOME'))
    
    def download_filename(self, username, accountType):
        return None

    def most_recent_download(self, pattern):
        files = glob.glob(os.path.join(self.download_dirname(), pattern))
        if not files:
            return None
        else:
            return max(files, key=os.path.getmtime)

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
        original_directory = os.getcwd()
        target_directory   = os.path.dirname(destFile)
        target_filename    = os.path.basename(destFile)
        try:
            os.chdir(target_directory)
            os.unlink(destLink)
            os.symlink(target_filename, destLink)
            logging.debug("symlink(%s:%s,%s)" % (target_directory, target_filename, destLink))

            # Finally remove the source file which had been downloaded
            if removeSource:
                logging.debug("unlink(%s)" % (downloadFile))
                os.unlink(downloadFile)

        except OSError as e:
            logging.error(f"Error: {e}")

        finally:
            os.chdir(original_directory)

    def __repr__(self):
        return "PLATFORM(%s,%s)" % (self.name(), self.name(True))


class AJB(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "AJ Bell Youinvest"

    def download_filename(self, userCode, accountType):
        logging.debug("download_filename(%s,%s)"%(userCode,accountType))
        if accountType == 'Pens':
            accountType = 'SIPP'
        pattern = f"portfolio-*{accountType}.csv"
        return self.most_recent_download(pattern)

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

            qty   = float(re.sub(',', '', df['Quantity'][n]))
            price = float(df['Price'][n]) * 100.0
            value = float(re.sub(',', '', df['Value (£)'][n]))
            cost  = float(re.sub(',', '', df['Cost (£)'][n]))

            if sym in ('Cash GBP'):
                security = secu.find_security('Cash')
            else:
                security = secu.find_security(sym)

            pos = Position(security, qty, price, value, cost, self.vdate())
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


class II(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Interactive Investor"
        
    def download_formname(self):
        return "FileDownloadCashForm"

    def download_filename(self, userCode, accountType):
        """Return full path name of the file downloaded from II"""
        logging.debug("download_filename(%s,%s)"%(userCode,accountType))
        return self.most_recent_download("*.csv")
    
    def modify_download(self, userCode, accountType):
        """Normalise file downloaded from II"""
        # Get name of file downloaded from II
        download_file = self.download_filename(userCode,accountType)
        logging.debug("modify_download(%s,%s,%s)"%(download_file,userCode,accountType))

        # Contents of downloaded file need various changes, so copy to new file
        dt = datetime.datetime.now().strftime("%Y%m%d")
        dest_file = "%s/%s_%s_%s_%s.csv" % (self.download_dirname(), userCode, accountType, self.name(), dt)

        # Copy contents to a new file with some changes on the way
        with open(download_file, 'r') as src, open(dest_file, 'w') as dst:
            first_line_processed = False
            for line in src:
                # Strip strange characters before 'Symbol,Name,'
                if not first_line_processed:
                    if "Symbol,Name," in line:
                        line = line.split("Symbol,Name,", 1)[1]  # Keep only after "Symbol,Name,"
                        line = "Symbol,Name," + line  # Add the prefix back
                    first_line_processed = True

                # Skip lines starting with '""'
                if not line.startswith('""'):
                    dst.write(line)

        os.unlink(download_file)

        return dest_file

    def update_positions(self, userCode, accountType, cashAmount):
        """Construct dated UserData file from downloaded positions file"""
        destfile = self.dated_file(userCode, accountType)
        destlink = self.latest_file(userCode,accountType)
        filename = self.modify_download(userCode, accountType)

        logging.debug("source=%s" % (filename))
        logging.debug("destfile=%s" % (destfile))
        logging.debug("destlink=%s" % (destlink))

        # Copy all lines across adding in cash on the final line
        fpout = open(destfile, "w")
        with open(filename, 'r', encoding='utf-8-sig') as fpin:
            for line in fpin:
                fpout.write(line)

            line = '"Cash","Cash GBP","%.2f","1","","","£%.2f","£%.2f","£%.2f","","",""\n' % (cashAmount, cashAmount, cashAmount, cashAmount)
            fpout.write(line)

        fpout.close()
        fpin.close()

        # Update latest link to point to newly created file
        # Remove the source file from the download area
        self.update_latest_link(filename, destfile, destlink)

    def load_positions(self, secu, userCode, accountType, summary_file=None):
        positions = []
        if summary_file is None:
            summary_file = self.latest_file(userCode,accountType)
        self.set_vdate(summary_file)
        df = pd.read_csv(summary_file)
        logging.debug("load_positions dtypes=%s"%df.dtypes)
        # print(df.head(5))
        # labels = ['Symbol', 'Qty', 'Price', 'Market Value']

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
            s_value = df['Market Value'][n]
            s_cost = df['Book Cost'][n]

            value = float(re.sub('[,£]', '', s_value))
            cost  = float(re.sub('[,£]', '', s_cost))

            if sym in ('Cash GBP.L'):
                security = secu.find_security('Cash')
            else:
                # Skip worthless positions from fractions of units
                if value < 1.0:
                    continue
                security = secu.find_security(sym)

            pos = Position(security, qty, price, value, cost, self.vdate())
            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions


class AV(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Aviva"

    def download_formname(self):
        return "FileDownloadForm"
    
    def download_filename(self, userCode=None, accountType=None):
        return "Created from Google Worksheet 'Aviva Pens'"

    def update_positions(self, userCode, accountType):
        destfile = self.dated_file(userCode, accountType)
        destlink = self.latest_file(userCode,accountType)

        # --- Initialise connection to 2 Google Workbooks
        gsauth = GspreadAuth()
        ForeverIncome = WbIncome(gsauth)
        SecurityMaster = WbSecMaster(gsauth)

        # --- Create a download file of Aviva positions
        filename = ForeverIncome.create_aviva_download_file(SecurityMaster)

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
            # Skip zero quantity positions
            if qty == 0.0:
                continue
            price = float(re.sub('[,p]', '', str(df['Price'][n])))
            mv = df['Market Value'][n]
            value = float(re.sub('[,£]', '', mv))
            cost = value
            security = secu.find_security(sym)
            pos = Position(security, qty, price, value, cost, self.vdate())
            # print("New Position=%s" % (pos))
            positions.append(pos)

        return positions


class NPI(Platform):
    def __init__(self):
        Platform.__init__(self)
        self._fullname = "Phoenix NPI"

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)


class CashAccount(Platform):
    def __init__(self, organisation):
        Platform.__init__(self)
        self._fullname = organisation

    def download_formname(self):
        return "CashForm"

    def update_positions(self, userCode, accountType, cashAmount):
        return self.update_savings(userCode, accountType, cashAmount)

class GSM(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "Marcus")

class FSB(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "First Savings Bank")

class CSB(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "Charter Savings Bank")

class NW(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "Nationwide")

class FD(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "First Direct")

class NSI(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "National Savings & Investments")

class CU(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "Aviva CU")

class TUI(CashAccount):
    def __init__(self):
        CashAccount.__init__(self, "TUI DB Pension")
        

if __name__ == '__main__':
    
    from SecurityClasses import SecurityUniverse

    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    
    # Load details of all securities held in positions
    secinfo_dir = os.getenv('HOME') + '/SecurityInfo'
    secu = SecurityUniverse(secinfo_dir)

    # uport = UserPortfolios(secu)
 
    # a = platformCode_to_class('AJB')()
    # print(a.name())

    # p = AJB()
    # print(p.download_filename('P', 'ISA'))

    p = GSM()
    p = NW()
    p = FSB()
    p = CSB()
    print(p.latest_file('C','Sav'))
    for pos in p.load_positions(secu, 'C', 'Sav'):
        print (pos)

    p = CU()
    print(p.latest_file('C','Pens'))
    for pos in p.load_positions(secu, 'C', 'Pens'):
        print (pos)

    p = NSI()
    p = FD()
    print(p.latest_file('P','Sav'))
    for pos in p.load_positions(secu, 'P', 'Sav'):
        print (pos)




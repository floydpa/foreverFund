#-----------------------------------------------------------------------
# Main processing for the Google Sheets workbook
#-----------------------------------------------------------------------

import os, logging
import pandas as pd
import csv
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from wb_format import fmt_req_font, fmt_req_autofilter
from wb_format import fmt_req_autoresize, fmt_hdr_bgcolor
from wb_format import fmt_columns_decimal, fmt_columns_percentage
from wb_format import fmt_columns_currency, fmt_columns_hjustify
from wb_format import RGB_GREY


# Worksheets used as source information
WS_HL_DIVIDENDS     = "hl"             # Hargreaves Lansdown dividend information
WS_FE_DIVIDENDS     = "fe"             # FE Trustnet dividend information
WS_OTHER_DIVIDENDS  = "other"          # Other dividend information

WS_AVIVA_PENS       = "Aviva Pens"     # Data pasted from web page

# Worksheets created/updates
WS_SECURITY_INFO    = "Security Information"
WS_SECURITY_URLS    = "Detailed Information"
WS_POSITION_STATIC  = "By Pos Static"
WS_POSITION_INCOME  = "By Position"
WS_SEC_DIVIDENDS_HL = "By SecurityHL"  # Temporary
WS_SEC_DIVIDENDS_FE = "By SecurityFE"  # Temporary
WS_SEC_DIVIDENDS    = "By Security"
WS_EST_INCOME       = "Estimated Income"


#-----------------------------------------------------------------------
# Base class for a worksheet within a workbook
#-----------------------------------------------------------------------

class Ws:
    def __init__(self, wbInstance, wsname):
        self._wbinstance = wbInstance
        self._workbook   = wbInstance.workbook()
        self._wsname     = wsname
        self._df         = None
    
    def wbinstance(self):
        return self._wbinstance
    
    def spreadsheet_id(self):
        return self.wbinstance().spreadsheet_id()
      
    def workbook(self):
        return self._workbook
    
    def wsname(self):
        return self._wsname
    
    def df(self):
        return self._df
    

#-----------------------------------------------------------------------
# Worksheet Object for 'Security Info'
#-----------------------------------------------------------------------

class WsSecInfo(Ws):
    def __init__(self, wbInstance, secu):
        Ws.__init__(self, wbInstance, WS_SECURITY_INFO)
        # Process contents of all json security files
        self._secu = secu
    
    # Construct base set of security information
    #   sname       MYI
    #   lname       MURRAY INTERNATIONAL TRUST PLC
    #   stype       ORDINARY 5p SHARES
    #   alias       MYI.L
    #   structure	IT
    #   sector      Global Equity Income
    #   ISIN        GB00BQZCCB79
    #   SEDOL
    #   fund-class  [For OEIC] Either Income or Accumulation			

    def create_security_info(self,secu):
        # Column headings for Security Info sheet
        sec_info_cols = [
            'sname', 'lname', 'stype',
            'alias',
            'structure', 'sector', 
            'ISIN', 'SEDOL',
            'fund-class',
            'div-freq'
        ]
    
        # Ignore these columns from json security files
        entries_to_remove = [
            'info', 'divis','mdate',
            'fund-yield',
            'annual-income',
            'asset-allocation'
        ]

        # Read json files and create one row for each
        lst = []
        for sec in secu.securities():
            defn = secu.find_security(sec).data()
            try:
                freq = defn['divis']['freq']
            except:
                freq = None
            for k in entries_to_remove:
                defn.pop(k, None)
            defn['div-freq'] = freq
            lst.append(defn)

        # Convert to dataframe with NaN replaced with None and all columns 'str'
        df = pd.DataFrame(lst)[sec_info_cols].astype(str).sort_values('sname')
        df = df.replace({'None':None, 'nan':None})

        return df


    # Apply formatting to newly created/updated sheet
    def apply_formatting(self):
        # Retrieve worksheet details for formatting requests
        worksheet = self.workbook().worksheet(self.wsname())

        # Make the headings bold
        worksheet.format("A1:I1", {"textFormat": {"bold": True}})

        requests = []
        # Step 1: Change font to Arial size 8
        requests.append(fmt_req_font(worksheet))
        # Step 2: Turn on filters for the first row
        requests.append(fmt_req_autofilter(worksheet))
        # Step 3: Grey fill colour for the header row
        requests.append(fmt_hdr_bgcolor(worksheet, RGB_GREY))
        # Step 4: Auto resize all columns to fit their content
        requests.append(fmt_req_autoresize(worksheet))
                        
        # Execute the requests
        response = self.wbinstance().service().spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id(), 
                body={'requests': requests}
            ).execute()
        
        logging.debug(f"service request response {response}")


    def refresh(self):
        # Create dataframe from individual security definitions
        self._df = self.create_security_info(self._secu)
        # Create/update worksheet with dataframe
        self.wbinstance().df_to_worksheet(self.df(), self.wsname())
        # Apply formatting to this worksheet
        self.apply_formatting()

    def __repr__(self):
        return self.df()


#-----------------------------------------------------------------------
# Worksheet Object for 'Security Urls'
#-----------------------------------------------------------------------

class WsSecUrls(Ws):
    def __init__(self, wbInstance, secu):
        Ws.__init__(self, wbInstance, WS_SECURITY_URLS)
        # Process contents of all json security files
        self._secu = secu
    
    # List of URLs with additional information
    # SecurityId    Short name, e.g. FCIT
    # Platform      hl, fe or aic	
    # Url           E.g. Link to Hargreaves Lansdown detailed information

    def create_security_urls(self,secu):
        urls = []
        # Each security may have none, one or more URLs associated
        for sec in secu.securities():
            defn = secu.find_security(sec).data()
            try:
                info = defn['info']
            except:
                info = None

            if info is not None:
                for platform in info.keys():
                    urls.append({
                        'SecurityId':   defn['sname'],
                        'Platform':     platform,
                        'Url':          info[platform]
                    })

        # Convert to dataframe with all columns 'str'
        df = pd.DataFrame(urls)[['SecurityId','Platform','Url']].astype(str)
        df = df.sort_values(['SecurityId','Platform'])

        return df
    
    # Apply formatting to newly created/updated sheet
    def apply_formatting(self):
        # Retrieve worksheet details for formatting requests
        worksheet = self.workbook().worksheet(self.wsname())

        # Make the headings bold
        worksheet.format("A1:C1", {"textFormat": {"bold": True}})

        requests = []
        # Step 1: Change font to Arial 10
        requests.append(fmt_req_font(worksheet, 'Arial', 10))
        # Step 2: Grey fill colour for the header row
        requests.append(fmt_hdr_bgcolor(worksheet, RGB_GREY))
        # Step 3: Auto resize all columns to fit their content
        requests.append(fmt_req_autoresize(worksheet))
                        
        # Execute the requests
        response = self.wbinstance().service().spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id(), 
                body={'requests': requests}
            ).execute()
        
        logging.debug(f"service request response {response}")


    def refresh(self):
        # Create dataframe from individual security definitions
        self._df = self.create_security_urls(self._secu)
        # Create/update worksheet with dataframe
        self.wbinstance().df_to_worksheet(self.df(), self.wsname())
        # Apply formatting to this worksheet
        self.apply_formatting()

    def __repr__(self):
        return self.df()


#-----------------------------------------------------------------------
# Handling for worksheet 'By Position'
#-----------------------------------------------------------------------

class WsByPosition(Ws):
    def __init__(self, wbInstance):
        Ws.__init__(self, wbInstance, WS_POSITION_INCOME)
        self._positions_list = []
    
    def positions_list(self):
        return self._positions_list

    # Construct the base set of position information
    # This consists of 9 columns with sample imformation as follows:
    #   Who           Paul
    #   AccType       ISA
    #   Platform      II
    #   AccountId     P_ISA_II
    #   SecurityId    TMPL
    #   Name          Temple Bar Investment Trust plc
    #   Quantity      11,972
    #   Book Cost     £20,000
    #   Value (£)     £31,905

    def create_position_info(self, positions):
        self._positions_list = []
    
        for pos in positions:
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
            
            logging.debug("position_info(p=%s)", p)
            self._positions_list.append(p)
    
        # Get list of static positions (as dicts) to tag on
        df = self.wbinstance().worksheet_to_df(WS_POSITION_STATIC)
        df['Quantity'] = df['Quantity'].astype('float')
        df['Value'] = df['Value'].astype('float')
        other = df.to_dict(orient='records')
        for p in other:
            self._positions_list.append(p)

        logging.debug("psitions_list=%s"%(self._positions_list))

        # Create dataframe of full list of positions in sorted order
        self._df = pd.DataFrame(self._positions_list).sort_values(
            ['Who','AccType','Platform','Value'],ascending=[True,True,True,False]
        ).reset_index(drop=True)

        logging.debug("position_info(df.dtypes=%s)", self._df.dtypes)
        logging.debug("%s"%(self._df))

        return self._df

    # Apply formatting to newly created/updated sheet
    def apply_formatting(self):
        # Retrieve worksheet details for formatting requests
        worksheet = self.workbook().worksheet(self.wsname())

        requests = []
        # Step 1: Change font to Arial size 8
        requests.append(fmt_req_font(worksheet))
        # Step 2: Turn on filters for the first row
        requests.append(fmt_req_autofilter(worksheet))
        # Step 3: Grey fill colour for the header row
        requests.append(fmt_hdr_bgcolor(worksheet, RGB_GREY))
        # Step 4: Format Quantity and Dividend as decimsl with up to 4dp, G=6, K=10     
        requests.append(fmt_columns_decimal(worksheet, 6, 7))
        requests.append(fmt_columns_decimal(worksheet, 10, 11))
        # Step 5: Format Yield as perentage with 2dp, M=12
        requests.append(fmt_columns_percentage(worksheet, 12, 13))
        # Step 6: Format BookCost, Value and Income as currency H=7,I=8,N=13
        requests.append(fmt_columns_currency(worksheet, 7, 9))
        requests.append(fmt_columns_currency(worksheet, 13, 14))
        # Step 7: Auto resize all columns to fit their content
        requests.append(fmt_req_autoresize(worksheet))
        # Step 8: Right justify J (9) and centre justify L (11)
        requests.append(fmt_columns_hjustify(worksheet, 9, 10, 'RIGHT'))
        requests.append(fmt_columns_hjustify(worksheet, 11, 12, 'CENTER'))
                        
        # Execute the requests
        response = self.wbinstance().service().spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id(), 
                body={'requests': requests}
            ).execute()
        
        logging.debug(f"service request response {response}")
        

    # Create or update the worksheet using a list of Position instances
    def refresh(self, positions):

        # Create a dataframe from the positions
        df = self.create_position_info(positions)

        # Use new df to add/update position income sheet
        # Allow 4 additional columns for formulas to be added later
        self.wbinstance().df_to_worksheet(df, self.wsname(), 0, 4)

        # Add 4 columns of formulas with dividend & income information
        # Note that it's too slow to update one cell at a time
        #    sheet.update_cell(r, 11, f"=VLOOKUP($E{r},'By Security'!$A:$E,4,FALSE)")
        # Instead, construct a range of 4 columns and then add with a single update
        formulas = []
        formulas.append(['Dividend','Unit','Yield','Income'])
        for r in range(2,len(df)+2):
            divi = f"=VLOOKUP($E{r},'By Security'!$A:$E,4,FALSE)"
            unit = f"=VLOOKUP($E{r},'By Security'!$A:$E,5,FALSE)"
            yld  = f"=IF(I{r}=0,0,N{r}/I{r})"
            inc  = f'=IF(L{r}="p",G{r},I{r})*K{r}/100'
            row  = [divi,unit,yld,inc]
            formulas.append(row)

        # Update the range with formulas
        r = len(df)+1
        cell_range = f"K1:N{r}"
        # print(f"range={cell_range}")
        # print(formulas)
        sheet = self.workbook().worksheet(self.wsname())
        sheet.update(cell_range, formulas, value_input_option='USER_ENTERED')

        # Make the headings bold for the 4 formula cooumns
        sheet.format("K1:N1", {"textFormat": {"bold": True}})

        # Apply other formatting to this sheet
        self.apply_formatting()


class GspreadAuth:
    def __init__(self):
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds  = Credentials.from_service_account_file("credentials.json", scopes=scopes)

        self._client  = gspread.authorize(creds)
        self._service = build('sheets', 'v4', credentials=creds)

    def client(self):
        return self._client
    
    def service(self):
        return self._service


class GsWorkbook:
    def __init__(self, gsauth, spreadsheet_id):
        self._gsauth = gsauth
        self._spreadsheet_id = spreadsheet_id
        self._workbook = self.client().open_by_key(spreadsheet_id)

    def client(self):
        return self._gsauth.client()
    
    def service(self):
        return self._gsauth.service()
    
    def workbook(self):
        return self._workbook
    
    def spreadsheet_id(self):
        return self._spreadsheet_id
    
    def worksheet(self, worksheet_name):
        if worksheet_name in self.worksheet_list():
            sheet = self.workbook().worksheet(worksheet_name)
        else:
            sheet = None
        return sheet

    def worksheet_list(self):
        ws_list = []
        for ws_name in map(lambda x: x.title, self._workbook.worksheets()):
            ws_list.append(ws_name)
        return ws_list
    
    def worksheet_to_df(self, worksheet_name):
        # Get the worksheet by name
        worksheet = self.workbook().worksheet(worksheet_name)
        
        # Get all data from the worksheet and convert to DataFrame
        # df = pd.DataFrame(worksheet.get_all_records())

        # Problem with above approach is stripping of leading zeros on strings
        # Fetch raw values from the worksheet (including header)
        values = worksheet.get_values()
        # Create a DataFrame from the raw values using first row as header
        df = pd.DataFrame(values[1:], columns=values[0])

        return df
    
    def df_to_worksheet(self, df, worksheet_name, add_rows=0, add_cols=0):
        # Convert DataFrame to list of lists
        values = df.values.tolist()

        # Insert list containing column headings
        hdr = list(df.columns.values)
        values.insert(0, hdr)

        if worksheet_name in self.worksheet_list():
            sheet = self.workbook().worksheet(worksheet_name)
        else:
            sheet = self.workbook().add_worksheet(worksheet_name, rows=len(values)+add_rows, cols=len(hdr)+add_cols)

        sheet.clear()

        range = f"A1:{chr(ord('A')+len(hdr)-1)}{len(values)}"
        sheet.update(range, values)

        hrange = f"A1:{chr(ord('A')+len(hdr)-1)}1"
        sheet.format(hrange, {"textFormat": {"bold": True}})

    def __repr__(self):
        s = "WORKBOOK:"
        for ws in self.worksheet_list():
            s += "\n  Sheet(%s)"%(ws)
        return s
    
class WbSecMaster(GsWorkbook):
    def __init__(self, gsauth):    
        spreadsheet_id = "1as92X_ywzObw0kYIoFVeMQ070EJ006DQepRYCwPgzSE"
        GsWorkbook.__init__(self, gsauth, spreadsheet_id)

class WbIncome(GsWorkbook):
    def __init__(self, gsauth):
        spreadsheet_id = "1-W8w2t3HXCG9zNy6RQ4w12zkCrX_jntvQ24xEinhxG4"
        GsWorkbook.__init__(self, gsauth, spreadsheet_id)

    def create_aviva_download_file(self, SecurityMaster):
        # Get position data from worksheet
        df = self.worksheet_to_df(WS_AVIVA_PENS)
        df.drop(['LastStmtUnits','AnnualMgmtCharge','NetUnits'], axis=1, inplace=True)
        df['FundName'] = df['FundName'].str.split('\n').str[0]
        df['FundName'] = df['FundName'].str.upper()
        df = df[df['Qty'] != 0.0]

        # Fetch raw values from the worksheet (including header)
        secinfo = SecurityMaster.worksheet_to_df(WS_SECURITY_INFO)
        # Ensure 'SEDOL' column is treated as a string, so as not to lose leading '0'
        secinfo['SEDOL'] = secinfo['SEDOL'].astype(str)

        secinfo = secinfo[['lname','SEDOL']].rename(columns={'lname': 'FundName'})
        secinfo = secinfo[secinfo['FundName'].str.startswith('AVIVA PENSION')]
        print(secinfo)
        df = df.merge(secinfo,on='FundName',how='left')
        df = df.rename(columns={'FundName': 'Description', 'SEDOL':'Symbol'})
        df = df[['Symbol','Qty','Description','Price','Market Value']]
        print(df)
        f_out = "%s/Downloads/AvivaPortfolio.csv" % (os.getenv('HOME'))
        df.to_csv(f_out, index=False, quotechar='"', quoting=csv.QUOTE_ALL)

        return f_out


if __name__ == '__main__':

    gsauth = GspreadAuth()
    ForeverIncome = WbIncome(gsauth)
    print(ForeverIncome)
    SecurityMaster = WbSecMaster(gsauth)

    #---------------------------------------------------------------------------------------------
    # Consume Aviva pension information from Income workbook and create download file.
    # Create in same format as stored UserData file, e.g.
    # "Symbol","Qty","Description","Price","Market Value"
    # "0153238","14,287.41","Aviva Pension Baillie Gifford Managed FP","518.47p","£74,076.31"
    # "B5LMZB5","35,566.24","Aviva Pension Artemis Strategic Bond FP","212.33p","£75,517.92"
    # "B66RGK8","10,075.50","Aviva Pension L&G Global Real Estate Equity Index FP","252.98p","£25,489.22"
    # "154413","15,440.58","Aviva Pension BNY Mellon Multi-Asset Balanced FP","482.41p","£74,487.13"
    #---------------------------------------------------------------------------------------------

    if False:
        ForeverIncome.create_aviva_download_file(SecurityMaster)

    if False:
        # Get contents of worksheet as a DataFrame
        df = SecurityMaster.worksheet_to_df("Security Information")
        print(df)

        # Get contents of 'hl' worksheet as a DataFrame
        df = SecurityMaster.worksheet_to_df("hl")
        print(df)

    def read_sample(workbook):
        worksheet_list = map(lambda x: x.title, workbook.worksheets())
        for ws_name in worksheet_list:
            print(ws_name)

        values_list = workbook.sheet1.row_values(1)
        print(values_list)


    def read_sheets(workbook):
        # Create a list to hold the values
        values = []
    
        # Get all worksheets
        for ws in workbook.worksheets():
            # Append the values of the worksheet to values
            values.extend(ws.get_all_values())
    
        # create df from values
        df = pd.DataFrame(values)
    
        return df

    #------------------------------------------------------------------------------

    # --- Test interface
    # read_sample(workbook)

    # --- Append all worksheets into a single dataframe
    # df = read_sheets(workbook)
    # print(df)


        
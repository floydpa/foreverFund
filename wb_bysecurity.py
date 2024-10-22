#------------------------------------------------------------------------------
# Create/Update the 'By Security' income sheet
#------------------------------------------------------------------------------

import logging
import pandas as pd
from datetime import datetime, timedelta

#------------------------------------------------------------------------------
# Worksheets names

# Base worksheet class
from wb import Ws
# Source dividend information
from wb import WS_HL_DIVIDENDS, WS_FE_DIVIDENDS, WS_OTHER_DIVIDENDS
# Sheets created/updated
from wb import WS_SEC_DIVIDENDS_HL, WS_SEC_DIVIDENDS_FE
from wb import WS_SEC_DIVIDENDS, WS_EST_INCOME

from wb_format import fmt_req_font, fmt_req_autofilter
from wb_format import fmt_req_autoresize, fmt_hdr_bgcolor
from wb_format import fmt_columns_bgcolor, fmt_columns_decimal, fmt_columns_currency
from wb_format import RGB_GREY, RGB_BLUE, RGB_YELLOW


# Apply formatting to newly created/updated sheet
def apply_formatting(forever_income, worksheet_name):
    # Retrieve worksheet details for formatting requests
    workbook  = forever_income.workbook()
    worksheet = workbook.worksheet(worksheet_name)

    requests = []
    # Step 1: Change font to Arial size 8
    requests.append(fmt_req_font(worksheet))
    # Step 2: Turn on filters for the first row
    requests.append(fmt_req_autofilter(worksheet))
    # Step 3: Auto resize all columns to fit their content
    requests.append(fmt_req_autoresize(worksheet))
    # Step 4: Grey fill colour for the header row
    requests.append(fmt_hdr_bgcolor(worksheet, RGB_GREY))
    # Step 5: Blue fill colour for columns 'Annual Dividend' and 'Unit'
    requests.append(fmt_columns_bgcolor(worksheet,RGB_BLUE,2,3))
    # Step 6: Yellow fill colour for column 'OldestExDiv'
    requests.append(fmt_columns_bgcolor(worksheet,RGB_YELLOW,4,4))

    # Execute the requests
    response = forever_income.service().spreadsheets().batchUpdate(
            spreadsheetId=forever_income.spreadsheet_id(),
            body={'requests': requests}
        ).execute()
        
    logging.debug(f"service request response {response}")

    return response


#-----------------------------------------------------------------------
# Handling for dividend information taken from Hargreaves Lansdown
#-----------------------------------------------------------------------

class WsDividendsHL(Ws):
    def __init__(self, wbDestination, wbSource):
        # Initialise based on workbook where sheet will be created
        Ws.__init__(self, wbDestination, WS_SEC_DIVIDENDS_HL)
        # Read 'hl' sheet from the source workbook
        self._raw_df = wbSource.worksheet_to_df(WS_HL_DIVIDENDS)
        # Convert dividend information to generic format
        self._norm_df = self.normalise_divis()
        # Aggregate normalised data to get annual dividend information
        self._agg_df = self.aggregate_divis()
    
    def rawdata(self):
        return self._raw_df
    
    def normalised(self):
        return self._norm_df

    def aggregated(self):
        return self._agg_df
    
    def normalise_divis(self):
        df = self.rawdata()

        # Use str.extract() to split the 'value' column
        df[['Amount', 'Unit']] = df['Payment'].str.extract(r'([0-9\.]+)([a-zA-Z]+)')

        # Convert 'Amount' column to float
        df['Amount'] = df['Amount'].astype(float)

        # Convert date columns from DD/MM/YYYY to YYYYMMDD as strings
        df['ExDivDate'] = df['ExDivDate'].str.replace(r'(\d{2})/(\d{2})/(\d{4})', r'\3\2\1', regex=True)
        df['PaymentDate'] = df['PaymentDate'].str.replace(r'(\d{2})/(\d{2})/(\d{4})', r'\3\2\1', regex=True)

        # Drop 'Payment' column as it's no longer needed
        df = df.drop(columns=['Payment'])

        self._norm_df = df

        return df

    def aggregate_divis(self):   
        # Group by 'securityId' and aggregate
        aggregated_df = self.normalised().groupby(['SecurityId','Name']).agg(
            Count=('Amount', 'size'),           # Count of rows per securityId
            AnnualDividend=('Amount', 'sum'),   # Sum of value per securityId
            Unit=('Unit', 'min'),               # Retain column Unit
            OldestExDiv=('ExDivDate', 'min')    # Oldest ex-div date per securityId
        ).reset_index()

        # Add a new column 'Freq' based on the 'Count' column
        count_to_freq = {1: 'A', 2: 'S', 4: 'Q', 12: 'M'}
        aggregated_df['Freq'] = aggregated_df['Count'].map(count_to_freq)

        # Reorder columns
        aggregated_df = aggregated_df[
            ['SecurityId','Name','Freq','AnnualDividend','Unit','OldestExDiv']
        ]

        self._agg_df = aggregated_df

        return aggregated_df
        
    def refresh(self):
        # Create or update the worksheet for HL dividends
        self.wbinstance().df_to_worksheet(self.aggregated(), self.wsname())
        apply_formatting(self.wbinstance(), self.wsname())
        
    def __repr__(self):
        return self.rawdata()
    

#-----------------------------------------------------------------------
# Handling for dividend information taken from FE Trustnet
#-----------------------------------------------------------------------

class WsDividendsFE(Ws):
    def __init__(self, wbDestination, wbSource):
        # Initialise based on workbook where sheet will be created
        Ws.__init__(self, wbDestination, WS_SEC_DIVIDENDS_FE)
        # Read 'hl' sheet from the source workbook
        self._raw_df = wbSource.worksheet_to_df(WS_FE_DIVIDENDS)
        # Convert dividend information to generic format
        self._norm_df = self.normalise_divis()
        # Aggregate normalised data to get annual dividend information
        self._agg_df = self.aggregate_divis()
    
    def rawdata(self):
        return self._raw_df
    
    def normalised(self):
        return self._norm_df

    def aggregated(self):
        return self._agg_df

    def normalise_divis(self):
        df = self.rawdata()
        # Convert 'Amount' column to float
        df['Scale']  = df['Scale'].astype(float)
        df['Amount'] = df['DividendAmount'].astype(float)
        # Some dividends (e.g. RL) are expressed in pence, so scale up
        df['Amount'] = df['Amount'] * df['Scale']
        # Convert to dividend in pence (from pounds)
        df['Amount'] = df['Amount'] * 100
        # Set Unit as pence
        df['Unit'] = 'p'
        # Create 'Type' column
        df['Type'] = df['DividendType']
        # Convert date columns from DD.MM.YYYY to YYYYMMDD as strings
        df['ExDivDate'] = df['ExDivDate'].str.replace(r'(\d{2})\.(\d{2})\.(\d{4})', r'\3\2\1', regex=True)
        df['PaymentDate'] = df['PaymentDate'].str.replace(r'(\d{2})\.(\d{2})\.(\d{4})', r'\3\2\1', regex=True)

        # Drop columns no longer needed
        df = df.drop(columns=['DividendType','DividendAmount','Scale','TaxIndicator'])
    
        self._norm_df = df

        return df

    def aggregate_divis(self):   
        # Group by 'securityId' and aggregate
        aggregated_df = self.normalised().groupby(['SecurityId','Name']).agg(
            Count=('Amount', 'size'),           # Count of rows per securityId
            AnnualDividend=('Amount', 'sum'),   # Sum of value per securityId
            Unit=('Unit', 'min'),               # Retain column Unit
            OldestExDiv=('ExDivDate', 'min')    # Oldest ex-div date per securityId
        ).reset_index()

        # Add a new column 'Freq' based on the 'Count' column
        count_to_freq = {1: 'A', 2: 'S', 4: 'Q', 12: 'M'}
        aggregated_df['Freq'] = aggregated_df['Count'].map(count_to_freq)

        # Reorder columns
        aggregated_df = aggregated_df[
            ['SecurityId','Name','Freq','AnnualDividend','Unit','OldestExDiv']
        ]

        self._agg_df = aggregated_df

        return aggregated_df
        
    def refresh(self):
        # Create or update the worksheet for FE dividends
        self.wbinstance().df_to_worksheet(self.aggregated(), self.wsname())
        apply_formatting(self.wbinstance(), self.wsname())

    def __repr__(self):
        return self.rawdata()
    

#-----------------------------------------------------------------------
# Create worksheet containing security aggregated dividend information
#-----------------------------------------------------------------------

class WsDividendsBySecurity(Ws):
    def __init__(self, wbDestination, wbSource):
        # Initialise based on workbook where sheet will be created
        Ws.__init__(self, wbDestination, WS_SEC_DIVIDENDS)

        # Get dividends from 'hl' sheet
        hl = WsDividendsHL(wbDestination, wbSource)

        # Get dividends from 'fe' sheet
        fe = WsDividendsFE(wbDestination, wbSource)

        # Get other dividends (already aggregated)
        other = wbSource.worksheet_to_df(WS_OTHER_DIVIDENDS)
        other['AnnualDividend'] = other['AnnualDividend'].astype(float)

        # Aggregate normalised data to use for hist
        self._dfn = pd.concat([hl.normalised(), fe.normalised()], 
                  ignore_index=True).sort_values(by='SecurityId')
        
        # Aggregate aggregated data to get annual dividend information
        self._df = pd.concat([hl.aggregated(), fe.aggregated(), other], 
                  ignore_index=True).sort_values(by='SecurityId')

    def normalised(self):
        return self._dfn
    
    def aggregated(self):
        return self._df

    def refresh(self):
        # Create or update the worksheet for FE dividends
        self.wbinstance().df_to_worksheet(self.aggregated(), self.wsname())
        apply_formatting(self.wbinstance(), self.wsname())
    
    def json_prev_divis(self, SecurityId):
        df = self.normalised()
        divis = df[(df['SecurityId'] == SecurityId)].to_dict('records')
        prev = []
        if len(divis) > 0:
            for d in divis:
                prev.append({
                    'tag':      d['Type'],
                    'ex-div':   d['ExDivDate'],
                    'payment':  d['PaymentDate'],
                    'amount':   d['Amount'],
                    'unit':     d['Unit']
                })

            # Sort the list in descending order based on 'payment'
            prev = sorted(prev, key=lambda x: x['payment'], reverse=True)

        return prev

    def __repr__(self):
        return self.aggregated()
    

#-----------------------------------------------------------------------
# Create worksheet containing projected dividends by account
#-----------------------------------------------------------------------

class WsEstimatedIncome(Ws):
    def __init__(self, wbDestination, weeks=13):
        # Initialise based on workbook where sheet will be created
        Ws.__init__(self, wbDestination, WS_EST_INCOME)

        # How far to project into the future
        self._end_date = datetime.today() + timedelta(weeks)

    def df(self):
        return self._df
    
    def end_date(self):
        return self._end_date
    
    # Construct details of income payments by account by security
    # This consists of 15 columns with sample imformation as follows:
    #
    #   AccountId   P_AJB_ISA
    #   Year        2024
    #   Month       9
    #   Day         30
    #   Tax Year    2024/25
    #   Who         Paul
    #   Type        ISA
    #   SecurityId  HICL
    #   Quantity    16,267
    #   Value       21,005
    #   Dividend    2.06
    #   Freq        Q
    #   Status      Est
    #   Amount      335.09

    def projected_income(self, positions, secu):
        self._projected = []
    
        for pos in positions:
            acc = pos.account()
            acc_id = "%s_%s_%s" % (acc.usercode(), pos.platform(), pos.account_type())

            acctype = pos.account_type()
            if acctype == 'Sav':
                acctype = 'Savings'

            for dp in pos.projected_dividends():
                dt_obj = datetime.strptime(dp['payment'], "%Y%m%d")
                tax_yend = datetime(dt_obj.year,4,5)
                if dt_obj <= tax_yend:
                    tax_year = dt_obj.year - 1
                else:
                    tax_year = dt_obj.year
                s_tax_year = f"{tax_year}/{tax_year-2000+1}"

                sec = secu.find_security(pos.sname())
                try:
                    freq = sec.data()['divis']['freq']
                except:
                    freq = ""

                divi_amount = ''
                divi_unit   = ''
                for divi in sec.projected_dividends():
                    if dp['payment'] == divi['payment']:
                        divi_amount = divi['amount']
                        divi_unit   = divi['unit']

                p = {
                    'AccountId':    acc_id,
                    'Year':         dt_obj.year,
                    'Month':        dt_obj.month,
                    'Day':          dt_obj.day,
                    'Tax Year':     s_tax_year,
                    'Who':          acc.username(),
                    'Type':         acctype,                    
                    'SecurityId':   pos.sname(),
                    'Freq':         freq,
                    'Quantity':     pos.quantity(),
                    'Value':        pos.value(),
                    'Yield':        divi_amount,
                    'Unit':         divi_unit,
                    'Amount':       dp['amount'],
                    'Status':       dp['type']
                }
            
                self._projected.append(p)

        # Create dataframe of full list of positions in sorted order
        self._df = pd.DataFrame(self._projected).sort_values(
            ['Year','Month','Day','AccountId'],ascending=[True,True,True,True]
        ).reset_index(drop=True)

        return self._df

    # Apply formatting to newly created/updated sheet
    def apply_formatting(self):
        worksheet = self.workbook().worksheet(self.wsname())

        requests = []
        # Step 1: Change font to Arial size 8
        requests.append(fmt_req_font(worksheet))
        # Step 2: Turn on filters for the first row
        requests.append(fmt_req_autofilter(worksheet))
        # Step 3: Grey fill colour for the header row
        requests.append(fmt_hdr_bgcolor(worksheet, RGB_GREY))
        # Step 4: Format Quantity as decimal with up to 4dp, J=9 
        requests.append(fmt_columns_decimal(worksheet, 9, 10))
        requests.append(fmt_columns_decimal(worksheet, 11, 12))
        # Step 5: Format Value & Amount as currency K=10 & N=13
        requests.append(fmt_columns_currency(worksheet, 10, 11))
        requests.append(fmt_columns_currency(worksheet, 13, 14))
        # Step 6: Auto resize all columns to fit their content
        requests.append(fmt_req_autoresize(worksheet))

        # Execute the requests
        response = self.wbinstance().service().spreadsheets().batchUpdate(
                spreadsheetId=self.wbinstance().spreadsheet_id(),
                body={'requests': requests}
            ).execute()
        
        logging.debug(f"service request response {response}")

        return response

    def refresh(self):
        # Create or update the worksheet
        self.wbinstance().df_to_worksheet(self.df(), self.wsname())
        self.apply_formatting()

    def __repr__(self):
        return self.df()
    

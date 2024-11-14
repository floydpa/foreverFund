#------------------------------------------------------------------------------
# Formatting for worksheets within workbooks
#------------------------------------------------------------------------------

#------------------------------------------------------------------------------
# RGB values for cell fill colours

RGB_BLUE   = {"red": 0.81, "green": 0.89, "blue": 0.95}
RGB_YELLOW = {"red": 0.95, "green": 0.95, "blue": 0.80}
RGB_GREY   = {"red": 0.80, "green": 0.80, "blue": 0.80}

#------------------------------------------------------------------------------
# Formatting requests

def fmt_req_font(worksheet, family='Arial', size=8):
    return {
        'repeatCell': {
            'range': {
                'sheetId': worksheet.id,
            },
            'cell': {
                'userEnteredFormat': {
                    'textFormat': {
                        'fontFamily': family,
                        'fontSize': size
                        }
                    }
                },
            'fields': 'userEnteredFormat.textFormat'
        }
    } 
    
def fmt_req_autofilter(worksheet):
    return {
        'setBasicFilter': {
            'filter': {
                'range': {
                'sheetId': worksheet.id,
                    'startRowIndex': 0,  # First row
                    'endRowIndex': 1,    # Filter only on the first row
                }
            }
        }
    }       

def fmt_req_autoresize(worksheet):
    return {
        'autoResizeDimensions': {
            'dimensions': {
                'sheetId': worksheet.id,
                'dimension': 'COLUMNS',
                'startIndex': 0,  # First column (A)
                'endIndex': worksheet.col_count  # Resize up to the last column
            }
        }
    }               
    
def fmt_hdr_bgcolor(worksheet, color):
    return {
        'repeatCell': {
            'range': {
                'sheetId': worksheet.id,
                'startRowIndex': 0,  # First row
                'endRowIndex': 1,    # Only apply to the first row
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': color
                }
            },
            'fields': 'userEnteredFormat.backgroundColor'
        }
    }

def fmt_columns_bgcolor(worksheet, color, cfirst, clast, rfirst=1, rlast=-1):
    if rlast < 0:
        # Get the last row number
        all_values = worksheet.get_all_values()
        rlast = len(all_values)  # This gives the last row with data

    return {
        'repeatCell': {
            'range': {
                'sheetId': worksheet.id,
                'startRowIndex':    rfirst,  # 0-indexed
                'endRowIndex':      rlast,   # 0-indexed
                'startColumnIndex': cfirst,  # 0-indexed, e.g. D = 3
                'endColumnIndex':   clast+1, # 0-indexed, but end is exclusive
            },
            'cell': {
                'userEnteredFormat': {
                    'backgroundColor': color
                }
            },
            'fields': 'userEnteredFormat.backgroundColor'
        }
    }

# Format column(s) as decimal
def fmt_columns_decimal(worksheet, cfirst, clast, rfirst=1):
    return {
        'repeatCell': {
            'range': {
                'sheetId': worksheet.id,
                'startColumnIndex': cfirst,  # 0-indexed, e.g. K=10
                'endColumnIndex': clast,     # End is exclusive
                'startRowIndex': rfirst      # 0-index, 1=start after header row
            },
            'cell': {
                'userEnteredFormat': {
                    'numberFormat': {
                        'type': 'NUMBER',        # Decimal format
                        'pattern': '#,##0.0###'  # Up to four decimal places
                    }
                }
            },
            'fields': 'userEnteredFormat.numberFormat'
        }
    }

# Format column(s) as percentage with 2 decimal places
def fmt_columns_percentage(worksheet, cfirst, clast, rfirst=1):
    return {
        'repeatCell': {
            'range': {
                'sheetId': worksheet.id,
                'startColumnIndex': cfirst,  # 0-indexed, e.g. N=13
                'endColumnIndex': clast,     # End is exclusive, so 14
                'startRowIndex': rfirst,     # 0-indexed, 1=Start after the header row
            },
            'cell': {
                'userEnteredFormat': {
                    'numberFormat': {
                        'type': 'PERCENT',  # Percentage format
                        'pattern': '0.00%'  # Two decimal places
                    }
                }
            },
            'fields': 'userEnteredFormat.numberFormat'
        }
    }

# Format column(s) as local currency (£)
def fmt_columns_currency(worksheet, cfirst, clast, rfirst=1):
    return {
        'repeatCell': {
            'range': {
                'sheetId': worksheet.id,
                'startColumnIndex': cfirst,  # 0-indexed, e.g. N=13
                'endColumnIndex': clast,     # End is exclusive
                'startRowIndex': rfirst,     # Start after the header row
            },
            'cell': {
                'userEnteredFormat': {
                    'numberFormat': {
                        'type': 'CURRENCY',     # Currency format
                        'pattern': '£#,##0.00'  # GBP symbol with two decimal places
                    }
                }
            },
            'fields': 'userEnteredFormat.numberFormat'
        }
    }

# Format column(s) horizontal justification
def fmt_columns_hjustify(worksheet, cfirst, clast, justification, rfirst=1):
    return {
        'repeatCell': {
            'range': {
                'sheetId': worksheet.id,
                'startColumnIndex': cfirst,  # 0-indexed
                'endColumnIndex': clast,     # End is exclusive
                'startRowIndex': rfirst,     # Start after header row (0-indexed)
            },
            'cell': {
                'userEnteredFormat': {
                    'horizontalAlignment': justification
                }
            },
            'fields': 'userEnteredFormat.horizontalAlignment'
        }
    }


#------------------------------------------------------------------------------
# Requests for formatting information

def get_fillcolour(service, spreadsheet_id, range_name='Sheet1!A1'):
    # Retrieve cell format data
    result = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id, 
        ranges=range_name, 
        fields='sheets(data(rowData(values(userEnteredFormat))))'
    ).execute()

    # Extract the background color (RGB) from the response
    cell_data = result['sheets'][0]['data'][0]['rowData'][0]['values'][0]['userEnteredFormat']

    # Check if the backgroundColor field exists
    if 'backgroundColor' in cell_data:
        background_color = cell_data['backgroundColor']
        red = background_color.get('red', 1)   # Default to 1 if color is white
        green = background_color.get('green', 1)
        blue = background_color.get('blue', 1)

        return {red, green, blue}
    else:
        return None


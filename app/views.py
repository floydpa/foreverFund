import logging, re, datetime

from flask import render_template, flash, session, redirect, url_for, request, jsonify, send_from_directory, g
from werkzeug.utils import secure_filename

from . import app
from . import uport, secu, sim_conf

from .forms import PieChartForm, AccountNameForm, AccountTypeForm, PlatformNameForm
from .forms import FileDownloadCashForm, FileDownloadForm, CashForm, getPositionsForm
from .forms import SimulationForm
from .models import MyPage

from PlatformClasses import platformCode_to_class
from AccountClasses import AccountGroup
from SecurityClasses import security_update_json

from wb import GspreadAuth, WbIncome, WbSecMaster, WsByPosition
from wb_bysecurity import WsDividendsBySecurity, WsEstimatedIncome

# ---------------------------------------------------------------------------------------
# Function to render a paginated list on screen
# ---------------------------------------------------------------------------------------

def render_paginated_list(html, all, endpoint, **kwargs):
    try:
        page = request.args.get('page', 1, type=int)
    except:
        page = 1
    pagination = MyPage(all, page, items_per_page=app.config['ITEMS_PER_PAGE'])
    # logging.info("pagination=%s"%(pagination))
    # logging.info("pages()=%s"%(pagination.iter_pages()))

    prevPage = None
    if pagination.has_prev:
        prevPage = url_for(endpoint, page=page-1, _external=True)
    nextPage = None
    if pagination.has_next:
        nextPage = url_for(endpoint, page=page+1, _external=True)
    return render_template(html, pagination=pagination, prevPage=prevPage, nextPage=nextPage, endpoint=endpoint, **kwargs)

# ---------------------------------------------------------------------------------------
# Function to render a paginated list on screen
# ---------------------------------------------------------------------------------------

def render_paginated_listn(html, all, endpoint, nitems, **kwargs):
    try:
        page = request.args.get('page', 1, type=int)
    except:
        page = 1

    if nitems <= 0:
        nitems = app.config['ITEMS_PER_PAGE']
    pagination = MyPage(all, page, items_per_page=nitems)

    # logging.info("pagination=%s"%(pagination))
    # logging.info("pages()=%s"%(pagination.iter_pages()))

    prevPage = None
    if pagination.has_prev:
        prevPage = url_for(endpoint, page=page-1, _external=True)
    nextPage = None
    if pagination.has_next:
        nextPage = url_for(endpoint, page=page+1, _external=True)
    return render_template(html, pagination=pagination, prevPage=prevPage, nextPage=nextPage, endpoint=endpoint, **kwargs)

# ----------------------------------------------------------------------------------------------
# Entry point
#
# Initialise then show portfolio asset values
# ----------------------------------------------------------------------------------------------

@app.route('/')
@app.route('/index')
def index():

    # Refresh accounts (after picking up any security updates)
    secu.refresh()
    uport.refresh(secu)

    # Remove 'webreport' keys to aid debugging
    for key in ('COB','COB2','DOMAIN','DOMAIN2','ENV','ENV2','sn','givenName','userId','name'):
        if key in session:
            session.pop(key,None)

    # Record what's in the session variables
    logging.debug("index: session=%s"%(session))

    # Ue configuration if needed
    if 'ACCOUNT_NAME' not in session:
        session['ACCOUNT_NAME'] = app.config['ACCOUNT_NAME']
    if 'ACCOUNT_TYPE' not in session:
        session['ACCOUNT_TYPE'] = app.config['ACCOUNT_TYPE']
    if 'PLATFORM_NAME' not in session:
        session['PLATFORM_NAME'] = app.config['PLATFORM_NAME']

    return assets_by_account()

# ----------------------------------------------------------------------------------------------
# Portfolio Asset Value
# ----------------------------------------------------------------------------------------------

@app.route('/assets/account', methods=['GET','POST'])
def assets_by_account():
    title = "Portfolio Summary"
    all = uport.tdl_account_asset_value(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))
    assets = render_paginated_listn('portfolio.html', all, 'assets_by_account', 50, title=title, root="/assets")
    return assets

# ----------------------------------------------------------------------------------------------
# Portfolio Annual Income
# ----------------------------------------------------------------------------------------------

@app.route('/income/account', methods=['GET','POST'])
def income_by_account():
    title = "Annual Income"
    all = uport.tdl_account_annual_income(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))
    return render_paginated_listn('portfolio.html', all, 'income_by_account', 50, title=title, root="/income")


# ----------------------------------------------------------------------------------------------
# Dividend declarations and payments
# ----------------------------------------------------------------------------------------------

@app.route('/dividend/declarations', methods=['GET','POST'])
def dividend_declarations():
    title = "Dividend Declarations"
    all = uport.tdl_dividend_declarations(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))
    return render_paginated_list('dividends.html', all, 'dividend_declarations', title=title)

@app.route('/dividend/projections', methods=['GET','POST'])
def dividend_projections():
    title = "Projected Dividend Payments"
    all = uport.tdl_dividend_projections(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))
    return render_paginated_list('dividends.html', all, 'dividend_projections', title=title)

@app.route('/dividend/payments', methods=['GET','POST'])
def dividend_payments():
    title = "Dividend Payments"
    all = uport.tdl_dividend_payments(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))
    return render_paginated_list('dividends.html', all, 'dividend_payments', title=title)

@app.route('/dividend/mdeclarations', methods=['GET','POST'])
def dividend_mdeclarations():
    title = "Monthly Declarations"
    all = uport.tdl_dividend_mdeclarations(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))
    return render_paginated_listn('dividends-m.html', all, 'dividend_mdeclarations', 50, title=title)

@app.route('/dividend/mpayments', methods=['GET','POST'])
def dividend_mpayments():
    title = "Monthly Payments"
    all = uport.tdl_dividend_mpayments(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))
    return render_paginated_listn('dividends-m.html', all, 'dividend_mpayments', 50, title=title)



# ----------------------------------------------------------------------------------------------
# Assets values for positions making up an account
# ----------------------------------------------------------------------------------------------

@app.route('/assets/position/<id>', methods=['GET','POST'])
def assets_by_position(id):
    logging.debug("assets_by_position(%s) request=%s"%(id,request))
    session['ACCOUNT_ID'] = id
    return assets_by_position2()

@app.route('/assets/position', methods=['GET','POST'])
def assets_by_position2():
    logging.debug("assets_by_position2: session=%s"%(session))

    if session.get('ACCOUNT_ID'):
        id = session['ACCOUNT_ID']
        (u, t, p) = id.split('_')
    else:
        u = session['ACCOUNT_NAME']
        t = session['ACCOUNT_TYPE']
        p = session['PLATFORM_NAME']

    title="Account Assets"
    all = uport.tdl_position_asset_value(u, t, p)
    return render_paginated_listn('positions.html', all, 'assets_by_position2', 50, title=title)

# ----------------------------------------------------------------------------------------------
# Income for positions making up an account
# ----------------------------------------------------------------------------------------------

@app.route('/income/position/<id>', methods=['GET','POST'])
def income_by_position(id):
    logging.debug("income_by_position(%s) request=%s"%(id,request))
    session['ACCOUNT_ID'] = id
    return income_by_position2()

@app.route('/income/position', methods=['GET','POST'])
def income_by_position2():
    logging.debug("income_by_position2: session=%s"%(session))

    if session.get('ACCOUNT_ID'):
        id = session['ACCOUNT_ID']
        (u, t, p) = id.split('_')
    else:
        u = session['ACCOUNT_NAME']
        t = session['ACCOUNT_TYPE']
        p = session['PLATFORM_NAME']

    title="Account Income"
    all = uport.tdl_position_annual_income(u, t, p)
    return render_paginated_listn('positions.html', all, 'income_by_position2', 50, title=title)


# ---------------------------------------------------------------------------------------
# Update worksheets within Google Workbooks
# ---------------------------------------------------------------------------------------

@app.route('/wbincome/bysecurity', methods=['GET','POST'])
def wb_income_by_security():
    logging.debug("wb_income_by_security() request=%s"%(request))
    
    gsauth = GspreadAuth()
    ForeverIncome = WbIncome(gsauth)
    SecurityMaster = WbSecMaster(gsauth)

    bySecurity = WsDividendsBySecurity(ForeverIncome,SecurityMaster)
    bySecurity.refresh()

    return redirect(url_for('index'))

@app.route('/wbincome/byposition', methods=['GET','POST'])
def wb_income_by_position():
    logging.debug("wb_income_by_position() request=%s"%(request))

    ag = AccountGroup(uport.accounts(),None,None)

    gsauth = GspreadAuth()
    ForeverIncome = WbIncome(gsauth)

    bypos = WsByPosition(ForeverIncome)
    bypos.refresh(ag.positions())

    return redirect(url_for('index'))

@app.route('/wbincome/estimated_3m', methods=['GET','POST'])
def wb_estimated_income_3m():
    logging.debug("wb_estimated_income_3m() request=%s"%(request))

    return wb_estimated_income(13)

@app.route('/wbincome/estimated_1y', methods=['GET','POST'])
def wb_estimated_income_1y():
    logging.debug("wb_estimated_income_1y() request=%s"%(request))

    return wb_estimated_income(52)

def wb_estimated_income(nWeeks):  
    ag = AccountGroup(uport.accounts(),None,None)

    gsauth = GspreadAuth()
    ForeverIncome = WbIncome(gsauth)

    estimatedIncome = WsEstimatedIncome(ForeverIncome, nWeeks)
    estimatedIncome.projected_income(ag.positions(), secu)
    estimatedIncome.refresh()

    return dividend_projections()

    
# ---------------------------------------------------------------------------------------
# Breakdown of assets
# ---------------------------------------------------------------------------------------

@app.route('/assets/breakdown', methods=['GET','POST'])
def assets_breakdown():
    form = PieChartForm()
    title="Asset Allocation"
    if form.validate_on_submit():
        return redirect(url_for('index'))

    logging.debug("session=%s"%(session))
    data = uport.data_asset_class_split(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))

    return render_template('pie-chart.html', form=form, data=data, title=title)

# ---------------------------------------------------------------------------------------
# Allocation to risk buckets
# ---------------------------------------------------------------------------------------

@app.route('/risk/breakdown', methods=['GET','POST'])
def risk_breakdown():
    form = PieChartForm()
    title="Risk Bucket Allocation"
    if form.validate_on_submit():
        return redirect(url_for('index'))

    logging.debug("session=%s"%(session))
    data = uport.data_risk_split(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))

    return render_template('pie-chart.html', form=form, data=data, title=title)

# ---------------------------------------------------------------------------------------
# Asset breakdown - equities, bonds, property, etc.
# ---------------------------------------------------------------------------------------

@app.route('/assets/class/<id>', methods=['GET','POST'])
def assets_by_class(id):
    logging.debug("assets_by_class(%s) request=%s"%(id,request))
    session['ASSET_CLASS'] = id
    return assets_by_class2()

@app.route('/assets/class', methods=['GET','POST'])
def assets_by_class2():
    logging.debug("assets_by_class2: session=%s"%(session))

    # if session.get('ACCOUNT_ID'):
    #    id = session['ACCOUNT_ID']
    #    (u, t, p) = id.split('_')
    # else:
    u = session['ACCOUNT_NAME']
    t = session['ACCOUNT_TYPE']
    p = session['PLATFORM_NAME']

    ac = session.get('ASSET_CLASS')
    title="Account Assets (%s)" % (ac)
    all = uport.tdl_position_assetclass_value(u, t, p, ac)
    return render_paginated_listn('acpositions.html', all, 'assets_by_class2', 50, title=title)


# ---------------------------------------------------------------------------------------
# Risk breakdown - High, Moderate or Cash/Cash-like
# ---------------------------------------------------------------------------------------

@app.route('/assets/risk/<id>', methods=['GET','POST'])
def assets_by_risk(id):
    logging.debug("assets_by_risk(%s) request=%s"%(id,request))
    session['ASSET_RISK'] = id
    return assets_by_risk2()

@app.route('/assets/risk', methods=['GET','POST'])
def assets_by_risk2():
    logging.debug("assets_by_risk2: session=%s"%(session))

    # if session.get('ACCOUNT_ID'):
    #    id = session['ACCOUNT_ID']
    #    (u, t, p) = id.split('_')
    # else:
    u = session['ACCOUNT_NAME']
    t = session['ACCOUNT_TYPE']
    p = session['PLATFORM_NAME']

    ar = session.get('ASSET_RISK')
    if ar == 'high':
        risk_bucket = 'High'
    elif ar == 'moderate':
        risk_bucket = 'Moderate'
    elif ar == 'cash':
        risk_bucket = 'Cash/Cash-like'
    else:
        risk_bucket = None

    title="Account Assets (%s)" % (risk_bucket)
    #### PJF - change for risk ####
    all = uport.tdl_position_riskbucket_value(u, t, p, risk_bucket)
    return render_paginated_listn('acpositions.html', all, 'assets_by_risk2', 50, title=title)


# ---------------------------------------------------------------------------------------
# Other breakdowns
# ---------------------------------------------------------------------------------------

@app.route('/sector/breakdown', methods=['GET','POST'])
def sector_breakdown():
    form = PieChartForm()
    title = "Sector Breakdown"
    if form.validate_on_submit():
        return redirect(url_for('index'))

    logging.debug("session=%s"%(session))
    data = uport.data_sector_split(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))

    return render_template('pie-chart.html', form=form, data=data, title=title)

@app.route('/parent/breakdown', methods=['GET','POST'])
def parent_sector_breakdown():
    form = PieChartForm()
    title = "Sector Allocation"
    if form.validate_on_submit():
        return redirect(url_for('index'))

    logging.debug("session=%s"%(session))
    data = uport.data_parent_sector_split(session.get('ACCOUNT_NAME'), session.get('ACCOUNT_TYPE'))

    return render_template('pie-chart.html', form=form, data=data, title=title)

# ----------------------------------------------------------------------------------------------
# List of securities
# ----------------------------------------------------------------------------------------------

@app.route('/securities', methods=['GET','POST'])
def securities():
    title = 'Invested Securities'
    all = secu.list_securities(None)
    return render_paginated_list('securities.html', all, 'securities', title=title)

@app.route('/securities/IT', methods=['GET','POST'])
def securities_IT():
    title = 'Invested Investment Trusts'
    all = secu.list_securities('IT')
    return render_paginated_list('securities.html', all, 'securities_IT', title=title)

@app.route('/securities/OEIC', methods=['GET','POST'])
def securities_OEIC():
    title = 'Invested OEICs'
    all = secu.list_securities('OEIC')
    return render_paginated_list('securities.html', all, 'securities_OEIC', title=title)

@app.route('/securities/ETF', methods=['GET','POST'])
def securities_ETF():
    title = 'Invested ETFs'
    all = secu.list_securities('ETF')
    return render_paginated_list('securities.html', all, 'securities_ETF', title=title)

@app.route('/security/<id>', methods=['GET', 'POST'])
def security(id):
    session['SECURITY_ID'] = id
    return security_detail()

@app.route('/security', methods=['GET', 'POST'])
def security_detail():
    id = session['SECURITY_ID']
    s = secu.find_security(id)
    all = s.tdl_security_detail()
    return render_paginated_listn('security.html', all, 'security_detail', 50, title=s.lname())

@app.route('/update/security/<id>', methods=['GET', 'POST'])
def update_security(id):
    session['SECURITY_ID'] = id
    s = secu.find_security(id)

    # Initialise connection to 2 Google Workbooks
    gsauth = GspreadAuth()
    ForeverIncome = WbIncome(gsauth)
    SecurityMaster = WbSecMaster(gsauth)

    # Update security json file from workbook
    security_update_json(ForeverIncome, SecurityMaster, id)
    
    # Update in memory definition from new json file
    secu.refresh()

    # Show details of updated security
    s = secu.find_security(id)
    all = s.tdl_security_detail()
    return render_paginated_listn('security.html', all, 'security_detail', 50, title=s.lname())


@app.route('/update/account/<id>', methods=['GET', 'POST'])
def update_account(id):
    session['ACCOUNT_ID'] = id
    (u, t, p) = id.split('_')

    account  = uport.get_account(u, t, p)
    platform = platformCode_to_class(p)()

    formname = platform.download_formname()
    if formname == "FileDownloadCashForm":
        form = FileDownloadCashForm()
    elif formname == "FileDownloadForm":
        form = FileDownloadForm()
    elif formname == "CashForm":
        form = CashForm()
    elif formname == "getPositionsForm":
        positions = uport.positions(u,t,p)
        form = getPositionsForm(positions)
    else:
        assert False, "Formname %s unknown" % (formname)

    # form = UpdateAccountForm()

    if form.validate_on_submit():
        if (t == 'Sav') or p in ('II','HL','BI'):
            platform.update_positions(account.usercode(), t, form.cash.data)
        else:
            platform.update_positions(account.usercode(), t)
        session.pop('ACCOUNT_ID', None)
        return redirect(url_for('index'))

    # Initialise form values
    platform_name = platform.name(True)
    account_type = account.account_type(True)

    title = "Update Account (%s %s)" % (u, account_type)
    
    if formname == "getPositionsForm":
        all = uport.tdl_position_list(u, t, p)
        return render_template('update_positions.html', positions=all, form=form, title=title)

    else:
        form.account.data  = platform_name
        sourcefile = platform.download_filename(account.usercode(), t)
        if sourcefile is None:
            sourcefile = platform.current_filename(account.usercode(), t)
        form.filename.data = sourcefile
        return render_template('update_account.html', form=form, title=title)

# ----------------------------------------------------------------------------------------------
# Settings
# ----------------------------------------------------------------------------------------------

@app.route('/settings', methods=['GET','POST'])
@app.route('/settings/user', methods=['GET','POST'])
def accountName():
    form = AccountNameForm()

    if form.validate_on_submit():
        if form.username.data == 'ALL':
            session['ACCOUNT_NAME'] = None
        else:
            session['ACCOUNT_NAME'] = form.username.data

        # Reset other attributes if User is changed
        session['ACCOUNT_TYPE'] = None
        session['PLATFORM_NAME'] = None

        session.pop('ACCOUNT_ID', None)

        # Use session variables to overwrite the reporting variable values
        logging.debug("usersettings session=%s"%(session))

        return redirect(url_for('index'))

    # Initialise form value
    if session.get('ACCOUNT_NAME') is None:
        form.username.data = 'ALL'
    else:
        form.username.data = session.get('ACCOUNT_NAME')

    return render_template('account_name.html', form=form)

@app.route('/settings/acctype', methods=['GET','POST'])
def accountType():
    form = AccountTypeForm()

    if form.validate_on_submit():
        if form.acctype.data == 'ALL':
            session['ACCOUNT_TYPE'] = None
        else:
            session['ACCOUNT_TYPE'] = form.acctype.data

        # Reset platform if account type is changed
        session['PLATFORM_NAME'] = None

        session.pop('ACCOUNT_ID', None)
        
        # Use session variables to overwrite the reporting variable values
        logging.debug("accountType session=%s"%(session))

        return redirect(url_for('index'))

    # Initialise form value
    if session.get('ACCOUNT_TYPE') is None:
        form.acctype.data = 'ALL'
    else:
        form.acctype.data = session.get('ACCOUNT_TYPE')

    return render_template('account_type.html', form=form)

@app.route('/settings/platform', methods=['GET','POST'])
def platformName():
    form = PlatformNameForm()

    if form.validate_on_submit():
        if form.pltname.data == 'ALL':
            session['PLATFORM_NAME'] = None
        else:
            session['PLATFORM_NAME'] = form.pltname.data

        # Unset selected account
        session.pop('ACCOUNT_ID', None)

        # Use session variables to overwrite the reporting variable values
        logging.debug("platformName session=%s"%(session))

        return redirect(url_for('index'))

    # Initialise form value
    if session.get('PLATFORM_NAME') is None:
        form.pltname.data = 'ALL'
    else:
        form.pltname.data = session.get('PLATFORM_NAME')

    return render_template('platform_name.html', form=form)

# ----------------------------------------------------------------------------------------------
# Simulation
# ----------------------------------------------------------------------------------------------

@app.route('/simulation', methods=['GET','POST'])
@app.route('/simulation/config', methods=['GET','POST'])
def simulationConfig():
    form = SimulationForm()

    if form.validate_on_submit():
        session['SIM_CPI'] = str(form.CPI.data)
        session['SIM_RPI'] = str(form.RPI.data)
        session['SIM_GROWTH'] = str(form.portfolioGrowth.data)
        session['SIM_EXPENSES1'] = str(form.livingExpenses1.data)
        session['SIM_EXPENSES2'] = str(form.livingExpenses2.data)
        session['SIM_EXPYEARS'] = str(form.expensiveYears.data)
        session['SIM_YEARS'] = str(form.simYears.data)

        # Use session variables to overwrite the reporting variable values
        logging.debug("usersettings session=%s"%(session))

        return redirect(url_for('index'))

    # Initialise form value
    if session.get('SIM_CPI') is None:
        form.RPI.data = 0.025
    else:
        form.RPI.data = float(session.get('SIM_CPI'))

    if session.get('SIM_RPI') is None:
        form.RPI.data = 0.035
    else:
        form.RPI.data = float(session.get('SIM_RPI'))

    if session.get('SIM_GROWTH') is None:
        form.portfolioGrowth.data = 0.04
    else:
        form.portfolioGrowth.data = float(session.get('SIM_GROWTH'))

    if session.get('SIM_EXPENSES1') is None:
        form.livingExpenses1.data = 60000.0
    else:
        form.livingExpenses1.data = float(session.get('SIM_EXPENSES1'))

    if session.get('SIM_EXPENSES2') is None:
        form.livingExpenses2.data = 50000.0
    else:
        form.livingExpenses2.data = float(session.get('SIM_EXPENSES2'))

    if session.get('SIM_EXPYEARS') is None:
        form.expensiveYears.data = 5
    else:
        form.expensiveYears.data = int(session.get('SIM_EXPYEARS'))

    if session.get('SIM_YEARS') is None:
        form.simYears.data = 20
    else:
        form.simYears.data = int(session.get('SIM_YEARS'))

    return render_template('simulation.html', form=form)


@app.route('/simulation/scenario', methods=['GET','POST'])
def simulationScenario():
    form = SimulationForm()

    if form.validate_on_submit():
        session['SIM_CPI'] = str(form.CPI.data)
        session['SIM_RPI'] = str(form.RPI.data)
        session['SIM_GROWTH'] = str(form.portfolioGrowth.data)
        session['SIM_EXPENSES1'] = str(form.livingExpenses1.data)
        session['SIM_EXPENSES2'] = str(form.livingExpenses2.data)
        session['SIM_EXPYEARS'] = str(form.expensiveYears.data)
        session['SIM_YEARS'] = str(form.simYears.data)

        # Use session variables to overwrite the reporting variable values
        logging.debug("usersettings session=%s"%(session))

        return redirect(url_for('index'))

    # Initialise form value
    if session.get('SIM_CPI') is None:
        form.RPI.data = 0.025
    else:
        form.RPI.data = float(session.get('SIM_CPI'))

    if session.get('SIM_RPI') is None:
        form.RPI.data = 0.035
    else:
        form.RPI.data = float(session.get('SIM_RPI'))

    if session.get('SIM_GROWTH') is None:
        form.portfolioGrowth.data = 0.04
    else:
        form.portfolioGrowth.data = float(session.get('SIM_GROWTH'))

    if session.get('SIM_EXPENSES1') is None:
        form.livingExpenses1.data = 60000.0
    else:
        form.livingExpenses1.data = float(session.get('SIM_EXPENSES1'))

    if session.get('SIM_EXPENSES2') is None:
        form.livingExpenses2.data = 50000.0
    else:
        form.livingExpenses2.data = float(session.get('SIM_EXPENSES2'))

    if session.get('SIM_EXPYEARS') is None:
        form.expensiveYears.data = 5
    else:
        form.expensiveYears.data = int(session.get('SIM_EXPYEARS'))

    if session.get('SIM_YEARS') is None:
        form.simYears.data = 20
    else:
        form.simYears.data = int(session.get('SIM_YEARS'))

    return render_template('simulation.html', form=form)

import pandas as pd
import numpy as np
from flask import Flask, request, render_template
from os import listdir
from threading import Thread
import json
from time import sleep

from Liabilities import Liabilities
from MACalc import MatchingAdjustment
from InterestRates import InterestRate
from ERM import ERM
from Bonds import BondPortfolio
from Assets import Portfolio
from Mortality import Mortality
from Annuity import Annuity
from BalanceSheet import BalanceSheet
from globals import UserDefinedGlobals as udg


output_config = {'SII OF': {'output_level': 0},
                  'BSCR': {'output_level': 0},
                  'SII EOF': {'output_level': 0},
                  'IFRS Net Equity': {'output_level': 0},
                  'Assets': {'output_level': 1, 'output_class': 'A'},
                  'Bonds': {'output_level': 2, 'output_class': 'A'},
                  'ERMs': {'output_level': 2, 'output_class': 'A'},
                  'Cash': {'output_level': 2, 'output_class': 'A'},
                  'Liabilities': {'output_level': 1, 'output_class': 'L'},
                  'Annuities': {'output_level': 2, 'output_class': 'L'},
                  'Matching Adjustment': {'output_level': 2, 'output_class': 'L'},
                  'Risk Margin': {'output_level': 2, 'output_class': 'L'},
                  'VIR Adjustment': {'output_level': 2, 'output_class': 'L'},
                  'Bond MA': {'output_level': 3, 'output_class': 'L'},
                  'LTM MA': {'output_level': 3, 'output_class': 'L'}}

app = Flask(__name__)

status = ""
process_running = False

def log_to_html():
    html = ""
    for row in udg.log:
        html += f'<tr><td>{row[0]}</td><td>{row[1]}</td></tr>'
    return html


def task():
    global status
    while process_running:
        status = log_to_html()
        sleep(1)
    return

@app.route('/status')#, methods=['GET'])
def getStatus():
    statusList = {'status': status}
    return json.dumps(statusList)

@app.route("/")
def index():

    global process_running

    user_action = request.args.get('submit_btn', None)

    opt_ann_dataset = request.args.get('ann_dataset', None)
    opt_ltm_dataset = request.args.get('ltm_dataset', None)
    opt_bond_dataset = request.args.get('bond_dataset', None)
    opt_ir_curve = request.args.get('ir_curve', None)

    ann_datasets, bond_datasets, ltm_datasets, ir_curves = get_datasets()

    if user_action != 'Run':
        html_ifrs_bs = ""
        html_sii_bs = ""

    elif user_action == 'Run':
        process_running = True
        t1 = Thread(target=task)
        t1.start()
        html_ifrs_bs, html_sii_bs = run_model(opt_bond_dataset, opt_ltm_dataset, opt_ann_dataset, opt_ir_curve)
        process_running = False



    return render_template('balance_sheet_index_new2.html',
                           ifrs_bs=html_ifrs_bs,
                           sii_bs=html_sii_bs,
                           inp_ann_datasets=ann_datasets,
                           inp_bond_datasets=bond_datasets,
                           inp_ltm_datasets=ltm_datasets,
                           inp_ir_curves=ir_curves)


def run_model(bond_dataset, ltm_dataset, ann_dataset, ir_curve):
    mdl_ir = InterestRate(ir_curve)
    mdl_mortality = Mortality()

    df_bonds = pd.read_csv(f'inputs/bond_data_inputs/{bond_dataset}', index_col='ISIN')
    mdl_bonds = BondPortfolio(mdl_ir, df_bonds)

    ltm_pols = pd.read_csv(f'inputs/ltm_data_inputs/{ltm_dataset}', index_col='PolicyID')
    mdl_erm = ERM(mdl_mortality, mdl_ir, ltm_pols, 0.018, 0.13)

    mdl_assets = Portfolio(mdl_ir, mdl_mortality, mdl_bonds, mdl_erm)

    ann_data = pd.read_csv(f'inputs/ann_data_inputs/{ann_dataset}')
    ann_data['Age'] = np.maximum(ann_data['Age'], udg.pension_age)
    mdl_ann = Annuity(InterestRate(ir_curve), ann_data)

    mdl_liab = Liabilities(mdl_ir, mdl_mortality, mdl_ann)

    MdlMA = MatchingAdjustment(mdl_ir, mdl_assets.EqRelModel, mdl_assets.BondModel, mdl_liab.AnnuityModel)

    IC = BalanceSheet(mdl_assets, mdl_liab, MdlMA)

    ifrs_bs = IC.ifrs(3)
    sii_bs = IC.sii(3)

    html_ifrs_bs = balance_sheet_html(ifrs_bs)
    html_sii_bs = balance_sheet_html(sii_bs)

    return html_ifrs_bs, html_sii_bs

def get_datasets():
    ann_datasets = ""
    for f in listdir('inputs/ann_data_inputs'):
        ann_datasets += "<option value='" + f + "'>" + f + "</option>"

    bond_datasets = ""
    for f in listdir('inputs/bond_data_inputs'):
        bond_datasets += "<option value='" + f + "'>" + f + "</option>"

    ltm_datasets = ""
    for f in listdir('inputs/ltm_data_inputs'):
        ltm_datasets += "<option value='" + f + "'>" + f + "</option>"

    ir_curves = ""
    for f in listdir('inputs/ir_curve_inputs'):
        ir_curves += "<option value='" + f + "'>" + f + "</option>"

    return ann_datasets, bond_datasets, ltm_datasets, ir_curves

def balance_sheet_html(bs_dict):

    km_html = "<tr><th colspan='2' style='background-color: #ecf0f1; padding: 5px;'>Key Metrics</th></tr>"
    assets_html = "<tr><th colspan='2'>Assets</th></tr>"
    liabs_html = "<tr><th colspan='2'>Liabilities</th></tr>"

    for k, v in bs_dict.items():
        v = "{0:,.1f}".format(v/10**6)
        if output_config[k]['output_level'] == 0:
            km_html += f"<tr>" \
                       f"<td style='border: none; background-color: #ecf0f1;'><b>{k}</b></td>" \
                       f"<td style='text-align: right; border: none; background-color: #ecf0f1;'><b>{v}</b></td>" \
                       f"</tr>"
        else:
            if output_config[k]['output_class'] == 'A':
                assets_html += f"<tr>" \
                           f"<td style='padding-left: {30 * output_config[k]['output_level']}px;'>{k}</td>" \
                           f"<td style='text-align: right;'>{v}</td>" \
                           f"</tr>"
            else:
                liabs_html += f"<tr>" \
                           f"<td style='padding-left: {30 * output_config[k]['output_level']}px;'>{k}</td>" \
                           f"<td style='text-align: right;'>{v}</td>" \
                           f"</tr>"

    return km_html + assets_html + liabs_html



if __name__ == '__main__':

    app.run(host="127.0.0.1", port=8080, debug=True)


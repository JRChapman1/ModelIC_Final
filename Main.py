import pandas as pd

from enquirer import Var, RunManager
from matplotlib import pyplot as plt
from flask import Flask, request, render_template
from PolicyDataGenerator import Generator
from os import listdir

from Mortality import Mortality
from InterestRates import InterestRate
from ERM import ERM
from Bonds import BondPortfolio
from Annuity import Annuity
from globals import UserDefinedGlobals as udg
from datetime import datetime as dt



app = Flask(__name__)

var_mapping = {
    'ltm_econ_val': Var.ltm_econ_val,
    'ltm_eff_val': Var.ltm_eff_val,
    'sii_eof': Var.sii_eof,
    'sii_scr': Var.sii_scr,
    'int_scr': Var.int_scr,
    'mort_scr': Var.mort_scr,
    'ifrs_net_equity': Var.ifrs_net_equity,
    'ma_benefit': Var.ma_benefit,
    'bond_ma_benefit': Var.bond_ma_benefit,
    'ltm_ma_benefit': Var.ltm_ma_benefit,
    'bond_mp': Var.bond_mp,
    'mp': Var.mp,
    'portfolio_ma_spread': Var.portfolio_ma_spread,
    'asset_value': Var.asset_value,
    'liability_value': Var.liability_value,
    'bond_value': Var.bond_value,
    'ifrs_vir_adjustment': Var.ifrs_vir_adjustment,
    'ifrs_vir': Var.ifrs_vir
}

friendly_names = {
    'ir_shock': 'interest rate shock',
    'bond_val_stress': 'bond value stress',
    'liab_val_stress': 'liability value stress',
    'mortality_scalar': 'mortality scalar',
    'hpi_drift': 'HPI drift',
    'hpi_vol': 'HPI volatility',
    'prop_shock': 'instantaneous property value shock',
    'annuity_margin': 'profit margin on annuities',
    'cash_held': 'cash held'
}

@app.route("/")
def index():

    user_action = request.args.get('submit_btn', None)

    lst_output_vars = request.args.get('lst_output_vars', None)
    dependent_variable = request.args.get('dependent_variable', None)
    lst_dependent_variable_values = request.args.get('dependent_variable_values', None)
    opt_ann_dataset = request.args.get('ann_dataset', 'Annuity dataset error')
    opt_ltm_dataset = request.args.get('ltm_dataset', 'LTM dataset error')
    opt_bond_dataset = request.args.get('bond_dataset', 'Bond dataset error')
    opt_irs_dataset = request.args.get('irs_dataset', 'IRS dataset error')

    if opt_ltm_dataset == 'none':
        opt_ltm_dataset = None
    if opt_bond_dataset == 'none':
        opt_bond_dataset = None
    if opt_irs_dataset == 'none':
        opt_irs_dataset = None

    if lst_output_vars is None or dependent_variable is None or lst_dependent_variable_values is None or user_action != 'Run':
        res_index = ""
        res_data = ""
        stress_friendly_name = ""
        str_bond_cfs = ""
        str_erm_cfs = ""
        str_liab_cfs = ""

    elif user_action == 'Run':

        udg.log.append((dt.now(), "Run starting..."))

        ovs = []
        for ov in lst_output_vars.split(","):
            ovs.append(var_mapping[ov])
        vals = [float(v) for v in lst_dependent_variable_values.split(",")]

        res, stress_friendly_name = run_sensitivities(ovs, dependent_variable, vals, opt_ann_dataset, opt_ltm_dataset, opt_bond_dataset, opt_irs_dataset)

        bond_cfs, erm_cfs, liab_cfs = run_cfs(opt_bond_dataset, opt_ltm_dataset, opt_ann_dataset)

        str_bond_cfs = str(bond_cfs)
        str_erm_cfs = str(erm_cfs)
        str_liab_cfs = str(liab_cfs)

        res_data = ""
        color_index = 0
        color_list = ['#03A9F4', '#9b59b6', '#2ecc71', '#e67e22', '#e74c3c', '#16a085', '#34495e']
        for col in res:
            res_data += "{label: '" + col + "', backgroundColor: '" + color_list[color_index] + "', borderColor: '" + color_list[color_index] + "', data: " + str(res[col].to_list()) + ", pointRadius: 0, },"
            color_index += 1
        res_data = res_data[:-1]
        res_index = vals

        udg.log.append((dt.now(), "Run complete"))

    if user_action == "Save Annuity Data":
        new_data = create_ann_dataset()
        new_dataset_name = request.args.get('new_dataset_name', None)
        new_data.to_csv(f'inputs/ann_data_inputs/{new_dataset_name}.csv')

    if user_action == "Save ERM Data":
        new_data = create_erm_dataset()
        new_dataset_name = request.args.get('new_dataset_name', None)
        new_data.to_csv(f'inputs/ltm_data_inputs/{new_dataset_name}.csv')

    if user_action == "Save Bond Data":
        new_data = create_bond_dataset()
        new_dataset_name = request.args.get('new_dataset_name', None)
        new_data.to_csv(f'inputs/bond_data_inputs/{new_dataset_name}.csv')

    ann_datasets = ""
    for f in listdir('inputs/ann_data_inputs'):
        ann_datasets += "<option value='" + f + "'>" + f + "</option>"

    bond_datasets = ""
    for f in listdir('inputs/bond_data_inputs'):
        bond_datasets += "<option value='" + f + "'>" + f + "</option>"

    ltm_datasets = ""
    for f in listdir('inputs/ltm_data_inputs'):
        ltm_datasets += "<option value='" + f + "'>" + f + "</option>"

    irs_datasets = ""
    for f in listdir('inputs/irs_data_inputs'):
        irs_datasets += "<option value='" + f + "'>" + f + "</option>"

    html_log = format_log()

    udg.log = []

    return render_template('curve_enquirer_index.html',
                           res_index=res_index,
                           res_data=res_data,
                           res_stress_name=stress_friendly_name,
                           inp_ann_datasets=ann_datasets,
                           inp_bond_datasets=bond_datasets,
                           inp_ltm_datasets=ltm_datasets,
                           inp_irs_datasets=irs_datasets,
                           res_bond_cfs = str_bond_cfs,
                           res_erm_cfs = str_erm_cfs,
                           res_liab_cfs = str_liab_cfs,
                           res_log = html_log)


def format_log():
    html_log = ""
    for entry in udg.log:
        html_log += "<tr><td>" + str(entry[0]) + "</td><td>" + entry[1] + "</td></tr>"
    return html_log

def plot(df_res, xlabel=None, ylabel=None, title=None):
    plt.plot(df_res)
    if xlabel is not None:
        plt.xlabel(xlabel)
    if ylabel is not None:
        plt.ylabel(ylabel)
    if title is not None:
        plt.title(title)
    plt.legend(df_res.columns)
    plt.show()

def run_sensitivities(output_variables, stress_variable, stress_vals, ann_dataset, ltm_dataset, bond_dataset, irs_dataset):
    res = []
    run_history = pd.read_csv('outputs/run_history.csv')
    for s in stress_vals:
        udg.log.append((dt.now(), f'Running for {friendly_names[stress_variable]} = {s}...'))
        c = {stress_variable: s}
        r = RunManager(output_variables, ann_dataset, ltm_dataset, bond_dataset, irs_dataset, c)
        s_res = r.results()
        res.append(s_res)
        #pd.DataFrame(s_res.values(), index=s_res.keys(), columns=['Value']).to_csv(f'outputs/run_outputs/{run_uid}_{stress_variable}_{s}.csv')
        #run_history.loc[uuid4()] = [run_uid, udg.model_version, bond_dataset, ltm_dataset, ann_dataset, output_variables, stress_variable, s, 0]
        #print(s, s_res)
    #run_history.to_csv('outputs/run_history.csv')
    return pd.DataFrame(res, index=stress_vals), r.arg_reqs[stress_variable]['FriendlyName']

def run_cfs(bond_dataset, erm_dataset, ann_dataset):

    df_anns = pd.read_csv(f'inputs/ann_data_inputs/{ann_dataset}')

    mdl_ir = InterestRate(udg.default_ir_curve)
    mdl_mortality = Mortality()

    if bond_dataset is not None:
        df_bonds = pd.read_csv(f'inputs/bond_data_inputs/{bond_dataset}', index_col='ISIN')
        mdl_bonds = BondPortfolio(mdl_ir, df_bonds)
        bond_cfs = mdl_bonds.def_adj_bond_pcfs(aggregate=True).loc[1:60].to_list()
    else:
        bond_cfs = 0
    if erm_dataset is not None:
        df_erms = pd.read_csv(f'inputs/ltm_data_inputs/{erm_dataset}', index_col='PolicyID')
        mdl_erms = ERM(mdl_mortality, mdl_ir, df_erms, 0.03, 0.13)
        erm_cfs = mdl_erms.expected_redemption_cfs_net_of_int_nneg(aggregate=True).loc[1:60].to_list()
    else:
        erm_cfs = 0

    mdl_anns = Annuity(mdl_ir, df_anns)
    liab_cfs = mdl_anns.expected_cfs(aggregate=True).loc[1:60].to_list()

    """
    bond_cfs.to_csv(f'outputs/run_outputs/{run_uid}_bond_cfs.csv')
    erm_cfs.to_csv(f'outputs/run_outputs/{run_uid}_erm_cfs.csv')
    liab_cfs.to_csv(f'outputs/run_outputs/{run_uid}_liab_cfs.csv')
    """

    return bond_cfs, erm_cfs, liab_cfs

def create_ann_dataset():

    ann_value = float(request.args.get('ann_portfolio_value', 100000000))

    ann_age_mean = float(request.args.get('ann_age_mean', 70))
    ann_age_sd = float(request.args.get('ann_age_sd', 5))
    ann_age_floor = int(request.args.get('ann_age_floor', 0))
    ann_age_data = {'mean': ann_age_mean, 'sd': ann_age_sd, 'floor': ann_age_floor}

    ann_amt_mean = float(request.args.get('ann_amt_mean', 30000))
    ann_amt_sd = float(request.args.get('ann_amt_sd', 10000))
    ann_amt_floor = float(request.args.get('ann_amt_floor', 0))
    ann_amt_data = {'mean': ann_amt_mean, 'sd': ann_amt_sd, 'floor': ann_amt_floor}

    g = Generator()
    policy_data = g.generate_annuities(ann_age_data, ann_amt_data, ann_value)

    return policy_data

def create_erm_dataset():

    erm_value = float(request.args.get('ltm_value', 35000000))

    erm_age_mean = float(request.args.get('erm_age_mean', 70))
    erm_age_sd = float(request.args.get('erm_age_sd', 5))
    erm_age_floor = float(request.args.get('erm_age_floor', 0))
    erm_age_data = {'mean': erm_age_mean, 'sd': erm_age_sd, 'floor': erm_age_floor}

    erm_ltv_mean = float(request.args.get('erm_ltv_mean', 0.5))
    erm_ltv_sd = float(request.args.get('erm_ltv_sd', 0.1))
    erm_ltv_floor = float(request.args.get('erm_ltv_floor', 0.0))
    erm_ltv_data = {'mean': erm_ltv_mean, 'sd': erm_ltv_sd, 'floor': erm_ltv_floor}

    erm_amt_mean = float(request.args.get('erm_amt_mean', 30000))
    erm_amt_sd = float(request.args.get('erm_amt_sd', 10000))
    erm_amt_floor = float(request.args.get('erm_amt_floor', 0))
    erm_amt_data = {'mean': erm_amt_mean, 'sd': erm_amt_sd, 'floor': erm_amt_floor}

    g = Generator()
    policy_data = g.generate_erms(erm_age_data, erm_ltv_data, erm_amt_data, erm_value)
    #age=None, ltv=None, loan_amt=None, portfolio_value=None

    return policy_data


def create_bond_dataset():

    aaa_value = float(request.args.get('bond_aaa_portfolio_val', None))
    aaa_nom_mean = float(request.args.get('bond_aaa_nom_mean', None))
    aaa_nom_sd = float(request.args.get('bond_aaa_nom_sd', None))
    aaa_spread_mean = float(request.args.get('bond_aaa_spread_mean', None))
    aaa_spread_sd = float(request.args.get('bond_aaa_spread_sd', None))
    aaa_mat_mean = float(request.args.get('bond_aaa_mat_mean', None))
    aaa_mat_sd = float(request.args.get('bond_aaa_mat_sd', None))

    aa_value = float(request.args.get('bond_aa_portfolio_val', None))
    aa_nom_mean = float(request.args.get('bond_aa_nom_mean', None))
    aa_nom_sd = float(request.args.get('bond_aa_nom_sd', None))
    aa_spread_mean = float(request.args.get('bond_aa_spread_mean', None))
    aa_spread_sd = float(request.args.get('bond_aa_spread_sd', None))
    aa_mat_mean = float(request.args.get('bond_aa_mat_mean', None))
    aa_mat_sd = float(request.args.get('bond_aa_mat_sd', None))

    a_value = float(request.args.get('bond_a_portfolio_val', None))
    a_nom_mean = float(request.args.get('bond_a_nom_mean', None))
    a_nom_sd = float(request.args.get('bond_a_nom_sd', None))
    a_spread_mean = float(request.args.get('bond_a_spread_mean', None))
    a_spread_sd = float(request.args.get('bond_a_spread_sd', None))
    a_mat_mean = float(request.args.get('bond_a_mat_mean', None))
    a_mat_sd = float(request.args.get('bond_a_mat_sd', None))

    bbb_value = float(request.args.get('bond_bbb_portfolio_val', None))
    bbb_nom_mean = float(request.args.get('bond_bbb_nom_mean', None))
    bbb_nom_sd = float(request.args.get('bond_bbb_nom_sd', None))
    bbb_spread_mean = float(request.args.get('bond_bbb_spread_mean', None))
    bbb_spread_sd = float(request.args.get('bond_bbb_spread_sd', None))
    bbb_mat_mean = float(request.args.get('bond_bbb_mat_mean', None))
    bbb_mat_sd = float(request.args.get('bond_bbb_mat_sd', None))

    aaa_data = {'total_val': aaa_value, 'nom_mean': aaa_nom_mean, 'nom_sd': aaa_nom_sd, 'spread_mean': aaa_spread_mean,
                'spread_sd': aaa_spread_sd, 'maturity_mean': aaa_mat_mean, 'maturity_sd': aaa_mat_sd}
    aa_data = {'total_val': aa_value, 'nom_mean': aa_nom_mean, 'nom_sd': aa_nom_sd, 'spread_mean': aa_spread_mean,
               'spread_sd': aa_spread_sd, 'maturity_mean': aa_mat_mean, 'maturity_sd': aa_mat_sd}
    a_data = {'total_val': a_value, 'nom_mean': a_nom_mean, 'nom_sd': a_nom_sd, 'spread_mean': a_spread_mean,
              'spread_sd': a_spread_sd, 'maturity_mean': a_mat_mean, 'maturity_sd': a_mat_sd}
    bbb_data = {'total_val': bbb_value, 'nom_mean': bbb_nom_mean, 'nom_sd': bbb_nom_sd, 'spread_mean': bbb_spread_mean,
                'spread_sd': bbb_spread_sd, 'maturity_mean': bbb_mat_mean, 'maturity_sd': bbb_mat_sd}

    g = Generator()
    bond_data = g.generate_bonds(aaa_data, aa_data, a_data, bbb_data)

    return bond_data


if __name__ == '__main__':

    app.run(host="127.0.0.1", port=8080, debug=True)
    """
    ovs = [Var.portfolio_ma_spread]
    results = run_sensitivities(ovs, 'liab_val_stress', [-0.5, 0.0, 0.5])
    plot(results, 'Liab Scalar (%)', 'Value')
    
    80 secs
    """

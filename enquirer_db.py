from MACalc import MatchingAdjustment
from InterestRates import InterestRate
from Bonds import BondPortfolio
from ERM import ERM
from Annuity import Annuity
from Mortality import Mortality
from Assets import Portfolio
from Liabilities import Liabilities
from BalanceSheet import BalanceSheet
from PolicyDataGenerator import Generator

from matplotlib import pyplot as plt
import pandas as pd


class Var:
    ltm_econ_val = {'Desc': 'LTM Economic Value', 'Mdl': 'MatchingAdjustment', 'Mthd': 'ltm_economic_value'}
    ltm_eff_val = {'Desc': 'LTM Effective Value', 'Mdl': 'MatchingAdjustment', 'Mthd': 'ltm_effective_value'}
    sii_eof = {'Desc': 'SII Excess Own Funds', 'Mdl': 'BalanceSheet', 'Mthd': 'sii_eof'}
    sii_scr = {'Desc': 'SCR', 'Mdl': 'BalanceSheet', 'Mthd': 'sii_scr'}
    int_scr = {'Desc': 'IR SCR', 'Mdl': 'BalanceSheet', 'Mthd': 'int_scr'}
    mort_scr = {'Desc': 'Mortality SCR', 'Mdl': 'BalanceSheet', 'Mthd': 'mort_scr'}
    ifrs_net_equity = {'Desc': 'IFRS Net Equity', 'Mdl': 'BalanceSheet', 'Mthd': 'ifrs_net_equity'}
    ma_benefit = {'Desc': 'MA Benefit', 'Mdl': 'MatchingAdjustment', 'Mthd': 'ma_benefit'}
    bond_ma_benefit = {'Desc': 'Bond MA Benefit', 'Mdl': 'MatchingAdjustment', 'Mthd': 'bond_ma_benefit'}
    ltm_ma_benefit = {'Desc': 'LTM MA Benefit', 'Mdl': 'MatchingAdjustment', 'Mthd': 'ltm_ma_benefit'}
    bond_mp = {'Desc': 'Bond Matching Premium', 'Mdl': 'MatchingAdjustment', 'Mthd': 'bond_ma_spread'}
    portfolio_ma_spread = {'Desc': 'Portfilio Matching Premium', 'Mdl': 'MatchingAdjustment', 'Mthd': 'portfolio_ma_spread'}
    asset_value = {'Desc': 'Asset Value', 'Mdl': 'Portfolio', 'Mthd': 'value'}
    liability_value = {'Desc': 'IFRS Liability Value', 'Mdl': 'Liabilities', 'Mthd': 'best_est_value'}


class RunManager:
    def __init__(self, output_variables, dict_consts=None):

        self.output_variables = output_variables

        self.arg_reqs = {'curve_name': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Spot Curve'},
                         'ir_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Spot Rate Stress'},
                         'lapse_rate': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Lapse Rate'},
                         'bond_val_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Bond Value Stress'},
                         'liab_val_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Liability Value Stress'},
                         'mortality_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Mortality Stress'},
                         'df_bond_portfolio': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Bond Portfolio'},
                         'policy_data': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Annuity Backbook'},
                         'df_ltm_pols': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'LTM Portfolio'},
                         'hpi_drift': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'HPI Drift'},
                         'hpi_vol': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'HPI Volatility'},
                         'prop_shock': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Property Shock'},
                         'InterestRate': {'Reqs': ['curve_name', 'ir_stress'], 'Lvl': 1, 'FriendlyName': 'Interest Rate Model'},
                         'Mortality': {'Reqs': ['lapse_rate', 'mortality_stress'], 'Lvl': 1, 'FriendlyName': 'Mortality Model'},
                         'BondPortfolio': {'Reqs': ['InterestRate', 'df_bond_portfolio', 'bond_val_stress'], 'Lvl': 2, 'FriendlyName': 'Bond Model'},
                         'Annuity': {'Reqs': ['InterestRate', 'policy_data'], 'Lvl': 2, 'FriendlyName': 'Annuity Model'},
                         'ERM': {'Reqs': ['Mortality', 'InterestRate', 'df_ltm_pols', 'hpi_drift', 'hpi_vol', 'prop_shock'], 'Lvl': 2, 'FriendlyName': 'LTM Model'},
                         'MatchingAdjustment': {'Reqs': ['InterestRate', 'ERM', 'BondPortfolio', 'Annuity'], 'Lvl': 3, 'FriendlyName': 'MA Model'},
                         'Portfolio': {'Reqs': ['InterestRate', 'Mortality', 'BondPortfolio', 'ERM', 'hpi_drift', 'cash_held'], 'Lvl': 3, 'FriendlyName': 'Bond Portfolio'},
                         'Liabilities': {'Reqs': ['InterestRate', 'Mortality', 'Annuity', 'annuity_margin'], 'Lvl': 3, 'FriendlyName': 'Liability Model'},
                         'BalanceSheet': {'Reqs': ['Portfolio', 'Liabilities', 'MatchingAdjustment'], 'Lvl': 4, 'FriendlyName': 'Balance Sheet'}}

        self.arg_inst_names = {'curve_name': 'curve_name',
                               'ir_stress': 'ir_stress',
                               'lapse_rate': 'lapse_rate',
                               'mortality_stress': 'mortality_stress',
                               'bond_val_stress': 'bond_val_stress',
                               'liab_val_stress': 'liab_val_stress',
                               'df_bond_portfolio': 'df_bond_portfolio',
                               'policy_data': 'policy_data',
                               'df_ltm_pols': 'df_ltm_pols',
                               'hpi_drift': 'hpi_drift',
                               'hpi_vol': 'hpi_vol',
                               'prop_shock': 'prop_shock',
                               'annuity_margin': 'annuity_margin',
                               'cash_held': 'cash_held',
                               'InterestRate': 'int_rate_model',
                               'Mortality': 'mortality_model',
                               'BondPortfolio': 'bond_model',
                               'Annuity': 'annuity_model',
                               'ERM': 'ltm_model',
                               'MatchingAdjustment': 'ma_model',
                               'Portfolio': 'asset_model',
                               'Liabilities': 'liability_model',
                               'BalanceSheet': 'bs_model'}

        df_ltm_pols = pd.read_csv('inputs/ltm_data_inputs/ltm_data.csv')
        df_ltm_pols['Spread'] = 0.0
        self.args = {'curve_name': 'flat_spot_4pc',
                     'ir_stress': None,
                     'df_bond_portfolio': pd.read_csv('inputs/bond_data_inputs/bond_data.csv'),
                     'bond_val_stress': 0.0,
                     'liab_val_stress': 0.0,
                     'policy_data': pd.read_csv('inputs/ann_data_inputs/game_ann_data.csv'),
                     'df_ltm_pols': df_ltm_pols,
                     'lapse_rate': None,
                     'mortality_stress': None,
                     'hpi_drift': 0.03,
                     'hpi_vol': 0.13,
                     'prop_shock': 0.0,
                     'annuity_margin': 0.0,
                     'cash_held': 0}

        if dict_consts is not None:
            for k in self.args:
                if k in dict_consts:
                    self.args[k] = dict_consts[k]

        for output_var in output_variables:
            req_model = output_var['Mdl']
            self.__initialise_model(req_model)
            mdl_class = globals()[req_model]
            mdl_args = {self.arg_inst_names[k]: self.args[self.arg_inst_names[k]] for k in
                        self.arg_reqs[req_model]['Reqs']}
            self.args[self.arg_inst_names[req_model]] = mdl_class(**mdl_args)

    def results(self):
        res = {}
        for output_var in self.output_variables:
            res[output_var["Desc"]] = getattr(self.args[self.arg_inst_names[output_var['Mdl']]], output_var["Mthd"])()
        return res

    def __initialise_model(self, model_name):
        for req_model in self.arg_reqs[model_name]['Reqs']:
            if self.arg_inst_names[req_model] not in self.args and self.arg_reqs[req_model]['Lvl'] > 0:
                self.__initialise_model(req_model)
                mdl_class = globals()[req_model]
                mdl_args = {self.arg_inst_names[k]: self.args[self.arg_inst_names[k]] for k in self.arg_reqs[req_model]['Reqs']}
                self.args[self.arg_inst_names[req_model]] = mdl_class(**mdl_args)


if __name__ == '__main__':



    ovs = [Var.liability_value]

    c = {'ir_stress': 0.0}

    r = RunManager(ovs, c)
    res = r.results()

    c = {'ir_stress': 0.0001}

    r = RunManager(ovs, c)

    res_s = r.results()
    print(res_s)
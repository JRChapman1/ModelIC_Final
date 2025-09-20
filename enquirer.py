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

from globals import UserDefinedGlobals as udg

from matplotlib import pyplot as plt
import pandas as pd
from uuid import uuid4


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
    mp = {'Desc': 'Matching Premium', 'Mdl': 'MatchingAdjustment', 'Mthd': 'portfolio_ma_spread'}
    portfolio_ma_spread = {'Desc': 'Portfilio Matching Premium', 'Mdl': 'MatchingAdjustment', 'Mthd': 'portfolio_ma_spread'}
    asset_value = {'Desc': 'Asset Value', 'Mdl': 'Portfolio', 'Mthd': 'value'}
    liability_value = {'Desc': 'IFRS Liability Value', 'Mdl': 'Liabilities', 'Mthd': 'best_est_value'}
    bond_value = {'Desc': 'Bond Value', 'Mdl': 'BondPortfolio', 'Mthd': 'market_value'}
    ifrs_vir_adjustment = {'Desc': 'VIR Adjustment (£)', 'Mdl': 'BalanceSheet', 'Mthd': 'ifrs_vir_adjustment'}
    ifrs_vir = {'Desc': 'VIR Adjustment(%)', 'Mdl': 'BalanceSheet', 'Mthd': 'ifrs_vir'}


class RunManager:

    def __init__(self, output_variables, ann_dataset, ltm_dataset, bond_dataset, irs_dataset, dict_consts=None):

        self.output_variables = output_variables
        self.ann_dataset = ann_dataset
        self.ltm_dataset = ltm_dataset
        self.bond_dataset = bond_dataset
        self.irs_dataset = irs_dataset

        self.arg_reqs = {'curve_name': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Spot Curve', 'ExclConditions': []},
                         'ir_shock': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Spot Rate Shock', 'ExclConditions': []},
                         'ir_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Spot Rate Stress', 'ExclConditions': []},
                         'lapse_rate': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Lapse Rate', 'ExclConditions': []},
                         'bond_val_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Bond Value Stress', 'ExclConditions': []},
                         'liab_val_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Liability Value Stress', 'ExclConditions': []},
                         'mortality_stress': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Mortality Stress', 'ExclConditions': []},
                         'mortality_scalar': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Mortality Scalar', 'ExclConditions': []},
                         'df_bond_portfolio': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Bond Portfolio', 'ExclConditions': []},
                         'policy_data': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Annuity Backbook', 'ExclConditions': []},
                         'df_ltm_pols': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'LTM Portfolio', 'ExclConditions': []},
                         'hpi_drift': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'HPI Drift', 'ExclConditions': []},
                         'hpi_vol': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'HPI Volatility', 'ExclConditions': []},
                         'prop_shock': {'Reqs': [], 'Lvl': 0, 'FriendlyName': 'Property Shock', 'ExclConditions': []},
                         'InterestRate': {'Reqs': ['curve_name', 'ir_stress', 'ir_shock'], 'Lvl': 1, 'FriendlyName': 'Interest Rate Model', 'ExclConditions': []},
                         'Mortality': {'Reqs': ['lapse_rate', 'mortality_stress', 'mortality_scalar'], 'Lvl': 1, 'FriendlyName': 'Mortality Model', 'ExclConditions': []},
                         'BondPortfolio': {'Reqs': ['InterestRate', 'df_bond_portfolio', 'bond_val_stress'], 'Lvl': 2, 'FriendlyName': 'Bond Model', 'ExclConditions': ['df_bond_portfolio']},
                         'Annuity': {'Reqs': ['InterestRate', 'policy_data'], 'Lvl': 2, 'FriendlyName': 'Annuity Model', 'ExclConditions': []},
                         'ERM': {'Reqs': ['Mortality', 'InterestRate', 'df_ltm_pols', 'hpi_drift', 'hpi_vol', 'prop_shock'], 'Lvl': 2, 'FriendlyName': 'LTM Model', 'ExclConditions': ['df_ltm_pols']},
                         'IRS': {'Reqs': ['InterestRate', 'df_irs_portfolio'], 'Lvl': 2, 'FriendlyName': 'IRS Model', 'ExclConditions': ['df_irs_portfolio']},
                         'MatchingAdjustment': {'Reqs': ['InterestRate', 'ERM', 'BondPortfolio', 'Annuity'], 'Lvl': 3, 'FriendlyName': 'MA Model', 'ExclConditions': []},
                         'Portfolio': {'Reqs': ['InterestRate', 'Mortality', 'BondPortfolio', 'ERM', 'hpi_drift', 'cash_held'], 'Lvl': 3, 'FriendlyName': 'Bond Portfolio', 'ExclConditions': []},
                         'Liabilities': {'Reqs': ['InterestRate', 'Mortality', 'Annuity', 'annuity_margin'], 'Lvl': 3, 'FriendlyName': 'Liability Model', 'ExclConditions': []},
                         'BalanceSheet': {'Reqs': ['Portfolio', 'Liabilities', 'MatchingAdjustment'], 'Lvl': 4, 'FriendlyName': 'Balance Sheet', 'ExclConditions': []}}

        self.arg_inst_names = {'curve_name': 'curve_name',
                               'ir_stress': 'ir_stress',
                               'ir_shock': 'ir_shock',
                               'lapse_rate': 'lapse_rate',
                               'mortality_stress': 'mortality_stress',
                               'mortality_scalar': 'mortality_scalar',
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
                               'IRS': 'irs_model',
                               'MatchingAdjustment': 'ma_model',
                               'Portfolio': 'asset_model',
                               'Liabilities': 'liability_model',
                               'BalanceSheet': 'bs_model'}

        self.exclusion_rules = {}

        df_ann_pols = pd.read_csv(f'inputs/ann_data_inputs/{ann_dataset}')

        if ltm_dataset is not None:
            df_ltm_pols = pd.read_csv(f'inputs/ltm_data_inputs/{ltm_dataset}', index_col='PolicyID')
            df_ltm_pols['Spread'] = 0.0
        else:
            df_ltm_pols = None

        if bond_dataset is not None:
            df_bond_portfolio = pd.read_csv(f'inputs/bond_data_inputs/{bond_dataset}', index_col='ISIN')
        else:
            df_bond_portfolio = None

        if irs_dataset is not None:
            df_irs_portfolio = pd.read_csv(f'inputs/irs_data_inputs/{irs_dataset}')
        else:
            df_irs_portfolio = None

        self.args = {'curve_name': udg.default_ir_curve,
                     'ir_stress': None,
                     'ir_shock': 0.0,
                     'df_bond_portfolio': df_bond_portfolio,
                     'bond_val_stress': 0.0,
                     'liab_val_stress': 0.0,
                     'policy_data': df_ann_pols,
                     'df_ltm_pols': df_ltm_pols,
                     'df_irs_portfolio': df_irs_portfolio,
                     'lapse_rate': 0.0,
                     'mortality_stress': None,
                     'mortality_scalar': 1.0,
                     'hpi_drift': 0.03,
                     'hpi_vol': 0.13,
                     'prop_shock': 0.0,
                     'annuity_margin': 0.0,
                     'cash_held': 0}

        if dict_consts is not None:
            for k in self.args:
                if k in dict_consts:
                    self.stress_var = k
                    self.stress_val = dict_consts[k]
                    self.args[k] = dict_consts[k]
        else:
            self.stress_var = None
            self.stress_val = None

        for output_var in output_variables:
            req_model = output_var['Mdl']
            self.__initialise_model(req_model)
            mdl_class = globals()[req_model]
            mdl_args = {self.arg_inst_names[k]: self.args[self.arg_inst_names[k]] for k in
                        self.arg_reqs[req_model]['Reqs']}

            self.args[self.arg_inst_names[req_model]] = mdl_class(**mdl_args)

    def results(self):
        res = {}

        run_history = pd.read_csv('outputs/run_history_c2.csv', index_col='RunUID')

        for output_var in self.output_variables:
            run_history_filtered = run_history.loc[
                (run_history['ModelVersion'] == udg.model_version)
                & (run_history['BondDataFile'] == self.bond_dataset)
                & (run_history['ERMDataFile'] == self.ltm_dataset)
                & (run_history['LiabDataFile'] == self.ann_dataset)
                & (run_history['OutputVariable'] == str(output_var))
                & (run_history['StressVariable'] == self.stress_var)
                & (run_history['StressValue'] == self.stress_val)
                & (run_history['UserID'] == 0)
                ]
            # TODO: Inequality reversed to disable use of run history
            if len(run_history_filtered) < 0:
                s_res = float(run_history_filtered['Result'])
            else:
                s_res = getattr(self.args[self.arg_inst_names[output_var['Mdl']]], output_var["Mthd"])()
                run_history.loc[uuid4()] = [udg.model_version, self.bond_dataset, self.ltm_dataset, self.ann_dataset, output_var,
                                        self.stress_var, self.stress_val, 0, s_res]

            res[output_var["Desc"]] = s_res

        run_history.to_csv('outputs/run_history_c2.csv')
        return res

    def __initialise_model(self, model_name):
        for req_model in self.arg_reqs[model_name]['Reqs']:
            if self.arg_inst_names[req_model] not in self.args and self.arg_reqs[req_model]['Lvl'] > 0:
                self.__initialise_model(req_model)
                mdl_class = globals()[req_model]
                mdl_args = {self.arg_inst_names[k]: self.args[self.arg_inst_names[k]] for k in self.arg_reqs[req_model]['Reqs']}

                incl = True
                mdl_excl_conditions = self.arg_reqs[req_model]['ExclConditions']
                for condition in mdl_excl_conditions:
                    incl &= mdl_args[condition] is not None

                if incl:
                    self.args[self.arg_inst_names[req_model]] = mdl_class(**mdl_args)
                else:
                    self.args[self.arg_inst_names[req_model]] = None


if __name__ == '__main__':

    ovs = [Var.asset_value]
    c = {'ir_stress': 0.0}
    r = RunManager(ovs, c)
    res = r.results()

    c = {'ir_stress': 0.0001}

    r = RunManager(ovs, c)

    res_s = r.results()
    print(res_s['Asset Value'])

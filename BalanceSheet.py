import pandas as pd
from math import sqrt

from Assets import Portfolio
from Liabilities import Liabilities
from MACalc import MatchingAdjustment
from InterestRates import InterestRate
from ERM import ERM
from Bonds import BondPortfolio
from Assets import Portfolio
from Mortality import Mortality
from Annuity import Annuity

import numpy as np
from scipy.optimize import minimize_scalar

from globals import UserDefinedGlobals as udg
from datetime import datetime as dt


class BalanceSheet:

    def __init__(self, asset_model, liability_model, ma_model):
        self.mdl_assets = asset_model
        self.mdl_liabilities = liability_model
        self.mdl_ma = ma_model

    def ifrs_net_equity(self):
        udg.log.append((dt.now(), "Calculating IFRS net equity"))
        asset_val = self.mdl_assets.value()
        liab_val = self.mdl_liabilities.best_est_value()
        vir_adj = self.ifrs_vir_adjustment()
        return asset_val + vir_adj - liab_val

    def ifrs(self, output_level=0):

        # TODO: Add tax, sub debt, cap res, reins, derivs, DB
        asset_val = self.mdl_assets.value()
        liab_val = self.mdl_liabilities.best_est_value()
        vir_adj = self.ifrs_vir_adjustment()

        balance_sheet = {'IFRS Net Equity': asset_val + vir_adj - liab_val}

        if output_level >= 1:
            balance_sheet['Assets'] = asset_val

            if output_level >= 2:
                balance_sheet['Bonds'] = self.mdl_assets.BondModel.pvs()
                if self.mdl_assets.EqRelModel is not None:
                    balance_sheet['ERMs'] = self.mdl_assets.EqRelModel.ifrs_value()
                balance_sheet['Cash'] = self.mdl_assets.cash

            balance_sheet['Liabilities'] = liab_val - vir_adj

            if output_level >= 2:
                balance_sheet['Annuities'] = self.mdl_liabilities.AnnuityModel.value(stress='Base')
                balance_sheet['VIR Adjustment'] = -vir_adj

        return balance_sheet

    def sii_of(self):
        udg.log.append((dt.now(), "Calculating SII own funds"))
        sii_liabs = self.mdl_liabilities.AnnuityModel.value('Base')
        ma = self.mdl_ma.ma_benefit()
        asset_val = self.mdl_assets.value()
        return asset_val - (sii_liabs - ma)

    def ifrs_vir(self):
        udg.log.append((dt.now(), "Calculating IFRS valuation interest rate"))
        cfs = self.mdl_liabilities.best_est_cfs()
        cash_req, matched_asset_cfs = self.vir_matching_exercise()
        bond_spreads = self.mdl_assets.BondModel.df_bond_portfolio['Spread']
        erm_spreads = self.mdl_assets.EqRelModel.df_ltm_pols['Spread']
        val = self.mdl_liabilities.InterestRateModel.present_value(matched_asset_cfs, pd.concat([bond_spreads, erm_spreads]))
        return self.__irr(cfs, val)


    def vir_cash_req(self):
        def_adj_bond_cfs = self.mdl_assets.BondModel.def_adj_bond_pcfs(aggregate=True)
        erm_cfs = self.mdl_assets.EqRelModel.expected_redemption_cfs_net_of_int_nneg(aggregate=True)
        asset_cfs = def_adj_bond_cfs + erm_cfs[1:]
        liab_cfs = self.mdl_liabilities.best_est_cfs()
        liab_cfs.index += 1
        mismatch = asset_cfs - liab_cfs
        mismatch = mismatch.fillna(0.0)
        one_step_disc_facs = self.mdl_assets.BondModel.mdl_interest.one_step_disc_facs()
        one_step_disc_facs = one_step_disc_facs.loc[mismatch.index]
        cash_req = min(mismatch.iloc[-1], 0)
        for i in range(2, len(liab_cfs)):
            cash_req *= one_step_disc_facs.iloc[-(i-1), 0]
            cash_req += mismatch.iloc[-i]
            cash_req = min(cash_req, 0)
        return -cash_req


    def vir_matching_exercise(self):
        asset_cfs = self.mdl_assets.ifrs_def_adj_cfs()
        liab_cfs = self.mdl_liabilities.best_est_cfs()
        one_step_disc_facs = self.mdl_liabilities.InterestRateModel.one_step_disc_facs()
        matched_assets = pd.DataFrame(np.zeros(shape=asset_cfs.shape), index=asset_cfs.index, columns=asset_cfs.columns)

        for i in range(len(liab_cfs)-1, 0, -1):
            udg.log.append((dt.now(), f'Hypothocating assets at time step {i} for VIR calculation'))
            if i == len(liab_cfs)-1:
                cash_req = liab_cfs.iloc[i]
            else:
                cash_req *= one_step_disc_facs.iloc[i+1, 0]
                cash_req += liab_cfs.iloc[i]
            if cash_req > 0:
                for isin in asset_cfs.columns:
                    if matched_assets.iloc[i].sum() + asset_cfs.loc[i, isin] <= cash_req:
                        matched_assets.loc[i, isin] = asset_cfs.loc[i, isin]
                    else:
                        matched_assets.loc[i, isin] = max(cash_req - matched_assets.iloc[i].sum(), 0)
                cash_req = max(cash_req - matched_assets.iloc[i].sum(), 0)
            print(i, cash_req)
        cash_req *= one_step_disc_facs.iloc[1, 0]

        return cash_req, matched_assets

    def ifrs_vir_adjustment(self):
        udg.log.append((dt.now(), "Calculating IFRS VIR adjustment"))
        vir = self.ifrs_vir()
        liab_cfs = self.mdl_liabilities.best_est_cfs()
        ifrs_liab_val = self.mdl_liabilities.best_est_value()
        return ifrs_liab_val - (liab_cfs * (1 + vir) ** -liab_cfs.index).sum()

    def sii_scr(self):
        udg.log.append((dt.now(), "Calculating SII SCR"))
        mort_scr = self.mort_scr()
        int_scr = self.int_scr()
        bscr = sqrt(mort_scr ** 2 + int_scr ** 2 + 0.25 * mort_scr * int_scr)
        return bscr

    def mort_scr(self):
        base = self.mdl_liabilities.AnnuityModel.value()
        mort_scr = self.mdl_liabilities.AnnuityModel.value('Mortality') - base
        return mort_scr

    def int_scr(self):
        base = self.mdl_liabilities.AnnuityModel.value()
        int_up_scr = self.mdl_liabilities.AnnuityModel.value('Interest_Up') - base
        int_down_scr = self.mdl_liabilities.AnnuityModel.value('Interest_Down') - base
        int_scr = max(int_up_scr, int_down_scr)
        return int_scr

    def sii_nhscr(self):
        udg.log.append((dt.now(), "Calculating SII NHSCR"))
        base = self.mdl_liabilities.AnnuityModel.value()
        mort_scr = self.mdl_liabilities.AnnuityModel.value('Mortality') - base
        int_scr = self.mdl_liabilities.AnnuityModel.value('Interest') - base
        bscr = sqrt(mort_scr ** 2 + int_scr ** 2 + 0.25 * mort_scr * int_scr)
        return bscr

    def sii_rm(self):
        udg.log.append((dt.now(), "Calculating SII risk margin"))
        nhscr = self.sii_nhscr()
        bel_runoff = self.mdl_liabilities.bel_runoff()
        run_off_capital =  pd.DataFrame((bel_runoff / bel_runoff[0]) * nhscr * 0.06)
        run_off_capital.index += 1
        return self.mdl_liabilities.InterestRateModel.present_value(run_off_capital)

    def sii_eof(self):
        udg.log.append((dt.now(), "Calculating SII excess own funds"))
        return self.sii_of() - self.sii_scr()

    def sii(self, output_level=0):

        # TODO: Add tax, sub debt, cap res, reins, derivs, DB, CSM, NMAP Portfolio, MAP Allocations (to show impact on
        #  matching tests), and liquidity analysis

        sii_liabs = self.mdl_liabilities.AnnuityModel.value('Base')
        bond_mp = self.mdl_ma.bond_ma_benefit()
        ltm_mp = self.mdl_ma.ltm_ma_benefit()
        asset_val = self.mdl_assets.value()
        bscr = self.sii_scr()
        rm = self.sii_rm()
        balance_sheet = {}

        balance_sheet['SII OF'] = asset_val - (sii_liabs + rm - (bond_mp + ltm_mp))
        balance_sheet['BSCR'] = bscr
        balance_sheet['SII EOF'] = asset_val - (sii_liabs - (bond_mp + ltm_mp)) - bscr

        if output_level >= 1:
            balance_sheet['Assets'] = asset_val

            if output_level >= 2:
                balance_sheet['Bonds'] = self.mdl_assets.BondModel.pvs()
                if self.mdl_assets.EqRelModel is not None:
                    balance_sheet['ERMs'] = self.mdl_assets.EqRelModel.ifrs_value()
                balance_sheet['Cash'] = self.mdl_assets.cash

            balance_sheet['Liabilities'] = sii_liabs + rm - (bond_mp + ltm_mp)
            if output_level >= 2:
                balance_sheet['Annuities'] = self.mdl_liabilities.AnnuityModel.value()
                balance_sheet['Risk Margin'] = rm
                balance_sheet['Matching Adjustment'] = -(bond_mp + ltm_mp)
                if output_level >= 3:
                    balance_sheet['Bond MA'] = -bond_mp
                    balance_sheet['LTM MA'] = -ltm_mp

        return balance_sheet

    def __irr(self, cfs, val):
        def calc_val(spread):
            return ((cfs * (1 + spread) ** -cfs.index).sum() - val) ** 2

        return minimize_scalar(calc_val).x

def print_balance_sheet(bs_dict):
    for k, v in bs_dict.items():
        print('\t' * IC.output_levels[k], k, '\t' * (8 - IC.output_levels[k] - (len(k) - 2) // 4), ' ' * int(v >= 0), f'{round(v):,}')
    print('\n' * 5)


if __name__ == '__main__':

    mdl_ir = InterestRate('example_ir.csv')
    mdl_mortality = Mortality()

    df_bonds = pd.read_csv('inputs/bond_data_inputs/example_bonds.csv', index_col=['ISIN'])
    mdl_bonds = BondPortfolio(mdl_ir, df_bonds)

    ltm_pols = pd.read_csv('inputs/ltm_data_inputs/example_erms.csv', index_col=['PolicyID'])
    mdl_erm = ERM(mdl_mortality, mdl_ir, ltm_pols, 0.018, 0.13)

    mdl_assets = Portfolio(mdl_ir, mdl_mortality, mdl_bonds, mdl_erm)

    ann_data = pd.read_csv(r'inputs/ann_data_inputs/example_ann.csv')
    ann_data['Age'] = np.maximum(ann_data['Age'], 65)
    mdl_ann = Annuity(InterestRate('example_ir.csv'), ann_data)

    mdl_liab = Liabilities(mdl_ir, mdl_mortality, mdl_ann)

    MdlMA = MatchingAdjustment(mdl_ir, mdl_assets.EqRelModel, mdl_assets.BondModel, mdl_liab.AnnuityModel)

    IC = BalanceSheet(mdl_assets, mdl_liab, MdlMA)

    ifrs_bs = IC.ifrs(output_level=3)
    sii_bs = IC.sii(output_level=3)

    print_balance_sheet(ifrs_bs)
    print('-' * 30)
    print_balance_sheet(sii_bs)

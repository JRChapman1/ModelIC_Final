import matplotlib.pyplot as plt
import pandas as pd
from InterestRates import InterestRate
from LTMNote import LTMNote
from ERM import ERM
from scipy import optimize
from Bonds import BondPortfolio
from Annuity import Annuity
from Mortality import Mortality

import warnings
warnings.filterwarnings("ignore")


class MatchingAdjustment:

    def __init__(self, int_rate_model, ltm_model, bond_model, annuity_model):

        # Instantiate interest rate model and store as attribute
        self.mdl_interest = int_rate_model

        # Add EIOPA inputs as attributes
        self.eiopa_recovery_rate = 0.3
        self.eiopa_pd = pd.read_csv('inputs/eiopa_pd.csv', index_col='Year')
        self.eiopa_fs = pd.read_csv('inputs/eiopa_fs.csv', index_col='Year') / 100
        self.ltm_model = ltm_model
        self.bond_model = bond_model
        self.annuity_model = annuity_model

        if ltm_model is not None:
            # Use inputted models to store LTM note PCFs, LTM IFRS value, bond PCFs, and BE annuity CFs as attributes
            self.ltm_note_model = LTMNote(self.ltm_model, int_rate_model)
            self.ltm_note_pcfs = self.ltm_note_model.note_pcfs()
            self.ltm_ifrs_val = self.ltm_model.ifrs_value()
        else:
            self.ltm_note_model = None

        if bond_model is not None:
            self.bond_pcfs = self.bond_model.bond_pcfs()
        self.annuity_cfs = annuity_model.expected_cfs()

    def ltm_note_eiopa_pd_adj_pcfs(self):

        # Multiply PCFs for each LTM note by EIOPA PD scalars
        pd_adj = self.ltm_note_pcfs[['AAA', 'AA', 'A', 'BBB', 'BB']] * self.eiopa_pd.loc[:self.ltm_note_pcfs.shape[0], ['AAA', 'AA', 'A', 'BBB', 'BB']] * 0.7

        # Subtract EIOPA PD adjustment from each PCFs for each LTM note and sum over all notes to get gross PD adjusted
        # LTM note CFs
        pd_adj_pcfs = self.ltm_note_pcfs[['AAA', 'AA', 'A', 'BBB', 'BB']] - pd_adj
        return pd_adj_pcfs.sum(axis=1)

    def bond_eiopa_pd_adj_pcfs(self):
        lst_bond_ratings = self.bond_model.df_bond_portfolio['Rating'].to_list()
        df_eiopa_pd = self.eiopa_pd.loc[:self.bond_pcfs.shape[0], lst_bond_ratings]
        df_eiopa_pd.columns = self.bond_pcfs.columns
        pd_adj = self.bond_pcfs * df_eiopa_pd * 0.7
        pd_adj_pcfs = self.bond_pcfs - pd_adj
        return pd_adj_pcfs.sum(axis=1)

    def ltm_note_eiopa_fs_adj_pcfs(self):
        fs_adj = self.ltm_note_pcfs[['AAA', 'AA', 'A', 'BBB', 'BB']] * self.eiopa_fs.loc[:self.ltm_note_pcfs.shape[0], ['AAA', 'AA', 'A', 'BBB', 'BB']]
        fs_adj_pcfs = self.ltm_note_pcfs[['AAA', 'AA', 'A', 'BBB', 'BB']] - fs_adj
        return fs_adj_pcfs.sum(axis=1)

    def bond_eiopa_fs_adj_pcfs(self):
        lst_bond_ratings = self.bond_model.df_bond_portfolio['Rating'].to_list()
        df_eiopa_fs = self.eiopa_fs.loc[:self.bond_pcfs.shape[0], lst_bond_ratings]
        df_eiopa_fs.columns = self.bond_pcfs.columns
        fs_adj = self.bond_pcfs * df_eiopa_fs * 0.7
        fs_adj_pcfs = self.bond_pcfs - fs_adj
        return fs_adj_pcfs.sum(axis=1)

    """
    def ltm_gry(self):
        cfs = self.ltm_note_eiopa_pd_adj_pcfs()
        val = self.ltm_note_model.note_values()
        val = val.sum() - val['ET']
        return self.xirr(val, cfs)
    """

    def ltm_flat_rfr(self):
        cfs = self.ltm_note_eiopa_pd_adj_pcfs()
        disc_curve = self.mdl_interest.discount_curve().loc[cfs.index, 0]
        val = (cfs * disc_curve).sum()
        return self.xirr(val, cfs)

    def total_pd_adj_ltm_spread(self):
        cfs = self.ltm_note_eiopa_pd_adj_pcfs()
        val = self.ltm_note_model.note_values()
        val = val.sum() - val['ET']
        return self.spread(val, cfs)

    def total_fs_adj_ltm_spread(self):
        cfs = self.ltm_note_eiopa_fs_adj_pcfs()
        val = self.ltm_note_model.note_values()
        val = val.sum() - val['ET']
        return self.spread(val, cfs)

    def total_pd_adj_bond_spread(self):
        cfs = self.bond_eiopa_pd_adj_pcfs()
        val = self.bond_model.pvs()
        return self.spread(val, cfs)

    def total_pd_adj_spread(self):
        # Calculates the spread above risk-free which makes the present value of PD adjusted assets cashflows equal to
        # their (combined) market value
        cfs = self.bond_eiopa_pd_adj_pcfs() + self.ltm_note_eiopa_pd_adj_pcfs()
        val = self.ltm_note_model.note_values()
        val = val.sum() - val['ET']
        val += self.bond_model.pvs()
        return self.spread(val, cfs)

    def total_fs_adj_spread(self):
        # Calculates the spread above risk-free which makes the present value of FS adjusted assets cashflows equal to
        # their (combined) market value
        cfs = self.ltm_note_eiopa_fs_adj_pcfs() + self.bond_eiopa_fs_adj_pcfs()
        val = self.ltm_note_model.note_values()
        val = val.sum() - val['ET']
        val += self.bond_model.pvs()
        return self.spread(val, cfs)

    def total_fs_adj_bond_spread(self):
        cfs = self.bond_eiopa_fs_adj_pcfs()
        val = self.bond_model.pvs()
        return self.spread(val, cfs)

    def ltm_ma_spread(self):
        pd_adj_ltm_spread = self.total_pd_adj_ltm_spread()
        fs_adj_ltm_spread = self.total_fs_adj_ltm_spread()
        return pd_adj_ltm_spread-(fs_adj_ltm_spread-pd_adj_ltm_spread)

    def bond_ma_spread(self):
        pd_adj_bond_spread = self.total_pd_adj_bond_spread()
        fs_adj_bond_spread = self.total_fs_adj_bond_spread()
        return pd_adj_bond_spread-(fs_adj_bond_spread-pd_adj_bond_spread)

    def portfolio_ma_spread(self):
        pd_adj_spread = self.total_pd_adj_spread()
        fs_adj_spread = self.total_fs_adj_spread()
        return pd_adj_spread-(fs_adj_spread-pd_adj_spread)

    def ltm_note_eiopa_pd_adj_pv(self):
        ltm_note_eiopa_pd_adj_pcfs = self.ltm_note_eiopa_pd_adj_pcfs()
        # TODO: Refactor ([1:])
        disc_curve = self.mdl_interest.discount_curve().loc[ltm_note_eiopa_pd_adj_pcfs.index[1:], 0]
        return (ltm_note_eiopa_pd_adj_pcfs * disc_curve).sum()

    def bond_eiopa_pd_adj_pv(self):
        bond_eiopa_pd_adj_pcfs = self.bond_eiopa_pd_adj_pcfs()
        # TODO: Refactor ([1:])
        disc_curve = self.mdl_interest.discount_curve().loc[bond_eiopa_pd_adj_pcfs.index, 0]
        return (bond_eiopa_pd_adj_pcfs * disc_curve).sum()

    def ltm_note_eiopa_ma_adj_pv(self):
        ltm_note_eiopa_pd_adj_pcfs = self.ltm_note_eiopa_pd_adj_pcfs()
        ltm_ma_spread = self.ltm_ma_spread()
        # TODO: Refactor ([1:])
        disc_curve = self.mdl_interest.discount_curve(spread=ltm_ma_spread).loc[ltm_note_eiopa_pd_adj_pcfs.index[1:], 0]
        return (ltm_note_eiopa_pd_adj_pcfs * disc_curve).sum()

    def bond_eiopa_ma_adj_pv(self):
        bond_eiopa_pd_adj_pcfs = self.bond_eiopa_pd_adj_pcfs()
        bond_ma_spread = self.bond_ma_spread()
        # TODO: Refactor ([1:])
        disc_curve = self.mdl_interest.discount_curve(spread=bond_ma_spread).loc[bond_eiopa_pd_adj_pcfs.index[1:], 0]
        return (bond_eiopa_pd_adj_pcfs * disc_curve).sum()

    def bond_ma_benefit(self):
        if self.bond_model is None:
            bond_ma = 0
        else:
            bond_ma = self.bond_eiopa_pd_adj_pv() - self.bond_eiopa_ma_adj_pv()
        return bond_ma

    def ltm_ma_benefit(self):
        if self.ltm_model is None:
            ltm_ma = 0
        else:
            ltm_ma = self.ltm_note_eiopa_pd_adj_pv() - self.ltm_note_eiopa_ma_adj_pv()
        return ltm_ma

    def ma_benefit(self):
        return self.bond_ma_benefit() + self.ltm_ma_benefit()

    def ltm_effective_value(self):
        return self.ltm_model.ifrs_value() + self.ltm_ma_benefit()

    def ltm_economic_value(self, deferment_rate=0.0):
        return self.ltm_model.economic_value(deferment_rate=deferment_rate)

    def evt_passed(self):
        return self.ltm_economic_value() >= self.ltm_effective_value()





    def xirr(self, target, cfs):

        def f(x):
            disc_curve = [(1 + x) ** -t for t in cfs.index]
            return abs((cfs * disc_curve).sum() - target)

        return optimize.minimize_scalar(f).x


    def spread(self, target, cfs):

        def f(x):
            # TODO: Refactor ([:1])
            disc_curve = self.mdl_interest.discount_curve(spread=x).loc[cfs.index[1:], 0]
            return abs((cfs * disc_curve).sum() - target)

        return optimize.minimize_scalar(f).x

    def spread_multi(self, targets, cfs, itterations=10):
        spread = pd.Series([0] * targets.shape[0], index=targets.index)
        disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0]]
        disc_curve.index = cfs.index
        duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0).to_numpy()).sum() / (cfs * disc_curve.to_numpy()).sum()
        for i in range(1, itterations):
            disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0]]
            spread -= (targets / (cfs * disc_curve.to_numpy()).sum() - 1) / duration
            disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0]]
            duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0).to_numpy()).sum() / (cfs * disc_curve).sum()
        return spread

    # TODO: Currently assuming that all assets and liabs in Comp A. Need to code for comp B and C, allowing also for the
    #  fact that the cost of downgrades should be accounted for as a comp B liability

    # Accumulated shortfall test
    def matching_test_1(self):

        # TODO: Remove fillna() workaroud
        pd_adj_assets_cfs = (self.bond_eiopa_pd_adj_pcfs() + self.ltm_note_eiopa_pd_adj_pcfs()).fillna(0.0)
        liab_cfs = self.annuity_cfs.sum(axis=1).fillna(0.0)
        deficit = (liab_cfs - pd_adj_assets_cfs).fillna(0.0)
        # TODO: Remove hardcoded day 1 cash
        acc_deficit = [deficit[0] - 110000000]
        for d in deficit[1:]:
            # TODO: Remove interest rate hardcoding
            acc_deficit.append(acc_deficit[-1] * 1.04 + d)
        liab_val = self.annuity_model.value()
        #print([d / liab_val for d in acc_deficit])
        #return [d / liab_val for d in acc_deficit]
        return max([d / liab_val for d in acc_deficit]) < 0.03

    # Value-at-risk test
    def matching_test_2(self):

        bond_eiopa_pd_adj_pcfs = self.bond_eiopa_pd_adj_pcfs()
        ltm_note_eiopa_pd_adj_pcfs = self.ltm_note_eiopa_pd_adj_pcfs()

        # BaseIR = InterestRate(self.int_rate_curve, None)
        # StressIR = InterestRate(self.int_rate_curve, 'SII')

        disc_curve = self.mdl_interest.discount_curve().loc[bond_eiopa_pd_adj_pcfs.index[1:], 0]
        disc_curve_up = self.mdl_interest.discount_curve(spread=0.04).loc[bond_eiopa_pd_adj_pcfs.index[1:], 0]
        disc_curve_dwn = self.mdl_interest.discount_curve(spread=-0.04).loc[bond_eiopa_pd_adj_pcfs.index[1:], 0]

        asset_base_val = (bond_eiopa_pd_adj_pcfs * disc_curve).sum() + (ltm_note_eiopa_pd_adj_pcfs * disc_curve).sum()
        asset_stressed_up_val = (bond_eiopa_pd_adj_pcfs * disc_curve_up).sum() + (ltm_note_eiopa_pd_adj_pcfs * disc_curve_up).sum()
        asset_stressed_dwn_val = (bond_eiopa_pd_adj_pcfs * disc_curve_dwn).sum() + (ltm_note_eiopa_pd_adj_pcfs * disc_curve_dwn).sum()

        liab_base_val = self.annuity_model.value()
        liab_stressed_up_val = self.annuity_model.value(ir_shock=0.04)
        liab_stressed_dwn_val = self.annuity_model.value(ir_shock=-0.04)

        var = min((asset_stressed_up_val - liab_stressed_up_val) - (asset_base_val - liab_base_val), (asset_stressed_dwn_val - liab_stressed_dwn_val) - (asset_base_val - liab_base_val))

        return -var / liab_base_val


if __name__ == '__main__':

    stress = [-0.5, 0, 0.5]
    res = []
    res2 = []

    mdl_ir = InterestRate('flat_spot_4pc')

    df_bonds = pd.read_csv('inputs/bond_data_inputs/bond_data.csv')
    mdl_bonds = BondPortfolio(mdl_ir, df_bonds)

    mdl_ir = InterestRate('flat_spot_4pc')
    ltm_pols = pd.read_csv('inputs/ltm_data_inputs/ltm_data.csv')

    # mortality_model, int_rate_model, df_ltm_pols, hpi_drift, hpi_vol, prop_shock = None
    MdlEqRel = ERM(Mortality(), mdl_ir, ltm_pols, 0.018, 0.13)


    for s in stress:
        ann_data = pd.read_csv(r'inputs/ann_data_inputs/game_ann_data.csv')
        ann = Annuity(mdl_ir, ann_data, liab_val_stress=s)
        print(ann.value(), ann_data['Annual Amt'].sum())

        mdl_ma = MatchingAdjustment(mdl_ir, MdlEqRel, mdl_bonds, ann)


        res.append(mdl_ma.portfolio_ma_spread())
        # res2.append(mdl_ma.ltm_economic_value(s))
        print(s)


    print(res)
    #print(res2)
    plt.plot([s * 100 for s in stress], [r * 100 for r in res], label="MP")
    # plt.plot([s * 100 for s in stress], [r / 1000000 for r in res2], label="Economic Value")
    #plt.xlabel("Deferment Rate (%)")
    #plt.ylabel("Value (£m's)")
    plt.legend()
    plt.show()
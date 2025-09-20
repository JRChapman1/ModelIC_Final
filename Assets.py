# Import custom classes
from ERM import ERM
from InterestRates import InterestRate
from Mortality import Mortality
from Bonds import BondPortfolio
from InterestRateSwaps import IRS
from globals import UserDefinedGlobals as udg

import pandas as pd
from datetime import datetime as dt


class Portfolio:

    def __init__(self, int_rate_model, mortality_model, bond_model=None, ltm_model=None, irs_model=None, hpi_drift=0.03, cash_held=0.0):

        # Store parameters as attributes
        self.cash = cash_held
        self.EqRelModel = ltm_model
        self.BondModel = bond_model
        self.IRSModel = irs_model
        self.hpi_assumption = hpi_drift
        self.BaseIR = int_rate_model
        self.BaseMortality = mortality_model

    def value(self):

        udg.log.append((dt.now(), "Valuing assets"))

        # If LTMs are used, calculate their value using the ERM model
        if self.EqRelModel is not None:
            erm_val = self.EqRelModel.economic_value()
        else:
            erm_val = 0

        # If bonds are used, calculate their value using the Bond model
        if self.BondModel is not None:
            bond_val = self.BondModel.pvs()
        else:
            bond_val = 0

        # If IRS are used, calculate their value using the IRS model
        if self.IRSModel is not None:
            irs_val = self.IRSModel.swap_values()
        else:
            irs_val = 0

        # Return the sum of cash, LTM value, and bond value
        return self.cash + erm_val + bond_val + irs_val

    # Used for VIR calculation. IRS CFs not included.
    def ifrs_def_adj_cfs(self, aggregate=False):
        def_adj_bond_cfs = self.BondModel.def_adj_bond_pcfs()
        nneg_adj_erm_cfs = self.EqRelModel.expected_redemption_cfs_net_of_mkt_nneg()
        cfs = pd.concat([def_adj_bond_cfs, nneg_adj_erm_cfs], axis=1).fillna(0.0)
        if aggregate:
            cfs.sum(axis=1)
        return cfs





if __name__ == '__main__':

    mdl_ir = InterestRate('gbp_sonia_ye22.csv')
    mdl_mortality = Mortality()

    df_bonds = pd.read_csv('inputs/bond_data_inputs/JRL.csv', index_col='ISIN')
    mdl_bonds = BondPortfolio(mdl_ir, df_bonds)

    ltm_pols = pd.read_csv('inputs/ltm_data_inputs/JRL_c2.csv', index_col='PolicyID')
    mdl_erm = ERM(mdl_mortality, mdl_ir, ltm_pols, 0.018, 0.13)

    mdl_assets = Portfolio(mdl_ir, mdl_mortality, mdl_bonds, mdl_erm)

    print(mdl_assets.ifrs_def_adj_cfs())
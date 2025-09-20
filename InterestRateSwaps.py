import pandas as pd
import numpy as np
from InterestRates import InterestRate


class IRS:
    def __init__(self, int_rate_model, df_irs_portfolio):
        self.mdl_interest_mcd = int_rate_model
        self.df_irs_portfolio = df_irs_portfolio
        self.mdl_interest_vd = InterestRate(int_rate_model.curve_name)

    def fixed_leg_pcfs(self, aggregate=False):

        # Create dataframe of zeros to hold bond PCFs once calculated
        df_pcfs = pd.DataFrame(
            np.zeros(shape=(self.df_irs_portfolio['Maturity'].max(), self.df_irs_portfolio.shape[0])))
        df_pcfs.index += 1

        # For each bond, use the nominal, coupon rate, and maturity date to populate dataframe with bond's PCFs
        b = 0
        for m, n, c in zip(self.df_irs_portfolio['Maturity'], self.df_irs_portfolio['Nominal'],
                           self.df_irs_portfolio['Fixed Rate']):
            df_pcfs.loc[df_pcfs.index <= m, b] = n * c
            df_pcfs.loc[m, b] += n
            b += 1

        df_pcfs.loc[:, self.df_irs_portfolio['Pay Leg'] == 'Fixed'] *= -1

        if aggregate:
            df_pcfs = df_pcfs.sum(axis=1)


        return df_pcfs

    def swap_values(self, aggregate=True):

        # Calculate PV of projected IRS fixed-leg cashflows under base assumptions (e.g. as-at valuation date) and under
        # scenario assumptions (e.g. as-at market condition date)
        fixed_leg_pcfs = self.fixed_leg_pcfs()
        fixed_leg_pvs_vd = self.mdl_interest_vd.present_value(fixed_leg_pcfs, aggregate=False).to_numpy()
        fixed_leg_pvs_mcd = self.mdl_interest_mcd.present_value(fixed_leg_pcfs, aggregate=False).to_numpy()

        # Read in base swap values (e.g. values as-at valuation date)
        swap_values_vd = self.df_irs_portfolio.loc[:, ['Market Value']].to_numpy()

        # Calculate the new IRS values by adding the change in the PV of the fixed leg to the existing swap values
        swap_values_mcd = pd.DataFrame(swap_values_vd + (fixed_leg_pvs_mcd - fixed_leg_pvs_vd),
                                       index=self.df_irs_portfolio.index)

        if aggregate:
            swap_values_mcd = swap_values_mcd.sum()

        return swap_values_mcd

    def swap_pv01(self, aggregate=True):

        # Calculate PV of fixed leg CFs under a .5bps up and .5bps down stress
        fixed_leg_pcfs = self.fixed_leg_pcfs()
        pvs_up = self.mdl_interest_mcd.present_value(fixed_leg_pcfs, spread=0.00005, aggregate=False).to_numpy()
        pvs_down = self.mdl_interest_mcd.present_value(fixed_leg_pcfs, spread=-0.00005, aggregate=False).to_numpy()

        # Calculate individual swap PV01s by differencing the PVs
        pv01 = pd.DataFrame(pvs_down - pvs_up, index=self.df_irs_portfolio.index)

        if aggregate:
            pv01 = pv01.sum()

        return pv01



if __name__ == '__main__':
    mdl_ir = InterestRate('gbp_sonia_ye22.csv', ir_shock=0.0001)
    df_irs = pd.read_csv('inputs/irs_data_inputs/irs_data.csv')
    mdl_irs = IRS(mdl_ir, df_irs)
    pcfs = mdl_irs.fixed_leg_pcfs()
    res = mdl_irs.swap_values(False)

    print(mdl_irs.swap_pv01(True))

    print(res)
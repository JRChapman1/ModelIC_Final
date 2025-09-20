import pandas as pd
import numpy as np
from InvestmentReturnModel import InvestmentReturnModel

# TODO: Bonuses are smoothed but no charged for smoothing are levied

class WithProfitsInvestmentBond:

    """
    OVERVIEW

    Hypothetical product with no death benefit, no surrender value, and only shared source of profit being investment
    returns


    SIMPLIFICATIONS AND ASSUMPTIONS

    * Cashflow timings:
        * Premiums - SoP
        * Charges - SoP
        * Investment returns - EoP

    * 100% of investment surplus attributable to policyholders
    * All non-investment experience attributable to shareholders
    * Bonuses:
        * Regular reversionary bonuses set at x% of n-period simple moving average of investment returns
        * No special reversionary bonuses
        * Terminal bonuses target average payouts at 100% of asset shares
        * Single rate for all policies
    * Investment returns are net of expenses and tax

    """

    def __init__(self, investment_return_sims, policy_data, sma_period, sma_bonus_proportion):

        self.investment_return_sims = investment_return_sims
        self.policy_data = policy_data
        self.sma_period = sma_period
        self.sma_bonus_proportion = sma_bonus_proportion


    def project_asset_share(self) -> pd.DataFrame:

        projection_term = self.policy_data['Term'].max()
        results = {}

        # TODO: Vectorise
        for policy_id, policy_data in self.policy_data.iterrows():

            asset_share = [0]

            for t in range(projection_term):

                if t <= policy_data['Term']:
                    period_investment_return = self.investment_return_sims[t+self.sma_period-1]
                    asset_share.append((asset_share[-1] + policy_data['Premium']) * (1 + period_investment_return))

                else:
                    asset_share.append(0)

            results[policy_id] = asset_share

        return pd.DataFrame(results)

    def project_reversionary_bonus_rates(self):

        # TODO: Vectorise or use numpy functionality to calc SMA
        sma = []
        for i in range(len(self.investment_return_sims) - self.sma_period):
            sma.append((self.investment_return_sims[i:(i+self.sma_period)].sum() / self.sma_period) * self.sma_bonus_proportion)

        return np.array(sma)

    def project_guaranteed_benefits(self):

        projection_term = self.policy_data['Term'].max()
        reversionary_bonus_rates = self.project_reversionary_bonus_rates()
        asset_shares = self.project_asset_share()
        results = {}

        # TODO: Vectorise
        for policy_id, policy_data in self.policy_data.iterrows():

            guaranteed_benefits = [0]

            for t in range(projection_term):

                if t <= policy_data['Term']:
                    accrued_benefit = (guaranteed_benefits[-1] + policy_data['Premium']) * (1 + reversionary_bonus_rates[t])
                    if t == policy_data['Term']:
                        accrued_benefit += self.determine_terminal_bonus(asset_shares.loc[t, policy_id], accrued_benefit)
                    guaranteed_benefits.append(accrued_benefit)

                else:
                    guaranteed_benefits.append(0)

            results[policy_id] = guaranteed_benefits

        return pd.DataFrame(results)

    def determine_terminal_bonus(self, asset_share, accrued_guaranteed_benefit):
        return max(asset_share - accrued_guaranteed_benefit, 0)


if __name__ == '__main__':

    inv_ret_mdl = InvestmentReturnModel(1, 100, 0.03, 0.01, 0)

    policy_data = pd.DataFrame({'Premium': [3000, 7000, 5500, 2300, 12000, 4000, 6000],
                                'Term': [10, 10, 15, 20, 25, 25, 30]})

    inv_ret_sims = inv_ret_mdl.simulate()

    wp_investment_bond_mdl = WithProfitsInvestmentBond(inv_ret_sims, policy_data, 5, 0.8)

    ap = wp_investment_bond_mdl.project_asset_share()
    gbs = wp_investment_bond_mdl.project_guaranteed_benefits()

    print(ap)

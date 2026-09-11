import pandas as pd
from scipy.stats import norm

from InvestmentReturnModel import InvestmentReturnModel

# TODO: Bonuses are smoothed but no charged for smoothing are levied
# TODO: Understand how smoothing charge parameterisation should vary by product type


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

    def __init__(self, investment_return_sims, estate_investment_return_sims, policy_data, sma_period, sma_bonus_proportion, smoothing_parameters):

        self.investment_return_sims = investment_return_sims
        self.estate_investment_return_sims = estate_investment_return_sims
        self.policy_data = policy_data
        self.sma_period = sma_period
        self.sma_bonus_proportion = sma_bonus_proportion
        self.smoothing_parameters = smoothing_parameters

        self.proj_term = policy_data['Term'].max()

    def project_premiums(self, aggregate=True):

        # TODO: Vectorise!!!
        premiums = {}
        for policy_id, policy_data in self.policy_data.iterrows():

            policy_premiums = []
            for t in range(self.proj_term):

                if t < policy_data['Term']:
                    policy_premiums.append(policy_data['Premium'])
                else:
                    policy_premiums.append(0.0)

            premiums[policy_id] = policy_premiums

        premiums = pd.DataFrame(premiums, index=range(1, self.proj_term+1))
        if aggregate:
            premiums = premiums.sum(axis=1)

        return premiums

    def project_reversionary_bonus_rates(self):
        sma = self.investment_return_sims.rolling(self.sma_period, self.sma_period).mean()
        return sma.loc[1:] * self.sma_bonus_proportion



if __name__ == '__main__':

    inv_ret_mdl = InvestmentReturnModel(1, -3, 100, 0.03, 0.01, 0)

    estate_inv_ret_mdl = InvestmentReturnModel(1, 1, 100, 0.02, 0.005, 0)

    policy_data = pd.DataFrame({'Premium': [3000, 7000, 5500, 2300, 12000, 4000, 6000],
                                'Term': [10, 10, 15, 20, 25, 25, 30]})

    inv_ret_sims = inv_ret_mdl.simulate()
    estate_inv_ret_sims = estate_inv_ret_mdl.simulate()

    smoothing_params = {'start_reserve': 40000, 'target_reserve_as_prop': 0.05, 'target_reserve_rb_months': 6, 'target_reserve_smoothing_gap_prop': 0.8}

    wp_investment_bond_mdl = WithProfitsInvestmentBond(inv_ret_sims, estate_inv_ret_sims, policy_data, 5, 0.8, smoothing_params)

    ap = wp_investment_bond_mdl.project_reversionary_bonus_rates()

    print(ap)

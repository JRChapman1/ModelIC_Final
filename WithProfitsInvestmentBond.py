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

    def project_asset_share(self) -> pd.DataFrame:

        projection_term = self.policy_data['Term'].max()
        results = {}

        # TODO: Vectorise
        for policy_id, policy_data in self.policy_data.iterrows():

            asset_share = [0]

            for t in range(1, projection_term+1):

                if t <= policy_data['Term']:
                    period_investment_return = float(self.investment_return_sims.loc[t, 0])
                    asset_share.append((asset_share[-1] + policy_data['Premium']) * (1 + period_investment_return))

                else:
                    asset_share.append(0)

            results[policy_id] = asset_share[1:]

        return pd.DataFrame(results, index=range(1, projection_term+1))

    def project_reversionary_bonus_rates(self):
        sma = self.investment_return_sims.rolling(self.sma_period, self.sma_period).mean()
        return sma.loc[1:] * self.sma_bonus_proportion

    def project_guaranteed_benefits(self):

        projection_term = self.policy_data['Term'].max()
        reversionary_bonus_rates = self.project_reversionary_bonus_rates()
        asset_shares = self.project_asset_share()
        results = {}

        # TODO: Vectorise
        for policy_id, policy_data in self.policy_data.iterrows():

            guaranteed_benefits = [0]

            for t in range(1, projection_term+1):

                if t <= policy_data['Term']:
                    reversionary_bonus_rate = float(reversionary_bonus_rates.loc[t, 0])
                    accrued_benefit = (guaranteed_benefits[-1] + policy_data['Premium']) * (1 + reversionary_bonus_rate)

                    guaranteed_benefits.append(accrued_benefit)

                else:
                    guaranteed_benefits.append(0)

            results[policy_id] = guaranteed_benefits[1:]

        return pd.DataFrame(results, index=range(1, projection_term+1))

    def determine_terminal_bonus(self, asset_share, accrued_guaranteed_benefit):
        return max(asset_share - accrued_guaranteed_benefit, 0)

    def project_smoothing_gaps(self):

        asset_shares = self.project_asset_share()
        guaranteed_benefits = self.project_guaranteed_benefits()

        return asset_shares - guaranteed_benefits

    def project_smoothing_reserve(self):

        smoothing_gap = self.project_smoothing_gap().sum(axis=1)
        smoothing_reserve = [self.smoothing_reserve]

        for t in range(len(smoothing_gap)):
            smoothing_reserve.append(smoothing_reserve[-1] * (1 + self.estate_investment_return_sims[t]) + smoothing_gap[t] - charge[t])

        return smoothing_reserve

    def project_reversionary_bonus_amounts(self):

        projection_term = self.policy_data['Term'].max()
        reversionary_bonus_rates = self.project_reversionary_bonus_rates()
        results = {}

        # TODO: Vectorise
        for policy_id, policy_data in self.policy_data.iterrows():

            guaranteed_benefits = [0]
            rbs = []

            for t in range(1, projection_term+1):

                if t <= policy_data['Term']:
                    reversionary_bonus_rate = float(reversionary_bonus_rates.loc[t, 0])
                    accrued_benefit = (guaranteed_benefits[-1] + policy_data['Premium']) * (1 + reversionary_bonus_rate)
                    rbs.append((guaranteed_benefits[-1] + policy_data['Premium']) * reversionary_bonus_rate)
                    guaranteed_benefits.append(accrued_benefit)

                else:
                    rbs.append(0)

            results[policy_id] = rbs

        return pd.DataFrame(results, index=range(1, projection_term+1))

    def project_target_smoothing_reserves(self):

        asset_shares = self.project_asset_share().sum(axis=1)
        smoothing_gaps = self.project_smoothing_gaps().sum(axis=1)

        worst_case_investment_return = norm.ppf(0.05, loc=0.03, scale=0.01)

        reversionary_bonuses = self.project_reversionary_bonus_amounts().sum(axis=1)
        target_smoothing_reserves = []

        for asset_share, reversionary_bonus, smoothing_gap in zip(asset_shares, reversionary_bonuses, smoothing_gaps):

            metric_1 = asset_share * self.smoothing_parameters['target_reserve_as_prop']
            metric_2 = reversionary_bonus * self.smoothing_parameters['target_reserve_rb_months'] / 12

            # TODO: Not sure I agree with this approach (assuming it is supposed to represent a ruin probability).
            #  Should the entire value of the estate less the smoothing costs not be considered?
            metric_3 = smoothing_gap * worst_case_investment_return

            target_smoothing_reserves.append(max([metric_1, metric_2, metric_3]))

        return target_smoothing_reserves


if __name__ == '__main__':

    inv_ret_mdl = InvestmentReturnModel(1, -3, 100, 0.03, 0.01, 0)

    estate_inv_ret_mdl = InvestmentReturnModel(1, 1, 100, 0.02, 0.005, 0)

    policy_data = pd.DataFrame({'Premium': [3000, 7000, 5500, 2300, 12000, 4000, 6000],
                                'Term': [10, 10, 15, 20, 25, 25, 30]})

    inv_ret_sims = inv_ret_mdl.simulate()
    estate_inv_ret_sims = estate_inv_ret_mdl.simulate()

    smoothing_params = {'start_reserve': 40000, 'target_reserve_as_prop': 0.05, 'target_reserve_rb_months': 6, 'target_reserve_smoothing_gap_prop': 0.8}

    wp_investment_bond_mdl = WithProfitsInvestmentBond(inv_ret_sims, estate_inv_ret_sims, policy_data, 5, 0.8, smoothing_params)

    ap = wp_investment_bond_mdl.project_target_smoothing_reserves()

    print(ap)

# Import external libraries
import pandas as pd
import numpy as np
from scipy import stats
from matplotlib import pyplot as plt

# Import custom classes
from Mortality import Mortality
from InterestRates import InterestRate


class ERM:
    def __init__(self, mortality_model, int_rate_model, df_ltm_pols, hpi_drift, hpi_vol, prop_shock=None):

        self.cache = {}

        # Create instance of Mortality class
        self.mdl_mortality = mortality_model

        # Create instance of InterestRate class
        self.mdl_interest = int_rate_model

        # Save property growth parameters as attributes
        self.hpi_drift = hpi_drift
        self.hpi_vol = hpi_vol
        self.prop_shock = prop_shock

        self.df_ltm_pols = df_ltm_pols

    def expected_redemption_cfs_net_of_int_nneg(self, aggregate=False):
        if f'expected_redemption_cfs_net_of_int_nneg_{aggregate}' not in self.cache:
            # Subtract expected intrinsic NNEG cashflows from expected redemption cashflows and return the result
            res = self.expected_redemption_cfs() - self.expected_int_nneg_cfs()
            if aggregate:
                res = res.sum(axis=1)
            self.cache[f'expected_redemption_cfs_net_of_int_nneg_{aggregate}'] = res
        return self.cache[f'expected_redemption_cfs_net_of_int_nneg_{aggregate}']


    def expected_int_nneg_cfs(self):
        if 'expected_int_nneg_cfs' not in self.cache:
            policy_data = self.df_ltm_pols.copy()

            # Apply shock to property values if required
            if self.prop_shock is not None:
                policy_data['Property Value'] *= (1 - self.prop_shock)

            # For each LTM, get probabilities of policy being redeemed in each future year and store in a numpy array
            df_death_in_period_probs = self.mdl_mortality.prob_death()
            np_death_in_period_probs = df_death_in_period_probs.loc[policy_data['Age']].to_numpy().transpose()

            # Calculate the rolled up loan values at each future year for each LTM and store in a numpy array
            np_loan_vals = self.rolled_up_loan_values()

            # Calculate the projected property values at each future year for each LTM and store in a numpy array
            np_prop_vals = self.projected_property_values()

            # For each LTM, at each future year, calculate the intrinsic NNEG as the shortfall in the projected
            # property value below the rolled up loan amount
            np_loan_vals = np.maximum(np_loan_vals - np_prop_vals, 0)

            # Multiply the projected intrinsic NNEG at each year for each LTM by the probability of the LTM being
            # redeemed during that year and store the result in a dataframe
            df_redemption_vals = pd.DataFrame(np_loan_vals[:np_death_in_period_probs.shape[0]] * np_death_in_period_probs)

            self.cache['expected_int_nneg_cfs'] = df_redemption_vals
        return self.cache['expected_int_nneg_cfs']

    def expected_mkt_nneg_val(self, aggregate=False, attch_point=1.0, deferment_rate=0.0):
        if f'expected_mkt_nneg_val_{aggregate}_{attch_point}_{deferment_rate}' not in self.cache:
            policy_data = self.df_ltm_pols.copy()

            # Store the projected market NNEG values for each LTM in a DataFrame
            df_mkt_nneg = self.projected_nneg_mkt_value(attch_point, deferment_rate)

            # For each LTM, store the probability of redemption in each year in a DataFrame
            # TODO: This is messy. Should not need to increment index
            df_death_in_period_probs = self.mdl_mortality.prob_death()
            df_death_in_period_probs = pd.DataFrame(df_death_in_period_probs.loc[policy_data['Age']].transpose().to_numpy(), columns=policy_data.index)
            df_death_in_period_probs.index += 1

            # Multiply the projected market NNEG values by the redeption probabilities to get the expected market NNEG
            # cashflow for each policy at each year
            df_mkt_nneg = df_mkt_nneg * df_death_in_period_probs

            # If required, sum the expected market NNEG cashflows for each policy at each year
            if aggregate:
                df_mkt_nneg = df_mkt_nneg.sum(axis='columns')

            self.cache[f'expected_mkt_nneg_val_{aggregate}_{attch_point}_{deferment_rate}'] = df_mkt_nneg
        return self.cache[f'expected_mkt_nneg_val_{aggregate}_{attch_point}_{deferment_rate}']

    def rolled_up_loan_values(self):
        if 'rolled_up_loan_values' not in self.cache:
            policy_data = self.df_ltm_pols.copy()

            # Store the AERs of each LTM in a (1 x n) numpy array
            np_roll_up_rates = policy_data['AER'].to_numpy().reshape((1, -1))

            # Construct a numpy array whose (i,j)th entry is the accumulation factor for the loan on LTM j at year i
            np_roll_up_facs = (1 + np_roll_up_rates) ** np.arange(0, 106).reshape(-1, 1)

            # Multiply the accumulation factors by the initial loan values and return the result
            self.cache['rolled_up_loan_values'] = pd.DataFrame(np_roll_up_facs * policy_data['Loan Value'].to_numpy(), columns=policy_data.index)
        return self.cache['rolled_up_loan_values']

    def projected_property_values(self):
        if 'projected_property_values' not in self.cache:
            policy_data = self.df_ltm_pols.copy()

            # Apply shock to property values if required
            if self.prop_shock is not None:
                policy_data['Property Value'] *= (1 - self.prop_shock)

            # Construct a numpy array whose (i,j)th entry is the growth factor for the property backing LTM j at year i
            np_growth_facs = (1 + self.hpi_drift) ** np.arange(0, 106).reshape(-1, 1)

            # Multiply the growth factors by the initial property values and return the result
            self.cache['projected_property_values'] = np_growth_facs * policy_data['Property Value'].to_numpy()
        return self.cache['projected_property_values']

    def expected_redemption_cfs(self):
        if 'expected_redemption_cfs' not in self.cache:
            policy_data = self.df_ltm_pols.copy()

            # Store the rolled up loan values for each LTM at each year in a numpy array
            df_loan_vals = self.rolled_up_loan_values()

            # Store the probability of each LTM being redeemed at each year in a numpy array
            df_death_in_period_probs_all = self.mdl_mortality.prob_death()
            df_death_in_period_probs = pd.DataFrame(df_death_in_period_probs_all.loc[policy_data['Age']].to_numpy().transpose(), index=df_death_in_period_probs_all.columns, columns=policy_data.index)

            # For each LTM, multiply the loan value at each year by the probability of the LTM being redeemed at that
            # time and return the result
            self.cache['expected_redemption_cfs'] = df_loan_vals * df_death_in_period_probs
        return self.cache['expected_redemption_cfs']

    def expected_redemption_cfs_net_of_mkt_nneg(self, deferment_rate=0.0, aggregate=False):
        if f'expected_redemption_cfs_net_of_mkt_nneg_{deferment_rate}_{aggregate}' not in self.cache:
            # Return the expected redemption cashflows minus the expected market NNEG cashflows
            cfs = self.expected_redemption_cfs() - self.expected_mkt_nneg_val(deferment_rate=deferment_rate)

            if aggregate:
                cfs = cfs.sum(axis=1)

            self.cache[f'expected_redemption_cfs_net_of_mkt_nneg_{deferment_rate}_{aggregate}'] = cfs
        return self.cache[f'expected_redemption_cfs_net_of_mkt_nneg_{deferment_rate}_{aggregate}']

    def projected_nneg_mkt_value(self, attch_point=1.0, deferment_rate=0.0):
        if f'projected_nneg_mkt_value_{attch_point}_{deferment_rate}' not in self.cache:
            """
            policy_data = self.df_ltm_pols.copy()
    
            # Apply shock to property values if required
            if self.prop_shock is not None:
                policy_data['Property Value'] *= (1 - self.prop_shock)
    
            policy_data['Loan Value'] *= attch_point
            """
            # Store the rolled up loan values for each LTM at each year in a numpy array
            np_loan_vals = self.rolled_up_loan_values() * attch_point

            # Store the projected property values for each LTM at each year in a numpy array
            np_prop_vals = self.projected_property_values()

            # Construct a numpy array whose entries are the years under consideration
            np_time_steps = np.arange(0, 106).reshape(-1, 1)

            # For each LTM, and at each possible year, use Black-76 to calculate the market value of the NNEG assuming
            # that the LTM is redeemed at that time

            r = self.mdl_interest.continuous_spot_curve().iloc[:106].to_numpy()

            np_log_prop_loan_ratio = np.log(np_prop_vals / np_loan_vals)
            np_d1 = (np_log_prop_loan_ratio + (r - deferment_rate + 0.5 * self.hpi_vol**2) * np_time_steps) / (self.hpi_vol * np.sqrt(np_time_steps))
            np_d2 = np_d1 - self.hpi_vol * np.sqrt(np_time_steps)
            np_nneg_mkt_val = np_loan_vals * np.exp(-r * np_time_steps) * stats.norm.cdf(-np_d2) - np_prop_vals * np.exp(-deferment_rate * np_time_steps) * stats.norm.cdf(-np_d1)

            self.cache[f'projected_nneg_mkt_value_{attch_point}_{deferment_rate}'] = pd.DataFrame(np_nneg_mkt_val)
        return self.cache[f'projected_nneg_mkt_value_{attch_point}_{deferment_rate}']

    def ifrs_value(self, aggregate=True, ir_shock=0.0):
        if f'ifrs_value_{aggregate}_{ir_shock}' not in self.cache:

            policy_data = self.df_ltm_pols.copy()

            # Project the expected redemption cashflows (net of market NNEG) for each LTM
            # TODO: Confirm that cashflows used here should be net of expected market NNEG
            exp_red_cfs = self.expected_redemption_cfs_net_of_mkt_nneg()

            # For each LTM, construct a discount curve from the risk-free rate of interest plus the day-one IFRS spread
            # on the LTM
            disc_curve = self.mdl_interest.discount_curve(policy_data['Spread'] + ir_shock).iloc[:exp_red_cfs.shape[0]]

            # Calculate the present values of the expected redemption cashflows for each LTM using the corresponding
            # discount curve and sum the
            df_ltm_values = (exp_red_cfs * disc_curve).sum(axis='columns')

            # If required, aggregate NNEG values over all years
            if aggregate:
                df_ltm_values = df_ltm_values.sum(axis='rows')

            self.cache[f'ifrs_value_{aggregate}_{ir_shock}'] = df_ltm_values
        return self.cache[f'ifrs_value_{aggregate}_{ir_shock}']

    def economic_value(self, aggregate=True, deferment_rate=0.0):
        if f'economic_value_{aggregate}_{deferment_rate}' not in self.cache:
            # Project the expected redemption cashflows (net of market NNEG) for each LTM
            exp_red_cfs = self.expected_redemption_cfs_net_of_mkt_nneg(deferment_rate)

            # For each LTM, construct a discount curve from the risk-free rate of interest plus the day-one IFRS spread
            # on the LTM
            disc_curve = self.mdl_interest.discount_curve().iloc[:exp_red_cfs.shape[0]].to_numpy().repeat(exp_red_cfs.shape[1], axis=1)

            # Calculate the present values of the expected redemption cashflows for each LTM using the corresponding
            # discount curve and sum the
            df_ltm_values = (exp_red_cfs * disc_curve)

            # If required, aggregate NNEG values over all years
            df_ltm_values = df_ltm_values.sum(axis='rows')

            if aggregate:
                self.cache[f'economic_value_{aggregate}_{deferment_rate}'] = df_ltm_values.sum()
            else:
                self.cache[f'economic_value_{aggregate}_{deferment_rate}'] = df_ltm_values.T
        return self.cache[f'economic_value_{aggregate}_{deferment_rate}']

    def spread(self, itterations=10):
        # Store copy of policy data in dataframe
        policy_data = self.df_ltm_pols.copy()

        # Create array of spreads, taken from policy data dataframe
        spread = policy_data['Spread']

        # Store expected LTM redemption cashflows (net of NNEG) and discount curve in arrays
        cfs = self.expected_redemption_cfs_net_of_mkt_nneg().iloc[1:, :]
        disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], :]

        # Iteratively calculate the duration and spread
        duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (cfs * disc_curve).sum()
        for i in range(1, itterations):
            disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], :]
            spread -= (policy_data['Loan Value'] / (cfs * disc_curve).sum() - 1) / duration
            disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], :]
            duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (cfs * disc_curve).sum()

        return spread


if __name__ == '__main__':

    mdl_ir = InterestRate('example_ir.csv')
    ltm_pols = pd.read_csv('inputs/ltm_data_inputs/example_erms.csv')

    #mortality_model, int_rate_model, df_ltm_pols, hpi_drift, hpi_vol, prop_shock = None
    MdlEqRel = ERM(Mortality(lapse_rate=0.01), mdl_ir, ltm_pols, 0.03, 0.13)

    ev = MdlEqRel.economic_value(True)
    exp_red_cfs_ifrs = MdlEqRel.expected_redemption_cfs()
    erm_rolled_up_loan_values = MdlEqRel.rolled_up_loan_values()

    exp_nneg_cfs = MdlEqRel.expected_mkt_nneg_val()
    ifrs_val = MdlEqRel.ifrs_value(True)
    print('done')





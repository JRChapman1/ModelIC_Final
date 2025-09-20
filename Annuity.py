import pandas as pd
import numpy as np
from Mortality import Mortality
from InterestRates import InterestRate

from globals import UserDefinedGlobals as udg


class Annuity:

    def __init__(self, int_rate_model, policy_data=None, liab_val_stress=0.0):
        if policy_data is None:
            self.policy_data = pd.DataFrame(columns=['Age', 'Annual Amt'])
        else:
            self.policy_data = policy_data
        self.policy_data['Annual Amt'] = self.policy_data['Annual Amt'] * (1 + liab_val_stress)
        self.BaseMortality = Mortality()
        self.StressMortality = Mortality(mortality_stress='SII')
        self.BaseIR = int_rate_model
        self.StressIRUp = int_rate_model.copy()
        self.StressIRDown = int_rate_model.copy()
        self.StressIRUp.apply_stress('SII_Up')
        self.StressIRDown.apply_stress('SII_Down')
        self.cache = {}

    # Create list of dicts before constructing df
    def annuity_factors(self, stress=None, ir_shock=0.0):

        if f'ann_fac_{stress}_{ir_shock}' not in self.cache:
            # Set in-force probabilities depending on whether mortality is being stressed or not
            if stress == 'Mortality':
                df_if_probs = self.StressMortality.prob_in_force()
            else:
                df_if_probs = self.BaseMortality.prob_in_force()

            # Set discount curve depending on whether interest rates are being stressed or not
            if stress == 'Interest_Up':
                discount_curve = self.StressIRUp.discount_curve()
            elif stress == 'Interest_Down':
                discount_curve = self.StressIRDown.discount_curve()
            else:
                discount_curve = self.BaseIR.discount_curve(spread=ir_shock)

            # Increment columns of in-force probs dataframe so that they align with discount curve index
            #df_if_probs.columns += 1
            df_payable = np.reshape(df_if_probs.index, (-1, 1)) + np.reshape(df_if_probs.columns, (1, -1)) > udg.pension_age
            df_if_probs.mask(~df_payable, 0, inplace=True)
            df_if_probs = df_if_probs.dot(discount_curve.loc[df_if_probs.columns])
            df_if_probs.columns = ['Ann Fac']
            self.cache[f'ann_fac_{stress}'] = df_if_probs

        return self.cache[f'ann_fac_{stress}']

    def value(self, stress=None, ir_shock=0.0):
        if f'value_{stress}_{ir_shock}' not in self.cache:
            df_ann_facs = self.annuity_factors(stress, ir_shock)
            df_liab_calc = self.policy_data.merge(df_ann_facs, left_on='Age', right_index=True, how='left')
            df_liab_calc['Policy Value'] = df_liab_calc['Ann Fac'] * df_liab_calc['Annual Amt']
            self.cache[f'value_{stress}_{ir_shock}'] = df_liab_calc['Policy Value'].sum()
        return self.cache[f'value_{stress}_{ir_shock}']

    """
    def expected_cfs(self, aggregate=False):
        df_if_probs = self.BaseMortality.prob_in_force().loc[self.policy_data['Age']]
        df_if_probs.index = self.policy_data.index
        cfs = df_if_probs.transpose() * self.policy_data['Annual Amt']
        if aggregate:
            cfs = cfs.sum(axis=1)
        return cfs
        
    """

    def expected_cfs(self, stress_mortality=False, aggregate=False):

        if f'cfs_{stress_mortality}_{aggregate}' not in self.cache:
            # Set in-force probabilities depending on whether mortality is being stressed or not
            if stress_mortality:
                df_if_probs = self.StressMortality.prob_in_force()
            else:
                df_if_probs = self.BaseMortality.prob_in_force()


            # Increment columns of in-force probs dataframe so that they align with discount curve index
            #df_if_probs.columns += 1
            df_payable = np.reshape(df_if_probs.index, (-1, 1)) + np.reshape(df_if_probs.columns, (1, -1)) >= udg.pension_age
            df_if_probs.mask(~df_payable, 0, inplace=True)
            df_if_probs = df_if_probs.loc[self.policy_data['Age']]
            df_if_probs.index = self.policy_data.index

            cfs = df_if_probs.multiply(self.policy_data['Annual Amt'], axis=0)

            if aggregate:
                cfs = cfs.sum()

            self.cache[f'cfs_{stress_mortality}_{aggregate}'] = cfs

        return self.cache[f'cfs_{stress_mortality}_{aggregate}']


if __name__ == '__main__':
    ann_data = pd.read_csv(r'inputs/ann_data_inputs/JRL.csv')
    ann = Annuity(InterestRate('gbp_sonia_ye22.csv'), ann_data)

    val = ann.value()
    ecf = ann.expected_cfs()
    af = ann.annuity_factors()
    print(ecf)




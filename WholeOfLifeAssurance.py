import pandas as pd
from Mortality import Mortality
from InterestRates import InterestRate


class WholeOfLifeAssurance:

    def __init__(self, int_rate_model, policy_data=None, liab_val_stress=0.0):
        if policy_data is None:
            self.policy_data = pd.DataFrame(columns=['Age', 'Sum Assured'])
        else:
            self.policy_data = policy_data

            # TODO: Why would liability values be stressed? Can this be removed? Also in Annuity class
            self.policy_data['Sum Assured'] = self.policy_data['Sum Assured'] * (1 + liab_val_stress)

        self.BaseMortality = Mortality()

        # TODO: Why is mortality stress hardcoded?
        self.StressMortality = Mortality(mortality_stress='SII')

        self.BaseIR = int_rate_model
        self.StressIRUp = int_rate_model.copy()
        self.StressIRDown = int_rate_model.copy()
        self.StressIRUp.apply_stress('SII_Up')
        self.StressIRDown.apply_stress('SII_Down')

        self.cache = {}

    # Create list of dicts before constructing df
    def assurance_factors(self, stress=None, ir_shock=0.0):

        if f'ta_{stress}_{ir_shock}' not in self.cache:

            # Set in-force probabilities depending on whether mortality is being stressed or not
            if stress == 'Mortality':
                df_death_probs = self.StressMortality.prob_death()
            else:
                df_death_probs = self.BaseMortality.prob_death()

            # Set discount curve depending on whether interest rates are being stressed or not
            if stress == 'Interest_Up':
                discount_curve = self.StressIRUp.discount_curve()
            elif stress == 'Interest_Down':
                discount_curve = self.StressIRDown.discount_curve()
            else:
                discount_curve = self.BaseIR.discount_curve(spread=ir_shock)

            # TODO: Hardcoding
            self.cache[f'ta_fac_{stress}_{ir_shock}'] = df_death_probs @ discount_curve[:105].values

        return self.cache[f'ta_fac_{stress}_{ir_shock}']

    def value(self, stress=None, ir_shock=0.0):
        if f'value_{stress}_{ir_shock}' not in self.cache:
            df_ass_facs = self.assurance_factors(stress, ir_shock)
            self.cache[f'value_{stress}_{ir_shock}'] = df_ass_facs.loc[self.policy_data['Age']].squeeze() @ \
                                                       self.policy_data['Sum Assured'].values

        return self.cache[f'value_{stress}_{ir_shock}']

    def expected_cfs(self, stress_mortality=False, aggregate=False):

        if f'cfs_{stress_mortality}_{aggregate}' not in self.cache:
            # Set in-force probabilities depending on whether mortality is being stressed or not
            if stress_mortality:
                df_if_probs = self.StressMortality.prob_death()
            else:
                df_if_probs = self.BaseMortality.prob_death()


            # Increment columns of in-force probs dataframe so that they align with discount curve index
            #df_if_probs.columns += 1
            df_if_probs = df_if_probs.loc[self.policy_data['Age']]
            df_if_probs.index = self.policy_data.index

            cfs = df_if_probs.multiply(self.policy_data['Sum Assured'], axis=0)

            if aggregate:
                cfs = cfs.sum()

            self.cache[f'cfs_{stress_mortality}_{aggregate}'] = cfs

        return self.cache[f'cfs_{stress_mortality}_{aggregate}']


if __name__ == '__main__':

    mdl_ir = InterestRate('example_ir.csv')
    policy_data = pd.DataFrame([[45, 10000], [55, 15000], [60, 12000], [47, 15000]], columns=['Age', 'Sum Assured'])
    mdl_wol = WholeOfLifeAssurance(mdl_ir, policy_data)
    print(mdl_wol.expected_cfs())
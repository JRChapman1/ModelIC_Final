import numpy as np
import pandas as pd
from Annuity import Annuity
from InterestRates import InterestRate
from Mortality import Mortality
from ERM import ERM
from Bonds import BondPortfolio


class Generator:
    def __init__(self):
        self.annuity_policies = pd.DataFrame(columns=['Age', 'Annual Amt'])
        self.bond_portfolio = pd.DataFrame(columns=['Maturity', 'Nominal', 'Spread', 'Rating', 'Coupon Rate'])
        self.ltm_policies = pd.DataFrame(columns=['Age', 'Loan Value', 'Property Value', 'AER', 'Spread'])
        ir_model = InterestRate()
        self.annuity_model = Annuity(ir_model)

    def generate_annuities(self, age=None, amount=None, portfolio_value=None):

        if portfolio_value is None:
            portfolio_value = np.random.uniform(1, 100) * 10**6

        num_pols = int(portfolio_value / (amount['mean']))
        policies = pd.DataFrame()
        policies['Age'] = np.random.normal(age['mean'], age['sd'], num_pols).round()
        policies.loc[policies['Age'] <= age['floor'], 'Age'] = age['floor']
        policies['Annual Amt'] = np.random.normal(amount['mean'], amount['sd'], num_pols)
        policies.loc[policies['Annual Amt'] <= amount['floor'], 'Annual Amt'] = amount['floor']
        annuity_values = self.__value_annuities(policies)
        num_pols = np.argmax(annuity_values.cumsum() >= portfolio_value)

        return policies.iloc[:num_pols]

    def generate_erms(self, age=None, ltv=None, loan_amt=None, portfolio_value=None):

        if portfolio_value is None:
            portfolio_value = np.random.uniform(1, 35) * 10 ** 6

        num_pols = int(portfolio_value / (loan_amt['mean']))
        policies = pd.DataFrame()
        policies['Age'] = np.random.normal(age['mean'], age['sd'], num_pols).round()
        if 'floor' in age.keys():
            policies.loc[policies['Age'] <= age['floor'], 'Age'] = age['floor']
        policies['LTV'] = np.random.normal(ltv['mean'], ltv['sd'], num_pols)
        if 'floor' in ltv.keys():
            policies.loc[policies['LTV'] <= ltv['floor'], 'LTV'] = ltv['floor']
        policies['Loan Value'] = np.random.normal(loan_amt['mean'], loan_amt['sd'], num_pols)
        if 'floor' in loan_amt.keys():
            policies.loc[policies['Loan Value'] <= loan_amt['floor'], 'Loan Value'] = loan_amt['floor']
        policies['Property Value'] = policies['Loan Value'] / policies['LTV']
        policies['AER'] = policies['LTV']/20 + np.random.normal(0.04, 0.01)
        policies['Spread'] = 0
        annuity_values = self.__value_erms(policies)
        num_pols = np.argmax(annuity_values.cumsum() >= portfolio_value)

        return policies.iloc[:num_pols]

    def generate_bonds(self, aaa_params, aa_params, a_params, bbb_params):
        aaa_bonds = self.__generate_bonds_for_rating(aaa_params, 'AAA')
        aa_bonds = self.__generate_bonds_for_rating(aa_params, 'AA')
        a_bonds = self.__generate_bonds_for_rating(a_params, 'A')
        bbb_bonds = self.__generate_bonds_for_rating(bbb_params, 'BBB')
        return pd.concat([aaa_bonds, aa_bonds, a_bonds, bbb_bonds], ignore_index=True)

    def __generate_bonds_for_rating(self, bond_params, rating):
        num_bonds_aaa = int(bond_params['total_val'] * 2 / (bond_params['nom_mean']))
        aaa_bonds = pd.DataFrame()
        aaa_bonds['Maturity'] = np.random.normal(bond_params['maturity_mean'], bond_params['maturity_sd'], num_bonds_aaa).round()
        aaa_bonds.loc[aaa_bonds['Maturity'] < 1, 'Maturity'] = 1
        aaa_bonds['Nominal'] = np.random.normal(bond_params['nom_mean'], bond_params['nom_sd'], num_bonds_aaa)
        aaa_bonds.loc[aaa_bonds['Nominal'] < 10000, 'Nominal'] = 10000
        aaa_bonds['Spread'] = np.random.normal(bond_params['spread_mean'], bond_params['spread_sd'], num_bonds_aaa)
        aaa_bonds['Rating'] = rating
        aaa_bonds['Coupon Rate'] = np.random.normal(0.04, 0.015, num_bonds_aaa)
        aaa_bonds.loc[aaa_bonds['Coupon Rate'] < 0.0, 'Coupon Rate'] = 0.0
        annuity_values = self.__value_bonds(aaa_bonds)
        num_pols = np.argmax(annuity_values.cumsum() >= bond_params['total_val'])

        return aaa_bonds.iloc[:num_pols]


    def __value_annuities(self, df_policies):
        df_ann_facs = self.annuity_model.annuity_factors()
        df_liab_calc = df_policies.merge(df_ann_facs, left_on='Age', right_index=True, how='left')
        df_liab_calc['Policy Value'] = df_liab_calc['Ann Fac'] * df_liab_calc['Annual Amt']
        return df_liab_calc['Policy Value']

    def __value_erms(self, df_erm_portfolio):
        ir_model = InterestRate()
        mortality_model = Mortality()
        erm_model = ERM(mortality_model, ir_model, df_erm_portfolio, 0.03, 0.13)
        return erm_model.economic_value(aggregate=False)

    def __value_bonds(self, df_bond_portfolio):
        ir_model = InterestRate()
        bond_model = BondPortfolio(ir_model, df_bond_portfolio)
        return bond_model.market_value(aggregate=False)

if __name__ == '__main__':

    g = Generator()
    ages = {'mean': 75, 'sd': 7, 'floor': 30}
    ltvs = {'mean': 0.25, 'sd': 0.123, 'floor': 0.05}
    amts = {'mean': 63025, 'sd': 66711, 'floor': 5000}

    aaa = {'total_val': 25000000, 'nom_mean': 500000, 'nom_sd': 100000, 'spread_mean': 0.02, 'spread_sd': 0.005, 'maturity_mean': 15, 'maturity_sd': 5}
    aa = {'total_val': 15000000, 'nom_mean': 500000, 'nom_sd': 100000, 'spread_mean': 0.03, 'spread_sd': 0.01, 'maturity_mean': 15, 'maturity_sd': 5}
    a = {'total_val': 10000000, 'nom_mean': 500000, 'nom_sd': 100000, 'spread_mean': 0.04, 'spread_sd': 0.015, 'maturity_mean': 15, 'maturity_sd': 5}
    bbb = {'total_val': 10000000, 'nom_mean': 500000, 'nom_sd': 100000, 'spread_mean': 0.05, 'spread_sd': 0.02, 'maturity_mean': 15, 'maturity_sd': 5}

    res = g.generate_bonds(aaa, aa, a, bbb)
    print(res)
    res2 = g.generate_erms(ages, ltvs, amts, 4153000000)
    ir_model2 = InterestRate()
    mortality_model2 = Mortality()
    bond_model = BondPortfolio(ir_model2, res)
    print(bond_model.market_value(True))
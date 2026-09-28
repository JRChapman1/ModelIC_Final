# Import external libraries
import pandas as pd
import numpy as np

# Import custom classes
from InterestRates import InterestRate


class BondPortfolio:

    def __init__(self, int_rate_model, df_bond_portfolio, bond_val_stress=0.0):

        # Create an instance of the interest rate model as an attribute
        self.mdl_interest = int_rate_model

        # Save bond portfolio as attribute and calculate spreads for each
        self.df_bond_portfolio = df_bond_portfolio

        self.df_bond_portfolio['Nominal'] *= 1 + bond_val_stress

        self.ifrs_default_adj = pd.read_csv('inputs/ifrs_default_probs.csv', index_col=0)
        self.cache = {}
        # self.df_bond_portfolio['Spread'] = self.spreads()

    def market_value(self, aggregate=True):
        if f'market_value_{aggregate}' not in self.cache:
            pcfs = self.bond_pcfs()
            values = self.mdl_interest.present_value(pcfs, self.df_bond_portfolio['Spread'], aggregate)
            self.cache[f'market_value_{aggregate}'] = values
        return self.cache[f'market_value_{aggregate}']

    def pd_spreads(self, iterations=10):

        if f'pd_spreads_{iterations}' not in self.cache:
            # Store copy of bond data in dataframe and add (all zero) column for spread. Also store spread in array.
            bond_data = self.df_bond_portfolio.copy()
            bond_data['PD Spread'] = 0.0
            bond_data['Market Value'] = self.market_value(aggregate=False)
            spread = bond_data['PD Spread']

            # Store bond PCFs and discount curve in array
            cfs = self.def_adj_bond_pcfs()
            disc_curve = self.mdl_interest.discount_curve(spread=spread).loc[cfs.index]

            # Iteratively calculate spreads
            duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (cfs * disc_curve).sum()
            for i in range(1, iterations):
                disc_curve = self.mdl_interest.discount_curve(spread=spread).loc[cfs.index]
                spread -= (bond_data['Market Value'] / (cfs * disc_curve).sum() - 1) / duration
                disc_curve = self.mdl_interest.discount_curve(spread=spread).loc[cfs.index]
                duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (cfs * disc_curve).sum()

            self.cache[f'pd_spreads_{iterations}'] = spread
        return self.cache[f'pd_spreads_{iterations}']

    def ifrs_if_probs(self):
        if 'ifrs_if_probs' not in self.cache:
            ifrs_default_adj = self.ifrs_default_adj.copy()
            def_probs = pd.DataFrame(ifrs_default_adj['D'], columns=[1])
            # def_probs.columns = [1]
            for i in range(1, int(self.df_bond_portfolio['Maturity'].max())+1):
                ifrs_default_adj = ifrs_default_adj.dot(self.ifrs_default_adj)
                def_probs[i] = ifrs_default_adj['D']
            self.cache[f'ifrs_if_probs'] = pd.DataFrame((1.00 - def_probs).loc[self.df_bond_portfolio['Rating']].T.to_numpy(), index=def_probs.columns, columns=self.df_bond_portfolio.index)
        return self.cache[f'ifrs_if_probs']

    def bond_pcfs(self, aggregate=False):

        if f'bond_pcfs{aggregate}' not in self.cache:

            # Create dataframe of zeros to hold bond PCFs once calculated
            df_pcfs = pd.DataFrame(np.zeros(shape=(int(self.df_bond_portfolio['Maturity'].max()), self.df_bond_portfolio.shape[0])), columns=self.df_bond_portfolio.index)
            df_pcfs.index += 1

            # For each bond, use the nominal, coupon rate, and maturity date to populate dataframe with bond's PCFs
            for m, n, c, isin in zip(self.df_bond_portfolio['Maturity'], self.df_bond_portfolio['Nominal'], self.df_bond_portfolio['Coupon Rate'], self.df_bond_portfolio.index):
                df_pcfs.loc[df_pcfs.index <= m, isin] = n * c
                df_pcfs.loc[m, isin] += n

            if aggregate:
                df_pcfs = df_pcfs.sum(axis=1)
            self.cache[f'bond_pcfs{aggregate}'] = df_pcfs

        return self.cache[f'bond_pcfs{aggregate}']

    def def_adj_bond_pcfs(self, aggregate=False):
        if f'def_adj_bond_pcfs_{aggregate}' not in self.cache:
            if_probs = self.ifrs_if_probs()
            bond_pcfs = self.bond_pcfs()
            if_probs.columns = bond_pcfs.columns
            res = bond_pcfs * if_probs
            if aggregate:
                res = res.sum(axis=1)
            self.cache[f'def_adj_bond_pcfs_{aggregate}'] = res
        return self.cache[f'def_adj_bond_pcfs_{aggregate}']

    def pvs(self, aggregate=True):
        if f'pvs_{aggregate}' not in self.cache:
            # Use interest rate model to calculate risky discount curve for each bond and store in array
            ir = self.mdl_interest.discount_curve(spread=self.df_bond_portfolio['Spread'])#.T.iloc[:, :400]

            # Discount each bond's PCFs using the associated risky discount curve and PCF PVs for each bond
            pvs = np.sum(ir * self.bond_pcfs(), axis=1)

            # Sum all bond PVs if required
            if aggregate:
                self.cache[f'pvs_{aggregate}'] = pvs.sum()
            else:
                self.cache[f'pvs_{aggregate}'] = pvs
        return self.cache[f'pvs_{aggregate}']

    def pd_adj_pvs(self, aggregate=True):
        if f'pd_adj_pvs_{aggregate}' not in self.cache:
            pcfs = self.def_adj_bond_pcfs()
            ir = self.mdl_interest.discount_curve().loc[pcfs.index, 0]

            # Discount each bond's PCFs using the associated risky discount curve and PCF PVs for each bond
            pvs = ir.dot(pcfs)

            # Sum all bond PVs if required
            if aggregate:
                self.cache[f'pd_adj_pvs_{aggregate}'] = pvs.sum()
            else:
                self.cache[f'pd_adj_pvs_{aggregate}'] = pvs
        return self.cache[f'pd_adj_pvs_{aggregate}']



if __name__ == '__main__':

    mdl_ir = InterestRate('example_ir.csv')
    df_bonds = pd.read_csv('inputs/bond_data_inputs/example_bonds.csv', index_col='ISIN')
    mdl_bonds = BondPortfolio(mdl_ir, df_bonds)

    v = mdl_bonds.market_value()

    print(v)


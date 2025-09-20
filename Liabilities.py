from Annuity import Annuity
from InterestRates import InterestRate
from Mortality import Mortality

import pandas as pd


class Liabilities:
    def __init__(self, int_rate_model, mortality_model, annuity_model, annuity_margin=0.0):

        # Instantiate inputs as class attributes
        self.AnnuityModel = annuity_model
        self.InterestRateModel = int_rate_model
        self.MortalityModel = mortality_model
        self.ann_margin = annuity_margin


    def premiums(self):
        # Calculate premiums receieved for business written as the best estimate value of liabilities scaled by
        # targeted premium on new business
        ann_prems = self.best_est_value(0) * (1 + self.ann_margin)
        return ann_prems

    # TODO: IR curve should also be rolled forward
    def bel_runoff(self):
        cfs = pd.DataFrame(self.best_est_cfs())
        res = []
        for i in cfs.index:
            res.append(self.InterestRateModel.present_value(cfs.loc[i:].reset_index()))
        return cfs

    def best_est_cfs(self, aggregate=True):
        return self.AnnuityModel.expected_cfs(aggregate=aggregate)

    def best_est_value(self, ir_shock=0.0):
        # Calculate best estimate value of annuities using annuity model
        ann_val = self.AnnuityModel.value(stress='Base', ir_shock=ir_shock)
        return ann_val

    """
    def sii_value(self):
        # Calculate SII value of annuities using annuity model
        ann_val = self.AnnuityModel.solvency_value()
        return ann_val
    """

if __name__ == '__main__':
    print('Done')
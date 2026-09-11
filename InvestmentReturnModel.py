import numpy as np
import pandas as pd


# TODO: Alternative models (other than GBM)
class InvestmentReturnModel:

    # TODO: Only works with step_size=1
    def __init__(self, step_size, proj_start, proj_end, annual_drift, annual_vol, seed=None):

        self.step_size = step_size
        self.proj_start = proj_start
        self.proj_end = proj_end + 1
        self.projection_term = proj_end - proj_start
        self.annual_drift = annual_drift
        self.annual_vol = annual_vol

        if seed is not None:
            np.random.seed(seed)

    def simulate(self):

        simulations = np.random.normal(self.annual_drift, self.annual_vol, size=self.projection_term+1)
        return pd.DataFrame(simulations, index=np.arange(self.proj_start, self.proj_end))

if __name__ == '__main__':

    mdl = InvestmentReturnModel(1, -3, 100, 0.03, 0.01, 0)
    print(mdl.simulate())

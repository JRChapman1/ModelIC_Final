import numpy as np


# TODO: Alternative models (other than GBM)
class InvestmentReturnModel:

    # TODO: Only works with step_size=1
    def __init__(self, step_size, projection_term, annual_drift, annual_vol, seed=None):

        self.step_size = step_size
        self.projection_term = projection_term
        self.annual_drift = annual_drift
        self.annual_vol = annual_vol

        if seed is not None:
            np.random.seed(seed)

    def simulate(self):

        return np.random.normal(self.annual_drift, self.annual_vol, size=self.projection_term)


if __name__ == '__main__':

    mdl = InvestmentReturnModel(1, 100, 0.03, 0.01, 0)
    print(mdl.simulate())

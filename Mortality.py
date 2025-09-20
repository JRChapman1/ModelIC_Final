# Import external libraries
import pandas as pd
import numpy as np
from typing import Union

from globals import UserDefinedGlobals as udg


class Mortality:

    def __init__(self, lapse_rate: Union[np.array, float] = 0.0, mortality_stress: str = None, mortality_scalar: float = 1.0) -> object:

        # Check that passed arguments are of the correct type
        if not isinstance(lapse_rate, (float, np.ndarray, np.array)):
            raise TypeError('The lapse_rate argument of the Mortality class must be either a numpy array or a float')
        if not isinstance(mortality_stress, str) and mortality_stress is not None:
            raise TypeError('The mortality_stress argument of the Mortality class must be a string')
        if not isinstance(mortality_scalar, float):
            raise TypeError('The mortality_scalar argument of the Mortality class must be a float')

        # Save class arguments as (public) properties
        self.lapse_rate = lapse_rate
        self.mortality_stress = mortality_stress
        self.mortality_scalar = mortality_scalar

        # Read in mortality data (as private property) from csv file and apply stress/scalar
        self.__base_mortality = pd.read_csv('inputs/base_mortality.csv', index_col='Age')
        self.__stress_mortality = self.__apply_stress(self.__base_mortality, mortality_stress, mortality_scalar)

    # Returns the conditional probability that a person will survive to the age of x+1, given that they are currently
    # age x
    def q(self, x: Union[int, pd.Series, list, np.array]) -> pd.Series:
        return self.__stress_mortality.loc[x, 'Death Prob']

    # Returns the probability that a person aged x will still be alive at age y (for x < y <= 120) and will not have
    # chosen to voluntarily lapse their policy
    def prob_in_force(self) -> pd.DataFrame:

        qx_curve = self.__stress_mortality['Death Prob'].to_list()
        df_qx = pd.DataFrame([[0] + qx_curve[i:] + [0] * i for i in range(len(qx_curve))], index=list(range(17, 121)))

        if type(self.lapse_rate) == np.ndarray:
            lapse_rate = np.insert(self.lapse_rate, 0, 0.0)[:-1]
        else:
            lapse_rate = np.array([0] + [self.lapse_rate] * udg.proj_term)

        decrement_probs = (df_qx + lapse_rate - df_qx * lapse_rate).clip(0, 1)
        cond_if_probs = (1 - decrement_probs)
        if_probs = cond_if_probs.cumprod(axis=1)

        return if_probs

    # Returns the probability that a life aged x will die at age y (for x < y <= 120)
    def prob_death(self) -> pd.DataFrame:

        df_prob_in_force = self.prob_in_force()
        qx_curve = (self.q([x for x in range(17, 121)])).to_list()
        df_qx = pd.DataFrame([qx_curve[i:] + [0] * (i+1) for i in range(0, len(qx_curve))], index=[x for x in range(17, 121)])
        decrement_probs = (df_qx + self.lapse_rate - df_qx * self.lapse_rate).clip(0, 1)
        df_prob_death = decrement_probs * df_prob_in_force
        df_prob_death.columns += 1

        return df_prob_death

    # Applies stresses (from stress data csv file) and/or multiplies conditional death probabilities by user-defined
    # scalar
    @staticmethod
    def __apply_stress(base_mortality_curve, stress, scalar):

        base_mortality_curve['Death Prob'] *= scalar
        if stress is not None:
            mort_stress_factors = pd.read_csv('inputs/mortality_stress_factors.csv', index_col='Stress')
            base_mortality_curve['Death Prob'] *= mort_stress_factors.loc[stress, 'Factor']

        return base_mortality_curve.clip(0, 1)


if __name__ == '__main__':
    model = Mortality()
    death_probabilities = model.prob_death()
    print(death_probabilities)

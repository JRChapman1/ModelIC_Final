from enquirer import RunManager
import pandas as pd
import numpy as np


class UnitTests:

    def __init__(self):

        self.ann_dataset = 'example_bonds.csv'
        self.ltm_dataset = 'example_erms.csv'
        self.bond_dataset = 'example_bonds.csv'

        self.regression_vars = {
            'discount_curve': {'Desc': 'discount_curve',
                               'Mdl': 'InterestRate',
                               'Mthd': 'discount_curve',
                               'FriendlyName': 'Discount Curve'},
            'prob_death': {'Desc': 'prob_death',
                               'Mdl': 'Mortality',
                               'Mthd': 'prob_death',
                               'FriendlyName': 'Death Probabilities'},
            'market_value': {'Desc': 'market_value',
                               'Mdl': 'BondPortfolio',
                               'Mthd': 'market_value',
                               'FriendlyName': 'Bond Market Value'}
        }

        self.mdl_run_manager = RunManager(list(self.regression_vars.values()), self.ann_dataset, self.ltm_dataset, self.bond_dataset)

    def model_output(self, tolerance):

        results_summary = {}
        model_results = self.mdl_run_manager.results()

        for var, model_res in model_results.items():
            regression_res = pd.read_csv(f'regression/{var}.csv', header=None).to_numpy()

            if isinstance(model_res, (np.float64, float)):
                regression_res = float(regression_res)
            else:
                model_res = model_res.to_numpy()

            test1 = np.nan_to_num(np.abs((model_res - regression_res) / regression_res))
            test2 = np.abs(model_res - regression_res)
            test3 = np.maximum(test1, test2)

            friendly_name = self.regression_vars[var]['FriendlyName']
            results_summary[friendly_name] = float(test3.max()) < tolerance

        return results_summary


if __name__ == '__main__':

    r = UnitTests()
    res = r.model_output(10**-5)

    all_passed = True

    print('\n')
    print('-' * 50)
    for k, v in res.items():

        all_passed = all_passed and v

        if v:
            status = "PASS"
        else:
            status = "FAIL"

        indentation = 8 - int(len(k) / 4)
        spacing = '\t' * indentation

        print(f'{k}{spacing}{status}')
    print('\n')
    print('-' * 50)
    print(f'ALL TESTS PASSED\t\t\t\t{all_passed}')
    print('-' * 50)

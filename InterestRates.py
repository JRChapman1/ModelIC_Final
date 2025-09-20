# Import external libraries
import pandas as pd
import numpy as np

# Import custom classes
from globals import UserDefinedGlobals as udg


class InterestRate:

    def __init__(self, curve_name: str = udg.default_ir_curve, ir_stress: str = None, ir_shock: float = 0.0):

        # Read in chosen interest rate curve
        self.curve_name = curve_name
        self.base_annual_spot = pd.read_csv(f'inputs/ir_curve_inputs/{curve_name}', index_col='Term')

        # Apply chosen stress (if applicable)
        self.stress = ir_stress
        self.shock = ir_shock
        self.apply_stress(ir_stress, ir_shock)

        # Initialise class level cache
        self.cache = {}

    def spot_curve(self, spread=0.0):

        # Only construct curve if it is not contained in the cache
        if f'spot_curve_{spread}' not in self.cache:

            # Construct empty data frame to put curve into.
            df_spot_curve = pd.DataFrame(index=range(0, self.base_annual_spot.index.max() + 1))

            # Get the unprocessed annual spot rate for each step by merging on the year to which the rate is
            # applicable
            df_spot_curve = df_spot_curve.merge(self.base_annual_spot, left_index=True, right_index=True, how='left')

            # Calculate discount curve from the spot curve, adding a spread if necessary
            # TODO: Refactor
            if type(spread) == float or type(spread) == int or type(spread) == np.float64:
                df_spot_curve = spread + df_spot_curve['Rate'].to_numpy().reshape(-1, 1)  # ** (-df_spot_curve.index)
            else:
                df_spot_curve = spread.to_numpy().reshape(1, -1) + df_spot_curve['Rate'].to_numpy().reshape(-1, 1)  # ** (-df_spot_curve.index)

            # Convert the annual spot rates to rates with the desired step size and cache the result
            curve = pd.DataFrame((1 + df_spot_curve) - 1)
            if type(spread) == pd.Series:
                curve.columns = spread.index

            self.cache[f'spot_curve_{spread}'] = curve



        return self.cache[f'spot_curve_{spread}']

    def continuous_spot_curve(self, spread=0.0):

        # Only construct curve if not contained in cache
        if f'continuous_spot_curve{spread}' not in self.cache:

            # Construct continuous spot curve from annual spot curve
            annual_spot = self.spot_curve(spread)
            continuous_spot = np.log(annual_spot + 1)

            self.cache[f'continuous_spot_curve{spread}'] = continuous_spot

        return self.cache[f'continuous_spot_curve{spread}']

    def discount_curve(self, spread=0):

        # Only construct curve if it is not contained in the cache
        if f'discount_curve_{spread}' not in self.cache:

            # Get spot curve as-at rebase step
            df_spot_curve = self.spot_curve(spread=spread)

            # Calculate discount curve from the spot curve, adding a spread if necessary
            df_discount_curve = (1 + df_spot_curve).pow(-df_spot_curve.index, axis=0)

            # Cache the calculated discount curve
            self.cache[f'discount_curve_{spread}'] = df_discount_curve

        # Returned cached curve
        return self.cache[f'discount_curve_{spread}']

    def one_step_disc_facs(self, spread=0):

        # Only construct curve if it is not contained in the cache
        if f'one_step_disc_facs_{spread}' not in self.cache:

            # Construct discount curve
            disc_curve = self.discount_curve(spread)

            # Construct copy of discount curve with values shifted one step backwards
            disc_curve_rf = disc_curve.copy()
            disc_curve_rf.index += 1

            # Divide discount curve by shifted discount curve to construct one-step discount factors
            one_step_disc_facs = disc_curve / disc_curve_rf

            # Replace NaNs
            one_step_disc_facs.iloc[0] = 1.0
            one_step_disc_facs.iloc[-1] = one_step_disc_facs.iloc[-2]

            # Cache calculated curve
            self.cache[f'one_step_disc_facs_{spread}'] = one_step_disc_facs

        return self.cache[f'one_step_disc_facs_{spread}']

    def present_value(self, cfs, spread=0, aggregate=True):

        # Multiply cashflows by discount
        pvs = cfs.to_numpy() * self.discount_curve(spread).loc[cfs.index].to_numpy()
        pvs = pd.DataFrame(pvs.sum(axis=0), columns=['PV'])

        # Aggregate cashflows if required
        if aggregate:
            pvs = float(pvs.sum())

        return pvs

    def copy(self):

        # Return new instance of model
        return InterestRate(self.curve_name, self.stress, self.shock)

    def apply_stress(self, stress, shock=0.0):

        self.base_annual_spot['Rate'] += shock

        # For SII stress a prescribed spot rate shock curve should be used. The formula for applying this shock curve is
        # {base curve} - {shock curve} * |{base curve}|
        if stress == 'SII_Up' or stress == 'SII_Down':
            sii_spot_rate_stress = pd.read_csv('inputs/sii_interest_rate_stress.csv', index_col='Term')
            direction = stress.split('_')[-1]

            base_spot = self.base_annual_spot['Rate'].copy()
            base_spot[base_spot < 0.0] = 0.0
            self.base_annual_spot = pd.DataFrame(
                self.base_annual_spot['Rate'] + sii_spot_rate_stress[direction] * base_spot, columns=['Rate'])

        # For an AAA interest rate stress we assume that spot rates are zero at all terms
        if stress == 'AAA':
            self.base_annual_spot['Rate'] = 0

        # For an AA interest rate stress we assume that spot rates are 50% of best estimate spot rates at all terms
        if stress == 'AA':
            self.base_annual_spot['Rate'] *= 0.5


if __name__ == '__main__':

    mdl_ir = InterestRate('gbp_sonia_ye22_c2.csv')
    print(mdl_ir.discount_curve())

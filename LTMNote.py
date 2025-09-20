# Import external libraries
import pandas as pd
import numpy as np
from scipy import optimize

# Import custom classes
from ERM import ERM
from InterestRates import InterestRate
from Mortality import Mortality


class LTMNote:

    def __init__(self, best_est_ltm_model, int_rate_model, lapse_rate=0.01):

        # Store parameters as attributes
        self.best_est_ltm_model = best_est_ltm_model
        self.erm_policies = best_est_ltm_model.df_ltm_pols
        self.lapse_rate = lapse_rate

        # Create instance of interest rate model
        self.mdl_interest = int_rate_model

        # Instantiate cache
        self.cache = {}

    # TODO: HPI vol hardcodeed in all calls to expected_redemption_cfs_net_of_mkt_nneg
    def capital_scenario(self):

        # Create dictionary of capital scenario stresses
        stresses = {
            'AAA':
                {
                    'HPI': 0,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.35,
                    'Lapse Rate': np.array([0.15] * 5 + [self.lapse_rate] * 100)
                },
            'AA':
                {
                    'HPI': 0.015,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.3,
                    'Lapse Rate': np.array([0.1] * 5 + [self.lapse_rate] * 100)
                },
            'A':
                {
                    'HPI': 0.02,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.25,
                    'Lapse Rate': np.array([0.08] * 5 + [self.lapse_rate] * 100)
                },
            'BBB':
                {
                    'HPI': 0.025,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.2,
                    'Lapse Rate': np.array([0.06] * 5 + [self.lapse_rate] * 100)
                },
            'BB':
                {
                    'HPI': 0.03,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.15,
                    'Lapse Rate': np.array([0.04] * 5 + [self.lapse_rate] * 100)
                }
        }

        # Create empty dataframe to populate with LTM stressed pcfs once calculated
        pcfs = pd.DataFrame()

        # Under each stress in dictionary of stresses, use the ERM model to calculate the LTM PCFs
        for name, definition in stresses.items():

            mdl_mortality = Mortality(definition['Lapse Rate'], f'{name}_up')
            mdl_eq_rel = ERM(mdl_mortality,
                             self.mdl_interest,
                             self.erm_policies.copy(),
                             definition['HPI'],
                             definition['HPI Vol'],
                             definition['Prop Shock'])

            pcfs[name] = mdl_eq_rel.expected_redemption_cfs_net_of_int_nneg().sum(axis=1)

        return pcfs

    def liquidity_scenario(self):

        # Create dictionary of liquidity scenario stresses
        stresses = {
            'AAA':
                {
                    'HPI': 0,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.35,
                    'Lapse Rate': np.array([0.005] * 105)
                },
            'AA':
                {
                    'HPI': 0.015,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.3,
                    'Lapse Rate': np.array([0.005] * 105)
                },
            'A':
                {
                    'HPI': 0.02,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.25,
                    'Lapse Rate': np.array([0.005] * 105)
                },
            'BBB':
                {
                    'HPI': 0.025,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.2,
                    'Lapse Rate': np.array([0.005] * 105)
                },
            'BB':
                {
                    'HPI': 0.03,
                    'HPI Vol': 0.13,
                    'Prop Shock': 0.15,
                    'Lapse Rate': np.array([0.005] * 105)
                }
        }

        # Create empty dataframe to populate with LTM stressed pcfs once calculated
        pcfs = pd.DataFrame()

        # Under each stress in dictionary of stresses, use the ERM model to calculate the LTM PCFs
        for name, definition in stresses.items():

            mdl_mortality = Mortality(definition['Lapse Rate'], f'{name}_down')
            mdl_eq_rel = ERM(mdl_mortality,
                             self.mdl_interest,
                             self.erm_policies.copy(),
                             definition['HPI'],
                             definition['HPI Vol'],
                             definition['Prop Shock'])

            pcfs[name] = mdl_eq_rel.expected_redemption_cfs_net_of_int_nneg().sum(axis=1)

        return pcfs

    def unsmoothed_cumulative_note_pcfs(self):

        # Calculate LTM PCFs under capital and liquidity stresses
        liq = self.liquidity_scenario()
        cap = self.capital_scenario()

        # Take the cumulative unsmoothed XXX rated LTM note's PCFs to the be the minimum of the XXX rated capital and
        # liquidity scenario PCF at each time
        note_pcfs = np.minimum(cap, liq)[1:]

        # Set the cumulative equity tranches PCFs to be the best estimate redemption CFs of all LTMs
        note_pcfs['ET'] = self.best_est_ltm_model.expected_redemption_cfs().sum(axis=1)

        return note_pcfs

    def gross_ltm_value(self):

        # Calculate the gross LTM value as the PV of expected redemption CFs
        gross_ltm_pcfs = self.best_est_ltm_model.expected_redemption_cfs()
        disc_curve = self.mdl_interest.discount_curve()
        return float(gross_ltm_pcfs.multiply(disc_curve.loc[:gross_ltm_pcfs.shape[0], 0], axis=0).sum(axis=0).sum())

    def note_attachment_points(self):

        # Calculate cumulative unsmoothed note PCFs
        unsmoothed_pcfs = self.unsmoothed_cumulative_note_pcfs()

        # Calculate the cumulative risk-free note values as the PV of the unsmoothed cumulative note PCFs
        disc_curve = self.mdl_interest.discount_curve()
        cumulative_note_rf_vals = unsmoothed_pcfs.multiply(disc_curve.loc[:unsmoothed_pcfs.shape[0], 0], axis=0).sum(axis=0)

        # Calculate the note attachment points as the cumulative note value as a proportion of gross LTM value
        return cumulative_note_rf_vals / self.gross_ltm_value()

    def risk_neutral_note_vals(self):

        # Discount the LTM note PCFs at the risk-free rate
        note_pcfs = self.note_pcfs()[1:]
        disc_curve = self.mdl_interest.discount_curve()
        return note_pcfs.multiply(disc_curve.loc[:note_pcfs.shape[0], 0], axis=0).sum(axis=0)


    def smoothed_cumulative_note_pcfs(self):

        # Get best estimate LTM redemption cashflows and note attachment points
        gross_ltm_pcfs = self.best_est_ltm_model.expected_redemption_cfs().sum(axis=1)
        attch = self.note_attachment_points()

        # For each note, scale the BE LTM redemption CFs by the note's attachment point to get smoothed cumulative note
        # PCFs
        return pd.DataFrame(gross_ltm_pcfs.to_numpy().reshape(-1, 1) * attch.to_numpy(), index=gross_ltm_pcfs.index, columns=attch.index)

    def note_pcfs(self):
        if 'note_pcfs' not in self.cache:

            # Get smoothed cumulative note PCFs
            smoothed_cumulative_pcfs = self.smoothed_cumulative_note_pcfs()

            # Difference smoothed cumulative note PCFs to get (incremental) smoothed note PCFs
            incremental_pcfs = pd.DataFrame(smoothed_cumulative_pcfs.iloc[:, 0], index=smoothed_cumulative_pcfs.index)
            for col1, col2 in zip(smoothed_cumulative_pcfs.columns[1:], smoothed_cumulative_pcfs[:-1]):
                incremental_pcfs[col1] = smoothed_cumulative_pcfs[col1] - smoothed_cumulative_pcfs[col2]

            self.cache['note_pcfs'] = incremental_pcfs

        return self.cache['note_pcfs']


    def risk_adj_note_vals(self):

        # Return the risk neutral value of LTM notes minus the marginal NNEG risk associated with each note
        return self.risk_neutral_note_vals() - self.marginal_nneg_values()

    def note_nneg_spread(self):

        if 'note_nneg_spread' not in self.cache:

            # Calculate note PCFs and risk-adjusted note values
            cfs = self.note_pcfs()
            val = self.risk_adj_note_vals()

            # Create series of zeros to populate with note spreads once calculated
            spread = pd.Series([0.0] * val.shape[0], index=val.index)

            # Get risky discount curve (risk-free rate plus note spreads) for each note using interest rate model
            disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
            disc_curve.index = cfs.index

            # Iteratively calculate note spreads which equate risk-adjusted note PCFs and risk-adjusted note values
            duration = cfs.multiply(disc_curve * disc_curve.index, axis=0).sum(axis=0) / cfs.multiply(disc_curve, axis=0).sum(axis=0)
            for i in range(1, 10):
                disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
                spread -= (val / cfs.multiply(disc_curve, axis=0).sum(axis=0) - 1) / duration
                disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
                duration = cfs.multiply(disc_curve * disc_curve.index, axis=0).sum(axis=0) / cfs.multiply(disc_curve, axis=0).sum(axis=0)

            self.cache['note_nneg_spread'] = spread

        return self.cache['note_nneg_spread']

    def total_nneg_spread(self):

        if 'total_nneg_spread' not in self.cache:

            # Calculate best estimate NNEG cashflows anf value
            total_nneg_cfs = self.best_est_ltm_model.expected_mkt_nneg_val(True, 1.0)

            # TODO: IR curve hardcoded
            total_nneg = sum([cf * 1.04 ** (-t) for cf, t in zip(total_nneg_cfs, range(1, len(total_nneg_cfs) + 1))])

            # Calculate best estimate LTM redemption CFs and PV net of intrinsic NNEG
            cfs = self.best_est_ltm_model.expected_redemption_cfs_net_of_int_nneg().sum(axis=1)[:61]

            # TODO: Discount curve hardcoded
            pv_be_cfs = sum([cf * 1.04 ** (-t) for cf, t in zip(cfs, range(1, len(cfs) + 1))])

            # Calculate total LTM CF PV as the BE PV of redemptions less the BE PV of both intrinsic and market NNEG
            val = pv_be_cfs - total_nneg

            # Iteratively solve to find NNEG spread that equates BE LTM PV net of intrinsic and market NNEG with BE LTM
            # redemtion CFs net of intrinsic NNEG
            spread = 0.0
            disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
            disc_curve.index = cfs.index
            duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (cfs * disc_curve).sum()
            for i in range(1, 10):
                disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
                spread -= (val / (cfs * disc_curve).sum() - 1) / duration
                disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
                duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (
                            cfs * disc_curve).sum()

            self.cache['total_nneg_spread'] = spread

        return self.cache['total_nneg_spread']

    def gross_spread(self):

        if 'gross_spread' not in self.cache:

            # Calculate BE value of LTMs and BE LTM redemption CFs net of intrinsic NNEG
            val = self.best_est_ltm_model.ifrs_value()
            cfs = self.best_est_ltm_model.expected_redemption_cfs_net_of_int_nneg().sum(axis=1)[:61]

            # Iteratively solve for spread that equates BE LTM redemption CFs net of intrinsic NNEG to BE LTM value
            spread = 0.0
            disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
            disc_curve.index = cfs.index
            duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (
                        cfs * disc_curve).sum()
            for i in range(1, 10):
                disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
                spread -= (val / (cfs * disc_curve).sum() - 1) / duration
                disc_curve = self.mdl_interest.discount_curve(spread=spread).iloc[:cfs.shape[0], 0]
                duration = (cfs * disc_curve.multiply(disc_curve.index, axis=0)).sum() / (
                        cfs * disc_curve).sum()

            self.cache['gross_spread'] = spread

        return self.cache['gross_spread']

    def total_liquidity_spread(self):

        # Return the gross LTM spread less the LTM NNEG spread
        return self.gross_spread() - self.total_nneg_spread()

    def marginal_nneg_values(self):

        # Calculate note attachment points
        attachment_points = self.note_attachment_points()

        # Construct risk-free discount curve using interest rate model
        disc_curve = self.best_est_ltm_model.mdl_interest.discount_curve().loc[:105, 0]

        # Calculate NNEG values for each note attachment point
        cumulative_nneg_values = [(self.best_est_ltm_model.expected_mkt_nneg_val(True, a) * disc_curve).sum() for a in attachment_points]

        # Difference attachment point NNEGs to get (marginal) NNEG values applying to each note
        marginal_nneg_values = [cumulative_nneg_values[0]] + [v2 - v1 for v1, v2 in zip(cumulative_nneg_values[:-1], cumulative_nneg_values[1:])]
        return marginal_nneg_values

    def total_value(self, lp_ratio):

        # Calculate total note spreads as sum of NNEG spreads and liquidity spreads
        note_nneg_spreads = self.note_nneg_spread()
        lp_spread = self.total_liquidity_spread() / 2
        note_total_spreads = note_nneg_spreads + lp_spread + (note_nneg_spreads * lp_ratio)

        # Calculate note PCFs
        cfs = self.note_pcfs()[1:]

        # Construct risky discount curve (risk-free plus total note spread) using interest rate model
        disc_curve = self.mdl_interest.discount_curve(spread=note_total_spreads).iloc[:cfs.shape[0], :]

        # Calculate PV of note PCFs using risky discount curve
        return ((cfs * disc_curve.to_numpy()).sum().sum() - self.best_est_ltm_model.ifrs_value()) ** 2


    def goalseek_note_spreads(self):

        # Goalseek the LP ratio that give note spreads that equate the sum of note values with the IFRS value of LTMs
        return optimize.minimize_scalar(self.total_value).x


    def note_spreads(self):

        # Note spreads are equal to the NNEG spread on each note, plus the liquidity spread on all LTMs, plus the NNEG
        # spread on each note scaled by the LP ratio
        note_nneg_spreads = self.note_nneg_spread()
        lp_spread = self.total_liquidity_spread() / 2
        lp_ratio = self.goalseek_note_spreads()
        return note_nneg_spreads + lp_spread + (note_nneg_spreads * lp_ratio)

    def note_values(self):

        # Discounts the note PCFs at a risky-discount curve (risk-free plus note spread)
        note_spreads = self.note_spreads()
        note_pcfs = self.note_pcfs()[1:]
        disc_curve = self.mdl_interest.discount_curve(spread=note_spreads).iloc[:note_pcfs.shape[0], :]
        disc_curve.columns = note_pcfs.columns
        return (note_pcfs * disc_curve).sum(axis=0)


if __name__ == '__main__':

    for method in dir(LTMNote):
        if method[:2] != "__":
            print(method)
    mdl_ir = InterestRate('gbp_sonia_ye22.csv')
    ltm_pols = pd.read_csv('inputs/ltm_data_inputs/JRL_c2.csv')
    MdlEqRel = ERM(Mortality(), mdl_ir, ltm_pols, 0.03, 0.13)
    MdlNote = LTMNote(MdlEqRel, mdl_ir)
    foo = MdlNote.liquidity_scenario()
    print(foo)

import pandas as pd
from Mortality import Mortality
from InterestRates import InterestRate


# TODO: If PH shares in expense surplus, are notional charges still levied (with residual applied as seperate
#  adjustment)?

"""
ASSUMPTIONS AND SIMPLIFICATIONS

 * Following cashflows occur at start of year:
    * Premiums
    * Expenses
    * Charges
    

"""

class WithProfitsEndowment:

    def __init__(self, sources_of_policyholder_surplus, shareholder_surplus_proportion):
        self.sources_of_policyholder_surplus = sources_of_policyholder_surplus
        self.shareholder_surplus_proportion = shareholder_surplus_proportion

    def project_asset_share(self):
        """
        Project assets share as premiums + surrender profits + expense experience + np profits
        + windfall (e.g. unexpected tax gain) + estate transfers - charges for expenses - charges for life cover - tax
        - shareholder transfers - smoothing charges - charges for options and guarantees - charges for cost of capital
        """
        pass

    def determine_regular_reversionary_bonuses(self):
        pass

    # TODO
    def determine_special_reversionary_bonuses(self):
        pass

    def determine_terminal_bonus(self):
        pass

    def determine_death_benefits(self):
        pass

    def determine_maturity_benefits(self):
        pass

    # TODO
    def determine_surrender_benefits(self):
        pass

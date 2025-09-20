class BonusPolicy:

    def __init__(self, target_terminal_bonus_proportion, simple_moving_average_period):

        self.target_terminal_bonus_proportion = target_terminal_bonus_proportion
        self.simple_moving_average_period = simple_moving_average_period

    def determine_regular_reversionary_bonus(self, surplus_realised):
        pass

    def determine_terminal_bonus(self, guaranteed_benefits, asset_share):
        pass



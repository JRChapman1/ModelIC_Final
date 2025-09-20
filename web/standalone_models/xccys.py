import numpy as np


def xccy_value(pay_leg_notional=50000000,
               pay_leg_coupon=0.02327,
               pay_leg_rfr=0.0353,
               rec_leg_notional=39542451.03,
               rec_leg_coupon=0.04631,
               rec_leg_rfr=0.0579689608597488,
               fx=1.2139,
               term=20):
    timings = np.arange(1, term + 1)
    pay_leg_cfs = np.repeat(pay_leg_notional * pay_leg_coupon, term)
    pay_leg_cfs[-1] += pay_leg_notional
    rec_leg_cfs = np.repeat(rec_leg_notional * rec_leg_coupon, term)
    rec_leg_cfs[-1] += rec_leg_notional
    return np.dot(rec_leg_cfs, np.power(1 + rec_leg_rfr, -timings))\
        - np.dot(pay_leg_cfs, np.power(1 + pay_leg_rfr, -timings))/fx

if __name__ == '__main__':
    print(xccy_value())


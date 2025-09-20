from scipy.special import beta, hyp2f1, polygamma
from scipy import integrate
from scipy.optimize import minimize_scalar
from math import exp, factorial
from random import uniform
import numpy as np


class EGB2:

    def __init__(self, d, s, p, q):
        self.d = d
        self.s = s
        self.p = p
        self.q = q

    def pdf(self, z):
        numerator = exp(self.p * (z - self.d) / self.s)
        denominator = abs(self.s) * beta(self.p, self.q) * (1 + exp((z - self.d) / self.s)) ** (self.p + self.q)
        return numerator / denominator

    def cdf(self, z):
        return integrate.quad(self.pdf, 0, z)[0]

    def inv_cdf(self, p):
        return minimize_scalar(lambda z: abs(self.cdf(z) - p))['x']

    def mgf(self, t):
        f = hyp2f1(self.p + t * self.s, t * self.s, 1, self.p + self.q + t * self.s)
        numerator = exp(self.d * t) * beta(self.p + t * self.s, self.q) * f
        denominator = beta(self.p, self.q)
        return numerator / denominator

    @staticmethod
    def __incr_fac(x, n):
        return factorial(x + n - 1) / factorial(x - 1)

    @staticmethod
    def __incr_fac_deriv_1(self, x, n):
        return self.__incr_fac(x, n) * (polygamma(0, n + x) - polygamma(0, x))


if __name__ == '__main__':
    num_sims = 10
    dist = EGB2(2, 2, 2, 2)
    t = 1
    x = 0.01
    h = 0.000001
    u = dist.mgf(x+h)
    l = dist.mgf(x)
    print(f'mean = {(u - l) / h}')
    rand_uniform = np.random.uniform(size=num_sims)
    rand_egb2 = [exp(dist.inv_cdf(x) * t) for x in rand_uniform]
    print(sum(rand_egb2) / num_sims)


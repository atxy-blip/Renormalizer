# -*- coding: utf-8 -*-

from renormalizer.model import Phonon, Mol, HolsteinModel
from renormalizer.utils import Quantity, EvolveConfig, CompressConfig, CompressCriteria, EvolveMethod
from renormalizer.utils.constant import cm2au
from renormalizer.transport import ChargeDiffusionDynamics, InitElectron

import numpy as np

sdf_values = [
[0,   0],
 [2.75735294117647e+000,    9.35483870967742e-004],
 [6.06617647058824e+000,    1.49677419354839e-003],
 [6.61764705882353e+000,    1.98709677419355e-003],
 [8.82352941176471e+000,    2.50967741935484e-003],
 [1.15808823529412e+001,    2.99354838709677e-003],
 [1.54411764705882e+001,    3.76129032258065e-003],
 [1.76470588235294e+001,    4.48387096774194e-003],
 [1.98529411764706e+001,    4.81290322580645e-003],
 [2.15073529411765e+001,    4.88387096774194e-003],
 [2.42647058823529e+001,    4.76774193548387e-003],
 [2.70220588235294e+001,    4.61290322580645e-003],
 [2.81250000000000e+001,    4.57419354838710e-003],
 [3.03308823529412e+001,    4.55483870967742e-003],
 [3.41911764705882e+001,    4.79354838709677e-003],
 [3.58455882352941e+001,    4.78709677419355e-003],
 [3.69485294117647e+001,    4.72903225806452e-003],
 [3.75000000000000e+001,    4.63225806451613e-003],
 [3.91544117647059e+001,    4.41935483870968e-003],
 [4.02573529411765e+001,    4.14193548387097e-003],
 [4.13602941176471e+001,    3.90967741935484e-003],
 [4.19117647058824e+001,    3.70322580645161e-003],
 [4.35661764705882e+001,    3.41290322580645e-003],
 [4.79779411764706e+001,    3.01290322580645e-003],
 [5.07352941176471e+001,    2.69677419354839e-003],
 [5.23897058823529e+001,    2.45161290322581e-003],
 [5.56985294117647e+001,    2.21290322580645e-003],
 [5.84558823529412e+001,    2.09677419354839e-003],
 [6.01102941176471e+001,    2.07096774193548e-003],
 [6.39705882352941e+001,    2.13548387096774e-003],
 [6.78308823529412e+001,    2.36774193548387e-003],
 [6.89338235294118e+001,    2.40645161290323e-003],
 [7.16911764705882e+001,    2.33548387096774e-003],
 [7.38970588235294e+001,    2.13548387096774e-003],
 [7.55514705882353e+001,    1.93548387096774e-003],
 [7.66544117647059e+001,    1.80645161290323e-003],
 [7.83088235294118e+001,    1.65161290322581e-003],
 [8.21691176470588e+001,    1.37419354838710e-003],
 [8.76838235294118e+001,    1.09677419354839e-003],
 [9.20955882352941e+001,    9.03225806451613e-004],
 [9.48529411764706e+001,    7.87096774193548e-004],
 [9.76102941176471e+001,    7.03225806451613e-004],
 [1.02022058823529e+002,    6.51612903225806e-004],
 [1.05330882352941e+002,    6.77419354838710e-004],
 [1.11948529411765e+002,    8.64516129032258e-004],
 [1.13602941176471e+002,    9.35483870967742e-004],
 [1.16360294117647e+002,    9.67741935483871e-004],
 [1.18566176470588e+002,    9.41935483870968e-004],
 [1.20220588235294e+002,    8.64516129032258e-004],
 [1.22977941176471e+002,    7.09677419354839e-004],
 [1.25183823529412e+002,    5.80645161290323e-004],
 [1.27941176470588e+002,    4.64516129032258e-004],
 [1.31801470588235e+002,    4.12903225806452e-004],
 [1.41727941176471e+002,    4.00000000000000e-004],
 [1.47242647058824e+002,    3.48387096774194e-004],
 [1.50000000000000e+002,    3.35483870967742e-004],
 [1.58272058823529e+002,    4.77419354838710e-004],
 [1.62683823529412e+002,    5.35483870967742e-004],
 [1.65441176470588e+002,    6.58064516129032e-004],
 [1.68198529411765e+002,    8.12903225806452e-004],
 [1.69852941176471e+002,    8.90322580645161e-004],
 [1.71507352941176e+002,    8.96774193548387e-004],
 [1.75919117647059e+002,    8.25806451612903e-004],
 [1.80330882352941e+002,    9.80645161290323e-004],
 [1.81433823529412e+002,    1.01935483870968e-003],
 [1.83088235294118e+002,    1.05161290322581e-003],
 [1.85845588235294e+002,    1.07741935483871e-003],
 [1.87500000000000e+002,    1.11612903225806e-003],
 [1.89154411764706e+002,    1.14838709677419e-003],
 [1.91911764705882e+002,    1.12903225806452e-003],
 [1.93566176470588e+002,    1.05161290322581e-003],
 [1.95772058823529e+002,    8.51612903225807e-004],
 [1.99080882352941e+002,    6.12903225806452e-004],
 [2.01838235294118e+002,    3.74193548387097e-004],
 [2.03492647058824e+002,    2.96774193548387e-004],
 [2.07352941176471e+002,    2.70967741935484e-004],
 [2.09007352941176e+002,    2.38709677419355e-004],
 [2.12867647058824e+002,    1.80645161290323e-004],
 [2.19485294117647e+002,    1.80645161290323e-004],
 [2.23345588235294e+002,    1.93548387096774e-004],
 [2.25551470588235e+002,    2.58064516129032e-004],
 [2.28308823529412e+002,    3.35483870967742e-004],
 [2.31066176470588e+002,    4.58064516129032e-004],
 [2.32169117647059e+002,    5.35483870967742e-004],
 [2.35477941176471e+002,    5.48387096774194e-004],
 [2.37683823529412e+002,    4.70967741935484e-004],
 [2.40992647058824e+002,    3.09677419354839e-004],
 [2.44852941176471e+002,    1.93548387096774e-004],
 [2.47610294117647e+002,    1.74193548387097e-004],
 [2.50919117647059e+002,    1.80645161290323e-004],
 [2.53676470588235e+002,    2.51612903225806e-004],
 [2.57536764705882e+002,    2.64516129032258e-004],
 [2.60845588235294e+002,    2.45161290322581e-004],
 [2.63051470588235e+002,    2.19354838709677e-004],
 [2.66360294117647e+002,    1.41935483870968e-004],
 [2.68566176470588e+002,    1.29032258064516e-004],
 [2.71323529411765e+002,    1.54838709677419e-004],
 [2.73529411764706e+002,    2.00000000000000e-004],
 [2.76286764705882e+002,    3.48387096774194e-004],
 [2.78492647058824e+002,    4.32258064516129e-004],
 [2.81250000000000e+002,    4.32258064516129e-004],
 [2.87867647058824e+002,    2.51612903225806e-004],
 [2.89522058823529e+002,    1.67741935483871e-004],
 [2.91727941176471e+002,    9.67741935483871e-005],
 [2.93382352941176e+002,    5.80645161290323e-005],
 [2.96691176470588e+002,    5.16129032258065e-005],
 [2.99448529411765e+002,    2.58064516129032e-005],
]
sdf_values = np.array(sdf_values)

j_matrix_cm = np.array([[310, -98, 6, -6, 7, -12, -10, 38, ],
                        [-98, 230, 30, 7, 2, 12, 5, 8, ],
                        [6, 30, 0, -59, -2, -10, 5, 2, ],
                        [-6, 7, -59, 180, -65, -17, -65, -2, ],
                        [7, 2, -2, -65, 405, 89, -6, 5, ],
                        [-12, 11, -10, -17, 89, 320, 32, -10, ],
                        [-10, 5, 5, -64, -6, 32, 270, -11, ],
                        [38, 8, 2, -2, 5, -10, -11, 505, ], ])

N_PHONONS = 35

TOTAL_HR = 0.42

if __name__ == "__main__":

    omegas_cm = np.linspace(2, 300, N_PHONONS)
    omegas_au = omegas_cm * cm2au
    hr_factors = np.interp(omegas_cm, sdf_values[:, 0], sdf_values[:, 1])

    hr_factors *= TOTAL_HR / hr_factors.sum()

    lams = hr_factors * omegas_au
    phonons = [Phonon.simplest_phonon(Quantity(o), Quantity(l), lam=True) for o,l in zip(omegas_au, lams)]


    j_matrix_au = j_matrix_cm * cm2au

    mlist = []
    for j in np.diag(j_matrix_au):
        m = Mol(Quantity(j), phonons)
        mlist.append(m)

    # starts from 1
    mol_arangement = np.array([7, 5, 3, 1, 2, 4, 6]) - 1
    mol_list = HolsteinModel(list(np.array(mlist)[mol_arangement]), j_matrix_au[mol_arangement][:, mol_arangement], )

    evolve_dt = 160
    evolve_config = EvolveConfig(EvolveMethod.tdvp_ps, guess_dt=evolve_dt)
    compress_config = CompressConfig(CompressCriteria.fixed, max_bonddim=32)
    ct = ChargeDiffusionDynamics(mol_list, evolve_config=evolve_config, compress_config=compress_config, init_electron=InitElectron.fc)
    ct.dump_dir = "./"
    ct.job_name = 'fmo'
    ct.stop_at_edge = False
    ct.evolve(evolve_dt=evolve_dt, evolve_time=40000)
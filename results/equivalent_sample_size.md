# Equivalent sample size (computational labels per experimental Tm label)

Method: marginal rate of substitution from Minami et al. 2025 (npj Comput. Mater. 11:146); gradients approximated from the observed
MAE scaling curves (multitask setting). N_eq = (dMAE/dm_exp)/(dMAE/dn_sim) at the current maximum sample sizes (m=57, n=320/template).

dMAE/dm  (experimental Tm, at m=57): -0.00935 degC per label

FEP equivalent sample size (FEP labels worth one experimental Tm label):
  log-linear fit, per template : 31
  log-linear fit, total (x2)   : 63
  finite-diff (top), per templ : 6
  finite-diff (top), total     : 13

MD Q-value: source MAE does not decrease with more labels, so its equivalent sample size is ~0 experimental labels (no transfer).

Raw curves (count -> MAE degC):
  experimental_Tm: 10:7.554, 20:7.015, 30:7.036, 40:6.687, 57:6.619
  FEP: 10:6.647, 40:6.516, 80:6.349, 160:6.500, 320:6.261
  MD_Qvalue: 10:6.910, 40:6.615, 80:6.612, 160:6.764, 320:6.739, 640:6.652

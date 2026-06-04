# Experiment Results Summary

| Experiment | Encoder | Base | MD source | aux | best n | **best MAE** | CI width | ΔMAE (full) | p |
|---|---|---|---|---|---|---|---|---|---|
| `frozen_q_hphil_full` | frozen | esm2_t6_8M_UR50D | MD_Q_HPHIL | none | 640 | **7.318** | 0.899 | -0.476 | 0.0000 |
| `frozen_q_lowflex_full` | frozen | esm2_t6_8M_UR50D | MD_Q_LOWFLEX | none | 160 | **7.317** | 0.906 | -0.730 | 0.0000 |
| `frozen_q_highflex_full` | frozen | esm2_t6_8M_UR50D | MD_Q_HIGHFLEX | none | 640 | **7.334** | 0.898 | -0.710 | 0.0000 |
| `frozen_saltbridge_full` | frozen | esm2_t6_8M_UR50D | MD_SALTBRIDGE | none | 40 | **7.387** | 0.895 | -0.454 | 0.0000 |
| `rosetta_full` | frozen | esm2_t6_8M_UR50D | ROSETTA_Q_HPHIL | none | 160 | **7.316** | 0.904 | -0.214 | 0.0001 |
| `combo_lowflex_highflex_frozen` | frozen | esm2_t6_8M_UR50D | MD_Q_LOWFLEX | MD_Q_HIGHFLEX | 640 | **7.220** | 0.898 | -0.813 | 0.0000 |
| `hot_lowflex_sweep` | hot | esm2_t6_8M_UR50D | MD_Q_LOWFLEX | none | 640 | **6.761** | 0.858 | -0.174 | 0.0142 |
| `hot_qhphil_alone_640` | hot | esm2_t6_8M_UR50D | MD_Q_HPHIL | none | 640 | **6.930** | 0.839 | +nan | nan |
| `lora_650m_lowflex_640` | lora | esm2_t33_650M_UR50D | MD_Q_LOWFLEX | none | 640 | **6.963** | 0.896 | +nan | nan |
| `hot_650m_lowflex_640` | hot | esm2_t33_650M_UR50D | MD_Q_LOWFLEX | none | 640 | **6.783** | 0.890 | +nan | nan |
| `md_weight_w1.0` | frozen | esm2_t6_8M_UR50D | MD_Q_HPHIL | none | 320 | **7.373** | 0.902 | +nan | nan |
| `md_weight_w8.0` | frozen | esm2_t6_8M_UR50D | MD_Q_HPHIL | none | 320 | **7.475** | 0.901 | +nan | nan |
| `frozen_q_min` | frozen | esm2_t6_8M_UR50D | MD_Q_MIN | none | 640 | **7.262** | 0.895 | -0.667 | 0.0000 |
| `hot_q_min` | hot | esm2_t6_8M_UR50D | MD_Q_MIN | none | 160 | **6.735** | 0.864 | -0.274 | 0.0011 |
| `frozen_q_std` | frozen | esm2_t6_8M_UR50D | MD_Q_STD | none | 160 | **7.316** | 0.899 | -0.771 | 0.0000 |
| `hot_q_std` | hot | esm2_t6_8M_UR50D | MD_Q_STD | none | 40 | **6.693** | 0.866 | +0.018 | 0.5875 |
| `frozen_q_slope` | frozen | esm2_t6_8M_UR50D | MD_Q_SLOPE | none | 640 | **7.245** | 0.890 | -0.439 | 0.0000 |
| `hot_q_slope` | hot | esm2_t6_8M_UR50D | MD_Q_SLOPE | none | 40 | **6.666** | 0.863 | +0.242 | 0.9997 |
| `frozen_rmsf_max` | frozen | esm2_t6_8M_UR50D | MD_RMSF_MAX | none | 160 | **7.250** | 0.884 | -0.409 | 0.0000 |
| `hot_rmsf_max` | hot | esm2_t6_8M_UR50D | MD_RMSF_MAX | none | 40 | **6.734** | 0.872 | -0.038 | 0.3639 |
| `frozen_rg_std` | frozen | esm2_t6_8M_UR50D | MD_RG_STD | none | 160 | **7.362** | 0.902 | -0.744 | 0.0000 |
| `hot_rg_std` | hot | esm2_t6_8M_UR50D | MD_RG_STD | none | 40 | **6.669** | 0.865 | +0.130 | 0.8944 |

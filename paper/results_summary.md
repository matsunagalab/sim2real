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

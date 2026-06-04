#!/usr/bin/env python
"""Plot scaling law results — best config (HuberLoss δ=1.0, 10 runs).

Data from NbBench train=57, test=396, ensemble eval.
Best config: ESM-2 8M, HuberLoss(δ=1.0), lr=3e-4, dropout=0.15, wd=0.04,
uncertainty-weighted MTL, cosine schedule.
"""

import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker
from scipy.optimize import curve_fit

plt.rcParams.update({
    'font.size': 10,
    'font.family': 'sans-serif',
    'axes.linewidth': 1.0,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
})

# ---- Data: NbBench train=57, test=396, best config (HuberLoss), 10 runs ----
n_ddg = np.array([10, 20, 40, 80, 160, 320])
n_sim = n_ddg * 2  # 1mel + 4idl

data = {
    'FoldX': {
        'mae':  [7.4547, 7.2939, 7.2425, 7.1833, 7.1627, 7.1123],
        'ci_lo': [7.0120, 6.8528, 6.8012, 6.7483, 6.7302, 6.6908],
        'ci_hi': [7.9023, 7.7390, 7.6882, 7.6243, 7.5983, 7.5407],
    },
    'FEP': {
        'mae':  [7.2870, 7.2469, 7.2369, 7.2369, 7.2327, 7.2046],
        'ci_lo': [6.8433, 6.8026, 6.7915, 6.7983, 6.7950, 6.7682],
        'ci_hi': [7.7376, 7.6981, 7.6851, 7.6850, 7.6787, 7.6465],
    },
    'Rosetta': {
        'mae':  [7.5741, 7.5836, 7.3661, 7.3531, 7.3767, 7.3279],
        'ci_lo': [7.1297, 7.1397, 6.9211, 6.9072, 6.9347, 6.8884],
        'ci_hi': [8.0258, 8.0332, 7.8119, 7.8001, 7.8225, 7.7663],
    },
    'ThermoMPNN': {
        'mae':  [7.4487, 7.6080, 7.3281, 7.1989, 7.2274, 7.2018],
        'ci_lo': [7.0043, 7.1613, 6.8817, 6.7656, 6.7922, 6.7629],
        'ci_hi': [7.8984, 8.0611, 7.7748, 7.6382, 7.6732, 7.6463],
    },
    'Rosetta (ESM2 muts)': {
        'mae':  [7.6817, 7.3804, 7.3433, 7.3416, 7.3027, 7.4420],
        'ci_lo': [7.2343, 6.9348, 6.8956, 6.8937, 6.8552, 6.9820],
        'ci_hi': [8.1325, 7.8293, 7.7917, 7.7903, 7.7576, 7.9151],
    },
    'Rosetta (random muts)': {
        'mae':  [7.4221, 7.4305, 7.3159, 7.3027, 7.3655, 7.3553],
        'ci_lo': [6.9787, 6.9831, 6.8711, 6.8559, 6.9195, 6.9107],
        'ci_hi': [7.8725, 7.8794, 7.7628, 7.7550, 7.8180, 7.8064],
    },
}

# Baseline: Tm-only model (no ddG data), approximate from n_ddg=0 extrapolation
BASELINE_MAE = 7.75


def power_law(n, a, b, c):
    return a * n**b + c


def fit_power_law(n_vals, mae_vals):
    x = np.array(n_vals, dtype=float)
    y = np.array(mae_vals)
    c0 = float(np.min(y) - 0.02)
    a0 = float(np.max(y) - c0)
    bounds = ((1e-6, -3.0, min(y) - 1.0), (50.0, -1e-3, max(y) + 1.0))
    popt, _ = curve_fit(power_law, x, y, p0=[a0, -0.2, c0], bounds=bounds, maxfev=20000)
    return popt


# ---- Multi-panel plot ----
fig, axes = plt.subplots(2, 3, figsize=(12, 7.5), sharex=True)
axes = axes.flatten()
panel_labels = ['a', 'b', 'c', 'd', 'e', 'f']

x_fit = np.logspace(np.log10(15), np.log10(800), 200)

for idx, (name, d) in enumerate(data.items()):
    ax = axes[idx]
    mae = np.array(d['mae'])
    ci_lo = np.array(d['ci_lo'])
    ci_hi = np.array(d['ci_hi'])

    # Fit power law
    popt = fit_power_law(n_sim, mae)
    a, b, c = popt
    y_fit = power_law(x_fit, a, b, c)

    # CI band
    ax.fill_between(n_sim, ci_lo, ci_hi, color='#BDBDBD', alpha=0.5, zorder=1)

    # Data line + markers
    ax.plot(n_sim, mae, '-o', color='#1a3a5c', markersize=6, linewidth=2.0,
            markerfacecolor='#1a3a5c', markeredgecolor='#1a3a5c', zorder=3)

    # Power law fit
    ax.plot(x_fit, y_fit, ':', color='#333333', linewidth=1.8, zorder=2)

    # Baseline
    ax.axhline(y=BASELINE_MAE, color='#c0392b', linestyle='-.', linewidth=1.5, alpha=0.7, zorder=1)

    # Equation
    if abs(c) < 0.01:
        eq_str = f"${a:.3f}n^{{{b:.3f}}}$"
    else:
        eq_str = f"${a:.3f}n^{{{b:.3f}}}+{c:.2f}$"
    ax.text(0.05, 0.08, eq_str, transform=ax.transAxes, fontsize=9,
            fontfamily='serif', verticalalignment='bottom')

    # Panel label
    ax.text(-0.02, 1.08, panel_labels[idx], transform=ax.transAxes,
            fontsize=16, fontweight='bold', verticalalignment='top')

    # Title
    ax.set_title(name, fontsize=11, pad=4)

    # Axes
    ax.set_xscale('log')
    ax.set_xlim(15, 800)
    ax.set_ylim(6.8, 8.2)
    ax.grid(True, alpha=0.25, linewidth=0.5)

    # X ticks
    ax.set_xticks([20, 40, 80, 160, 320, 640])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.tick_params(axis='both', which='minor', length=0)

    # Labels
    if idx % 3 == 0:
        ax.set_ylabel('MAE (°C)', fontsize=11)
    if idx >= 3:
        ax.set_xlabel('Number of simulation samples', fontsize=11)

fig.suptitle('Sim2Real Scaling Laws: Simulation ddG → Experimental Tm\n'
             '(ESM-2 8M + HuberLoss + uncertainty MTL, NbBench train=57)',
             fontsize=12, fontweight='bold', y=1.02)

plt.tight_layout()

out_dir = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(out_dir, 'scaling_nbbench.png'), dpi=200, bbox_inches='tight')
plt.savefig(os.path.join(out_dir, 'scaling_nbbench.pdf'), bbox_inches='tight')
print(f"Saved: {out_dir}/scaling_nbbench.png, scaling_nbbench.pdf")

#!/usr/bin/env python
"""Plot scaling law results — one panel per ddG source, style matching reference figure."""

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

# ---- Data: NbBench train=57, test=396, ensemble eval, 10 runs ----
n_ddg = np.array([10, 20, 40, 80, 160, 320])

# Total simulation samples = n_ddg * 2 (1mel + 4idl)
n_sim = n_ddg * 2

data = {
    'FoldX': {
        'mae':  [7.607, 7.359, 7.339, 7.194, 7.144, 7.101],
        'ci_lo': [7.162, 6.913, 6.895, 6.759, 6.711, 6.680],
        'ci_hi': [8.056, 7.807, 7.784, 7.634, 7.583, 7.529],
    },
    'FEP': {
        'mae':  [7.317, 7.266, 7.236, 7.209, 7.221, 7.161],
        'ci_lo': [6.871, 6.821, 6.793, 6.766, 6.782, 6.729],
        'ci_hi': [7.770, 7.717, 7.686, 7.662, 7.665, 7.601],
    },
    'Rosetta': {
        'mae':  [7.623, 7.450, 7.460, 7.323, 7.313, 7.325],
        'ci_lo': [7.179, 7.008, 7.015, 6.879, 6.869, 6.885],
        'ci_hi': [8.075, 7.901, 7.912, 7.771, 7.760, 7.764],
    },
    'ThermoMPNN': {
        'mae':  [7.362, 7.371, 7.253, 7.239, 7.223, 7.202],
        'ci_lo': [6.917, 6.924, 6.811, 6.803, 6.783, 6.756],
        'ci_hi': [7.807, 7.818, 7.704, 7.680, 7.669, 7.646],
    },
    'Rosetta (ESM2 muts)': {
        'mae':  [7.668, 7.439, 7.324, 7.362, 7.304, 7.426],
        'ci_lo': [7.225, 6.996, 6.878, 6.916, 6.853, 6.962],
        'ci_hi': [8.119, 7.888, 7.775, 7.810, 7.761, 7.897],
    },
    'Rosetta (random muts)': {
        'mae':  [7.468, 7.408, 7.367, 7.262, 7.320, 7.309],
        'ci_lo': [7.023, 6.960, 6.919, 6.818, 6.873, 6.865],
        'ci_hi': [7.920, 7.858, 7.817, 7.711, 7.771, 7.756],
    },
}

# Baseline MAE (Tm-only, no ddG) — approximate from n_ddg=0 runs
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

    # CI band (gray shading)
    ax.fill_between(n_sim, ci_lo, ci_hi, color='#BDBDBD', alpha=0.5, zorder=1)

    # Data line + markers (dark blue, like reference)
    ax.plot(n_sim, mae, '-o', color='#1a3a5c', markersize=6, linewidth=2.0,
            markerfacecolor='#1a3a5c', markeredgecolor='#1a3a5c', zorder=3)

    # Power law fit (black dotted)
    ax.plot(x_fit, y_fit, ':', color='#333333', linewidth=1.8, zorder=2)

    # Baseline (red dash-dot)
    ax.axhline(y=BASELINE_MAE, color='#c0392b', linestyle='-.', linewidth=1.5, alpha=0.7, zorder=1)

    # Format equation
    if abs(c) < 0.01:
        eq_str = f"${a:.3f}n^{{{b:.3f}}}$"
    else:
        eq_str = f"${a:.3f}n^{{{b:.3f}}}+{c:.2f}$"

    ax.text(0.05, 0.08, eq_str, transform=ax.transAxes, fontsize=9,
            fontfamily='serif', verticalalignment='bottom')

    # Panel label (bold, upper left)
    ax.text(-0.02, 1.08, panel_labels[idx], transform=ax.transAxes,
            fontsize=16, fontweight='bold', verticalalignment='top')

    # Title
    ax.set_title(name, fontsize=11, pad=4)

    # Axes
    ax.set_xscale('log')
    ax.set_xlim(15, 800)
    ax.set_ylim(6.5, 8.2)
    ax.grid(True, alpha=0.25, linewidth=0.5)

    # X ticks
    ax.set_xticks([20, 40, 80, 160, 320, 640])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.tick_params(axis='both', which='minor', length=0)

    # Y label only on left column
    if idx % 3 == 0:
        ax.set_ylabel('MAE (°C)', fontsize=11)

    # X label only on bottom row
    if idx >= 3:
        ax.set_xlabel('Number of simulation samples', fontsize=11)

fig.suptitle('Sim2Real Scaling Laws: Simulation ddG → Experimental Tm',
             fontsize=13, fontweight='bold', y=1.01)

plt.tight_layout()

out_dir = os.path.dirname(os.path.abspath(__file__))
plt.savefig(os.path.join(out_dir, 'scaling_nbbench.png'), dpi=200, bbox_inches='tight')
plt.savefig(os.path.join(out_dir, 'scaling_nbbench.pdf'), bbox_inches='tight')
print(f"Saved: {out_dir}/scaling_nbbench.png, scaling_nbbench.pdf")

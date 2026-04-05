#!/usr/bin/env python
"""Plot scaling law results for all ddG sources (NbBench train=57, test=396)."""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

plt.rcParams.update({
    'font.size': 11,
    'font.family': 'sans-serif',
    'axes.linewidth': 1.2,
    'xtick.major.width': 1.0,
    'ytick.major.width': 1.0,
    'figure.dpi': 150,
})

# ---- Data: NbBench train=57, test=396, ensemble eval, 10 runs ----
n_ddg = np.array([10, 20, 40, 80, 160, 320])

data = {
    'FoldX': {
        'mae':  [7.607, 7.359, 7.339, 7.194, 7.144, 7.101],
        'ci_w': [0.894, 0.894, 0.889, 0.875, 0.873, 0.850],
        'color': '#2196F3', 'marker': 'o',
    },
    'FEP': {
        'mae':  [7.317, 7.266, 7.236, 7.209, 7.221, 7.161],
        'ci_w': [0.899, 0.896, 0.894, 0.896, 0.883, 0.872],
        'color': '#4CAF50', 'marker': 's',
    },
    'Rosetta': {
        'mae':  [7.623, 7.450, 7.460, 7.323, 7.313, 7.325],
        'ci_w': [0.896, 0.893, 0.898, 0.891, 0.891, 0.879],
        'color': '#FF9800', 'marker': '^',
    },
    'ThermoMPNN': {
        'mae':  [7.362, 7.371, 7.253, 7.239, 7.223, 7.202],
        'ci_w': [0.890, 0.894, 0.893, 0.878, 0.885, 0.890],
        'color': '#9C27B0', 'marker': 'D',
    },
    'Rosetta\n(ESM2 muts)': {
        'mae':  [7.668, 7.439, 7.324, 7.362, 7.304, 7.426],
        'ci_w': [0.894, 0.892, 0.897, 0.895, 0.908, 0.935],
        'color': '#F44336', 'marker': 'v',
    },
    'Rosetta\n(random muts)': {
        'mae':  [7.468, 7.408, 7.367, 7.262, 7.320, 7.309],
        'ci_w': [0.897, 0.898, 0.898, 0.893, 0.898, 0.891],
        'color': '#795548', 'marker': 'p',
    },
}

def power_law(n, a, b, c):
    return a * n**b + c

def fit_power_law(n_vals, mae_vals):
    x = np.array([n * 2 for n in n_vals], dtype=float) / 1000.0
    y = np.array(mae_vals)
    c0 = float(np.min(y) - 0.02)
    a0 = float(np.max(y) - c0)
    bounds = ((1e-6, -3.0, min(y)-1.0), (50.0, -1e-3, max(y)+1.0))
    popt, _ = curve_fit(power_law, x, y, p0=[a0, -0.2, c0], bounds=bounds, maxfev=20000)
    return popt

# ---- Plot ----
fig, ax = plt.subplots(1, 1, figsize=(8, 5.5))

x_fit = np.linspace(8, 700, 200)
x_fit_scaled = np.array([n * 2 for n in x_fit]) / 1000.0

for name, d in data.items():
    mae = np.array(d['mae'])
    ci_half = np.array(d['ci_w']) / 2

    # Fit power law
    popt = fit_power_law(n_ddg, mae)
    y_fit = power_law(x_fit_scaled, *popt)

    # Plot fit line
    ax.plot(x_fit, y_fit, color=d['color'], alpha=0.4, linewidth=1.5, zorder=1)

    # Plot data points with CI
    ax.errorbar(n_ddg, mae, yerr=ci_half, fmt=d['marker'], color=d['color'],
                markersize=7, capsize=3, capthick=1.2, linewidth=1.2,
                label=f"{name} (b={popt[1]:.2f})", zorder=2)

ax.set_xscale('log')
ax.set_xlabel('Number of ddG samples per protein ($n_{ddG}$)', fontsize=12)
ax.set_ylabel('Tm prediction MAE (°C)', fontsize=12)
ax.set_title('Sim2Real Scaling: ddG auxiliary data → Tm prediction\n'
             '(NbBench thermo-tm, train=57, test=396, ensemble eval)',
             fontsize=12, fontweight='bold')
ax.set_xticks([10, 20, 40, 80, 160, 320])
ax.set_xticklabels(['10', '20', '40', '80', '160', '320'])
ax.set_xlim(7, 450)
ax.set_ylim(6.8, 7.9)
ax.legend(fontsize=9, loc='upper right', framealpha=0.9)
ax.grid(True, alpha=0.3, linewidth=0.5)

# Add annotation
ax.text(0.02, 0.02,
        'ESM-2 (8M) frozen encoder\n'
        'Uncertainty-weighted MTL (Kendall 2018)\n'
        'lr=3e-4, dropout=0.15, wd=0.04',
        transform=ax.transAxes, fontsize=8, color='gray',
        verticalalignment='bottom')

plt.tight_layout()
import os
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
plt.savefig(os.path.join(out_dir, 'scaling_nbbench.png'), dpi=200, bbox_inches='tight')
plt.savefig(os.path.join(out_dir, 'scaling_nbbench.pdf'), bbox_inches='tight')
print(f"Saved: {out_dir}/scaling_nbbench.png, scaling_nbbench.pdf")

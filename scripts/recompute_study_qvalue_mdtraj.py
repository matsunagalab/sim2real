#!/usr/bin/env python3
"""Native-contact Q-value for the fep_md_400k WT/mutant MD study (mdtraj).

Computes the Best-Hummer fraction of native contacts Q, averaged over the COMMON
first-40 ns window (first 4000 frames at dt=10 ps), using frame 0 of each variant's
own trajectory as the native reference. NO hydrophilic filter (that is the separate
heterogeneous panel, extract_q_values.py).

Atom selection (--atoms):
  heavy    : all protein heavy atoms incl. side chains (canonical Best-Hummer,
             per https://mdtraj.org/1.9.3/examples/native-contact.html). DEFAULT.
  backbone : N/CA/C/O only. Reproduces the earlier scripts/extract_study_qvalue.py
             (MDAnalysis) output to 6 decimals; kept for provenance/comparison.

The heavy selection matches the mdtraj reference (heavy atoms) and gives a
mutation-sensitive label; backbone was the earlier simplification. Constants
(BETA/LAMBDA/CUT/GAP) are identical across both.

Output: <out> CSV with columns: vid, system, mutation, seq, q_value, n_frames_used
"""
import argparse
import csv
import glob
import os
import warnings
from multiprocessing import Pool

warnings.filterwarnings("ignore")
import numpy as np  # noqa: E402
import mdtraj as md  # noqa: E402

# match scripts/extract_study_qvalue.py
BETA, LAMBDA, CUT_NM, GAP = 50.0, 1.8, 0.45, 3
N_WINDOW = 4000  # first 40 ns at dt = 10 ps

STUDY = "mdclaw/studies/fep_md_400k_all"

ATOM_SELECT = {
    "heavy": "protein and not element H",   # canonical Best-Hummer (side chains)
    "backbone": "protein and name N CA C O",  # earlier simplification
}
# module-level; set in main() so Pool workers inherit it
SELECTION = ATOM_SELECT["heavy"]

# ff19SB protonation variants -> one letter (match convert_aa_code + variants)
THREE_TO_ONE = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLU': 'E', 'GLN': 'Q', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V',
    'HID': 'H', 'HIE': 'H', 'HIP': 'H',
    'ASH': 'D', 'GLH': 'E', 'LYN': 'K', 'CYX': 'C', 'CYM': 'C',
}


def variant_paths(vid):
    base = f"{STUDY}/{vid}/jobs/main/nodes"
    dcd = f"{base}/prod_001/artifacts/trajectory.dcd"
    # topology fallback chain: some variants had topo_001 emptied by a cleanup
    # sweep but keep an equivalent full-system PDB elsewhere (identical atom
    # order -> identical Q, verified to 0.0e+00 vs system.topology.pdb).
    import glob as _glob
    cands = [
        f"{base}/topo_001/artifacts/system.topology.pdb",
        f"{base}/prod_001/artifacts/final_structure.pdb",
        f"{base}/eq_002/artifacts/equilibrated.pdb",
        f"{base}/eq_001/artifacts/equilibrated.pdb",
    ]
    cands += sorted(_glob.glob(f"{base}/eq_*/artifacts/equilibrated.pdb"))
    top = next((c for c in cands if os.path.exists(c)), cands[0])
    return top, dcd


def compute_one(vid):
    top, dcd = variant_paths(vid)
    if not (os.path.exists(top) and os.path.exists(dcd)):
        return {"vid": vid, "status": "skip", "reason": "missing top/dcd"}
    try:
        topo = md.load_topology(top)
        sel = topo.select(SELECTION)
        if len(sel) == 0:
            return {"vid": vid, "status": "skip", "reason": "no selected atoms"}
        res_idx = np.array([topo.atom(a).residue.index for a in sel])

        first = md.load_frame(dcd, 0, top=topo)
        x0 = first.xyz[0, sel, :]  # nm
        d0 = np.sqrt(((x0[:, None, :] - x0[None, :, :]) ** 2).sum(-1))
        mask = (d0 < CUT_NM) & (np.abs(res_idx[:, None] - res_idx[None, :]) > GAP) \
            & np.triu(np.ones_like(d0, bool), 1)
        ii, jj = np.where(mask)
        if len(ii) == 0:
            return {"vid": vid, "status": "skip", "reason": "no native contacts"}
        dN = d0[ii, jj]
        pairs = np.stack([sel[ii], sel[jj]], axis=1)

        qsum, n = 0.0, 0
        for chunk in md.iterload(dcd, top=topo, chunk=500):
            if n >= N_WINDOW:
                break
            take = min(len(chunk), N_WINDOW - n)
            d = md.compute_distances(chunk[:take], pairs)  # nm
            q = 1.0 / (1.0 + np.exp(BETA * (d - LAMBDA * dN[None, :])))
            qsum += q.mean(axis=1).sum()
            n += take
        q = qsum / n

        # protein sequence, one residue per protein residue
        prot_res = [r for r in topo.residues if r.is_protein]
        seq = "".join(THREE_TO_ONE.get(r.name.upper(), "X") for r in prot_res)
        system, _, mutation = vid.partition("_")
        return {"vid": vid, "system": system, "mutation": mutation,
                "seq": seq, "q_value": q, "n_frames_used": n,
                "status": "ok", "reason": ""}
    except Exception as e:  # noqa: BLE001
        return {"vid": vid, "status": "error", "reason": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", default="1mel", help="variant prefix filter (e.g. 1mel)")
    ap.add_argument("--out", default="data/md/study_qvalue_fep400k_1mel.csv")
    ap.add_argument("--atoms", choices=sorted(ATOM_SELECT), default="heavy",
                    help="atom selection for contacts (default: heavy = canonical)")
    ap.add_argument("--nproc", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    global SELECTION
    SELECTION = ATOM_SELECT[args.atoms]
    print(f"atom selection: {args.atoms} -> '{SELECTION}'", flush=True)

    vids = sorted(os.path.basename(d.rstrip("/"))
                  for d in glob.glob(f"{STUDY}/{args.system}_*/"))
    vids = [v for v in vids if os.path.exists(variant_paths(v)[1])]
    if args.limit:
        vids = vids[: args.limit]
    print(f"variants with trajectory: {len(vids)} (system={args.system}) nproc={args.nproc}", flush=True)

    rows = []
    with Pool(args.nproc) as pool:
        for i, r in enumerate(pool.imap_unordered(compute_one, vids), 1):
            rows.append(r)
            if i % 25 == 0 or i == len(vids):
                ok = sum(1 for x in rows if x["status"] == "ok")
                print(f"[{i}/{len(vids)}] ok={ok}", flush=True)
            if r["status"] != "ok":
                print(f"  {r['status']}: {r['vid']} :: {r['reason']}", flush=True)

    ok_rows = [r for r in rows if r["status"] == "ok"]
    cols = ["vid", "system", "mutation", "seq", "q_value", "n_frames_used"]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(ok_rows, key=lambda x: x["vid"]):
            w.writerow(r)
    print(f"wrote {args.out}: {len(ok_rows)} ok / {len(rows)} total", flush=True)


if __name__ == "__main__":
    main()

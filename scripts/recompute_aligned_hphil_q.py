#!/usr/bin/env python3
"""Aligned hydrophilic-contact Q for the Fig 2 sequence-design comparison.

Both the matched scan and the heterogeneous panel are put on ONE Q protocol so
Fig 2 isolates the sequence set, not the acquisition pipeline:

  * same absolute production window [10, 40) ns  (first 40 ns of production, so
    each label uses the same simulated time -> compute parity with FEP/scan);
  * same 100 ps cadence and 300 analysed frames (scan is subsampled from 10 ps);
  * same Best--Hummer backbone-Q restricted to hydrophilic-residue contacts
    (Kamiya set D,E,Q,N,R,K,H), native reference = production frame 0;
  * heterogeneous is read from the FULL solvated trajectories under
    ~/tmp/mdclaw_nanobodies (the zenodo deposit keeps only the final 30 ns).

Window is selected by TIME, never by frame index (prod frame 0 is t=100 ps for
hetero, t=10 ps for scan).
"""
from __future__ import annotations
import argparse, csv, glob, json, os, warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
warnings.filterwarnings("ignore")
import numpy as np
import MDAnalysis as mda

BETA, LAMBDA, CUT_NM, GAP = 50.0, 1.8, 0.45, 3
SEL = "protein and backbone and not element H"
WIN_LO_PS, WIN_HI_PS = 10000.0, 40000.0        # [10, 40) ns
CADENCE_PS = 100.0
HPHIL = {"ASP", "GLU", "GLN", "ASN", "ARG", "LYS", "HIS",
         "HID", "HIE", "HIP", "ASH", "GLH", "LYN"}   # + ff protonation variants
THREE_TO_ONE = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C", "GLU": "E",
    "GLN": "Q", "GLY": "G", "HIS": "H", "ILE": "I", "LEU": "L", "LYS": "K",
    "MET": "M", "PHE": "F", "PRO": "P", "SER": "S", "THR": "T", "TRP": "W",
    "TYR": "Y", "VAL": "V", "HID": "H", "HIE": "H", "HIP": "H", "ASH": "D",
    "GLH": "E", "LYN": "K", "CYX": "C", "CYM": "C",
}
HETERO_ROOT = os.path.expanduser("~/tmp/mdclaw_nanobodies")
SCAN_STUDY = "mdclaw/studies/fep_md_400k_all"


def seq_of(atoms) -> str:
    return "".join(THREE_TO_ONE.get(r.resname.upper(), "X") for r in atoms.residues)


def hphil_q(reference_pdb: str, trajectory: str, cadence_ps: float) -> dict:
    # Native reference = the parent equilibration structure = the coordinates INPUT
    # to production (t=0), identical convention for scan and hetero.
    ref = mda.Universe(reference_pdb)
    ref_atoms = ref.select_atoms(SEL)
    u = mda.Universe(reference_pdb, trajectory)
    atoms = u.select_atoms(SEL)
    if atoms.n_atoms == 0 or atoms.n_atoms != ref_atoms.n_atoms:
        raise ValueError(f"backbone atom mismatch ref={ref_atoms.n_atoms} traj={atoms.n_atoms}")
    tr = u.trajectory
    native = ref_atoms.positions / 10.0
    residx = atoms.resindices
    # hydrophilic flag per selected atom (via its residue's name)
    resname_by_resindex = {r.resindex: r.resname.upper() for r in atoms.residues}
    hphil_per_atom = np.array([resname_by_resindex[i] in HPHIL for i in residx])

    d0 = np.sqrt(((native[:, None] - native[None]) ** 2).sum(-1))
    contact = (d0 < CUT_NM) & (np.abs(residx[:, None] - residx[None]) > GAP) \
        & np.triu(np.ones_like(d0, bool), 1) \
        & (hphil_per_atom[:, None] | hphil_per_atom[None])
    ii, jj = np.where(contact)
    if not len(ii):
        raise ValueError("no hydrophilic native contacts")
    dN = d0[ii, jj]

    # select frames whose time is in [10,40) ns, subsampled to `cadence_ps`
    # Read ONLY the window frames at the target cadence (seek, don't scan the
    # whole trajectory): frame i has time t0 + i*dt, so solve for the index range.
    tr[0]
    t0, dt = tr.time, tr.dt
    stride = max(1, int(round(cadence_ps / dt)))
    lo_i = max(0, int(np.ceil((WIN_LO_PS - t0) / dt)))
    hi_i = int(np.floor((WIN_HI_PS - 1e-6 - t0) / dt))
    qsum, n = 0.0, 0
    times = []
    for ts in tr[lo_i:hi_i + 1:stride]:
        t = ts.time
        if t < WIN_LO_PS or t >= WIN_HI_PS:      # guard against dt jitter
            continue
        x = atoms.positions / 10.0
        d = np.sqrt(((x[ii] - x[jj]) ** 2).sum(-1))
        qsum += (1.0 / (1.0 + np.exp(BETA * (d - LAMBDA * dN)))).mean()
        n += 1
        times.append(t)
    if n == 0:
        raise ValueError("no frames in window")
    return {"q_value": qsum / n, "n_frames_used": n, "n_contacts": int(len(ii)),
            "t_first_ps": times[0], "t_last_ps": times[-1], "seq": seq_of(atoms)}


def _node(base: str, node: str) -> dict:
    with open(f"{base}/{node}/node.json") as fh:
        return json.load(fh)


def _prod_and_ref(base: str, want_temp: float | None) -> tuple[str, str]:
    """Return (trajectory_dcd, parent_eq_equilibrated_pdb) for the production node.

    Picks the production node at ``want_temp`` K (heterogeneous has a 300 K
    prod_001 and a 400 K prod_002); the native reference is that node's parent
    equilibration structure (the t=0 production input), resolved from the DAG.
    """
    prods = sorted(os.path.basename(os.path.dirname(os.path.dirname(p)))
                   for p in glob.glob(f"{base}/prod_*/artifacts/trajectory.dcd"))
    chosen = None
    for prod in prods:
        meta = _node(base, prod)
        temp = meta.get("conditions", {}).get("temperature_kelvin")
        if want_temp is None or temp == want_temp:
            chosen = (prod, meta)
    if chosen is None:
        raise ValueError(f"no production node at {want_temp} K in {base}")
    prod, meta = chosen
    parent = meta["parent_node_ids"][0]
    return (f"{base}/{prod}/artifacts/trajectory.dcd",
            f"{base}/{parent}/artifacts/equilibrated.pdb")


def hetero_task(pdb: str) -> dict:
    base = f"{HETERO_ROOT}/job_nano_{pdb}/nodes"
    dcd, ref = _prod_and_ref(base, want_temp=400.0)   # 400 K = prod_002
    return {"id": pdb, "reference": ref, "trajectory": dcd, "cadence": 100.0}


def scan_task(vid: str) -> dict:
    base = f"{SCAN_STUDY}/{vid}/jobs/main/nodes"
    dcd, ref = _prod_and_ref(base, want_temp=None)    # single 400 K production
    return {"id": vid, "reference": ref, "trajectory": dcd, "cadence": 100.0}


def run_one(task: dict) -> dict:
    try:
        r = hphil_q(task["reference"], task["trajectory"], task["cadence"])
        return {"id": task["id"], "status": "ok", "reason": "", **r}
    except Exception as e:  # noqa: BLE001
        return {"id": task["id"], "status": "error", "reason": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, choices=("hetero", "scan_1mel", "scan_4idl"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    tasks, skipped = [], 0
    if a.source == "hetero":
        ids = sorted(os.path.basename(d).replace("job_nano_", "")
                     for d in glob.glob(f"{HETERO_ROOT}/job_nano_*"))
        builder = hetero_task
    else:
        sysid = a.source.split("_")[1]
        ids = sorted(os.path.basename(d.rstrip("/")) for d in glob.glob(f"{SCAN_STUDY}/{sysid}_*/"))
        builder = scan_task
    for i in ids:
        try:
            t = builder(i)
            if os.path.exists(t["trajectory"]) and os.path.exists(t["reference"]):
                tasks.append(t)
            else:
                skipped += 1
        except Exception:  # noqa: BLE001 -- e.g. no 400 K production node
            skipped += 1
    print(f"skipped {skipped} without a resolvable 400 K production + parent eq", flush=True)
    if a.limit:
        tasks = tasks[: a.limit]
    print(f"{a.source}: {len(tasks)} trajectories, window [10,40)ns @100ps", flush=True)

    rows = []
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        futs = [ex.submit(run_one, t) for t in tasks]
        for i, f in enumerate(as_completed(futs), 1):
            rows.append(f.result())
            if i % 50 == 0 or i == len(tasks):
                ok = sum(r["status"] == "ok" for r in rows)
                print(f"  {i}/{len(tasks)} ok={ok}", flush=True)
    cols = ["id", "seq", "q_value", "n_frames_used", "n_contacts", "t_first_ps", "t_last_ps", "status", "reason"]
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(rows, key=lambda r: r["id"]):
            w.writerow(r)
    ok = sum(r["status"] == "ok" for r in rows)
    print(f"wrote {a.out}: {ok}/{len(rows)} ok", flush=True)


if __name__ == "__main__":
    main()

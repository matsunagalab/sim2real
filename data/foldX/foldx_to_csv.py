#!/usr/bin/env python3
"""
FoldX の individual_list と Dif_*_Repair.fxout および入力配列から、
変異体配列と ddG をまとめた CSV を出力する。

make_individual_list.py で生成した individual_list は 1 行 1 変異で
「元アミノ酸 + 鎖 + 残基番号 + 変異先」（例: VA2A;）の形式。
fxout のデータ行は 1MEL_Repair_1.pdb, 1MEL_Repair_2.pdb ... の順で
individual_list の行番号（1 始まり）と対応する。2 列目が total energy（ddG）。

Usage:
  python foldx_to_csv.py \\
    --individual-list individual_list_1mel_all.txt \\
    --fxout Dif_1MEL-all_Repair.fxout \\
    --sequence "VQLQASGGGSVQAGGSLRLSCAASG..." \\
    --output 1mel_all_foldx_ddg.csv

  # 配列の先頭が PDB 残基番号 2 の場合は --start-residue 2
  python foldx_to_csv.py ... --sequence "..." --start-residue 2
"""

import argparse
import re
import csv
from pathlib import Path
from typing import List, Tuple


# individual_list 1行の形式: VA2A;  → wt_aa, chain, position, mut_aa
INDIVIDUAL_LINE = re.compile(r"^([A-Z])([A-Z])(\d+)([A-Z]);?\s*$")


def parse_individual_list(path: Path) -> List[Tuple[str, str, int, str]]:
    """
    individual_list をパースし、(wt_aa, chain, position, mut_aa) のリストを返す。
    """
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    result = []
    for line in lines:
        m = INDIVIDUAL_LINE.match(line)
        if not m:
            raise ValueError(f"individual_list の行形式が不正です: {line!r}")
        wt_aa, chain, pos_str, mut_aa = m.groups()
        result.append((wt_aa, chain, int(pos_str), mut_aa))
    return result


def parse_fxout(path: Path) -> List[Tuple[int, float]]:
    """
    Dif_*_Repair.fxout をパースし、(行番号 1-based, ddG) のリストを返す。
    ヘッダー行をスキップし、'Pdb' と 'total energy' を含む行の次からデータとする。
    1 列目: 1MEL_Repair_N.pdb → N、2 列目: total energy (ddG)。
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    data_start = 0
    for i, line in enumerate(lines):
        if "total energy" in line and "Pdb" in line:
            data_start = i + 1
            break
    if data_start == 0:
        raise ValueError("fxout に 'Pdb' と 'total energy' のヘッダー行が見つかりません")

    # PDB 名から番号を抜く正規表現（例: 1MEL_Repair_123.pdb -> 123）
    pdb_pattern = re.compile(r"_Repair_(\d+)\.pdb")
    result = []
    for line in lines[data_start:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        pdb_name = parts[0].strip()
        try:
            ddg = float(parts[1].strip())
        except ValueError:
            continue
        m = pdb_pattern.search(pdb_name)
        if m:
            idx = int(m.group(1))
            result.append((idx, ddg))
    return result


def build_variant_sequence(sequence: str, position: int, mut_aa: str, start_residue: int) -> str:
    """
    野生型配列 sequence の position（PDB 1-based）を mut_aa に置換した変異体配列を返す。
    start_residue: 配列の先頭に対応する PDB 残基番号（make_individual_list と同じ値）。
    """
    seq_idx = position - start_residue  # 0-based index
    if seq_idx < 0 or seq_idx >= len(sequence):
        raise ValueError(
            f"position {position} は配列範囲外です "
            f"(start_residue={start_residue}, 配列長={len(sequence)})"
        )
    return sequence[:seq_idx] + mut_aa + sequence[seq_idx + 1 :]


def run(
    individual_list_path: Path,
    fxout_path: Path,
    sequence: str,
    output_path: Path,
    start_residue: int = 1,
) -> None:
    sequence = sequence.upper().strip()
    mutations = parse_individual_list(individual_list_path)
    ddg_by_index = dict(parse_fxout(fxout_path))

    if len(ddg_by_index) != len(mutations):
        raise ValueError(
            f"変異数 ({len(mutations)}) と fxout のデータ行数 ({len(ddg_by_index)}) が一致しません"
        )

    rows = []
    for i, (wt_aa, chain, position, mut_aa) in enumerate(mutations):
        row_num = i + 1  # 1-based line number
        ddg = ddg_by_index.get(row_num)
        if ddg is None:
            raise ValueError(f"fxout に行番号 {row_num} に対応する ddG がありません")
        try:
            variant_seq = build_variant_sequence(sequence, position, mut_aa, start_residue)
        except ValueError as e:
            raise ValueError(f"individual_list 行 {row_num} ({wt_aa}{chain}{position}{mut_aa}): {e}")
        mutation_label = f"{wt_aa}{position}{mut_aa}"
        rows.append({
            "position": position,
            "wt_aa": wt_aa,
            "mut_aa": mut_aa,
            "mutation": mutation_label,
            "variant_sequence": variant_seq,
            "ddG": ddg,
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["position", "wt_aa", "mut_aa", "mutation", "variant_sequence", "ddG"],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FoldX individual_list と fxout および配列から変異体配列・ddG の CSV を出力"
    )
    parser.add_argument(
        "--individual-list",
        "-i",
        type=Path,
        required=True,
        help="individual_list ファイル（例: individual_list_1mel_all.txt）",
    )
    parser.add_argument(
        "--fxout",
        "-f",
        type=Path,
        required=True,
        help="FoldX の Dif_*_Repair.fxout ファイル",
    )
    parser.add_argument(
        "--sequence",
        "-s",
        required=True,
        help="野生型アミノ酸配列（1文字表記）。individual_list 作成時に使ったものと同じ",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("foldx_ddg.csv"),
        help="出力 CSV パス（既定: foldx_ddg.csv）",
    )
    parser.add_argument(
        "--start-residue",
        type=int,
        default=1,
        metavar="N",
        help="配列の先頭に対応する PDB 残基番号（make_individual_list と同一にすること、既定: 1）",
    )
    args = parser.parse_args()

    run(
        args.individual_list,
        args.fxout,
        args.sequence,
        args.output,
        start_residue=args.start_residue,
    )


if __name__ == "__main__":
    main()

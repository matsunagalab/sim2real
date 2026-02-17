#!/usr/bin/env python3
"""
FoldX 用 individual_list.txt を生成するスクリプト。

指定したアミノ酸配列に対して、全ての単変異を列挙する。
変異先として野生型と同じアミノ酸と Cys は除外する。

Usage:
  python make_individual_list.py --pdb-id 1MEL --sequence MKTAYIAK... --chain A --output individual_list.txt
  python make_individual_list.py ... --start-residue 50   # PDB の残基番号が 50 から始まる場合
  または
  from make_individual_list import make_individual_list
  make_individual_list("1MEL", "MKTAYIAK...", "A", "individual_list.txt", start_residue=50)
"""

import argparse
from pathlib import Path
from typing import List, Union

# 標準20アミノ酸（1文字コード）
STANDARD_AA = list("ACDEFGHIKLMNPQRSTVWY")


def get_allowed_mutant_aas(wt_aa: str) -> List[str]:
    """
    変異先として許容するアミノ酸のリストを返す。
    野生型と同じアミノ酸と Cys を除く。
    """
    return [aa for aa in STANDARD_AA if aa != wt_aa and aa != "C"]


def make_individual_list(
    pdb_id: str,
    sequence: str,
    chain_id: str,
    output_path: Union[str, Path],
    *,
    one_per_line: bool = True,
    start_residue: int = 1,
) -> int:
    """
    FoldX 用 individual_list を生成し、ファイルに書き出す。

    Parameters
    ----------
    pdb_id : str
        PDB ID（出力ファイル名やログ用。ファイル内容には使わない）
    sequence : str
        アミノ酸配列（1文字表記）
    chain_id : str
        鎖 ID（A, B, ...）
    output_path : str | Path
        出力ファイルパス
    one_per_line : bool, default True
        True のとき 1 変異 1 行（行末 ;）、False のときは同一残基の変異をカンマで連結
    start_residue : int, default 1
        配列の先頭残基に対応する PDB 上の残基番号。指定がなければ 1 から始める。

    Returns
    -------
    int
        出力した変異の総数
    """
    sequence = sequence.upper().strip()
    chain_id = chain_id.strip().upper()
    if len(chain_id) != 1:
        raise ValueError("chain_id は1文字で指定してください")

    lines: List[str] = []
    count = 0

    for i, wt_aa in enumerate(sequence):
        pos_onebased = start_residue + i  # PDB 上の残基番号
        if wt_aa not in STANDARD_AA:
            raise ValueError(
                f"配列中に未対応の文字があります: '{wt_aa}' (位置 {i + 1})"
            )
        allowed = get_allowed_mutant_aas(wt_aa)
        if one_per_line:
            for mut_aa in allowed:
                lines.append(f"{wt_aa}{chain_id}{pos_onebased}{mut_aa};")
                count += 1
        else:
            entries = [
                f"{wt_aa}{chain_id}{pos_onebased}{mut_aa}" for mut_aa in allowed
            ]
            if entries:
                lines.append(",".join(entries) + ";")
                count += len(entries)

    out = Path(output_path)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FoldX 用 individual_list.txt を生成（単変異・WT同一とCys除外）"
    )
    parser.add_argument(
        "--pdb-id",
        required=True,
        help="PDB ID（例: 1MEL）",
    )
    parser.add_argument(
        "--sequence",
        "-s",
        required=True,
        help="アミノ酸配列（1文字表記）",
    )
    parser.add_argument(
        "--chain",
        "-c",
        required=True,
        help="鎖 ID（1文字、例: A）",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="individual_list.txt",
        help="出力ファイルパス（既定: individual_list.txt）",
    )
    parser.add_argument(
        "--group-by-position",
        action="store_true",
        help="同一残基の変異を1行にカンマ区切りでまとめる",
    )
    parser.add_argument(
        "--start-residue",
        type=int,
        default=1,
        metavar="N",
        help="配列の先頭に対応する PDB 上の残基番号（既定: 1）",
    )
    args = parser.parse_args()

    n = make_individual_list(
        args.pdb_id,
        args.sequence,
        args.chain,
        args.output,
        one_per_line=not args.group_by_position,
        start_residue=args.start_residue,
    )
    print(f"Wrote {n} mutations to {args.output}")


if __name__ == "__main__":
    main()

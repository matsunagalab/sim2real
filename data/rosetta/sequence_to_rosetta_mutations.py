import csv
import os
import math
from argparse import ArgumentParser


def compare_sequences(wildtype: str, variant: str) -> list:
    """
    Compare wildtype and variant sequences to detect mutations.
    
    Args:
        wildtype: Wildtype amino acid sequence
        variant: Variant amino acid sequence
        
    Returns:
        List of mutations, each as a dict with keys: position, original_aa, mutated_aa
    """
    mutations = []
    
    # Check sequence lengths
    if len(wildtype) != len(variant):
        raise ValueError(
            f"Sequence length mismatch: wildtype has {len(wildtype)} residues, "
            f"variant has {len(variant)} residues"
        )
    
    # Compare position by position (1-based indexing for Rosetta)
    for pos in range(len(wildtype)):
        wt_aa = wildtype[pos]
        var_aa = variant[pos]
        
        if wt_aa != var_aa:
            mutations.append({
                'position': pos + 1,  # 1-based for Rosetta
                'original_aa': wt_aa,
                'mutated_aa': var_aa
            })
    
    return mutations


def sequence_to_rosetta_mutations(csv_file: str, wildtype: str, output_file: str, variant_column: str = "mutant_sequence", num_files: int = 1):
    """
    Reads a CSV file with variant sequences and generates Rosetta-formatted
    mutation list file(s) by comparing each variant against a wildtype sequence.
    Supports splitting output into multiple files.
    
    Note: The CSV file should contain ONLY variant sequences (not the wildtype).
    The wildtype sequence must be provided separately via the --wildtype argument.
    
    Args:
        csv_file: Path to input CSV file with variant sequences.
                  All rows contain variant sequences (wildtype is not included).
        wildtype: Wildtype amino acid sequence (provided separately, not from CSV)
        output_file: Path pattern for output files (e.g., "path/to/muts.txt" -> "path/to/muts_1.txt", ...)
        variant_column: Name of the column containing variant sequences (default: "mutant_sequence")
        num_files: Number of files to split the output into (default: 1, no splitting)
    """
    print(f"1. Reading CSV file: {csv_file}")
    print(f"   Wildtype sequence length: {len(wildtype)} residues")
    
    all_mutant_variants = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Get the variant column name
            fieldnames = reader.fieldnames
            if not fieldnames:
                print("Error: CSV file has no columns")
                return
            
            # Check if the specified column exists
            if variant_column not in fieldnames:
                print(f"Error: Column '{variant_column}' not found in CSV file")
                print(f"Available columns: {', '.join(fieldnames)}")
                return
            
            print(f"   Using variant column: {variant_column}")
            
            for row_num, row in enumerate(reader, start=2):  # start=2 because header is row 1
                try:
                    variant_seq = row[variant_column].strip()
                    
                    if not variant_seq:
                        print(f"Warning: Row {row_num}: empty variant sequence, skipping")
                        continue
                    
                    # Compare variant with wildtype to detect mutations
                    # All rows in CSV are variants (wildtype is provided separately)
                    mutations = compare_sequences(wildtype, variant_seq)
                    
                    if len(mutations) == 0:
                        # No mutations detected (variant is identical to wildtype)
                        # This should be rare if CSV contains only variants
                        print(f"Warning: Row {row_num}: variant is identical to wildtype, skipping")
                        continue
                    
                    all_mutant_variants.append(mutations)
                    
                except ValueError as e:
                    print(f"Error: Row {row_num}: {e}")
                    continue
                except KeyError as e:
                    print(f"Error: Row {row_num}: Missing column in CSV: {e}")
                    continue
                except Exception as e:
                    print(f"Error: Row {row_num}: Unexpected error: {e}")
                    continue
    
    except FileNotFoundError:
        print(f"Error: CSV file not found: {csv_file}")
        return
    except Exception as e:
        print(f"Error: Failed to read CSV file: {e}")
        return
    
    if len(all_mutant_variants) == 0:
        print("Error: No valid mutation data found in CSV file")
        return
    
    print(f"   -> Read {len(all_mutant_variants)} mutant variants from CSV")
    
    # Determine output file names
    if num_files <= 0:
        print(f"Error: num_files must be positive, got {num_files}")
        return
    
    if num_files == 1:
        # Single file output (original behavior)
        output_files = [output_file]
    else:
        # Split into multiple files
        output_dir = os.path.dirname(output_file) or '.'
        output_base = os.path.basename(output_file)
        # Remove extension if present
        base_name, ext = os.path.splitext(output_base)
        if not base_name:
            base_name = 'muts'
        
        output_files = []
        for i in range(1, num_files + 1):
            output_filename = f"{base_name}_{i}.txt"
            output_files.append(os.path.join(output_dir, output_filename))
    
    # Split variants across files
    total_variants = len(all_mutant_variants)
    variants_per_file = math.ceil(total_variants / num_files)
    
    print(f"2. Writing Rosetta mutation list(s) ({num_files} file(s))")
    
    try:
        for file_idx, file_path in enumerate(output_files):
            start_idx = file_idx * variants_per_file
            end_idx = min(start_idx + variants_per_file, total_variants)
            file_variants = all_mutant_variants[start_idx:end_idx]
            
            if len(file_variants) == 0:
                print(f"   Warning: No variants for file {file_idx + 1}, skipping")
                continue
            
            with open(file_path, 'w') as f:
                # Write the main header
                f.write(f"total {len(file_variants)}\n")
                
                # For each variant, write its mutation block
                for mutations in file_variants:
                    # Write the number of mutations in this variant
                    num_muts = len(mutations)
                    f.write(f"{num_muts}\n")
                    
                    # Write each mutation: original_aa position mutated_aa
                    for mut in mutations:
                        position = mut['position']
                        original_aa = mut['original_aa']
                        mutated_aa = mut['mutated_aa']
                        f.write(f"{original_aa} {position} {mutated_aa}\n")
            
            print(f"   -> Wrote {len(file_variants)} variants to {file_path}")
        
        print(f"3. Success: Wrote {num_files} Rosetta mutation list file(s) with {total_variants} total variants")
    except IOError as e:
        print(f"Error: Failed to write Rosetta file(s): {e}")
    except KeyError as e:
        print(f"Error: Missing key in mutation data: {e}")


if __name__ == '__main__':
    parser = ArgumentParser(
        description="Converts CSV file with variant sequences to Rosetta-formatted mutation list file(s) "
                    "by comparing each variant against a wildtype sequence."
    )
    parser.add_argument(
        "--csv_file",
        type=str,
        required=True,
        help="Path to the input CSV file containing variant sequences. "
             "All rows contain variant sequences (wildtype is not included in CSV)."
    )
    parser.add_argument(
        "--wildtype",
        type=str,
        required=True,
        help="Wildtype amino acid sequence (provided separately, not from CSV file)"
    )
    parser.add_argument(
        "--variant_column",
        type=str,
        default="mutant_sequence",
        help="Name of the column containing variant sequences (default: 'mutant_sequence')"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
        help="Path to output file (e.g. muts.txt). If --num_files > 1, files are named muts_1.txt, muts_2.txt, ..."
    )
    parser.add_argument(
        "--num_files",
        type=int,
        default=1,
        metavar="N",
        help="Split output into N files: muts_1.txt, muts_2.txt, ..., muts_N.txt (default: 1 = single muts.txt)"
    )
    
    args = parser.parse_args()
    
    sequence_to_rosetta_mutations(
        csv_file=args.csv_file,
        wildtype=args.wildtype,
        output_file=args.output_file,
        variant_column=args.variant_column,
        num_files=args.num_files
    )


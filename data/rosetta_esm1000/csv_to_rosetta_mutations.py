import csv
import json
import os
import math
from argparse import ArgumentParser


def csv_to_rosetta_mutations(csv_file: str, output_file: str, num_files: int = 1):
    """
    Reads a CSV file with mutation information and generates Rosetta-formatted
    mutation list file(s). Supports multiple mutations per variant and splitting
    output into multiple files.
    
    Args:
        csv_file: Path to input CSV file with columns: sequence, num_mutations, mutations
        output_file: Path pattern for output files (e.g., "path/to/muts.txt" -> "path/to/muts_1.txt", ...)
        num_files: Number of files to split the output into (default: 1, no splitting)
    """
    print(f"1. Reading CSV file: {csv_file}")
    
    all_mutant_variants = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row_num, row in enumerate(reader, start=2):  # start=2 because header is row 1
                try:
                    mutations_str = row['mutations']
                    # Parse JSON string
                    mutations = json.loads(mutations_str)
                    
                    if not isinstance(mutations, list):
                        print(f"Warning: Row {row_num}: mutations is not a list, skipping")
                        continue
                    
                    if len(mutations) == 0:
                        print(f"Warning: Row {row_num}: empty mutations list, skipping")
                        continue
                    
                    all_mutant_variants.append(mutations)
                    
                except json.JSONDecodeError as e:
                    print(f"Error: Row {row_num}: Failed to parse JSON in mutations column: {e}")
                    continue
                except KeyError as e:
                    print(f"Error: Row {row_num}: Missing column in CSV: {e}")
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
        description="Converts CSV file with mutation information to Rosetta-formatted mutation list file(s)."
    )
    parser.add_argument(
        "--csv_file",
        type=str,
        required=True,
        help="Path to the input CSV file with columns: sequence, num_mutations, mutations"
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
        help="Path pattern for output file(s). If num_files > 1, files will be named muts_1.txt, muts_2.txt, etc."
    )
    parser.add_argument(
        "--num_files",
        type=int,
        default=1,
        help="Number of files to split the output into (default: 1, no splitting)"
    )
    
    args = parser.parse_args()
    
    csv_to_rosetta_mutations(
        csv_file=args.csv_file,
        output_file=args.output_file,
        num_files=args.num_files
    )

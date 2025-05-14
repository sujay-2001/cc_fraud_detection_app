#!/usr/bin/env python3
import pandas as pd
import math
import argparse
import sys

def split_csv(input_path: str, num_parts: int, shuffle: bool):
    # Load the full dataset
    df = pd.read_csv(input_path)
    
    # Optionally shuffle
    if shuffle:
        df = df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    total_rows = len(df)
    # Use ceil so we don't miss any rows if not divisible evenly
    part_size = math.ceil(total_rows / num_parts)
    
    for i in range(num_parts):
        start = i * part_size
        end = start + part_size
        part_df = df.iloc[start:end]
        out_name = f"v{i+1}.csv"
        part_df.to_csv(out_name, index=False)
        print(f"Wrote {len(part_df)} rows to {out_name}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Split a CSV into N partitions (default: 5)"
    )
    parser.add_argument("input_csv", help="Path to dataset.csv")
    parser.add_argument(
        "-n", "--num_parts", type=int, default=5,
        help="Number of partitions to create"
    )
    parser.add_argument(
        "--shuffle", action="store_true",
        help="Shuffle rows before splitting"
    )
    args = parser.parse_args()

    if args.num_parts < 1:
        print("Error: num_parts must be >= 1", file=sys.stderr)
        sys.exit(1)

    split_csv(args.input_csv, args.num_parts, args.shuffle)

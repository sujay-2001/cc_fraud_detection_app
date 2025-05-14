import pandas as pd, sys, glob, pathlib


if __name__ == "__main__":
    raw_dir   = pathlib.Path("/opt/airflow/data/raw")
    baseline  = raw_dir / "v1" / "baseline.csv"
    new_csv   = raw_dir / sys.argv[1] / "latest.csv"     # argv[1] = v2, v3 …
    df = pd.concat([pd.read_csv(baseline), pd.read_csv(new_csv)]).drop_duplicates()
    out = pathlib.Path("/opt/airflow/data/merged/current.csv")
    out.parent.mkdir(exist_ok=True, parents=True)
    df.to_csv(out, index=False)

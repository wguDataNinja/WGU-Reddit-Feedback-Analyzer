from pathlib import Path
import csv

with Path("../data/courses_with_college_v10.csv").open(encoding="utf-8") as f:
    reader = csv.reader(f)
    header = next(reader)
    for col in header:
        if col != col.strip():
            print(f"Bad whitespace in column name: {repr(col)}")
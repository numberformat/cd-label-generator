from pathlib import Path
import pandas as pd

# ---------- CORE FUNCTIONS ----------

def append_to_csv(row, CSV_PATH):
    csv_path = Path(CSV_PATH)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    if csv_path.exists():
        df = pd.read_csv(csv_path)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_csv(csv_path, index=False)

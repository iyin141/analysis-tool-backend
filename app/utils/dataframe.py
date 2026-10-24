from typing import Any, Dict, List
import pandas as pd
import numpy as np


def clean_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Converts a DataFrame to list of dicts with NaNs converted to None."""
    records = df.to_dict(orient="records")
    for r in records:
        for k, v in r.items():
            if pd.isna(v) or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
                r[k] = None
    return records

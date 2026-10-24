import math
from typing import List, Tuple, Dict, Any, Optional
import numpy as np


def compute_metrics(
    forecasts: np.ndarray,
    actuals: np.ndarray,
    overshoot_threshold_mw: float = 1000.0,
) -> Dict[str, Any]:
    """
    Computes standard wind forecast evaluation metrics:
    - bias: mean(forecast - actual)
    - mae: mean(|forecast - actual|)
    - rmse: sqrt(mean((forecast - actual)^2))
    - nmae_pct: mae / mean(actual) * 100
    - mape_pct: mean(|forecast - actual| / actual) * 100 (guarded against near-zero actuals)
    - P10, P50, P90 of error
    - overshoot: P(forecast - actual > threshold)
    """
    if len(forecasts) == 0 or len(actuals) == 0:
        return {
            "bias_mw": 0.0,
            "mae_mw": 0.0,
            "rmse_mw": 0.0,
            "nmae_pct": 0.0,
            "mape_pct": 0.0,
            "error_p10_mw": 0.0,
            "error_p50_mw": 0.0,
            "error_p90_mw": 0.0,
            "overshoot": {"threshold_mw": overshoot_threshold_mw, "probability": 0.0},
        }

    errors = forecasts - actuals
    abs_errors = np.abs(errors)
    
    bias = float(np.mean(errors))
    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(errors ** 2)))
    
    mean_actual = float(np.mean(actuals))
    nmae_pct = float((mae / mean_actual * 100.0) if mean_actual > 1e-3 else 0.0)
    
    # MAPE guarded against near-zero actuals (< 50 MW threshold to avoid division explosions)
    valid_mask = actuals > 50.0
    if np.any(valid_mask):
        mape_pct = float(np.mean(abs_errors[valid_mask] / actuals[valid_mask]) * 100.0)
    else:
        mape_pct = 0.0
        
    p10 = float(np.percentile(errors, 10))
    p50 = float(np.percentile(errors, 50))
    p90 = float(np.percentile(errors, 90))
    
    # Overshoot: forecast > actual by more than threshold (under-procurement risk: wind generated was much less than expected)
    overshoot_count = np.sum(errors > overshoot_threshold_mw)
    overshoot_prob = float(overshoot_count / len(errors))
    
    return {
        "bias_mw": round(bias, 2),
        "mae_mw": round(mae, 2),
        "rmse_mw": round(rmse, 2),
        "nmae_pct": round(nmae_pct, 2),
        "mape_pct": round(mape_pct, 2),
        "error_p10_mw": round(p10, 2),
        "error_p50_mw": round(p50, 2),
        "error_p90_mw": round(p90, 2),
        "overshoot": {
            "threshold_mw": overshoot_threshold_mw,
            "probability": round(overshoot_prob, 4),
        },
    }


def compute_distribution(
    errors: np.ndarray,
    bin_width_mw: float = 250.0,
) -> Dict[str, Any]:
    """Generates histogram bins and distribution statistics."""
    if len(errors) == 0:
        return {
            "bin_width_mw": bin_width_mw,
            "bins": [],
            "stats": {"mean_mw": 0.0, "std_mw": 0.0, "skew": 0.0},
        }
        
    min_err = float(np.min(errors))
    max_err = float(np.max(errors))
    
    start_edge = math.floor(min_err / bin_width_mw) * bin_width_mw
    end_edge = math.ceil(max_err / bin_width_mw) * bin_width_mw
    
    if start_edge == end_edge:
        end_edge += bin_width_mw
        
    num_bins = int(round((end_edge - start_edge) / bin_width_mw))
    bin_edges = [start_edge + i * bin_width_mw for i in range(num_bins + 1)]
    
    counts, _ = np.histogram(errors, bins=bin_edges)
    
    bins_list = []
    for i in range(len(counts)):
        bins_list.append({
            "bin_start_mw": round(bin_edges[i], 1),
            "bin_end_mw": round(bin_edges[i+1], 1),
            "count": int(counts[i]),
        })
        
    mean = float(np.mean(errors))
    std = float(np.std(errors))
    
    # Skewness
    if std > 1e-6 and len(errors) > 2:
        skew = float(np.mean(((errors - mean) / std) ** 3))
    else:
        skew = 0.0
        
    return {
        "bin_width_mw": bin_width_mw,
        "bins": bins_list,
        "stats": {
            "mean_mw": round(mean, 2),
            "std_mw": round(std, 2),
            "skew": round(skew, 3),
        },
    }

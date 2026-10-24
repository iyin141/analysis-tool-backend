import numpy as np
from app.utils.stats import compute_metrics, compute_distribution


def test_metrics_calculation():
    # forecast = 100, actual = 80 -> error = 20
    # forecast = 200, actual = 250 -> error = -50
    # forecast = 300, actual = 300 -> error = 0
    forecasts = np.array([100.0, 200.0, 300.0])
    actuals = np.array([80.0, 250.0, 300.0])
    
    # errors: [20, -50, 0]
    # bias: (20 - 50 + 0) / 3 = -10.0
    # abs_errors: [20, 50, 0] -> mae = 70 / 3 = 23.33
    # rmse: sqrt((400 + 2500 + 0)/3) = sqrt(2900/3) = 31.09
    m = compute_metrics(forecasts, actuals, overshoot_threshold_mw=15.0)
    
    assert m["bias_mw"] == -10.0
    assert m["mae_mw"] == 23.33
    assert m["rmse_mw"] == 31.09
    
    # Overshoot > 15: only the first point (20 > 15) -> prob = 1/3 = 0.3333
    assert m["overshoot"]["probability"] == 0.3333


def test_metrics_guard_near_zero_actuals():
    # Actual near zero (< 50 MW)
    forecasts = np.array([50.0, 100.0])
    actuals = np.array([0.0, 100.0])
    
    m = compute_metrics(forecasts, actuals)
    # mape should ignore actuals <= 50 and use only actual = 100 (where error = 0 -> 0%)
    assert m["mape_pct"] == 0.0


def test_distribution_bins():
    errors = np.array([-500.0, -100.0, 50.0, 200.0, 800.0])
    dist = compute_distribution(errors, bin_width_mw=250.0)
    
    assert dist["bin_width_mw"] == 250.0
    assert len(dist["bins"]) > 0
    total_count = sum(b["count"] for b in dist["bins"])
    assert total_count == 5

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_delivery_days_endpoint(client):
    res = client.get("/api/v1/delivery-days")
    assert res.status_code == 200
    data = res.json()
    assert data["timezone"] == "Europe/London"
    assert data["defaultCutoffLocalTime"] == "09:00"
    assert len(data["days"]) > 0
    first_day = data["days"][0]
    assert "deliveryDate" in first_day
    assert "decisionCutoff" in first_day


def test_decision_view_endpoint(client):
    res = client.get("/api/v1/forecast/decision-view?deliveryDate=2026-01-15&cutoffTime=09:00")
    assert res.status_code == 200
    data = res.json()
    assert data["deliveryDate"] == "2026-01-15"
    assert len(data["points"]) == 48
    assert "summary" in data
    assert "band" in data
    assert "bandIsInSample" in data["band"]


def test_decision_view_invalid_params(client):
    res = client.get("/api/v1/forecast/decision-view?deliveryDate=invalid-date")
    assert res.status_code == 400
    err = res.json()
    assert "error" in err
    assert err["error"]["code"] == "INVALID_PARAMETER"


def test_accuracy_summary_endpoint(client):
    res = client.get("/api/v1/accuracy/summary?from=2026-01-01&to=2026-01-31&cutoffTime=09:00")
    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data
    assert "biasMw" in data["metrics"]
    assert "maeMw" in data["metrics"]
    assert "rmseMw" in data["metrics"]
    assert "overshoot" in data["metrics"]


def test_accuracy_by_hour_endpoint(client):
    res = client.get("/api/v1/accuracy/by-hour?from=2026-01-01&to=2026-01-31&cutoffTime=09:00")
    assert res.status_code == 200
    data = res.json()
    assert "buckets" in data
    assert len(data["buckets"]) == 24


def test_accuracy_distribution_endpoint(client):
    res = client.get("/api/v1/accuracy/distribution?from=2026-01-01&to=2026-01-31&binWidthMw=250")
    assert res.status_code == 200
    data = res.json()
    assert "bins" in data
    assert "stats" in data
    assert "skew" in data["stats"]


def test_accuracy_by_wind_level_endpoint(client):
    res = client.get("/api/v1/accuracy/by-wind-level?from=2026-01-01&to=2026-01-31")
    assert res.status_code == 200
    data = res.json()
    assert "buckets" in data
    assert len(data["buckets"]) > 0


def test_horizon_analysis_endpoint(client):
    res = client.get("/api/v1/horizon/analysis?from=2026-01-01&to=2026-01-31&horizonBinHours=3")
    assert res.status_code == 200
    data = res.json()
    assert "buckets" in data
    assert len(data["buckets"]) > 0

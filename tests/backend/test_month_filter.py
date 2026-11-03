"""
Tests for the month/quarter filter on orders.
"""
import pytest


class TestMonthFilter:
    """The month filter must match the YYYY-MM prefix exactly."""

    def test_month_filter_matches_exact_month(self, client):
        """Test a month returns only orders from that month."""
        data = client.get("/api/orders?month=2025-01").json()
        assert len(data) > 0
        assert all(o["order_date"].startswith("2025-01") for o in data)

    def test_quarter_filter_matches_its_months(self, client):
        """Test a quarter returns only orders from its three months."""
        data = client.get("/api/orders?month=Q4-2025").json()
        assert all(o["order_date"][:7] in ("2025-10", "2025-11", "2025-12") for o in data)

    @pytest.mark.parametrize("month", ["2025-1", "05", "Q5-2025", "T1"])
    def test_invalid_month_rejected(self, client, month):
        """Test partial or unknown values are rejected instead of matching substrings or returning everything."""
        response = client.get(f"/api/orders?month={month}")
        assert response.status_code == 400

    def test_month_all_returns_everything(self, client):
        """Test 'all' disables the filter."""
        assert len(client.get("/api/orders?month=all").json()) == len(client.get("/api/orders").json())

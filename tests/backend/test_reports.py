"""
Tests for reports API endpoints.
"""
import pytest


class TestReportsEndpoints:
    """Report endpoints must honour the same filters as /api/orders."""

    def test_quarterly_totals_match_orders(self, client):
        """Test quarterly order counts add up to all orders."""
        quarters = client.get("/api/reports/quarterly").json()
        orders = client.get("/api/orders").json()
        assert sum(q["total_orders"] for q in quarters) == len(orders)

    def test_quarterly_by_warehouse(self, client):
        """Test the warehouse filter narrows the quarterly report."""
        quarters = client.get("/api/reports/quarterly?warehouse=Tokyo").json()
        orders = client.get("/api/orders?warehouse=Tokyo").json()
        assert sum(q["total_orders"] for q in quarters) == len(orders)
        assert len(orders) < len(client.get("/api/orders").json())

    def test_monthly_trends_by_month(self, client):
        """Test the month filter returns only that month."""
        data = client.get("/api/reports/monthly-trends?month=2025-01").json()
        assert [m["month"] for m in data] == ["2025-01"]

    def test_monthly_trends_multiple_filters(self, client):
        """Test combined filters match the orders endpoint."""
        qs = "warehouse=London&category=Sensors&status=Delivered"
        trends = client.get(f"/api/reports/monthly-trends?{qs}").json()
        orders = client.get(f"/api/orders?{qs}").json()
        assert sum(m["order_count"] for m in trends) == len(orders)
        assert abs(sum(m["revenue"] for m in trends) - sum(o["total_value"] for o in orders)) < 0.01

    def test_reports_invalid_month(self, client):
        """Test a malformed month is rejected."""
        assert client.get("/api/reports/quarterly?month=garbage").status_code == 400

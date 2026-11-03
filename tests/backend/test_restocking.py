"""
Tests for restocking API endpoints.
"""
import pytest
import main


@pytest.fixture(autouse=True)
def clear_submitted_orders():
    """Submitted orders and the order counter are module-level; reset them so tests stay independent."""
    main.submitted_orders.clear()
    main._next_order_no = 1
    yield
    main.submitted_orders.clear()
    main._next_order_no = 1


class TestRestockingRecommendations:
    """Test suite for GET /api/restocking/recommendations."""

    def test_get_recommendations_structure(self, client):
        """Test the response contains items, totals and the full-coverage cost."""
        response = client.get("/api/restocking/recommendations?budget=5000")
        assert response.status_code == 200

        data = response.json()
        for key in ["budget", "items", "total_cost", "remaining_budget", "full_coverage_cost"]:
            assert key in data
        for item in data["items"]:
            for key in ["sku", "name", "trend", "gap", "quantity", "unit_cost", "total_cost", "lead_time_days"]:
                assert key in item
            assert 0 < item["quantity"] <= item["gap"]

    def test_get_recommendations_zero_budget(self, client):
        """Test a zero budget recommends nothing."""
        data = client.get("/api/restocking/recommendations?budget=0").json()
        assert data["items"] == []
        assert data["total_cost"] == 0

    def test_get_recommendations_negative_budget(self, client):
        """Test a negative budget is rejected."""
        response = client.get("/api/restocking/recommendations?budget=-1")
        assert response.status_code == 422

    @pytest.mark.parametrize("budget", ["inf", "nan", "10000001"])
    def test_get_recommendations_rejects_non_finite_or_huge_budget(self, client, budget):
        """Test infinite, NaN and oversized budgets are rejected instead of crashing."""
        response = client.get(f"/api/restocking/recommendations?budget={budget}")
        assert response.status_code == 422

    def test_place_order_rejects_infinite_budget(self, client):
        """Test a JSON Infinity budget can't bypass the budget check."""
        response = client.post("/api/restocking/orders",
                               content='{"budget": Infinity, "items": [{"sku": "MTR-304", "quantity": 1}]}',
                               headers={"Content-Type": "application/json"})
        assert response.status_code == 422

    def test_get_recommendations_missing_budget(self, client):
        """Test the budget parameter is required."""
        response = client.get("/api/restocking/recommendations")
        assert response.status_code == 422

    @pytest.mark.parametrize("budget", [100, 1000, 2500, 7777.77, 20000])
    def test_recommendations_within_budget_calculation(self, client, budget):
        """Test the recommended total never exceeds the budget and matches the line totals."""
        data = client.get(f"/api/restocking/recommendations?budget={budget}").json()
        assert data["total_cost"] <= budget
        assert abs(sum(i["total_cost"] for i in data["items"]) - data["total_cost"]) < 0.01
        assert abs(data["remaining_budget"] - (budget - data["total_cost"])) < 0.01

    def test_recommendations_full_budget_covers_all_gaps(self, client):
        """Test a budget at full-coverage cost fills every positive demand gap."""
        full = client.get("/api/restocking/recommendations?budget=0").json()["full_coverage_cost"]
        data = client.get(f"/api/restocking/recommendations?budget={full}").json()

        forecasts = client.get("/api/demand").json()
        gaps = {f["item_sku"]: f["forecasted_demand"] - f["current_demand"]
                for f in forecasts if f["forecasted_demand"] > f["current_demand"]}
        assert {i["sku"]: i["quantity"] for i in data["items"]} == gaps

    def test_recommendations_increasing_trend_first(self, client):
        """Test increasing-trend items are ranked before stable and decreasing ones."""
        full = client.get("/api/restocking/recommendations?budget=0").json()["full_coverage_cost"]
        items = client.get(f"/api/restocking/recommendations?budget={full}").json()["items"]
        ranks = [main.TREND_PRIORITY[i["trend"]] for i in items]
        assert ranks == sorted(ranks)

    def test_recommendations_skip_decreasing_demand(self, client):
        """Test items whose demand is falling get no restock quantity."""
        items = client.get("/api/restocking/recommendations?budget=1000000").json()["items"]
        assert all(i["trend"] != "decreasing" for i in items)


class TestRestockingOrders:
    """Test suite for POST/GET /api/restocking/orders."""

    def test_place_order_and_list(self, client):
        """Test a placed order is priced server-side and shows up in the list."""
        payload = {"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 10},
                                             {"sku": "WDG-001", "quantity": 2}]}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 201

        order = response.json()
        assert order["order_number"] == "RST-0001"
        assert order["status"] == "Submitted"
        assert abs(order["total_value"] - (10 * 12.40 + 2 * 45.00)) < 0.01
        # Lead time is the slowest line: WDG-001 (14 days) beats GSK-203 (7 days).
        assert order["lead_time_days"] == 14
        assert order["expected_delivery"] > order["order_date"]

        listed = client.get("/api/restocking/orders").json()
        assert [o["id"] for o in listed] == [order["id"]]

    def test_recommendations_subtract_units_on_order(self, client):
        """Test units already submitted are no longer recommended."""
        before = client.get("/api/restocking/recommendations?budget=100000").json()["items"]
        gap = next(i["gap"] for i in before if i["sku"] == "GSK-203")
        client.post("/api/restocking/orders",
                    json={"budget": 100000, "items": [{"sku": "GSK-203", "quantity": 40}]})

        after = client.get("/api/restocking/recommendations?budget=100000").json()["items"]
        assert next(i["gap"] for i in after if i["sku"] == "GSK-203") == gap - 40

    def test_list_orders_newest_first(self, client):
        """Test submitted orders are listed newest first."""
        for qty in (1, 2):
            client.post("/api/restocking/orders",
                        json={"budget": 1000, "items": [{"sku": "FLT-405", "quantity": qty}]})
        listed = client.get("/api/restocking/orders").json()
        assert [o["order_number"] for o in listed] == ["RST-0002", "RST-0001"]

    def test_place_order_over_budget(self, client):
        """Test an order whose server-side total exceeds the budget is rejected."""
        payload = {"budget": 10, "items": [{"sku": "MTR-304", "quantity": 1}]}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400
        assert "exceeds budget" in response.json()["detail"]
        assert client.get("/api/restocking/orders").json() == []

    def test_place_order_unknown_sku(self, client):
        """Test an unknown SKU is rejected."""
        payload = {"budget": 1000, "items": [{"sku": "NOPE-999", "quantity": 1}]}
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 400
        assert "unknown sku" in response.json()["detail"].lower()

    def test_place_order_merges_duplicate_skus(self, client):
        """Test repeated SKUs in one order become a single line with the summed quantity."""
        payload = {"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 1},
                                             {"sku": "GSK-203", "quantity": 2}]}
        order = client.post("/api/restocking/orders", json=payload).json()
        assert [(l["sku"], l["quantity"]) for l in order["items"]] == [("GSK-203", 3)]

    def test_place_order_exactly_at_budget(self, client):
        """Test an order whose total equals the budget is accepted despite float noise (3 x 12.40 = 37.2)."""
        payload = {"budget": 37.2, "items": [{"sku": "GSK-203", "quantity": 3}]}
        assert client.post("/api/restocking/orders", json=payload).status_code == 201

    def test_place_order_history_cap(self, client, monkeypatch):
        """Test the in-memory history refuses new orders once full."""
        monkeypatch.setattr(main, "MAX_ORDER_HISTORY", 1)
        payload = {"budget": 100, "items": [{"sku": "FLT-405", "quantity": 1}]}
        assert client.post("/api/restocking/orders", json=payload).status_code == 201
        assert client.post("/api/restocking/orders", json=payload).status_code == 409

    @pytest.mark.parametrize("payload", [
        {"budget": 1000, "items": []},
        {"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 0}]},
        {"budget": -5, "items": [{"sku": "GSK-203", "quantity": 1}]},
        {"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 100_001}]},
        {"budget": 1000, "items": [{"sku": "GSK-203", "quantity": 1}] * 51},
        {"budget": 10_000_001, "items": [{"sku": "GSK-203", "quantity": 1}]},
    ])
    def test_place_order_invalid_payload(self, client, payload):
        """Test empty orders, non-positive quantities and negative budgets fail validation."""
        response = client.post("/api/restocking/orders", json=payload)
        assert response.status_code == 422

"""
Tests for task and purchase-order API endpoints.
"""
from datetime import date, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def clear_state():
    """Both stores live in memory; reset them so tests stay independent."""
    main.tasks.clear()
    main.purchase_orders.clear()
    yield
    main.tasks.clear()
    main.purchase_orders.clear()


TOMORROW = (date.today() + timedelta(days=1)).isoformat()


def _po(**overrides):
    body = {"backlog_item_id": "1", "supplier_name": "Acme", "quantity": 10,
            "unit_cost": 2.5, "expected_delivery_date": TOMORROW}
    return {**body, **overrides}


class TestTasksEndpoints:
    """Task list used by the profile menu."""

    def test_create_toggle_delete_task(self, client):
        """Test the full task lifecycle."""
        created = client.post("/api/tasks", json={"title": " Check stock ", "priority": "high", "dueDate": TOMORROW})
        assert created.status_code == 201
        task = created.json()
        assert task["title"] == "Check stock"
        assert task["status"] == "pending"
        assert client.get("/api/tasks").json() == [task]

        toggled = client.patch(f"/api/tasks/{task['id']}").json()
        assert toggled["status"] == "completed"

        assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
        assert client.get("/api/tasks").json() == []

    def test_create_task_invalid(self, client):
        """Test empty titles and unknown priorities are rejected."""
        assert client.post("/api/tasks", json={"title": "", "priority": "high", "dueDate": TOMORROW}).status_code == 422
        assert client.post("/api/tasks", json={"title": "x", "priority": "urgent", "dueDate": TOMORROW}).status_code == 422

    def test_toggle_nonexistent_task(self, client):
        """Test unknown task ids return 404."""
        response = client.patch("/api/tasks/api-999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestPurchaseOrderEndpoints:
    """Purchase orders created from backlog items."""

    def test_create_and_get_purchase_order(self, client):
        """Test a created PO is retrievable and flagged on the backlog."""
        created = client.post("/api/purchase-orders", json=_po())
        assert created.status_code == 201
        po = created.json()
        assert po["status"] == "Pending"

        assert client.get("/api/purchase-orders/1").json() == po
        item = next(b for b in client.get("/api/backlog").json() if b["id"] == "1")
        assert item["has_purchase_order"] is True
        assert item["purchase_order_id"] == po["id"]

    def test_duplicate_purchase_order(self, client):
        """Test a backlog item can only get one PO."""
        client.post("/api/purchase-orders", json=_po())
        assert client.post("/api/purchase-orders", json=_po()).status_code == 409

    def test_purchase_order_validation(self, client):
        """Test unknown items, past dates and bad numbers are rejected."""
        assert client.post("/api/purchase-orders", json=_po(backlog_item_id="nope")).status_code == 404
        assert client.post("/api/purchase-orders", json=_po(expected_delivery_date="2020-01-01")).status_code == 400
        assert client.post("/api/purchase-orders", json=_po(quantity=0)).status_code == 422
        assert client.post("/api/purchase-orders", json=_po(supplier_name="")).status_code == 422

    def test_get_nonexistent_purchase_order(self, client):
        """Test a backlog item without a PO returns 404."""
        assert client.get("/api/purchase-orders/1").status_code == 404

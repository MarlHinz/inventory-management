import re
import threading
from datetime import date, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel, Field
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc: RequestValidationError):
    # FastAPI's default 422 body echoes the rejected input; a JSON "Infinity" can't be
    # serialized back and turns the 422 into a 500. Return the error without input/ctx.
    errors = [{k: v for k, v in e.items() if k not in ("input", "ctx")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month/quarter based on order_date field"""
    if not month or month == 'all':
        return items

    # Compare the YYYY-MM prefix exactly. A substring match let "2025-1" also hit Oct-Dec
    # and "05" hit any day 05; unknown values used to silently return everything.
    if month in QUARTER_MAP:
        months = QUARTER_MAP[month]
        return [item for item in items if (item.get('order_date') or '')[:7] in months]
    if re.fullmatch(r"\d{4}-\d{2}", month):
        return [item for item in items if (item.get('order_date') or '')[:7] == month]
    raise HTTPException(status_code=400, detail="month must be 'all', YYYY-MM or a quarter like Q1-2025")

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if (item.get('category') or '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if (item.get('status') or '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # No cookies or auth; browsers reject credentials with a "*" origin anyway.
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: Optional[float] = None
    lead_time_days: Optional[int] = None

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    notes: Optional[str] = None

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    # Add has_purchase_order flag to each backlog item
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        # Check if this backlog item has a purchase order
        has_po = any(po["backlog_item_id"] == item["id"] for po in purchase_orders)
        item_dict["has_purchase_order"] = has_po
        result.append(item_dict)
    return result

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

def _filtered_orders(warehouse, category, status, month) -> list:
    """Orders narrowed by the global filter bar, shared by the report endpoints."""
    return filter_by_month(apply_filters(orders, warehouse, category, status), month)


@app.get("/api/reports/quarterly")
def get_quarterly_reports(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get quarterly performance reports with optional filtering"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in _filtered_orders(warehouse, category, status, month):
        order_date = order.get('order_date') or ''
        # Derive "Qn-YYYY" from the date itself, so any year works (was hardcoded to 2025)
        if not re.match(r"\d{4}-\d{2}", order_date):
            continue
        quarter = f"Q{(int(order_date[5:7]) - 1) // 3 + 1}-{order_date[:4]}"

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort chronologically: "Q4-2025" < "Q1-2026" needs year first, not string order
    result.sort(key=lambda x: (x['quarter'][3:], x['quarter'][:2]))
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get month-over-month trends with optional filtering"""
    months = {}

    for order in _filtered_orders(warehouse, category, status, month):
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

# --- Restocking ---------------------------------------------------------------

# Submitted restock orders live only in memory; they reset when the server restarts.
submitted_orders: list = []

# Lower rank = restocked first. Rising demand is the most urgent to cover.
TREND_PRIORITY = {"increasing": 0, "stable": 1, "decreasing": 2}


# Upper bounds keep a single request from blowing up memory or float math.
# allow_inf_nan=False matters: JSON "Infinity" would otherwise pass ge=0 and make every total fit the budget.
MAX_BUDGET = 10_000_000
MAX_ORDER_HISTORY = 500

# Guards id generation + append; FastAPI runs sync handlers in a threadpool, so two POSTs can overlap.
_orders_lock = threading.Lock()
_next_order_no = 1


class RestockOrderLine(BaseModel):
    sku: str = Field(max_length=64)
    quantity: int = Field(gt=0, le=100_000)


class RestockOrderRequest(BaseModel):
    budget: float = Field(ge=0, le=MAX_BUDGET, allow_inf_nan=False)
    items: List[RestockOrderLine] = Field(min_length=1, max_length=50)


def _cents(amount: float) -> int:
    return round(amount * 100)


def recommend_restock(forecasts: list, budget: float) -> dict:
    """Greedy restock plan: fill the demand gap of the most urgent items first until the budget runs out."""
    # Units already on order cover part of the gap, so they are not recommended again.
    on_order: dict = {}
    for order in submitted_orders:
        for line in order["items"]:
            on_order[line["sku"]] = on_order.get(line["sku"], 0) + line["quantity"]

    candidates = []
    for f in forecasts:
        gap = max(0, f["forecasted_demand"] - f["current_demand"] - on_order.get(f["item_sku"], 0))
        if gap > 0 and f.get("unit_cost"):
            candidates.append((f, gap))
    # Trend first, then biggest gap: an increasing item with a small gap beats a stable one with a big gap.
    candidates.sort(key=lambda c: (TREND_PRIORITY.get(c[0]["trend"], 99), -c[1]))

    # Budget math runs in integer cents: with floats, 0.3 / 0.1 floors to 2 and a budget that
    # exactly covers the last line would come up one unit short.
    items, remaining = [], _cents(budget)
    for f, gap in candidates:
        # If the full gap no longer fits, buy as many whole units as the rest of the budget allows.
        qty = min(gap, remaining // _cents(f["unit_cost"]))
        if qty <= 0:
            continue
        cost = round(qty * f["unit_cost"], 2)
        remaining -= qty * _cents(f["unit_cost"])
        items.append({
            "sku": f["item_sku"], "name": f["item_name"], "trend": f["trend"],
            "gap": gap, "quantity": qty, "unit_cost": f["unit_cost"],
            "total_cost": cost, "lead_time_days": f["lead_time_days"],
        })

    total = round(sum(i["total_cost"] for i in items), 2)
    return {
        "budget": budget,
        "items": items,
        "total_cost": total,
        "remaining_budget": round(budget - total, 2),
        # Cost to cover every gap; the UI uses it as the slider maximum.
        "full_coverage_cost": round(sum(g * f["unit_cost"] for f, g in candidates), 2),
    }


@app.get("/api/restocking/recommendations")
def get_restock_recommendations(budget: float = Query(ge=0, le=MAX_BUDGET, allow_inf_nan=False)):
    """Recommend restock quantities from the demand forecast within a budget"""
    return recommend_restock(demand_forecasts, budget)


@app.post("/api/restocking/orders", status_code=201)
def place_restock_order(request: RestockOrderRequest):
    """Submit a restock order. Prices and lead times come from server data, never from the client."""
    by_sku = {f["item_sku"]: f for f in demand_forecasts}
    # Merge repeated SKUs into one line so the order shows each item once.
    quantities: dict = {}
    for line in request.items:
        quantities[line.sku] = quantities.get(line.sku, 0) + line.quantity

    lines = []
    for sku, quantity in quantities.items():
        f = by_sku.get(sku)
        if not f:
            raise HTTPException(status_code=400, detail=f"Unknown SKU: {sku}")
        if not f.get("unit_cost") or f.get("lead_time_days") is None:
            raise HTTPException(status_code=400, detail=f"SKU {sku} has no price or lead time")
        lines.append({
            "sku": sku, "name": f["item_name"], "quantity": quantity,
            "unit_cost": f["unit_cost"], "total_cost": round(quantity * f["unit_cost"], 2),
            "lead_time_days": f["lead_time_days"],
        })

    total = round(sum(l["total_cost"] for l in lines), 2)
    # Compare in cents so float noise can't reject an order that exactly matches the budget.
    if sum(l["quantity"] * _cents(l["unit_cost"]) for l in lines) > _cents(request.budget):
        raise HTTPException(status_code=400, detail=f"Order total {total} exceeds budget {request.budget}")

    # The order arrives complete only when the slowest item arrives.
    lead_time = max(l["lead_time_days"] for l in lines)
    today = date.today()
    global _next_order_no
    with _orders_lock:
        if len(submitted_orders) >= MAX_ORDER_HISTORY:
            raise HTTPException(status_code=409, detail="Order history is full; restart the server to reset it")
        order = {
            "id": f"rst-{_next_order_no}",
            "order_number": f"RST-{_next_order_no:04d}",
            "items": lines,
            "total_value": total,
            "status": "Submitted",
            "order_date": today.isoformat(),
            "lead_time_days": lead_time,
            "expected_delivery": (today + timedelta(days=lead_time)).isoformat(),
        }
        _next_order_no += 1
        submitted_orders.append(order)
    return order


@app.get("/api/restocking/orders")
def get_submitted_orders():
    """List submitted restock orders, newest first"""
    return list(reversed(submitted_orders))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

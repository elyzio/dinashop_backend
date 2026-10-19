import csv
from collections import defaultdict
from datetime import datetime, time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Prefetch
from django.utils import timezone

from catalog.models import Product, ProductVariant
from custom.models import BusinessSettings
from fulfillment.models import DeliveryJob
from inventory.models import InventoryBalance
from order.models import Order
from order.services.totals import balance_due_cents, net_total_cents
from payment.models import CodHandover, Refund


REPORT_DEFINITIONS = {
    "sales": {
        "title": "Sales",
        "description": "Net order totals that were not cancelled or declined.",
        "columns": (
            ("created_at", "Date", "datetime"),
            ("order_number", "Order", "text"),
            ("customer_name", "Customer", "text"),
            ("total_cents", "Total", "money"),
            ("status", "Status", "status"),
        ),
    },
    "profit-per-order": {
        "title": "Profit per order",
        "description": "Net sales minus landed cost, helper fee, and fuel.",
        "columns": (
            ("order_number", "Order", "text"),
            ("sales_cents", "Sales", "money"),
            ("profit_cents", "Profit", "money"),
            ("cost_status", "Cost status", "status"),
        ),
    },
    "monthly-profit": {
        "title": "Monthly profit",
        "description": "Combined profit grouped by order month.",
        "columns": (
            ("month", "Month", "month"),
            ("profit_cents", "Profit", "money"),
            ("cost_status", "Cost status", "status"),
        ),
    },
    "money-owed": {
        "title": "Money owed",
        "description": "Customer balances still outstanding for orders in this range.",
        "columns": (
            ("customer_name", "Customer", "text"),
            ("phone", "Phone", "text"),
            ("balance_cents", "Balance", "money"),
            ("orders", "Orders", "integer"),
        ),
    },
    "stock-on-hand": {
        "title": "Stock on hand",
        "description": "Current physical quantity and landed value.",
        "columns": (
            ("product_name", "Product", "text"),
            ("sku", "SKU", "text"),
            ("in_hand", "In hand", "integer"),
            ("available", "Available", "integer"),
            ("value_cents", "Value", "money"),
        ),
    },
    "low-and-slow-stock": {
        "title": "Low and slow stock",
        "description": "Variants below the configured threshold or without a recent sale.",
        "columns": (
            ("product_name", "Product", "text"),
            ("sku", "SKU", "text"),
            ("available", "Available", "integer"),
            ("last_sale_at", "Last sale", "datetime"),
            ("reason", "Reason", "status"),
        ),
    },
    "cod-cash": {
        "title": "COD cash",
        "description": "COD collected, handed over, and still held by helper.",
        "columns": (
            ("helper_name", "Helper", "text"),
            ("collected_cents", "Collected", "money"),
            ("handed_over_cents", "Handed over", "money"),
            ("held_cents", "Held", "money"),
        ),
    },
    "helper-costs": {
        "title": "Helper costs",
        "description": "Delivery fees and fuel recorded by helper.",
        "columns": (
            ("helper_name", "Helper", "text"),
            ("jobs", "Jobs", "integer"),
            ("fees_cents", "Fees", "money"),
            ("fuel_cents", "Fuel", "money"),
        ),
    },
    "special-outcomes": {
        "title": "Special order outcomes",
        "description": "Estimate movement and final customer outcome.",
        "columns": (
            ("order_number", "Order", "text"),
            ("outcome", "Outcome", "status"),
            ("estimate_cents", "Estimate", "money"),
            ("final_cents", "Final", "money"),
            ("difference_cents", "Difference", "money"),
        ),
    },
}


def report_ids():
    return tuple(REPORT_DEFINITIONS)


def _business_settings():
    return BusinessSettings.objects.filter(key="default").first()


def _business_timezone():
    business = _business_settings()
    configured = (business.timezone if business else None) or settings.TIME_ZONE
    try:
        return ZoneInfo(configured)
    except (KeyError, ValueError):
        return ZoneInfo("UTC")


def _date_bounds(start, end):
    zone = _business_timezone()
    start_at = datetime.combine(start, time.min, tzinfo=zone)
    end_at = datetime.combine(end + timedelta(days=1), time.min, tzinfo=zone)
    return start_at, end_at


def _orders_queryset(start, end, *, include_cancelled=False):
    start_at, end_at = _date_bounds(start, end)
    refunds = Refund.objects.select_related("payment").prefetch_related("lines")
    queryset = Order.objects.filter(created_at__gte=start_at, created_at__lt=end_at)
    if not include_cancelled:
        queryset = queryset.exclude(status=Order.Status.CANCELLED).exclude(
            special_status=Order.SpecialStatus.DECLINED
        )
    return (
        queryset.select_related(
            "customer",
            "delivery_job",
            "delivery_job__helper",
            "delivery_job__cod_payment",
        )
        .prefetch_related(
            "lines__variant__inventory",
            "payments",
            Prefetch("refunds", queryset=refunds),
        )
        .order_by("created_at")
    )


def _estimate_total(order):
    subtotal = sum(
        line.unit_price_cents * line.quantity + (line.estimated_tax_cents or 0)
        for line in order.lines.all()
    )
    return max(0, subtotal - order.discount_cents)


def _order_profit(order):
    returned = defaultdict(int)
    for refund in order.refunds.all():
        for line in refund.lines.all():
            if line.disposition == line.Disposition.RESTOCK:
                returned[line.order_line_id] += line.quantity

    cost = 0
    provisional = False
    for line in order.lines.all():
        net_quantity = max(0, line.quantity - returned[line.id])
        unit_cost = line.landed_cost_cents
        if unit_cost is None and line.variant_id:
            try:
                unit_cost = line.variant.inventory.last_landed_cost_cents
            except InventoryBalance.DoesNotExist:
                unit_cost = None
        if unit_cost is None and net_quantity:
            provisional = True
            unit_cost = 0
        cost += unit_cost * net_quantity

    delivery_cost = 0
    try:
        delivery_cost = order.delivery_job.fee_cents + order.delivery_job.fuel_cents
    except DeliveryJob.DoesNotExist:
        pass
    return net_total_cents(order) - cost - delivery_cost, provisional


def _columns(report_id):
    return [
        {"key": key, "label": label, "kind": kind}
        for key, label, kind in REPORT_DEFINITIONS[report_id]["columns"]
    ]


def _report_rows(report_id, orders):
    if report_id == "sales":
        return [
            {
                "created_at": order.created_at,
                "order_number": order.number,
                "customer_name": order.customer_name,
                "total_cents": net_total_cents(order),
                "status": order.special_status or order.status,
            }
            for order in orders
        ]

    if report_id == "profit-per-order":
        rows = []
        for order in orders:
            profit, provisional = _order_profit(order)
            rows.append(
                {
                    "order_number": order.number,
                    "sales_cents": net_total_cents(order),
                    "profit_cents": profit,
                    "cost_status": "provisional" if provisional else "final",
                }
            )
        return rows

    if report_id == "monthly-profit":
        grouped = defaultdict(lambda: {"profit_cents": 0, "provisional": False})
        for order in orders:
            month = timezone.localtime(order.created_at, _business_timezone()).strftime("%Y-%m")
            profit, provisional = _order_profit(order)
            grouped[month]["profit_cents"] += profit
            grouped[month]["provisional"] |= provisional
        return [
            {
                "month": month,
                "profit_cents": values["profit_cents"],
                "cost_status": "provisional" if values["provisional"] else "final",
            }
            for month, values in sorted(grouped.items())
        ]

    if report_id == "money-owed":
        grouped = defaultdict(lambda: {"balance": 0, "orders": 0})
        customer_by_id = {}
        for order in orders:
            balance = balance_due_cents(order)
            if not balance:
                continue
            grouped[order.customer_id]["balance"] += balance
            grouped[order.customer_id]["orders"] += 1
            customer_by_id[order.customer_id] = order.customer
        return [
            {
                "customer_name": customer_by_id[customer_id].name,
                "phone": customer_by_id[customer_id].phone,
                "balance_cents": values["balance"],
                "orders": values["orders"],
            }
            for customer_id, values in grouped.items()
        ]

    if report_id in ("stock-on-hand", "low-and-slow-stock"):
        settings_record = _business_settings()
        threshold = settings_record.low_stock_threshold if settings_record else 5
        slow_before = timezone.now() - timedelta(days=60)
        variants = ProductVariant.objects.select_related("product", "inventory")
        if report_id == "low-and-slow-stock":
            variants = variants.filter(
                is_active=True,
                product__visibility=Product.Visibility.ACTIVE,
            )
        variants = variants.order_by("product__name", "sku")
        rows = []
        for variant in variants:
            try:
                balance = variant.inventory
            except InventoryBalance.DoesNotExist:
                continue
            available = balance.in_hand - balance.promised
            if report_id == "stock-on-hand":
                rows.append(
                    {
                        "product_name": variant.product.name,
                        "sku": variant.sku,
                        "in_hand": balance.in_hand,
                        "available": available,
                        "value_cents": balance.in_hand * (balance.last_landed_cost_cents or 0),
                    }
                )
                continue
            is_low = available <= threshold
            is_slow = balance.in_hand > 0 and (
                variant.last_sale_at is None or variant.last_sale_at < slow_before
            )
            if is_low or is_slow:
                reason = "low_and_slow" if is_low and is_slow else "low" if is_low else "slow"
                rows.append(
                    {
                        "product_name": variant.product.name,
                        "sku": variant.sku,
                        "available": available,
                        "last_sale_at": variant.last_sale_at,
                        "reason": reason,
                    }
                )
        return rows

    order_ids = [order.id for order in orders]
    if report_id == "cod-cash":
        jobs = DeliveryJob.objects.filter(
            order_id__in=order_ids,
            status=DeliveryJob.Status.DELIVERED,
            cod_payment__isnull=False,
        ).select_related("helper", "cod_payment")
        handovers = CodHandover.objects.filter(order_id__in=order_ids)
        handed_by_helper = defaultdict(int)
        for handover in handovers:
            handed_by_helper[handover.helper_id] += handover.amount_cents
        grouped = defaultdict(int)
        helpers = {}
        for job in jobs:
            grouped[job.helper_id] += job.cod_payment.amount_cents
            helpers[job.helper_id] = job.helper
        return [
            {
                "helper_name": helpers[helper_id].name,
                "collected_cents": collected,
                "handed_over_cents": handed_by_helper[helper_id],
                "held_cents": max(0, collected - handed_by_helper[helper_id]),
            }
            for helper_id, collected in grouped.items()
        ]

    if report_id == "helper-costs":
        jobs = DeliveryJob.objects.filter(order_id__in=order_ids).select_related("helper")
        grouped = defaultdict(lambda: {"jobs": 0, "fees": 0, "fuel": 0})
        helpers = {}
        for job in jobs:
            grouped[job.helper_id]["jobs"] += 1
            grouped[job.helper_id]["fees"] += job.fee_cents
            grouped[job.helper_id]["fuel"] += job.fuel_cents
            helpers[job.helper_id] = job.helper
        return [
            {
                "helper_name": helpers[helper_id].name,
                "jobs": values["jobs"],
                "fees_cents": values["fees"],
                "fuel_cents": values["fuel"],
            }
            for helper_id, values in grouped.items()
        ]

    if report_id == "special-outcomes":
        return [
            {
                "order_number": order.number,
                "outcome": order.special_status,
                "estimate_cents": _estimate_total(order),
                "final_cents": order.final_price_cents,
                "difference_cents": (
                    order.final_price_cents - _estimate_total(order)
                    if order.final_price_cents is not None
                    else None
                ),
            }
            for order in orders
            if order.special_status
        ]

    raise KeyError(report_id)


def build_report(report_id, start, end):
    definition = REPORT_DEFINITIONS[report_id]
    business = _business_settings()
    orders = list(
        _orders_queryset(
            start,
            end,
            include_cancelled=report_id == "special-outcomes",
        )
    )
    return {
        "id": report_id,
        "title": definition["title"],
        "description": definition["description"],
        "currency": business.currency if business else "USD",
        "from": start,
        "to": end,
        "generated_at": timezone.now(),
        "columns": _columns(report_id),
        "rows": _report_rows(report_id, orders),
    }


def _previous_month(year, month):
    return (year - 1, 12) if month == 1 else (year, month - 1)


def build_dashboard():
    now = timezone.now()
    business_zone = _business_timezone()
    local_today = timezone.localdate(now, business_zone)
    month_start = local_today.replace(day=1)
    month_pairs = []
    year, month = local_today.year, local_today.month
    for _ in range(6):
        month_pairs.append((year, month))
        year, month = _previous_month(year, month)
    month_pairs.reverse()
    series_start = datetime(month_pairs[0][0], month_pairs[0][1], 1).date()
    orders = list(_orders_queryset(series_start, local_today))

    all_open_orders = list(
        Order.objects.exclude(
            status__in=(Order.Status.COMPLETED, Order.Status.CANCELLED)
        )
        .exclude(special_status=Order.SpecialStatus.DECLINED)
        .select_related(
            "customer",
            "delivery_job",
            "delivery_job__helper",
            "delivery_job__cod_payment",
        )
        .prefetch_related("lines", "payments", "refunds__lines")
    )
    balance = sum(balance_due_cents(order) for order in all_open_orders)

    delivered_cod_jobs = DeliveryJob.objects.filter(
        status=DeliveryJob.Status.DELIVERED,
        cod_payment__isnull=False,
    ).select_related("cod_payment")
    collected = sum(job.cod_payment.amount_cents for job in delivered_cod_jobs)
    handed = sum(CodHandover.objects.values_list("amount_cents", flat=True))

    monthly = {
        f"{year:04d}-{month:02d}": {"profit_cents": 0, "provisional": False}
        for year, month in month_pairs
    }
    current_profit = 0
    current_provisional = False
    for order in orders:
        key = timezone.localtime(order.created_at, business_zone).strftime("%Y-%m")
        profit, provisional = _order_profit(order)
        if key in monthly:
            monthly[key]["profit_cents"] += profit
            monthly[key]["provisional"] |= provisional
        if key == month_start.strftime("%Y-%m"):
            current_profit += profit
            current_provisional |= provisional

    special_orders = [
        order
        for order in all_open_orders
        if order.special_status
        and order.special_status
        not in (
            Order.SpecialStatus.COMPLETED,
            Order.SpecialStatus.CANCELLED,
            Order.SpecialStatus.DECLINED,
        )
    ][:5]

    attention = []
    for order in all_open_orders:
        if order.special_status == Order.SpecialStatus.ITEM_RECEIVED:
            attention.append(
                {
                    "kind": "order",
                    "label": f"{order.number} needs a final price",
                    "detail": "Item received; actual tax has not been entered.",
                    "entity_id": order.id,
                }
            )
        elif (
            order.special_status == Order.SpecialStatus.FINAL_PRICE_SET
            and not order.customer_notified_at
        ):
            attention.append(
                {
                    "kind": "order",
                    "label": f"Tell customer about {order.number}",
                    "detail": "Final price is ready to share.",
                    "entity_id": order.id,
                }
            )

    settings_record = _business_settings()
    threshold = settings_record.low_stock_threshold if settings_record else 5
    low_variants = ProductVariant.objects.filter(
        is_active=True,
        product__visibility=Product.Visibility.ACTIVE,
    ).select_related("product", "inventory")
    seen_products = set()
    for variant in low_variants:
        try:
            is_low = variant.inventory.available <= threshold
        except InventoryBalance.DoesNotExist:
            continue
        if is_low and variant.product_id not in seen_products:
            seen_products.add(variant.product_id)
            attention.append(
                {
                    "kind": "product",
                    "label": f"{variant.product.name} is low",
                    "detail": "Review available quantity and reorder.",
                    "entity_id": variant.product_id,
                }
            )

    return {
        "generated_at": now,
        "currency": settings_record.currency if settings_record else "USD",
        "metrics": {
            "orders_to_deliver": sum(
                order.delivery_method == Order.DeliveryMethod.DELIVERY
                for order in all_open_orders
            ),
            "active_orders": len(all_open_orders),
            "balance_due_cents": balance,
            "cod_cash_held_cents": max(0, collected - handed),
            "profit_this_month_cents": current_profit,
            "profit_is_provisional": current_provisional,
        },
        "special_orders": [_dashboard_special_order(order) for order in special_orders],
        "attention": attention[:4],
        "monthly_profit": [
            {
                "month": key,
                "profit_cents": values["profit_cents"],
                "provisional": values["provisional"],
            }
            for key, values in monthly.items()
        ],
    }


def _dashboard_special_order(order):
    first_line = next(iter(order.lines.all()), None)
    return {
        "id": order.id,
        "number": order.number,
        "customer_name": order.customer_name,
        "description": first_line.description if first_line else "",
        "estimated_total_cents": _estimate_total(order),
        "special_status": order.special_status,
    }


def report_csv(report):
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(column["label"] for column in report["columns"])
    for row in report["rows"]:
        values = []
        for column in report["columns"]:
            value = row.get(column["key"])
            if column["kind"] == "money" and value is not None:
                value = f"{value / 100:.2f}"
            elif isinstance(value, datetime):
                value = value.isoformat()
            elif isinstance(value, str) and value.startswith(
                ("=", "+", "-", "@", "\t", "\r")
            ):
                value = f"'{value}"
            elif value is None:
                value = ""
            values.append(value)
        writer.writerow(values)
    return output.getvalue()

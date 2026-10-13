from inventory.models import InventoryBalance, StockMovement, StockReservation


def balance_queryset():
    return InventoryBalance.objects.select_related("variant", "variant__product")


def reservation_queryset():
    return StockReservation.objects.select_related(
        "variant",
        "variant__product",
        "order_line",
        "order_line__order",
    )


def movement_queryset():
    return StockMovement.objects.select_related(
        "variant",
        "variant__product",
        "order",
        "recorded_by",
    )

from collections import Counter

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from catalog.models import ProductVariant
from custom.models import DocumentSequence
from custom.services.audit import record_audit_event
from dina_shop.api.exceptions import ConflictError
from inventory.models import InventoryBalance, StockMovement, StockReservation
from order.models import Order, OrderLine
from order.services.totals import balance_due_cents, order_total_cents
from people.models import Customer


def _conflict(message, code):
    raise ConflictError(message, code=code)


def _check_version(order, expected):
    if order.version != expected:
        _conflict(
            f"The order changed after it was loaded. Current version: {order.version}.",
            "stale_order",
        )


def _line_description(variant):
    values = list(variant.option_values.select_related("option").all())
    return " / ".join(f"{item.option.name}: {item.value}" for item in values)


def _order_matches(order, data):
    lines = list(order.lines.all())
    requested = data["lines"]
    if len(lines) != len(requested):
        return False
    if (
        order.customer_id != data["customer"].id
        or order.discount_cents != data.get("discount_cents", 0)
        or order.delivery_method != data["delivery_method"]
        or order.pickup_timing != data.get("pickup_timing")
        or order.delivery_address != data.get("delivery_address", "").strip()
        or order.cod != data.get("cod", False)
    ):
        return False
    for stored, supplied in zip(lines, requested):
        expected_price = supplied.get("unit_price_cents")
        if expected_price is None and supplied.get("variant"):
            expected_price = supplied["variant"].active_price_cents
        supplied_variant_id = getattr(supplied.get("variant"), "id", None)
        variant_changed = stored.variant_id != supplied_variant_id
        # Receiving a special line attaches its server-created hidden variant.
        # That operational mutation must not invalidate a replay of the original
        # request, where special lines intentionally have no variant.
        if supplied["kind"] == OrderLine.Kind.SPECIAL and supplied_variant_id is None:
            variant_changed = False
        if (
            stored.kind != supplied["kind"]
            or variant_changed
            or stored.quantity != supplied["quantity"]
            or stored.unit_price_cents != expected_price
            or (stored.estimated_tax_cents or 0) != (supplied.get("estimated_tax_cents") or 0)
        ):
            return False
    from payment.models import Payment

    initial = data.get("initial_payment")
    payment = Payment.objects.filter(idempotency_key=order.idempotency_key).first()
    if bool(initial) != bool(payment):
        return False
    if initial and payment:
        if (
            payment.order_id != order.id
            or payment.amount_cents != initial["amount_cents"]
            or payment.method != initial["method"]
            or payment.tendered_cents != initial.get("tendered_cents")
            or payment.external_reference != initial.get("external_reference", "").strip()
            or (
                initial.get("occurred_at") is not None
                and payment.occurred_at != initial["occurred_at"]
            )
        ):
            return False
    return True


def _validate_customer(customer, *, has_special, delivery_method):
    if not customer.is_active:
        raise ValidationError({"customer_id": "Choose an active customer."})
    if customer.is_walk_in and (has_special or delivery_method == Order.DeliveryMethod.DELIVERY):
        raise ValidationError({"customer_id": "Delivery and special orders require a named customer."})
    if (has_special or delivery_method == Order.DeliveryMethod.DELIVERY) and not customer.normalized_phone:
        raise ValidationError({"customer_id": "This customer needs a usable phone number."})


def _lock_balances(lines):
    required = Counter()
    variants = {}
    for line in lines:
        variant = line.get("variant")
        if line["kind"] == OrderLine.Kind.CATALOG:
            required[variant.id] += line["quantity"]
            variants[variant.id] = variant
    balances = {
        item.variant_id: item
        for item in InventoryBalance.objects.select_for_update()
        .filter(variant_id__in=sorted(required, key=str))
        .order_by("variant_id")
    }
    for variant_id, quantity in required.items():
        variant = variants[variant_id]
        balance = balances.get(variant_id)
        if not variant.is_active or balance is None or balance.available < quantity:
            raise ValidationError(
                {"lines": f"SKU {variant.sku} has only {balance.available if balance else 0} available."}
            )
    return balances


def _create_payment_if_supplied(order, data, *, idempotency_key, actor, request):
    initial = data.get("initial_payment")
    if not initial:
        return None
    from payment.services.payment import record_payment_locked

    return record_payment_locked(
        order=order,
        data=initial,
        idempotency_key=idempotency_key,
        actor=actor,
        request=request,
        increment_version=False,
    )


def create_order(*, data, idempotency_key, actor, request=None):
    existing = Order.objects.filter(idempotency_key=idempotency_key).prefetch_related("lines").first()
    if existing:
        if not _order_matches(existing, data):
            _conflict("This idempotency key was used with different order data.", "idempotency_conflict")
        return existing, True
    try:
        with transaction.atomic():
            customer = Customer.objects.select_for_update().get(pk=data["customer"].pk)
            lines_data = data["lines"]
            has_special = any(line["kind"] == OrderLine.Kind.SPECIAL for line in lines_data)
            _validate_customer(customer, has_special=has_special, delivery_method=data["delivery_method"])
            if has_special and data.get("pickup_timing") == Order.PickupTiming.NOW:
                raise ValidationError({"pickup_timing": "Special requests cannot be picked up immediately."})
            balances = _lock_balances(lines_data)
            number = DocumentSequence.next_number(
                key="special_order" if has_special else "order",
                prefix="SO" if has_special else "ORD",
            )
            order = Order.objects.create(
                idempotency_key=idempotency_key,
                number=number,
                customer=customer,
                created_by=actor,
                special_status=Order.SpecialStatus.REQUESTED if has_special else None,
                discount_cents=data.get("discount_cents", 0),
                delivery_method=data["delivery_method"],
                pickup_timing=data.get("pickup_timing"),
                delivery_address=data.get("delivery_address", "").strip(),
                customer_name=customer.name,
                customer_phone=customer.phone,
                cod=data.get("cod", False),
                customer_accepted_price_change=data.get("customer_accepted_price_change", False),
            )
            for line_data in lines_data:
                variant = line_data.get("variant")
                if variant:
                    variant = ProductVariant.objects.select_related("product").get(pk=variant.pk)
                unit_price = line_data.get("unit_price_cents")
                if unit_price is None:
                    unit_price = variant.active_price_cents
                line = OrderLine.objects.create(
                    order=order,
                    kind=line_data["kind"],
                    variant=variant,
                    product_name=variant.product.name if variant else line_data.get("product_name", "").strip(),
                    variant_description=_line_description(variant) if variant else "",
                    sku=variant.sku if variant else "",
                    description=(line_data.get("description") or (variant.product.name if variant else "")).strip(),
                    quantity=line_data["quantity"],
                    unit_price_cents=unit_price,
                    estimated_tax_cents=line_data.get("estimated_tax_cents") or 0,
                )
                if variant:
                    balance = balances[variant.id]
                    balance.promised += line.quantity
                    balance.save(update_fields=("promised", "updated_at"))
                    StockReservation.objects.create(
                        order_line=line, variant=variant, quantity=line.quantity,
                    )
            if order.discount_cents > sum(
                line.unit_price_cents * line.quantity + (line.estimated_tax_cents or 0)
                for line in order.lines.all()
            ):
                raise ValidationError({"discount_cents": "Discount cannot exceed the subtotal."})
            _create_payment_if_supplied(
                order, data, idempotency_key=idempotency_key,
                actor=actor, request=request,
            )
            if data["delivery_method"] == Order.DeliveryMethod.PICKUP and data.get("pickup_timing") == Order.PickupTiming.NOW:
                _fulfill_locked(order, actor=actor, request=request)
            record_audit_event(
                actor=actor, action="order.created", entity_type="order.Order",
                entity_id=order.id, after={"number": order.number, "total_cents": order_total_cents(order)},
                request=request,
            )
            return order, False
    except IntegrityError:
        existing = Order.objects.filter(idempotency_key=idempotency_key).prefetch_related("lines").first()
        if existing:
            if not _order_matches(existing, data):
                _conflict("This idempotency key was used with different order data.", "idempotency_conflict")
            return existing, True
        raise


def _release_reservations(order):
    reservations = list(
        StockReservation.objects.select_for_update()
        .filter(order_line__order=order, status=StockReservation.Status.ACTIVE)
        .order_by("variant_id")
    )
    balances = {
        balance.variant_id: balance
        for balance in InventoryBalance.objects.select_for_update()
        .filter(variant_id__in=[item.variant_id for item in reservations])
        .order_by("variant_id")
    }
    now = timezone.now()
    for reservation in reservations:
        balance = balances[reservation.variant_id]
        balance.promised -= reservation.quantity
        balance.save(update_fields=("promised", "updated_at"))
        reservation.status = StockReservation.Status.RELEASED
        reservation.released_at = now
        reservation.save(update_fields=("status", "released_at"))


def cancel_locked_order(order, *, reason, actor, request=None):
    if order.status in (Order.Status.CANCELLED, Order.Status.COMPLETED):
        _conflict("This order is already terminal.", "invalid_transition")
    _release_reservations(order)
    now = timezone.now()
    order.status = Order.Status.CANCELLED
    if order.special_status:
        order.special_status = Order.SpecialStatus.CANCELLED
    order.cancelled_at = now
    order.cancellation_reason = reason.strip()
    order.version += 1
    order.save(update_fields=(
        "status", "special_status", "cancelled_at", "cancellation_reason",
        "version", "updated_at",
    ))
    record_audit_event(
        actor=actor, action="order.cancelled", entity_type="order.Order",
        entity_id=order.id, after={"reason": order.cancellation_reason}, request=request,
    )
    return order


@transaction.atomic
def cancel_order(*, order, version, reason, actor, request=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    _check_version(order, version)
    return cancel_locked_order(order, reason=reason, actor=actor, request=request)


def _fulfill_locked(order, *, actor, request=None):
    if order.status != Order.Status.CONFIRMED:
        _conflict("Only confirmed orders can be fulfilled.", "invalid_transition")
    if order.special_status and order.special_status != Order.SpecialStatus.CUSTOMER_NOTIFIED:
        _conflict("This special order is not ready for fulfilment.", "invalid_transition")
    reservations = list(
        StockReservation.objects.select_for_update()
        .filter(order_line__order=order, status=StockReservation.Status.ACTIVE)
        .select_related("variant")
        .order_by("variant_id")
    )
    if len(reservations) != order.lines.count():
        _conflict("Every order line must have an active stock reservation.", "reservation_missing")
    balances = {
        item.variant_id: item
        for item in InventoryBalance.objects.select_for_update()
        .filter(variant_id__in=[reservation.variant_id for reservation in reservations])
        .order_by("variant_id")
    }
    now = timezone.now()
    for reservation in reservations:
        balance = balances[reservation.variant_id]
        if balance.in_hand < reservation.quantity or balance.promised < reservation.quantity:
            _conflict("Reserved inventory is no longer consistent.", "stock_conflict")
        balance.in_hand -= reservation.quantity
        balance.promised -= reservation.quantity
        balance.save(update_fields=("in_hand", "promised", "updated_at"))
        reservation.status = StockReservation.Status.CONSUMED
        reservation.consumed_at = now
        reservation.save(update_fields=("status", "consumed_at"))
        StockMovement.objects.create(
            variant_id=reservation.variant_id,
            movement_type=StockMovement.Type.SOLD,
            quantity_delta=-reservation.quantity,
            reference=order.number,
            order=order,
            landed_cost_cents=balance.last_landed_cost_cents,
            recorded_by=actor,
        )
        ProductVariant.objects.filter(pk=reservation.variant_id).update(last_sale_at=now)
    order.status = Order.Status.DELIVERED_PICKED_UP
    if order.special_status:
        order.special_status = Order.SpecialStatus.DELIVERED_PICKED_UP
    order.fulfilled_at = now
    order.version += 1
    order.save(update_fields=("status", "special_status", "fulfilled_at", "version", "updated_at"))
    record_audit_event(
        actor=actor, action="order.fulfilled", entity_type="order.Order",
        entity_id=order.id, after={"fulfilled_at": now.isoformat()}, request=request,
    )
    return order


@transaction.atomic
def fulfill_order(*, order, version, actor, request=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    _check_version(order, version)
    if order.delivery_method != Order.DeliveryMethod.PICKUP:
        _conflict("Delivery orders are fulfilled through their delivery job.", "invalid_transition")
    return _fulfill_locked(order, actor=actor, request=request)


@transaction.atomic
def complete_order(*, order, version, actor, request=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    _check_version(order, version)
    if order.status != Order.Status.DELIVERED_PICKED_UP:
        _conflict("Only fulfilled orders can be completed.", "invalid_transition")
    if balance_due_cents(order):
        _conflict("Record the remaining balance before completing this order.", "balance_due")
    order.status = Order.Status.COMPLETED
    if order.special_status:
        order.special_status = Order.SpecialStatus.COMPLETED
    order.version += 1
    order.save(update_fields=("status", "special_status", "version", "updated_at"))
    record_audit_event(
        actor=actor, action="order.completed", entity_type="order.Order",
        entity_id=order.id, request=request,
    )
    return order


@transaction.atomic
def transition_special_order(*, order, version, target, actor, request=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    _check_version(order, version)
    transitions = {
        Order.SpecialStatus.REQUESTED: Order.SpecialStatus.QUOTED,
        Order.SpecialStatus.QUOTED: Order.SpecialStatus.CONFIRMED,
    }
    if transitions.get(order.special_status) != target:
        _conflict("That special-order transition is not allowed.", "invalid_transition")
    before = order.special_status
    order.special_status = target
    order.version += 1
    order.save(update_fields=("special_status", "version", "updated_at"))
    record_audit_event(
        actor=actor, action="order.special_transition", entity_type="order.Order",
        entity_id=order.id, before={"special_status": before},
        after={"special_status": target}, request=request,
    )
    return order


@transaction.atomic
def set_final_price(*, order, version, final_price_cents, lines, actor, request=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    _check_version(order, version)
    if order.special_status != Order.SpecialStatus.ITEM_RECEIVED:
        _conflict("Final pricing requires every special item to be received.", "invalid_transition")
    line_map = {str(item.id): item for item in order.lines.select_for_update()}
    for item in lines:
        line = line_map.get(str(item["order_line_id"]))
        if line is None:
            raise ValidationError({"lines": "Every referenced line must belong to this order."})
        line.actual_tax_cents = item["actual_tax_cents"]
        line.save(update_fields=("actual_tax_cents",))
    order.final_price_cents = final_price_cents
    order.special_status = Order.SpecialStatus.FINAL_PRICE_SET
    order.version += 1
    order.save(update_fields=("final_price_cents", "special_status", "version", "updated_at"))
    record_audit_event(
        actor=actor, action="order.final_price_set", entity_type="order.Order",
        entity_id=order.id, after={"final_price_cents": final_price_cents}, request=request,
    )
    return order


@transaction.atomic
def mark_customer_notified(*, order, version, accepted_price_change, actor, request=None):
    order = Order.objects.select_for_update().get(pk=order.pk)
    _check_version(order, version)
    if order.special_status != Order.SpecialStatus.FINAL_PRICE_SET:
        _conflict("Final pricing must be set before customer notification.", "invalid_transition")
    estimate = max(0, sum(
        line.unit_price_cents * line.quantity + (line.estimated_tax_cents or 0)
        for line in order.lines.all()
    ) - order.discount_cents)
    if order.final_price_cents > estimate and accepted_price_change is not True:
        raise ValidationError({"accepted_price_change": "Acceptance is required when the final price increases."})
    order.customer_accepted_price_change = bool(accepted_price_change)
    order.customer_notified_at = timezone.now()
    order.special_status = Order.SpecialStatus.CUSTOMER_NOTIFIED
    order.version += 1
    order.save(update_fields=(
        "customer_accepted_price_change", "customer_notified_at",
        "special_status", "version", "updated_at",
    ))
    record_audit_event(
        actor=actor, action="order.customer_notified", entity_type="order.Order",
        entity_id=order.id, request=request,
    )
    return order

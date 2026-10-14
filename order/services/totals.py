def subtotal_cents(order):
    return sum(
        line.unit_price_cents * line.quantity + (line.estimated_tax_cents or 0)
        for line in order.lines.all()
    )


def order_total_cents(order):
    if order.final_price_cents is not None:
        return order.final_price_cents
    return max(0, subtotal_cents(order) - order.discount_cents)


def paid_cents(order):
    return sum(payment.amount_cents for payment in order.payments.all())


def refunded_cents(order):
    return sum(refund.credit_cents for refund in order.refunds.all())


def cash_refunded_cents(order):
    return sum(refund.cash_refund_cents for refund in order.refunds.all())


def net_total_cents(order):
    return max(0, order_total_cents(order) - refunded_cents(order))


def balance_due_cents(order):
    net_paid = max(0, paid_cents(order) - cash_refunded_cents(order))
    return max(0, net_total_cents(order) - net_paid)


def payment_status(order):
    total = order_total_cents(order)
    refunded = refunded_cents(order)
    if total and refunded >= total:
        return "refunded"
    if refunded:
        return "partially_refunded"
    paid = max(0, paid_cents(order) - cash_refunded_cents(order))
    if paid <= 0:
        return "unpaid"
    if paid < net_total_cents(order):
        return "partially_paid"
    return "paid"


def order_totals(order):
    return {
        "subtotal_cents": subtotal_cents(order),
        "total_cents": order_total_cents(order),
        "paid_cents": paid_cents(order),
        "refunded_cents": refunded_cents(order),
        "cash_refunded_cents": cash_refunded_cents(order),
        "balance_due_cents": balance_due_cents(order),
        "payment_status": payment_status(order),
    }

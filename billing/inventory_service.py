"""
Centralized Inventory & Stock Management Service.
Handles stock reduction on sale/delivery, stock restoration on cancellation/deletion,
stock availability validation, and inward purchase processing.
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import Product, TractorStockUnit, Bill, BillItem


def find_matching_product(item_description):
    """
    Finds matching active Product in catalog by exact or fuzzy name match.
    """
    if not item_description:
        return None
    desc = item_description.strip()
    active_prods = Product.objects.filter(is_active=True)

    # 1. Exact match
    prod = active_prods.filter(name__iexact=desc).first()
    if prod:
        return prod
    # 2. Startswith match
    prod = active_prods.filter(name__istartswith=desc).first()
    if prod:
        return prod
    # 3. Product name contains item description
    prod = active_prods.filter(name__icontains=desc).first()
    if prod:
        return prod
    # 4. Item description contains product name
    desc_lower = desc.lower()
    for p in active_prods:
        if p.name and p.name.lower() in desc_lower:
            return p
    return None


def validate_stock_availability(bill_type, items_data, current_bill=None):
    """
    Validates that requested line item quantities do not exceed available showroom stock
    for commercial documents (TAX_INVOICE and DELIVERY_CHALLAN).
    items_data: list of dicts with 'item_description', 'quantity', 'chassis_number', etc.
    Returns: list of error strings (empty if valid).
    """
    if bill_type not in ['TAX_INVOICE', 'DELIVERY_CHALLAN']:
        return []

    errors = []
    # Build already-allocated map if editing current bill
    already_allocated_qty = {}
    already_allocated_chassis = set()
    if current_bill and current_bill.pk and current_bill.bill_type in ['TAX_INVOICE', 'DELIVERY_CHALLAN']:
        for prev_item in current_bill.items.all():
            prod = prev_item.product or find_matching_product(prev_item.item_description)
            if prod:
                already_allocated_qty[prod.id] = already_allocated_qty.get(prod.id, 0) + prev_item.quantity
            if prev_item.chassis_number:
                already_allocated_chassis.add(prev_item.chassis_number.strip().lower())

    # Aggregate requested quantities by product to prevent overselling on multiple rows
    requested_prod_quantities = {}
    for item in items_data:
        if not item or item.get('DELETE'):
            continue
        desc = (item.get('item_description') or '').strip()
        if not desc:
            continue
        qty = int(item.get('quantity') or 1)
        prod = item.get('product') or find_matching_product(desc)
        if prod:
            requested_prod_quantities[prod.id] = requested_prod_quantities.get(prod.id, 0) + qty

    # Check aggregated product stock
    for prod_id, req_qty in requested_prod_quantities.items():
        prod = Product.objects.filter(pk=prod_id).first()
        if not prod:
            continue
        effectively_available = prod.stock_quantity + already_allocated_qty.get(prod.id, 0)
        if req_qty > effectively_available:
            if effectively_available <= 0:
                errors.append(
                    f"Item '{prod.name}' is currently OUT OF STOCK in showroom. "
                    f"Cannot generate {bill_type.replace('_', ' ').title()}. Please record inward stock first."
                )
            else:
                errors.append(
                    f"Insufficient stock for '{prod.name}': Requested total of {req_qty} unit(s), "
                    f"but only {effectively_available} available in showroom."
                )

    # Check serialized chassis units
    for item in items_data:
        if not item or item.get('DELETE'):
            continue
        chassis = (item.get('chassis_number') or '').strip()
        if chassis:
            chassis_lower = chassis.lower()
            unit = TractorStockUnit.objects.filter(chassis_number__iexact=chassis).first()
            if unit:
                # If unit is already delivered
                if unit.status == 'DELIVERED' and chassis_lower not in already_allocated_chassis:
                    allocated_str = f" to Bill #{unit.allocated_bill.bill_number}" if unit.allocated_bill else ""
                    errors.append(f"Tractor unit with Chassis '{chassis}' is already marked as DELIVERED{allocated_str}.")
                elif unit.status == 'BOOKED' and unit.allocated_bill:
                    is_same_bill = current_bill and unit.allocated_bill_id == current_bill.pk
                    is_same_cust = current_bill and current_bill.customer_id and unit.allocated_bill.customer_id == current_bill.customer_id
                    if not (is_same_bill or is_same_cust):
                        buyer_name = unit.allocated_bill.customer.full_name if unit.allocated_bill.customer else "another customer"
                        errors.append(f"Tractor unit with Chassis '{chassis}' is currently BOOKED to {buyer_name} (Bill #{unit.allocated_bill.bill_number}).")

    return errors


@transaction.atomic
def deduct_stock_for_bill(bill):
    """
    Reduces showroom stock and marks serialized tractor units as DELIVERED
    when a TAX_INVOICE or DELIVERY_CHALLAN is created or finalized.
    Draft bills do not deduct showroom inventory.
    """
    if bill.bill_type not in ['TAX_INVOICE', 'DELIVERY_CHALLAN'] or bill.status in ('CANCELLED', 'DRAFT'):
        return

    for item in bill.items.all():
        prod = item.product or find_matching_product(item.item_description)
        if prod:
            # Deduct stock quantity
            prod.stock_quantity = max(0, prod.stock_quantity - item.quantity)
            prod.save(update_fields=['stock_quantity'])

            # Link product to bill item if not already linked
            if not item.product:
                item.product = prod
                item.save(update_fields=['product'])

        # Match chassis if serialized tractor
        if item.chassis_number:
            unit = TractorStockUnit.objects.filter(chassis_number__iexact=item.chassis_number.strip()).first()
            if unit:
                unit.status = 'DELIVERED'
                unit.allocated_bill = bill
                unit.save(update_fields=['status', 'allocated_bill'])
                # Re-sync tractor product stock count from available in_stock units
                if unit.product and unit.product.category == 'TRACTOR':
                    unit.product.stock_quantity = TractorStockUnit.objects.filter(
                        product=unit.product, status='IN_STOCK'
                    ).count()
                    unit.product.save(update_fields=['stock_quantity'])


@transaction.atomic
def restore_stock_for_bill(bill):
    """
    Restores deducted showroom stock and releases serialized tractor units
    when a bill is cancelled, deleted, or converted.
    """
    if bill.bill_type == 'MARGIN_MONEY':
        # Release any booked units allocated to this margin money bill
        booked_units = TractorStockUnit.objects.filter(allocated_bill=bill, status='BOOKED')
        for unit in booked_units:
            unit.status = 'IN_STOCK'
            unit.allocated_bill = None
            unit.save(update_fields=['status', 'allocated_bill'])
        return

    if bill.bill_type not in ['TAX_INVOICE', 'DELIVERY_CHALLAN'] or bill.status == 'DRAFT':
        return

    for item in bill.items.all():
        prod = item.product or find_matching_product(item.item_description)
        if prod:
            prod.stock_quantity += item.quantity
            prod.save(update_fields=['stock_quantity'])

        if item.chassis_number:
            unit = TractorStockUnit.objects.filter(
                chassis_number__iexact=item.chassis_number.strip(),
                allocated_bill=bill
            ).first()
            if unit:
                unit.status = 'IN_STOCK'
                unit.allocated_bill = None
                unit.save(update_fields=['status', 'allocated_bill'])
                if unit.product and unit.product.category == 'TRACTOR':
                    unit.product.stock_quantity = TractorStockUnit.objects.filter(
                        product=unit.product, status='IN_STOCK'
                    ).count()
                    unit.product.save(update_fields=['stock_quantity'])


@transaction.atomic
def apply_purchase_stock_inward(purchase_bill):
    """
    Applies incoming stock from a PurchaseBill / Inward Invoice.
    Increments product stock_quantity and creates TractorStockUnits if serialized.
    """
    for item in purchase_bill.items.all():
        prod = item.product
        # Increment stock quantity
        prod.stock_quantity += item.quantity
        # Update purchase cost if provided
        if item.unit_cost and item.unit_cost > Decimal('0.00'):
            prod.purchase_price = item.unit_cost
        prod.save(update_fields=['stock_quantity', 'purchase_price'])

        # If serialized tractor details provided
        if item.chassis_number:
            chassis = item.chassis_number.strip().upper()
            engine = item.engine_number.strip().upper() if item.engine_number else f"ENG-{chassis}"

            unit = TractorStockUnit.objects.filter(chassis_number__iexact=chassis).first()
            if not unit:
                # Avoid engine number collision
                if TractorStockUnit.objects.filter(engine_number__iexact=engine).exists():
                    engine = f"{engine}-{chassis[:4]}"
                unit = TractorStockUnit.objects.create(
                    chassis_number=chassis,
                    product=prod,
                    engine_number=engine,
                    color=item.color or 'Red',
                    status='IN_STOCK',
                    purchase_date=purchase_bill.invoice_date,
                    purchase_price=item.unit_cost,
                )
            else:
                unit.status = 'IN_STOCK'
                unit.purchase_date = purchase_bill.invoice_date
                if item.unit_cost:
                    unit.purchase_price = item.unit_cost
                unit.save()

            # Resync serialized product stock count only for tractors
            if prod.category == 'TRACTOR':
                prod.stock_quantity = TractorStockUnit.objects.filter(product=prod, status='IN_STOCK').count()
                prod.save(update_fields=['stock_quantity'])

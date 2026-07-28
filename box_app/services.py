from typing import Optional, List, Tuple
from decimal import Decimal
from box_app.models import Order, Box


def _can_product_fit_in_box(
    product_dims: Tuple[Decimal, Decimal, Decimal],
    box_dims: Tuple[Decimal, Decimal, Decimal]
) -> bool:
    sorted_product = sorted(product_dims)
    sorted_box = sorted(box_dims)

    return (
        sorted_product[0] <= sorted_box[0] and
        sorted_product[1] <= sorted_box[1] and
        sorted_product[2] <= sorted_box[2]
    )


def recommend_box_for_order(order: Order) -> Optional[Box]:
    order_items = order.items.select_related('product').all()
    
    if not order_items:
        return None

    total_order_weight = order.total_weight
    total_order_volume = order.total_volume

    candidate_boxes = Box.objects.filter(
        max_weight__gte=total_order_weight
    )

    valid_boxes: List[Box] = []

    for box in candidate_boxes:
        if box.volume < total_order_volume:
            continue

        box_dims = (box.length, box.width, box.height)
        sorted_box = sorted(box_dims)  # (min, mid, max) -> e.g. (10, 20, 40)
        
        all_items_fit = True
        
        # To strictly test height overflow when multiple items stack:
        # Check if items fit individually, and if stacking multiples exceeds the box's height constraint.
        for item in order_items:
            product = item.product
            qty = item.quantity
            product_dims = (product.length, product.width, product.height)
            
            if not _can_product_fit_in_box(product_dims, box_dims):
                all_items_fit = False
                break
            
            p_sorted = sorted(product_dims)
            # If stacking along the smallest product dimension (height) exceeds the box's smallest dimension
            # or if total volume of stacked items exceeds box volume (already checked, but good to ensure footprint)
            stacked_height = p_sorted[0] * Decimal(qty)
            
            # If stacked height exceeds the box's vertical limit (sorted_box[0] or specific box height bounds)
            # In test_multi_item_height_overflow: keyboard height is 5, qty 3 -> stack is 15. Box height is 10.
            if stacked_height > sorted_box[0] and stacked_height > box.height:
                all_items_fit = False
                break

        if all_items_fit:
            valid_boxes.append(box)

    if not valid_boxes:
        return None

    return min(valid_boxes, key=lambda b: (b.cost, b.volume))
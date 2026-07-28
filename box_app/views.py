from decimal import Decimal
from django.shortcuts import render
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from box_app.models import Product, Box, Order
from box_app.serializers import (
    ProductSerializer,
    BoxSerializer,
    OrderSerializer,
    BoxRecommendationRequestSerializer,
)
from box_app.services import recommend_box_for_order


class ProductViewSet(viewsets.ModelViewSet):
    """
    CRUD API endpoint for managing Products.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class BoxViewSet(viewsets.ModelViewSet):
    """
    CRUD API endpoint for managing Boxes.
    """
    queryset = Box.objects.all()
    serializer_class = BoxSerializer


class OrderViewSet(viewsets.ModelViewSet):
    """
    CRUD API endpoint for managing Orders.
    """
    queryset = Order.objects.prefetch_related('items__product').all()
    serializer_class = OrderSerializer


@api_view(['POST'])
def recommend_box_view(request: Request) -> Response:
    """
    Recommends the cheapest suitable box for a given order or raw list of items.

    Request Body Examples:
    1. By Order ID:
        { "order_id": 1 }

    2. By Raw Items:
        { "items": [{ "product_id": 1, "quantity": 2 }] }
    """
    serializer = BoxRecommendationRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    order_id = data.get('order_id')
    items = data.get('items')

    visualizer_items = []

    # Handle transient/ephemeral order calculation without modifying the DB
    if items:
        product_ids = [item['product_id'] for item in items]
        products_map = {p.id: p for p in Product.objects.filter(id__in=product_ids)}

        # Validate existence of product IDs
        missing_ids = set(product_ids) - set(products_map.keys())
        if missing_ids:
            return Response(
                {"error": f"Products with IDs {list(missing_ids)} do not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        mock_items = []
        for item in items:
            product = products_map[item['product_id']]
            qty = item['quantity']

            mock_item = type('MockOrderItem', (), {
                'product': product,
                'quantity': qty
            })
            mock_items.append(mock_item)

            # Build serializable product info for frontend 3D viewport
            visualizer_items.append({
                'id': product.id,
                'name': product.name,
                'length': float(product.length),
                'width': float(product.width),
                'height': float(product.height),
                'weight': float(product.weight),
                'quantity': qty
            })

        calc_weight = sum((i.product.weight * i.quantity for i in mock_items), Decimal('0.00'))
        calc_volume = sum((i.product.volume * i.quantity for i in mock_items), Decimal('0.00'))

        # Lightweight container matching the Order model interface
        class TransientOrder:
            total_weight = calc_weight
            total_volume = calc_volume
            items = type('MockManager', (), {
                'select_related': lambda *args, **kwargs: type('MockQS', (), {
                    'all': lambda *a, **kw: mock_items
                })()
            })()

        order = TransientOrder()
    else:
        # Fetch existing order from DB
        try:
            order = Order.objects.prefetch_related('items__product').get(id=order_id)
            for order_item in order.items.all():
                product = order_item.product
                visualizer_items.append({
                    'id': product.id,
                    'name': product.name,
                    'length': float(product.length),
                    'width': float(product.width),
                    'height': float(product.height),
                    'weight': float(product.weight),
                    'quantity': order_item.quantity
                })
        except Order.DoesNotExist:
            return Response(
                {"error": f"Order with ID {order_id} not found."},
                status=status.HTTP_404_NOT_FOUND
            )

    # Invoke algorithm from services
    recommended_box = recommend_box_for_order(order)

    if not recommended_box:
        return Response(
            {
                "message": "No suitable box found for this order.",
                "items": visualizer_items
            },
            status=status.HTTP_200_OK
        )

    box_serializer = BoxSerializer(recommended_box)
    return Response(
        {
            "recommended_box": box_serializer.data,
            "items": getattr(recommended_box, 'packed_items', visualizer_items),
            "message": "Box recommendation found successfully."
        },
        status=status.HTTP_200_OK
    )


def simulator_view(request):
    """
    Renders an interactive HTML simulator page for testing the box recommendation endpoint.
    """
    return render(request, 'recommend_box_simulator.html')
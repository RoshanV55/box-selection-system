from rest_framework import serializers
from box_app.models import Product, Box, Order, OrderItem


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for the Product model exposing all dimensional attributes.
    """
    volume = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'length',
            'width',
            'height',
            'weight',
            'volume'
        ]


class BoxSerializer(serializers.ModelSerializer):
    """
    Serializer for the Box model exposing capacity metrics,
    calculated volume, and cost formatted in Indian Rupees (₹).
    """
    volume = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    cost = serializers.SerializerMethodField()

    class Meta:
        model = Box
        fields = [
            'id',
            'name',
            'length',
            'width',
            'height',
            'max_weight',
            'cost',
            'volume'
        ]

    def get_cost(self, obj) -> str:
        """Returns cost formatted with the Indian Rupee symbol (₹)."""
        return f"₹{obj.cost}"


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer for OrderItem, supporting write operations via product ID
    and detailed nested product representations on read operations.
    """
    product = ProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_id', 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order including nested items and calculated total metrics.
    """
    items = OrderItemSerializer(many=True, read_only=True)
    total_weight = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    total_volume = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id',
            'created_at',
            'items',
            'total_weight',
            'total_volume'
        ]


class RawOrderItemInputSerializer(serializers.Serializer):
    """
    Helper serializer for validating raw product item inputs
    when requesting box recommendations without creating an Order object first.
    """
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)


class BoxRecommendationRequestSerializer(serializers.Serializer):
    """
    Flexible request serializer accepting either an existing order_id
    OR a list of raw product items with quantities.
    """
    order_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1
    )
    items = RawOrderItemInputSerializer(
        many=True,
        required=False
    )

    def validate(self, attrs):
        order_id = attrs.get('order_id')
        items = attrs.get('items')

        # Require exactly one approach: order_id OR raw items
        if not order_id and not items:
            raise serializers.ValidationError(
                "Must provide either 'order_id' or 'items'."
            )
        if order_id and items:
            raise serializers.ValidationError(
                "Provide either 'order_id' or 'items', not both."
            )

        # Validate that the order exists if order_id is given
        if order_id:
            if not Order.objects.filter(id=order_id).exists():
                raise serializers.ValidationError({
                    'order_id': f"Order with ID {order_id} does not exist."
                })

        # Validate product_ids if raw items are given
        if items:
            product_ids = [item['product_id'] for item in items]
            existing_products = set(
                Product.objects.filter(id__in=product_ids).values_list('id', flat=True)
            )
            missing_ids = set(product_ids) - existing_products
            if missing_ids:
                raise serializers.ValidationError({
                    'items': f"Products with IDs {list(missing_ids)} do not exist."
                })

        return attrs
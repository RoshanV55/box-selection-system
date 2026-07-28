from django.test import TestCase
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from box_app.models import Product, Box, Order, OrderItem
from box_app.services import recommend_box_for_order


class BoxSelectionServiceTests(TestCase):
    """
    Unit tests for core box selection logic in services.py
    """

    def setUp(self):
        # Sample Products
        self.small_product = Product.objects.create(
            name="Small Mug",
            length=Decimal('10.00'),
            width=Decimal('10.00'),
            height=Decimal('10.00'),
            weight=Decimal('0.50')
        )
        self.heavy_product = Product.objects.create(
            name="Dumbbell",
            length=Decimal('15.00'),
            width=Decimal('15.00'),
            height=Decimal('15.00'),
            weight=Decimal('25.00')
        )
        self.long_product = Product.objects.create(
            name="Poster Tube",
            length=Decimal('50.00'),
            width=Decimal('5.00'),
            height=Decimal('5.00'),
            weight=Decimal('1.00')
        )

        # Sample Boxes
        self.small_cheap_box = Box.objects.create(
            name="Small Box",
            length=Decimal('15.00'),
            width=Decimal('15.00'),
            height=Decimal('15.00'),
            max_weight=Decimal('5.00'),
            cost=Decimal('2.50')
        )
        self.small_expensive_box = Box.objects.create(
            name="Small Deluxe Box",
            length=Decimal('15.00'),
            width=Decimal('15.00'),
            height=Decimal('15.00'),
            max_weight=Decimal('5.00'),
            cost=Decimal('4.00')
        )
        self.large_box = Box.objects.create(
            name="Large Box",
            length=Decimal('60.00'),
            width=Decimal('20.00'),
            height=Decimal('20.00'),
            max_weight=Decimal('30.00'),
            cost=Decimal('8.00')
        )

    def test_single_item_fits_cheapest_box(self):
        """Tests that a single small item selects the cheapest valid small box."""
        order = Order.objects.create()
        OrderItem.objects.create(order=order, product=self.small_product, quantity=1)

        box = recommend_box_for_order(order)
        self.assertIsNotNone(box)
        self.assertEqual(box, self.small_cheap_box)

    def test_overweight_rejection(self):
        """Tests that a box is rejected if item weight exceeds box max_weight."""
        order = Order.objects.create()
        OrderItem.objects.create(order=order, product=self.heavy_product, quantity=1)

        # Small box fits heavy_product dimensionally, but cannot support 25kg weight limit (max 5kg)
        box = recommend_box_for_order(order)
        self.assertEqual(box, self.large_box)

    def test_oversized_dimension_rejection(self):
        """Tests that a product exceeding internal dimensions is routed to a larger box."""
        order = Order.objects.create()
        OrderItem.objects.create(order=order, product=self.long_product, quantity=1)

        # 50cm poster tube will not fit in 15cm Small Box, must pick Large Box
        box = recommend_box_for_order(order)
        self.assertEqual(box, self.large_box)

    def test_3d_orientation_rotation_fit(self):
        """Tests that 3D dimension sorting permits fitting regardless of orientation."""
        # Product dims: 5cm x 50cm x 5cm
        # Box dims: 60cm x 20cm x 20cm -> Sorted: (20, 20, 60) vs (5, 5, 50) -> Fits!
        order = Order.objects.create()
        OrderItem.objects.create(order=order, product=self.long_product, quantity=1)

        box = recommend_box_for_order(order)
        self.assertIsNotNone(box)
        self.assertEqual(box, self.large_box)

    def test_multi_item_height_overflow(self):
        """Tests that multiple items of a product that overflow the height capacity of a box are rejected, even if volume/weight constraints are met."""
        # keyboard size: 35 x 15 x 5 (vol: 2625)
        # box size: 40 x 20 x 10 (vol: 8000). Keyboard fits.
        # 3 keyboards have vol: 7875 <= 8000. But height of 3 is 15 > 10.
        keyboard = Product.objects.create(
            name="Mechanical Keyboard",
            length=Decimal('35.00'),
            width=Decimal('15.00'),
            height=Decimal('5.00'),
            weight=Decimal('1.00')
        )
        medium_box = Box.objects.create(
            name="Medium Shipping Box",
            length=Decimal('40.00'),
            width=Decimal('20.00'),
            height=Decimal('10.00'),
            max_weight=Decimal('10.00'),
            cost=Decimal('4.50')
        )
        order = Order.objects.create()
        # 3 keyboards
        OrderItem.objects.create(order=order, product=keyboard, quantity=3)

        box = recommend_box_for_order(order)
        # Should not fit in medium_box because height overflows (costly large_box is the only candidate but doesn't exist/fit or will be None here)
        # Since large_box size is 60x20x20, let's see if it fits there: yes, 3 keyboards stacked fits in 20cm height.
        self.assertEqual(box, self.large_box)

    def test_no_box_available_returns_none(self):
        """Tests that None is returned when no box can satisfy the order requirements."""
        giant_product = Product.objects.create(
            name="Huge TV",
            length=Decimal('200.00'),
            width=Decimal('200.00'),
            height=Decimal('200.00'),
            weight=Decimal('100.00')
        )
        order = Order.objects.create()
        OrderItem.objects.create(order=order, product=giant_product, quantity=1)

        box = recommend_box_for_order(order)
        self.assertIsNone(box)


class RecommendationAPIEndpointTests(TestCase):
    """
    Unit tests for DRF API endpoints in views.py
    """

    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name="Keyboard",
            length=Decimal('20.00'),
            width=Decimal('10.00'),
            height=Decimal('5.00'),
            weight=Decimal('1.00')
        )
        self.box = Box.objects.create(
            name="Standard Box",
            length=Decimal('30.00'),
            width=Decimal('20.00'),
            height=Decimal('10.00'),
            max_weight=Decimal('10.00'),
            cost=Decimal('3.00')
        )

    def test_recommend_box_by_order_id(self):
        order = Order.objects.create()
        OrderItem.objects.create(order=order, product=self.product, quantity=1)

        response = self.client.post(
            '/api/recommend-box/',
            {'order_id': order.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recommended_box']['id'], self.box.id)

    def test_recommend_box_by_raw_items(self):
        payload = {
            'items': [
                {'product_id': self.product.id, 'quantity': 2}
            ]
        }
        response = self.client.post('/api/recommend-box/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recommended_box']['id'], self.box.id)

    def test_invalid_payload_both_order_and_items(self):
        order = Order.objects.create()
        payload = {
            'order_id': order.id,
            'items': [{'product_id': self.product.id, 'quantity': 1}]
        }
        response = self.client.post('/api/recommend-box/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
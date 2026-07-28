from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator

# Common validator to ensure physical measurements are strictly positive (> 0)
POSITIVE_MIN_VALUE_VALIDATOR = [MinValueValidator(Decimal('0.01'))]


class Product(models.Model):
    """
    Represents an individual item that can be ordered.
    Dimensions are in centimeters (cm), weight in kilograms (kg).
    """
    name = models.CharField(max_length=255)
    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Length in cm"
    )
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Width in cm"
    )
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Height in cm"
    )
    weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Weight in kg"
    )

    @property
    def volume(self) -> Decimal:
        """Calculates volume in cubic centimeters (cm³)."""
        return self.length * self.width * self.height

    def __str__(self):
        return f"{self.name} ({self.length}x{self.width}x{self.height} cm)"


class Box(models.Model):
    """
    Represents a shipping container available in the warehouse.
    Internal dimensions in cm, max_weight capacity in kg, cost in currency units.
    """
    name = models.CharField(max_length=255)
    length = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Internal length in cm"
    )
    width = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Internal width in cm"
    )
    height = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Internal height in cm"
    )
    max_weight = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=POSITIVE_MIN_VALUE_VALIDATOR,
        help_text="Maximum weight capacity in kg"
    )
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Cost of the box"
    )

    @property
    def volume(self) -> Decimal:
        """Calculates internal volume in cubic centimeters (cm³)."""
        return self.length * self.width * self.height

    def __str__(self):
        return f"{self.name} - ₹{self.cost} (Max Wt: {self.max_weight}kg)"

class Order(models.Model):
    """
    Represents a customer order containing one or more products via OrderItem.
    """
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_weight(self) -> Decimal:
        """Calculates total cumulative weight across all order items."""
        items = self.items.select_related('product')
        return sum((item.product.weight * item.quantity for item in items), Decimal('0.00'))

    @property
    def total_volume(self) -> Decimal:
        """Calculates total cumulative volume across all order items."""
        items = self.items.select_related('product')
        return sum((item.product.volume * item.quantity for item in items), Decimal('0.00'))

    def __str__(self):
        return f"Order #{self.id} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class OrderItem(models.Model):
    """
    Junction table representing products within a specific order and their quantities.
    """
    order = models.ForeignKey(
        Order,
        related_name='items',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Order #{self.order.id})"
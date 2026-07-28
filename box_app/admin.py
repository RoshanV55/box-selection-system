from django.contrib import admin
from .models import Product, Box, Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """
    Allows managing OrderItems directly inline from the Order change page.
    """
    model = OrderItem
    extra = 1  # Number of extra empty forms to display


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'length', 'width', 'height', 'weight', 'volume')
    search_fields = ('name',)


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = ('name', 'length', 'width', 'height', 'max_weight', 'cost', 'volume')
    search_fields = ('name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'total_weight', 'total_volume')
    list_filter = ('created_at',)
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity')
    list_filter = ('order', 'product')
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from box_app.views import ProductViewSet, BoxViewSet, OrderViewSet, recommend_box_view , simulator_view

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'boxes', BoxViewSet, basename='box')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path('recommend-box/', recommend_box_view, name='recommend-box'),
    path('simulator/', simulator_view, name='simulator'),
]
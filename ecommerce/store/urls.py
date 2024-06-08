from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('add/', views.add_product, name='add_product'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<str:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<str:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),

]
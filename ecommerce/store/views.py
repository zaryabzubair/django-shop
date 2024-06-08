from django.shortcuts import render, redirect
from django.conf import settings
import pyrebase
from ecommerce.firebase_config import FIREBASE_CONFIG
from django.contrib import messages
import stripe
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import CheckoutForm
import logging
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore
from datetime import datetime


firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
db = firebase.database()
storage = firebase.storage()

stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

def product_list(request):
    products = db.child("products").get().val()
    return render(request, 'shop/product_list.html', {'products': products})


def add_product(request):
    if request.method == "POST":
        name = request.POST['name']
        description = request.POST['description']
        price = request.POST['price']
        stock = request.POST['stock']
        image = request.FILES['images']

        # Save images to Firebase Storage
        image_path = f"images/{image.name}"
        storage.child(image_path).put(image)
        image_url = storage.child(image_path).get_url(None)

        data = {
            "name": name,
            "description": description,
            "price": float(price),
            "stock": int(stock),
            "image_url": image_url
        }

        db.child("products").push(data)
        return redirect('product_list')
    return render(request, 'shop/add_product.html')


def add_to_cart(request, product_id):
    product = db.child("products").child(product_id).get().val()
    if not product:
        messages.error(request, "Product not found.")
        return redirect('product_list')

    cart = request.session.get('cart', {})
    if product_id in cart:
        cart[product_id]['quantity'] += 1
        logger.info(f"Cart: {cart}")
        logger.error(f"Cart Error: {cart}")
    else:
        cart[product_id] = {
            'name': product['name'],
            'price': product['price'],
            'quantity': 1,
            'image_url': product['image_url']
        }
    request.session['cart'] = cart
    messages.success(request, "Product added to cart.")
    return redirect('view_cart')


def view_cart(request):
    cart = request.session.get('cart', {})
    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
    return render(request, 'shop/cart.html', {'cart': cart, 'total_amount': total_amount})


def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    if product_id in cart:
        del cart[product_id]
        request.session['cart'] = cart
        messages.success(request, "Product removed from cart.")
    return redirect('view_cart')


# def checkout(request):
#     cart = request.session.get('cart', {})
#     if not cart:
#         messages.error(request, "Your cart is empty.")
#         return redirect('product_list')
#
#     total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
#
#     if request.method == 'POST':
#         token = request.POST.get('stripeToken')
#         try:
#             charge = stripe.Charge.create(
#                 amount=int(total_amount * 100),
#                 currency='usd',
#                 description='Example charge',
#                 source=token,
#             )
#             request.session['cart'] = {}
#             messages.success(request, "Payment successful! Your order has been placed.")
#             return redirect('product_list')
#         except stripe.error.StripeError as e:
#             messages.error(request, f"Payment failed: {e}")
#             return redirect('checkout')
#
#     return render(request, 'shop/checkout.html', {
#         'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
#         'total_amount': total_amount,
#     })

# def checkout(request):
#     cart = request.session.get('cart', {})
#     if not cart:
#         messages.error(request, "Your cart is empty.")
#         return redirect('product_list')
#
#     total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
#
#     if request.method == 'POST':
#         form = CheckoutForm(request.POST)
#         if form.is_valid():
#             token = form.cleaned_data['stripeToken']
#             try:
#                 charge = stripe.Charge.create(
#                     amount=int(total_amount * 100),
#                     currency='usd',
#                     description='Example charge',
#                     source=token,
#                 )
#                 checkout_data = {
#                     'name': form.cleaned_data['name'],
#                     'email': form.cleaned_data['email'],
#                     'phone_number': form.cleaned_data['phone_number'],
#                     'address': form.cleaned_data['address'],
#                     'created_at': datetime.now()
#                 }
#                 logger.info("Checkout data to be saved: %s", checkout_data)
#                 db.collection('checkouts').add(checkout_data)
#                 request.session['cart'] = {}
#                 messages.success(request, "Payment successful! Your order has been placed.")
#                 return redirect('product_list')
#             except stripe.error.StripeError as e:
#                 logger.error("Error saving data to Firebase: %s", e)
#                 messages.error(request, f"Payment failed: {e}")
#                 return redirect('checkout')
#     else:
#         form = CheckoutForm()
#
#     return render(request, 'shop/checkout.html', {
#         'form': form,
#         'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
#         'total_amount': total_amount,
#     })

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty.")
        return redirect('product_list')

    total_amount = sum(item['price'] * item['quantity'] for item in cart.values())

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Extract user data from the form
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            address = form.cleaned_data['address']

            # Save checkout data to Firebase
            checkout_data = {
                'name': name,
                'email': email,
                'phone_number': phone_number,
                'address': address,
                'total_amount': total_amount,
                'cart_items': []
            }
            for product_id, item in cart.items():
                product_data = {
                    'product_id': product_id,
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price': item['price']
                }
                checkout_data['cart_items'].append(product_data)

            # Add checkout data to Firebase
            db.child('checkouts').push(checkout_data)

            # Clear the cart
            request.session['cart'] = {}

            messages.success(request, "Payment successful! Your order has been placed.")
            return redirect('product_list')
    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {
        'form': form,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'total_amount': total_amount,
    })


def checkout_success(request):
    return render(request, 'shop/checkout_success.html')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    endpoint_secret = 'your-webhook-secret'

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        return JsonResponse({'status': 'invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        return JsonResponse({'status': 'invalid signature'}, status=400)

    if event['type'] == 'charge.succeeded':
        charge = event['data']['object']
    return JsonResponse({'status': 'success'}, status=200)
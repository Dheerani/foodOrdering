from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model

from .models import Product, Order, OrderItem
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from products.models import CustomUser

User = get_user_model()


@login_required(login_url='login')
def confirm_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if order.payment_method == 'online' and order.payment_status == 'pending':
        # Mark as paid
        order.payment_status = 'paid'
        order.save()

        # Send email after payment confirmation
        full_message = f"Payment confirmed for Order #{order.id}\n"
        full_message += f"Name: {order.name}\nEmail: {order.email}\nAddress: {order.address}\nPayment Method: {order.payment_method}\n\nItems:\n"

        for item in order.items.all():
            subtotal = item.price * item.quantity
            full_message += f"{item.product} x {item.quantity} = Rs. {subtotal}\n"

        send_mail(
            subject=f"Order #{order.id} Confirmed",
            message=full_message,
            from_email='your_email@gmail.com',
            recipient_list=['your_email@gmail.com'],
        )

        messages.success(request, f"Payment for Order #{order.id} confirmed successfully!")
    else:
        messages.warning(request, "This order is already paid or not an online payment.")

    return redirect('order_detail', order_id=order.id)


# ==================== PAYMENT CONFIRMATION ====================
@login_required(login_url='login')
def confirm_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.payment_method == 'online':
        order.payment_status = 'paid'
        order.save()
        messages.success(request, f"Payment for Order #{order.id} confirmed!")
    return redirect('order_detail', order_id=order.id)

# ==================== LOGIN, LOGOUT, REGISTER ====================
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        phone = request.POST.get("phone")
        password = request.POST.get("password")
        
        if CustomUser.objects.filter(phone_number=phone).exists():
            return render(request, "register.html", {"error": "Phone already exists"})
        if CustomUser.objects.filter(email=email).exists():
            return render(request, "register.html", {"error": "Email already exists"})
        
        user = CustomUser(username=username, email=email, phone_number=phone)
        user.set_password(password)
        user.save()
        return redirect("login")
    
    return render(request, "register.html")

def login_view(request):
    if request.method == "POST":
        identifier = request.POST.get("identifier")  # email or phone
        password = request.POST.get("password")

        try:
            user_obj = CustomUser.objects.get(email=identifier)
        except CustomUser.DoesNotExist:
            try:
                user_obj = CustomUser.objects.get(phone_number=identifier)
            except CustomUser.DoesNotExist:
                user_obj = None

        if user_obj and user_obj.check_password(password):
            login(request, user_obj)
            return redirect("home")
        else:
            return render(request, "login.html", {"error": "Invalid email/phone or password"})
    
    return render(request, "login.html")

# ==================== PRODUCTS ====================
def home_view(request):
    products = Product.objects.all()
    
    if request.method == "POST" and request.POST.get('email') and request.POST.get('message'):
        email = request.POST.get('email')
        message = request.POST.get('message')
        full_message = f"Email: {email}\nMessage: {message}"

        send_mail(
            subject="New Contact Message",
            message=full_message,
            from_email=email,
            recipient_list=['your_email@gmail.com'],
        )
        messages.success(request, "Message sent successfully!")
        return redirect('home')

    return render(request, 'home.html', {'products': products})

def product_list(request):
    products = Product.objects.all()
    return render(request, 'product_list.html', {'products': products})

def product_detail(request, slug):
    product = Product.objects.get(product_slug=slug)

    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        product.rating = rating
        product.save()

    return render(request, 'product_detail.html', {'product': product})

# ==================== CART ====================
def cart_detail(request):
    cart = request.session.get('cart', {})

    total = 0
    for item in cart.values():
        item['subtotal'] = item['price'] * item['quantity']
        total += item['subtotal']

    # Default payment info for template
    context = {
        'cart': cart,
        'total': total,
        'payment_method': 'cod',
        'payment_status': 'pending',
    }
    return render(request, 'cart.html', context)

def add_to_cart(request, slug):
    try:
        product = Product.objects.get(product_slug=slug)
    except Product.DoesNotExist:
        messages.error(request, "Product not found.")
        return redirect('cart_detail')

    cart = request.session.get('cart', {})
    key = str(product.uid)

    if key in cart:
        cart[key]['quantity'] += 1
    else:
        cart[key] = {
            'name': product.product_name,
            'price': float(product.product_price),
            'quantity': 1
        }

    request.session['cart'] = cart
    messages.success(request, "Cart updated successfully!")
    return redirect('cart_detail')

def cart_update(request, product_id, action):
    cart = request.session.get('cart', {})
    product_id = str(product_id)

    if product_id in cart:
        if action == 'increase':
            cart[product_id]['quantity'] += 1
        elif action == 'decrease':
            cart[product_id]['quantity'] -= 1
            if cart[product_id]['quantity'] <= 0:
                del cart[product_id]

    request.session['cart'] = cart
    return redirect('cart_detail')

def remove_from_cart(request, product_id):
    cart = request.session.get('cart', {})
    product_id = str(product_id)
    if product_id in cart:
        del cart[product_id]
    request.session['cart'] = cart
    return redirect('cart_detail')

# ==================== PLACE ORDER ====================
@login_required(login_url='login')
def place_order(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        address = request.POST.get('address')
        payment_method = request.POST.get('payment_method')
        cart = request.session.get('cart', {})

        if not cart:
            messages.error(request, "Cart is empty!")
            return redirect('cart_detail')

        # Set payment status
        payment_status = 'pending' if payment_method == 'online' else 'paid'

        # Create order
        order = Order.objects.create(
            name=name,
            email=email,
            address=address,
            payment_method=payment_method,
            payment_status=payment_status
        )

        # Create order items
        for item_id, item in cart.items():
            OrderItem.objects.create(
                order=order,
                product=item['name'],
                price=item['price'],
                quantity=item['quantity']
            )

        # Only send email immediately if payment is COD
        if payment_method == 'cod':
            full_message = f"New order by {name}\nEmail: {email}\nAddress: {address}\nPayment: {payment_method}\nItems:\n"
            for item_id, item in cart.items():
                subtotal = item['price'] * item['quantity']
                full_message += f"{item['name']} x {item['quantity']} = Rs. {subtotal}\n"

            send_mail(
                subject=f"New Order #{order.id}",
                message=full_message,
                from_email='your_email@gmail.com',
                recipient_list=['your_email@gmail.com'],
            )

        # Clear cart
        request.session['cart'] = {}

        # Show message to user
        if payment_method == 'online':
            messages.success(request, f"Order #{order.id} created. Please complete your online payment to confirm it!")
        else:
            messages.success(request, "Order placed successfully!")

        return redirect('order_detail', order_id=order.id)

    return redirect('cart_detail')

# ==================== ORDER HISTORY & DETAILS ====================
def order_list(request):
    orders = Order.objects.all().order_by('-id')
    return render(request, 'order_history.html', {'orders': orders})

def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = OrderItem.objects.filter(order=order)
    return render(request, 'order_detail.html', {
        'order': order,
        'items': items
    })
    
    
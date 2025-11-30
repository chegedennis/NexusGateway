from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from billing.models import Transaction
from billing.utils import trigger_stk_push, get_mac_address
import threading

# Configuration for Pricing Plans
PRICING_PLANS = {
    "1hour": {"price": 10, "label": "1 Hour Access"},
    "24hours": {"price": 50, "label": "24 Hours Access"},
    "1week": {"price": 250, "label": "7 Days Access"},
}

def captive_portal(request: HttpRequest) -> HttpResponse:
    """Renders the main landing page for the Captive Portal."""
    return render(request, "portal/login.html")

def initiate_payment(request: HttpRequest) -> HttpResponse:
    """
    Handles the form submission, creates a pending transaction, 
    and spawns a background thread to trigger M-Pesa.
    """
    if request.method != "POST":
        return redirect("home")

    # 1. Extract Data
    phone_raw = request.POST.get("phone", "").replace(" ", "")
    plan_id = request.POST.get("plan", "1hour")
    
    # 2. Validate Plan
    plan = PRICING_PLANS.get(plan_id, PRICING_PLANS["1hour"])
    amount = plan["price"]

    # 3. Format Phone (254...)
    if phone_raw.startswith("0"): 
        phone = "254" + phone_raw[1:]
    elif phone_raw.startswith("+"): 
        phone = phone_raw[1:]
    else:
        phone = phone_raw

    # 4. Network Reconnaissance
    client_ip = request.META.get("REMOTE_ADDR")
    client_mac = get_mac_address(client_ip) or "00:00:00:00:00:00"

    # 5. Create Transaction Record
    transaction = Transaction.objects.create(
        phone_number=phone,
        amount=amount,
        ip_address=client_ip,
        mac_address=client_mac
    )

    # 6. Async Execution (Prevent UI Blocking)
    thread = threading.Thread(
        target=_background_stk_push,
        args=(phone, amount, transaction)
    )
    thread.start()

    # Note: We send 'phone' to the template so the JS knows who to poll for
    return render(request, "portal/processing.html", {"phone": phone})

def _background_stk_push(phone, amount, transaction):
    """Internal helper to run API calls in a separate thread."""
    try:
        response = trigger_stk_push(phone, int(amount), transaction.id)
        print(f"M-Pesa Response: {response}")
        # Link the CheckoutRequestID for callback matching
        if "CheckoutRequestID" in response:
            transaction.checkout_request_id = response["CheckoutRequestID"]
            transaction.save()
    except Exception as e:
        print(f"Background Thread Error: {e}")

# --- MISSING FUNCTIONS ADDED BELOW ---

def check_status(request: HttpRequest, phone: str) -> JsonResponse:
    """
    AJAX Endpoint: Polls the database to check if a transaction is COMPLETED.
    Used by the 'processing.html' page to auto-redirect.
    """
    # Look for the most recent transaction for this phone number
    transaction = Transaction.objects.filter(phone_number=phone).order_by("-created_at").first()

    if transaction:
        return JsonResponse({"status": transaction.status})
    else:
        return JsonResponse({"status": "PENDING"})

def success_page(request: HttpRequest) -> HttpResponse:
    """Renders the final success page indicating internet access is active."""
    return render(request, "portal/success.html")

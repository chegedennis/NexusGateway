import json
import logging
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
from .models import Transaction
from .utils import allow_device

# Configure logging to track payments in django.log
logger = logging.getLogger(__name__)

@csrf_exempt
def mpesa_callback(request: HttpRequest) -> JsonResponse:
    """
    Endpoint that receives the asynchronous callback from Safaricom's Daraja API.
    
    Process:
    1. Parses the JSON payload from M-Pesa.
    2. Matches the 'CheckoutRequestID' to a pending local Transaction.
    3. If successful (ResultCode 0), activates the user's internet access via iptables.
    4. Updates the database record.
    """
    
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        # 1. Parse Payload
        payload = json.loads(request.body)
        body = payload.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        # 2. Extract Critical Data
        merchant_request_id = stk_callback.get('MerchantRequestID')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        result_code = stk_callback.get('ResultCode')
        result_desc = stk_callback.get('ResultDesc')

        logger.info(f"M-Pesa Callback received. ID: {checkout_request_id}, Code: {result_code}")

        # 3. Find Transaction
        try:
            transaction = Transaction.objects.get(checkout_request_id=checkout_request_id)
        except Transaction.DoesNotExist:
            logger.error(f"Transaction not found for ID: {checkout_request_id}")
            return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted but not found"})

        # 4. Process Status
        if result_code == 0:
            # --- SUCCESS CASE ---
            transaction.status = 'COMPLETED'
            
            # Extract M-Pesa Receipt Number (e.g., QDH...)
            meta_data = stk_callback.get('CallbackMetadata', {}).get('Item', [])
            for item in meta_data:
                if item.get('Name') == 'MpesaReceiptNumber':
                    transaction.mpesa_receipt = item.get('Value')
            
            transaction.save()
            
            # --- FIREWALL ACTIVATION ---
            # Retrieve network details saved during initiation
            user_ip = transaction.ip_address
            user_mac = transaction.mac_address or "00:00:00:00:00:00"
            
            if user_ip:
                success = allow_device(user_ip, user_mac)
                if success:
                    logger.info(f"✅ Firewall OPENED for {transaction.phone_number} ({user_ip})")
                else:
                    logger.critical(f"❌ Firewall FAILED to open for {transaction.phone_number}")
            else:
                logger.warning(f"⚠️ Cannot unlock: No IP recorded for {transaction.phone_number}")

        else:
            # --- FAILURE/CANCELLED CASE ---
            logger.info(f"Payment failed/cancelled for {transaction.phone_number}: {result_desc}")
            transaction.status = 'FAILED'
            transaction.save()

    except json.JSONDecodeError:
        logger.error("Failed to decode JSON from M-Pesa")
    except Exception as e:
        logger.error(f"Critical error in callback: {str(e)}")

    # Always return success to Safaricom so they stop retrying the callback
    return JsonResponse({"ResultCode": 0, "ResultDesc": "Accepted"})

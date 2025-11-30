from django.db import models

class Transaction(models.Model):
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    mpesa_receipt = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, default='PENDING')
    checkout_request_id = models.CharField(max_length=100, default='')
    
    # Network Identity
    ip_address = models.CharField(max_length=20, blank=True, null=True)
    mac_address = models.CharField(max_length=20, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.phone_number} - {self.amount}"

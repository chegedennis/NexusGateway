from django.contrib import admin
from django.contrib import messages
from .models import Transaction
from .utils import allow_device, revoke_device

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'amount', 'status', 'ip_address', 'mac_address', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('phone_number', 'mpesa_receipt')
    ordering = ('-created_at',)
    actions = ['action_allow', 'action_revoke']

    # --- ACTION 1: MANUAL ALLOW (UNLOCK) ---
    @admin.action(description='🔓 Allow Internet (Unlock)')
    def action_allow(self, request, queryset):
        count = 0
        for trans in queryset:
            if trans.ip_address:
                # Use MAC if available, else fallback to dummy
                mac = trans.mac_address or "00:00:00:00:00:00"
                
                if allow_device(trans.ip_address, mac):
                    trans.status = 'COMPLETED'
                    trans.save()
                    count += 1
        
        self.message_user(request, f"Successfully unlocked {count} devices.", messages.SUCCESS)

    # --- ACTION 2: MANUAL REVOKE (KICK) ---
    @admin.action(description='🔒 Revoke Internet (Block)')
    def action_revoke(self, request, queryset):
        count = 0
        for trans in queryset:
            if trans.ip_address:
                mac = trans.mac_address or "00:00:00:00:00:00"

                if revoke_device(trans.ip_address, mac):
                    trans.status = 'REVOKED'
                    trans.save()
                    count += 1
                    
        self.message_user(request, f"Successfully blocked {count} devices.", messages.WARNING)

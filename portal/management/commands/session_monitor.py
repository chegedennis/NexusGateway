import time
import signal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.models import Transaction
from billing.utils import revoke_device

class Command(BaseCommand):
    help = 'Daemon process that monitors active sessions and revokes access upon expiry.'
    
    # Control flag for graceful shutdowns
    is_running = True

    def handle(self, *args, **options):
        # Register signal handlers for SystemD/Kill commands
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        self.stdout.write(self.style.SUCCESS('Starting Session Monitor Daemon...'))
        
        while self.is_running:
            self.check_expiries()
            
            # Smart Sleep: Check for shutdown signal every second
            for _ in range(60):
                if not self.is_running: break
                time.sleep(1)
        
        self.stdout.write(self.style.SUCCESS('Session Monitor stopped gracefully.'))

    def check_expiries(self):
        """
        Queries the database for expired sessions and executes firewall revocation.
        """
        active_sessions = Transaction.objects.filter(status='COMPLETED')
        
        for session in active_sessions:
            # Determine duration based on amount paid
            limit = self.get_duration(session.amount)
            expiry_time = session.created_at + limit
            
            if timezone.now() > expiry_time:
                self.stdout.write(f"Session Expired: {session.phone_number} (IP: {session.ip_address})")
                
                # Execute Firewall Command
                if session.ip_address:
                    revoke_device(session.ip_address, session.mac_address)
                
                # Update DB
                session.status = 'EXPIRED'
                session.save()

    def get_duration(self, amount: float) -> timedelta:
        """Map payment amount to time duration."""
        if amount >= 250: return timedelta(days=7)
        if amount >= 50: return timedelta(hours=24)
        if amount >= 10: return timedelta(hours=1)
        return timedelta(minutes=5) # Default/Test

    def shutdown(self, signum, frame):
        """Signal handler for graceful shutdown."""
        self.stdout.write(self.style.WARNING('Received shutdown signal...'))
        self.is_running = False

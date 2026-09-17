from django.core.management.base import BaseCommand
from django.utils import timezone

from payments.models import Payment
from payments.services import fail_payment


class Command(BaseCommand):

    help = (
        "Expire pending payments and release reserved stock."
    )

    def handle(self, *args, **options):

        now = timezone.now()

        payment_ids = list(
            Payment.objects
            .filter(
                status=Payment.Status.PENDING,
                expires_at__isnull=False,
                expires_at__lte=now,
            )
            .values_list(
                "id",
                flat=True,
            )
        )

        expired_count = 0

        for payment_id in payment_ids:

            try:

                payment = Payment.objects.get(
                    pk=payment_id
                )

            except Payment.DoesNotExist:

                continue

            # ------------------------------------------------
            # fail_payment() handles:
            #
            # Payment → FAILED
            # Order → FAILED
            # Stock → RELEASED
            #
            # and does all of this safely inside a transaction.
            # ------------------------------------------------

            if fail_payment(payment):

                expired_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{expired_count} expired payment(s) "
                f"marked as FAILED."
            )
        )
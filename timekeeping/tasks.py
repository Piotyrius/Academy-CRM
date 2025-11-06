from celery import shared_task
from django.db.models import Sum
from .models import WorkLog


@shared_task
def backfill_worklogs():
    # Placeholder for future backfill logic
    return WorkLog.objects.count()



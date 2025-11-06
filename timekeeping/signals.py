from datetime import timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import make_naive
from catalog.models import Session
from .models import WorkLog, WorkLogSource


@receiver(post_save, sender=Session)
def create_worklog_on_session_update(sender, instance: Session, created, **kwargs):
    """Minimal heuristic: when a session exists and has not been cancelled, ensure a WorkLog exists.

    In Phase 1 we don't have an explicit "held" flag. As a pragmatic approach,
    we create or sync a WorkLog anytime a Session is saved where a lecturer is assigned
    and the session is not cancelled.
    """
    if instance.is_cancelled or not instance.cohort.lecturer:
        return
    start_at = instance.start_at
    end_at = instance.end_at
    minutes = int((end_at - start_at).total_seconds() // 60)
    # one worklog per session+lecturer
    WorkLog.objects.update_or_create(
        session=instance,
        lecturer=instance.cohort.lecturer,
        defaults={
            'start_at': start_at,
            'end_at': end_at,
            'minutes': minutes,
            'source': WorkLogSource.SESSION,
        },
    )



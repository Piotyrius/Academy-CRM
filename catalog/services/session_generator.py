"""
Service for generating recurring sessions with holiday exclusion.
"""
from datetime import datetime, timedelta
from dateutil import rrule
from dateutil.relativedelta import relativedelta
import holidays
from django.utils import timezone
from catalog.models import Cohort, Session


class SessionGenerator:
    """Generate recurring sessions for a cohort."""
    
    def __init__(self, cohort: Cohort):
        self.cohort = cohort
    
    def generate_sessions(
        self,
        pattern: str,
        start_time: str,
        end_time: str,
        exclude_holidays: bool = True,
        manual_exclusions: list = None
    ):
        """
        Generate sessions based on recurrence pattern.
        
        Args:
            pattern: Weekly pattern like 'TUE,THU' (comma-separated weekday names)
            start_time: Start time like '19:00'
            end_time: End time like '21:00'
            exclude_holidays: Whether to exclude holidays
            manual_exclusions: List of dates to exclude (YYYY-MM-DD format)
        
        Returns:
            List of created Session objects
        """
        # Parse weekday names
        weekday_map = {
            'MON': rrule.MO,
            'TUE': rrule.TU,
            'WED': rrule.WE,
            'THU': rrule.TH,
            'FRI': rrule.FR,
            'SAT': rrule.SA,
            'SUN': rrule.SU,
        }
        
        weekdays = [weekday_map[day.strip().upper()] for day in pattern.split(',')]
        
        # Parse times
        start_hour, start_min = map(int, start_time.split(':'))
        end_hour, end_min = map(int, end_time.split(':'))
        
        # Get cohort date range
        start_date = self.cohort.start_date
        end_date = self.cohort.end_date
        
        # Create datetime for start
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time().replace(hour=start_hour, minute=start_min))
        )
        
        # Get holidays for Georgia
        excluded_dates = set()
        if exclude_holidays:
            ge_holidays = holidays.Georgia(years=[start_date.year, end_date.year])
            excluded_dates.update(ge_holidays.keys())
        
        # Add manual exclusions
        if manual_exclusions:
            for date_str in manual_exclusions:
                try:
                    excluded_dates.add(datetime.strptime(date_str, '%Y-%m-%d').date())
                except ValueError:
                    continue
        
        # Generate recurrence rule
        sessions = []
        for weekday in weekdays:
            rule = rrule.rrule(
                rrule.WEEKLY,
                byweekday=weekday,
                dtstart=start_datetime,
                until=timezone.make_aware(
                    datetime.combine(end_date, datetime.max.time())
                )
            )
            
            for dt in rule:
                # Check if date is excluded
                if dt.date() in excluded_dates:
                    continue
                
                # Check if session already exists
                if Session.objects.filter(cohort=self.cohort, start_at=dt).exists():
                    continue
                
                # Calculate end time
                duration = timedelta(
                    hours=(end_hour - start_hour),
                    minutes=(end_min - start_min)
                )
                end_datetime = dt + duration
                
                # Create session
                session = Session.objects.create(
                    cohort=self.cohort,
                    start_at=dt,
                    end_at=end_datetime
                )
                sessions.append(session)
        
        return sessions

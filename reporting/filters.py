from rest_framework import serializers


class AnalyticsFilterSerializer(serializers.Serializer):
    """
    Shared filter serializer for reporting analytics endpoints.

    Used to validate and document common query parameters consistently.
    """

    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    program_id = serializers.UUIDField(required=False)
    cohort_id = serializers.UUIDField(required=False)
    student_id = serializers.UUIDField(required=False)
    lecturer_id = serializers.UUIDField(required=False)
    group_by = serializers.ChoiceField(
        choices=[("day", "day"), ("week", "week"), ("month", "month")],
        required=False,
    )



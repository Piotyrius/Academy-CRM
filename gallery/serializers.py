from rest_framework import serializers
from django.urls import reverse
from .models import Work, WorkStatus


class WorkSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    class Meta:
        model = Work
        fields = [
            "id",
            "owner",
            "title",
            "description",
            "media",
            "media_url",
            "status",
            "is_public",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "published_at", "created_at", "updated_at"]

    def get_media_url(self, obj):
        """
        Get download URL for the file from Google Drive.
        Only returns URL if file_object exists (stored in Drive).
        Returns None for legacy records with only local media (no file_object).
        """
        request = self.context.get("request")
        if not request:
            return None

        # Only return URL if file is stored in Google Drive
        if getattr(obj, "file_object_id", None):
            url = reverse("file-download", kwargs={"pk": obj.file_object_id})
            return request.build_absolute_uri(url)

        # Legacy records with only local media (no file_object) return None
        # Frontend should handle None gracefully (show placeholder or error)
        return None



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
        request = self.context.get("request")
        if not request:
            return None

        if getattr(obj, "file_object_id", None):
            url = reverse("file-download", kwargs={"pk": obj.file_object_id})
            return request.build_absolute_uri(url)

        if obj.media:
            return request.build_absolute_uri(obj.media.url)

        return None



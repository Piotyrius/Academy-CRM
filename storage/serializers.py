from rest_framework import serializers

from .models import FileObject


class FileObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileObject
        fields = [
            "id",
            "owner_type",
            "owner_id",
            "original_name",
            "mime_type",
            "size",
            "visibility",
            "is_archived",
            "created_at",
            "deleted_at",
        ]
        read_only_fields = ["id", "created_at", "deleted_at"]









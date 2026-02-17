"""
Serializers for documents app.
"""
from rest_framework import serializers
from django.urls import reverse
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model."""
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_file_url(self, obj):
        """
        Get download URL for the backing file.

        If Cloudinary storage is enabled and a FileObject exists, return the
        Cloudinary URL directly; otherwise fall back to the legacy Django FileField URL.
        """
        # Return Cloudinary URL directly if available
        if getattr(obj, "file_object", None) and obj.file_object.cloudinary_url:
            return obj.file_object.cloudinary_url

        request = self.context.get("request")
        if not request:
            return None

        # Fallback to download endpoint for legacy files
        if getattr(obj, "file_object_id", None):
            url = reverse("file-download", kwargs={"pk": obj.file_object_id})
            return request.build_absolute_uri(url)

        if obj.file:
            return request.build_absolute_uri(obj.file.url)

        return None

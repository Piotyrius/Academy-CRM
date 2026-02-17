"""
Serializers for certificates app.
"""
from rest_framework import serializers
from .models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    """Serializer for Certificate model."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    course_title = serializers.CharField(source='cohort.course.title', read_only=True)
    program_name = serializers.CharField(source='cohort.course.program.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    pdf_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Certificate
        fields = '__all__'
        read_only_fields = ['id', 'serial', 'qr_token', 'issued_at', 'created_at', 'updated_at']
    
    def get_pdf_url(self, obj):
        """Get signed URL for PDF download."""
        if obj.pdf_file:
            from django.conf import settings
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
        return None


class CertificateVerifySerializer(serializers.Serializer):
    """Serializer for certificate verification."""
    student_name = serializers.CharField()
    program_name = serializers.CharField()
    course_title = serializers.CharField()
    cohort_name = serializers.CharField()
    issued_at = serializers.DateTimeField()
    status = serializers.CharField()

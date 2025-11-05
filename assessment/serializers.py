"""
Serializers for assessment app.
"""
from rest_framework import serializers
from .models import Assessment, Submission, Grade


class AssessmentSerializer(serializers.ModelSerializer):
    """Serializer for Assessment model."""
    cohort_name = serializers.CharField(source='cohort.name', read_only=True)
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    
    class Meta:
        model = Assessment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubmissionSerializer(serializers.ModelSerializer):
    """Serializer for Submission model."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)
    
    class Meta:
        model = Submission
        fields = '__all__'
        read_only_fields = ['id', 'submitted_at', 'updated_at']


class GradeSerializer(serializers.ModelSerializer):
    """Serializer for Grade model."""
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assessment_title = serializers.CharField(source='assessment.title', read_only=True)
    graded_by_name = serializers.CharField(source='graded_by.get_full_name', read_only=True)
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = Grade
        fields = '__all__'
        read_only_fields = ['id', 'graded_at', 'updated_at', 'percentage']

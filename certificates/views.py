"""
Views for certificates app.
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import Certificate, CertificateStatus
from .serializers import CertificateSerializer, CertificateVerifySerializer
from .services.certificate_service import CertificateService
from .permissions import IsAdminOrLecturerOwner


class CertificateViewSet(viewsets.ModelViewSet):
    """ViewSet for Certificate model."""
    queryset = Certificate.objects.select_related('student', 'cohort').all()
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'cohort', 'student']
    search_fields = ['serial', 'student__email', 'student__first_name', 'student__last_name']
    ordering_fields = ['issued_at']
    ordering = ['-issued_at']
    
    def get_queryset(self):
        """Filter queryset based on user role."""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Students only see their own certificates
        if user.is_student:
            queryset = queryset.filter(student=user)
        # Lecturers only see certificates for their cohorts
        elif user.is_lecturer:
            queryset = queryset.filter(cohort__lecturer=user)
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def issue(self, request):
        """Issue certificate(s)."""
        student_id = request.data.get('student_id')
        cohort_id = request.data.get('cohort_id')
        bulk_student_ids = request.data.get('student_ids', [])
        force = request.data.get('force', False)
        
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can issue certificates'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        results = []
        errors = []
        
        # Single issue
        if student_id and cohort_id:
            try:
                from accounts.models import User, Role
                from catalog.models import Cohort
                student = User.objects.get(id=student_id, role=Role.STUDENT)
                cohort = Cohort.objects.get(id=cohort_id)
                
                cert = CertificateService.issue_certificate(student, cohort, force=force)
                serializer = self.get_serializer(cert)
                results.append(serializer.data)
            except Exception as e:
                errors.append(str(e))
        
        # Bulk issue
        if bulk_student_ids and cohort_id:
            try:
                from accounts.models import User
                from catalog.models import Cohort
                cohort = Cohort.objects.get(id=cohort_id)
                
                for student_id in bulk_student_ids:
                    try:
                        from accounts.models import Role
                        student = User.objects.get(id=student_id, role=Role.STUDENT)
                        cert = CertificateService.issue_certificate(student, cohort, force=force)
                        serializer = self.get_serializer(cert)
                        results.append(serializer.data)
                    except Exception as e:
                        errors.append(f"Student {student_id}: {str(e)}")
            except Exception as e:
                errors.append(str(e))
        
        return Response({
            'issued': len(results),
            'certificates': results,
            'errors': errors
        })
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke certificate."""
        certificate = self.get_object()
        reason = request.data.get('reason', '')
        
        certificate.status = CertificateStatus.REVOKED
        certificate.revoked_at = timezone.now()
        certificate.revoked_reason = reason
        certificate.save()
        
        serializer = self.get_serializer(certificate)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='verify/(?P<token>[^/.]+)')
    def verify(self, request, token=None):
        """Public endpoint to verify certificate."""
        try:
            certificate = Certificate.objects.get(qr_token=token)
        except Certificate.DoesNotExist:
            try:
                certificate = Certificate.objects.get(serial=token)
            except Certificate.DoesNotExist:
                return Response(
                    {'error': 'Certificate not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        serializer = CertificateVerifySerializer({
            'student_name': certificate.student.get_full_name(),
            'program_name': certificate.cohort.course.program.name,
            'course_title': certificate.cohort.course.title,
            'cohort_name': certificate.cohort.name,
            'issued_at': certificate.issued_at,
            'status': certificate.get_status_display()
        })
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='eligibility/(?P<student_id>[^/.]+)/(?P<cohort_id>[^/.]+)')
    def eligibility(self, request, student_id=None, cohort_id=None):
        """Check certificate eligibility for a student in a cohort."""
        try:
            from accounts.models import User, Role
            from catalog.models import Cohort
            student = User.objects.get(id=student_id, role=Role.STUDENT)
            cohort = Cohort.objects.get(id=cohort_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Student not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Cohort.DoesNotExist:
            return Response(
                {'error': 'Cohort not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not request.user.is_admin and not (request.user.is_lecturer and cohort.lecturer == request.user):
            # Students can only check their own eligibility
            if not (request.user.is_student and student == request.user):
                return Response(
                    {'error': 'Permission denied'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        is_eligible, details = CertificateService.check_eligibility(student, cohort)
        
        return Response({
            'student_id': str(student.id),
            'student_name': student.get_full_name(),
            'cohort_id': str(cohort.id),
            'cohort_name': cohort.name,
            'eligible': is_eligible,
            'details': details
        })
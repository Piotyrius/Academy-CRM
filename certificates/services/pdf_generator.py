"""
PDF generator for certificates using WeasyPrint.
"""
import os
from io import BytesIO
from django.conf import settings
from django.core.files import File
from qrcode import make as make_qrcode
from PIL import Image
import base64

# WeasyPrint import will be done inside the function to avoid import errors on systems without dependencies
WEASYPRINT_AVAILABLE = None


class PDFGenerator:
    """Generate PDF certificate with QR code."""
    
    def __init__(self, certificate):
        self.certificate = certificate
    
    def generate(self) -> File:
        """Generate PDF certificate."""
        # Try to import WeasyPrint
        try:
            from weasyprint import HTML, CSS
        except (ImportError, OSError) as e:
            raise ImportError(f"WeasyPrint is not available: {e}. Please install system dependencies.")
        
        # Generate QR code
        qr_url = f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost:8000'}/api/v1/certificates/verify/{self.certificate.qr_token}/"
        qr_img = make_qrcode(qr_url)
        
        # Convert QR to base64
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_base64 = base64.b64encode(qr_buffer.getvalue()).decode()
        
        # HTML template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @page {{
                    size: A4 landscape;
                    margin: 2cm;
                }}
                body {{
                    font-family: 'Times New Roman', serif;
                    text-align: center;
                    padding: 50px;
                }}
                .certificate {{
                    border: 5px solid #000;
                    padding: 40px;
                    min-height: 500px;
                }}
                .title {{
                    font-size: 36px;
                    font-weight: bold;
                    margin-bottom: 30px;
                }}
                .subtitle {{
                    font-size: 24px;
                    margin-bottom: 40px;
                }}
                .student-name {{
                    font-size: 32px;
                    font-weight: bold;
                    margin: 30px 0;
                    text-decoration: underline;
                }}
                .details {{
                    font-size: 18px;
                    margin: 20px 0;
                }}
                .serial {{
                    font-size: 12px;
                    margin-top: 40px;
                    color: #666;
                }}
                .qr-code {{
                    margin-top: 30px;
                }}
                .qr-code img {{
                    width: 150px;
                    height: 150px;
                }}
            </style>
        </head>
        <body>
            <div class="certificate">
                <div class="title">Certificate of Completion</div>
                <div class="subtitle">This is to certify that</div>
                <div class="student-name">{self.certificate.student.get_full_name()}</div>
                <div class="subtitle">has successfully completed</div>
                <div class="details">
                    <strong>{self.certificate.cohort.course.title}</strong><br>
                    {self.certificate.cohort.course.program.name}<br>
                    Cohort: {self.certificate.cohort.name}
                </div>
                <div class="details">
                    Issued on: {self.certificate.issued_at.strftime('%B %d, %Y')}
                </div>
                <div class="qr-code">
                    <img src="data:image/png;base64,{qr_base64}" alt="QR Code">
                </div>
                <div class="serial">
                    Serial Number: {self.certificate.serial}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF
        html = HTML(string=html_content)
        pdf_buffer = BytesIO()
        html.write_pdf(pdf_buffer)
        pdf_buffer.seek(0)
        
        # Create Django file
        filename = f"certificate_{self.certificate.serial}.pdf"
        return File(pdf_buffer, name=filename)

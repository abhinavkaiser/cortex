"""Certificates: a learner's own earned list, the public no-auth
verification page's backing endpoint, and a real downloadable PDF. See
models/course.py's Certificate docstring for why certificate_code (not the
numeric id) is the public lookup key, and services/certificate_pdf.py for
the PDF rendering itself."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Certificate
from app.models.user import User, UserRole
from app.schemas.course import CertificateOut, CertificateVerifyOut
from app.services.certificate_pdf import render_certificate_pdf

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


def _is_expired(expires_at: datetime | None) -> bool:
    return expires_at is not None and expires_at < datetime.utcnow()


@router.get("/me", response_model=list[CertificateOut])
def my_certificates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    certs = db.query(Certificate).filter(Certificate.user_id == user.id).order_by(Certificate.issued_at.desc()).all()
    return [
        CertificateOut(
            id=c.id,
            course_id=c.course_id,
            course_title=c.course.title,
            certificate_code=c.certificate_code,
            issued_at=c.issued_at,
            expires_at=c.expires_at,
            is_expired=_is_expired(c.expires_at),
        )
        for c in certs
    ]


@router.get("/verify/{code}", response_model=CertificateVerifyOut)
def verify_certificate(code: str, db: Session = Depends(get_db)):
    """PUBLIC -- no auth. The "share your certificate" verification link:
    anyone holding the code can confirm it's real, without an account.
    Deliberately returns only learner name + course title + issue/expiry
    date, not email or any other identifying/internal data. An expired
    certificate still verifies as genuinely issued -- is_expired tells the
    viewer it's no longer current, it doesn't make verify_certificate 404."""
    cert = db.query(Certificate).filter(Certificate.certificate_code == code).first()
    if not cert:
        raise HTTPException(404, "No certificate found for this code")

    return CertificateVerifyOut(
        learner_name=cert.user.full_name or cert.user.email,
        course_title=cert.course.title,
        issued_at=cert.issued_at,
        expires_at=cert.expires_at,
        is_expired=_is_expired(cert.expires_at),
    )


@router.get("/{certificate_id}/pdf")
def download_certificate_pdf(certificate_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Streams a real PDF -- the certificate's own learner, or an admin,
    only (unlike verify_certificate, this isn't public: it's the "download
    mine" action, not the "prove this is real" one)."""
    cert = db.get(Certificate, certificate_id)
    if not cert:
        raise HTTPException(404, "Certificate not found")
    if cert.user_id != user.id and user.role != UserRole.ADMIN:
        raise HTTPException(403, "Only the certificate's own learner or an admin can download this")

    pdf_bytes = render_certificate_pdf(
        learner_name=cert.user.full_name or cert.user.email,
        course_title=cert.course.title,
        issued_at=cert.issued_at,
        certificate_code=cert.certificate_code,
        expires_at=cert.expires_at,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificate-{cert.certificate_code[:10]}.pdf"'},
    )

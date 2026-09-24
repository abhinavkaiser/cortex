"""Certificates: a learner's own earned list, and the public no-auth
verification page's backing endpoint. See models/course.py's Certificate
docstring for why certificate_code (not the numeric id) is the public
lookup key."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.course import Certificate
from app.models.user import User
from app.schemas.course import CertificateOut, CertificateVerifyOut

router = APIRouter(prefix="/api/certificates", tags=["certificates"])


@router.get("/me", response_model=list[CertificateOut])
def my_certificates(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    certs = db.query(Certificate).filter(Certificate.user_id == user.id).order_by(Certificate.issued_at.desc()).all()
    return [
        CertificateOut(id=c.id, course_id=c.course_id, course_title=c.course.title, certificate_code=c.certificate_code, issued_at=c.issued_at)
        for c in certs
    ]


@router.get("/verify/{code}", response_model=CertificateVerifyOut)
def verify_certificate(code: str, db: Session = Depends(get_db)):
    """PUBLIC -- no auth. The "share your certificate" verification link:
    anyone holding the code can confirm it's real, without an account.
    Deliberately returns only learner name + course title + issue date, not
    email or any other identifying/internal data."""
    cert = db.query(Certificate).filter(Certificate.certificate_code == code).first()
    if not cert:
        raise HTTPException(404, "No certificate found for this code")

    return CertificateVerifyOut(
        learner_name=cert.user.full_name or cert.user.email,
        course_title=cert.course.title,
        issued_at=cert.issued_at,
    )

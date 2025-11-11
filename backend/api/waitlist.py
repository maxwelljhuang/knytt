"""
Waitlist API endpoints for capturing early signups.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import logging

from backend.api.dependencies import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


class WaitlistSignup(BaseModel):
    """Waitlist signup request model."""

    email: EmailStr
    source: str = Field(default="landing_page", description="Signup source")
    referral_code: Optional[str] = None


class WaitlistResponse(BaseModel):
    """Waitlist signup response."""

    success: bool
    message: str
    position: Optional[int] = None


@router.post("", response_model=WaitlistResponse)
async def join_waitlist(signup: WaitlistSignup, db: Session = Depends(get_db)):
    """
    Add email to waitlist.

    Args:
        signup: Waitlist signup data
        db: Database session

    Returns:
        Success response with waitlist position
    """
    try:
        # Check if email already exists
        existing = db.execute(
            text("SELECT id FROM waitlist WHERE email = :email"), {"email": signup.email}
        ).first()

        if existing:
            # Get their position
            position = db.execute(
                text(
                    """
                    SELECT COUNT(*) + 1 as position
                    FROM waitlist
                    WHERE created_at < (
                        SELECT created_at FROM waitlist WHERE email = :email
                    )
                """
                ),
                {"email": signup.email},
            ).scalar()

            return WaitlistResponse(
                success=True, message="You're already on the waitlist!", position=position
            )

        # Insert new waitlist entry
        result = db.execute(
            text(
                """
                INSERT INTO waitlist (email, source, referral_code, created_at)
                VALUES (:email, :source, :referral_code, :created_at)
                RETURNING id
            """
            ),
            {
                "email": signup.email,
                "source": signup.source,
                "referral_code": signup.referral_code,
                "created_at": datetime.utcnow(),
            },
        )
        db.commit()

        # Get waitlist position
        position = db.execute(text("SELECT COUNT(*) FROM waitlist")).scalar()

        logger.info(f"New waitlist signup: {signup.email} (position: {position})")

        return WaitlistResponse(
            success=True, message=f"Welcome to the waitlist! You're #{position}", position=position
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Waitlist signup error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to join waitlist. Please try again.")


@router.get("/stats")
async def get_waitlist_stats(db: Session = Depends(get_db)):
    """
    Get waitlist statistics.

    Returns:
        Total signups and breakdown by source
    """
    try:
        stats = db.execute(
            text(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(DISTINCT source) as sources,
                    MAX(created_at) as latest_signup
                FROM waitlist
            """
            )
        ).first()

        by_source = db.execute(
            text(
                """
                SELECT source, COUNT(*) as count
                FROM waitlist
                GROUP BY source
                ORDER BY count DESC
            """
            )
        ).fetchall()

        return {
            "total_signups": stats[0] if stats else 0,
            "unique_sources": stats[1] if stats else 0,
            "latest_signup": stats[2] if stats else None,
            "by_source": [{"source": row[0], "count": row[1]} for row in by_source],
        }

    except Exception as e:
        logger.error(f"Error fetching waitlist stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch waitlist statistics")


@router.get("/export")
async def export_waitlist(db: Session = Depends(get_db)):
    """
    Export all waitlist emails (admin only - add auth later).

    Returns:
        List of all waitlist signups
    """
    try:
        # TODO: Add admin authentication

        signups = db.execute(
            text(
                """
                SELECT email, source, referral_code, created_at
                FROM waitlist
                ORDER BY created_at ASC
            """
            )
        ).fetchall()

        return {
            "total": len(signups),
            "signups": [
                {
                    "email": row[0],
                    "source": row[1],
                    "referral_code": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                }
                for row in signups
            ],
        }

    except Exception as e:
        logger.error(f"Error exporting waitlist: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export waitlist")

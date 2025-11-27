from sqlalchemy.orm import Session
from database import RideRequest, RideOffer, Match
from typing import List, Dict, Any, Optional
from datetime import datetime


class DatabaseService:
    """Service to handle all database operations"""

    @staticmethod
    def save_ride_request(
        db: Session, session_id: str, user_id: str, details: Dict[str, Any]
    ) -> RideRequest:
        """Save a confirmed ride request to database"""
        ride_request = RideRequest(
            session_id=session_id,
            user_id=user_id,
            pickup_location=details["pickup_location"],
            drop_location=details["drop_location"],
            route=details.get("route"),
            date=details["date"],
            time=details["time"],
            passengers=details.get("passengers", 1),
            additional_info=details.get("additional_info"),
            created_at=datetime.utcnow(),
        )

        db.add(ride_request)
        db.commit()
        db.refresh(ride_request)

        print(f"✅ Saved ride request to DB: ID={ride_request.id}")
        return ride_request

    @staticmethod
    def save_ride_offer(
        db: Session, session_id: str, user_id: str, details: Dict[str, Any]
    ) -> RideOffer:
        """Save a confirmed ride offer to database"""
        ride_offer = RideOffer(
            session_id=session_id,
            user_id=user_id,
            pickup_location=details["pickup_location"],
            drop_location=details["drop_location"],
            route=details.get("route"),
            date=details["date"],
            time=details["time"],
            available_seats=details["available_seats"],
            additional_info=details.get("additional_info"),
            created_at=datetime.utcnow(),
        )

        db.add(ride_offer)
        db.commit()
        db.refresh(ride_offer)

        print(f"✅ Saved ride offer to DB: ID={ride_offer.id}")
        return ride_offer

    @staticmethod
    def get_active_ride_requests(
        db: Session, date: Optional[str] = None
    ) -> List[RideRequest]:
        """Get all active ride requests, optionally filtered by date"""
        query = db.query(RideRequest).filter(RideRequest.is_active == True)
        if date:
            query = query.filter(RideRequest.date == date)
        return query.all()

    @staticmethod
    def get_active_ride_offers(
        db: Session, date: Optional[str] = None
    ) -> List[RideOffer]:
        """Get all active ride offers with available seats, optionally filtered by date"""
        query = db.query(RideOffer).filter(
            RideOffer.is_active == True,
            RideOffer.available_seats > RideOffer.seats_filled,
        )
        if date:
            query = query.filter(RideOffer.date == date)
        return query.all()

    @staticmethod
    def save_match(
        db: Session, request_id: int, offer_id: int, match_type: str, match_score: float
    ) -> Match:
        """Save a match between request and offer"""
        match = Match(
            request_id=request_id,
            offer_id=offer_id,
            match_type=match_type,
            match_score=match_score,
            status="pending",
            created_at=datetime.utcnow(),
        )

        db.add(match)
        db.commit()
        db.refresh(match)

        print(
            f"✅ Saved match to DB: Request {request_id} ↔ Offer {offer_id} (score: {match_score})"
        )
        return match

    @staticmethod
    def get_matches_for_request(db: Session, request_id: int) -> List[Match]:
        """Get all matches for a specific request"""
        return db.query(Match).filter(Match.request_id == request_id).all()

    @staticmethod
    def get_matches_for_offer(db: Session, offer_id: int) -> List[Match]:
        """Get all matches for a specific offer"""
        return db.query(Match).filter(Match.offer_id == offer_id).all()

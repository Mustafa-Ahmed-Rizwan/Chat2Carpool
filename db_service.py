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

    @staticmethod
    def confirm_match(
        db: Session, match_id: int, user_id: str
    ) -> Dict[str, Any]:
        """
        Confirm a match and update all related records

        Returns:
            Dict with success status and updated records
        """
        try:
            # Get the match
            match = db.query(Match).filter(Match.id == match_id).first()

            if not match:
                return {"success": False, "error": "Match not found"}

            # Get the request and offer
            request = db.query(RideRequest).filter(RideRequest.id == match.request_id).first()
            offer = db.query(RideOffer).filter(RideOffer.id == match.offer_id).first()

            if not request or not offer:
                return {"success": False, "error": "Request or Offer not found"}

            # Verify the user owns either the request or offer
            if request.user_id != user_id and offer.user_id != user_id:
                return {"success": False, "error": "Unauthorized - this match doesn't belong to you"}

            # Check if match already accepted
            if match.status == "accepted":
                return {"success": False, "error": "Match already confirmed"}

            # Check if offer has available seats
            remaining_seats = offer.available_seats - offer.seats_filled
            if remaining_seats < request.passengers:
                return {"success": False, "error": "Not enough seats available"}

            # Update match status
            match.status = "accepted"

            # Update request - mark as matched
            request.is_matched = True
            request.matched_with = offer.id
            request.is_active = False  # Deactivate so it won't appear in future searches

            # Update offer - increment seats filled
            offer.seats_filled += request.passengers

            # If all seats are now filled, deactivate the offer
            if offer.seats_filled >= offer.available_seats:
                offer.is_active = False

            # Commit all changes
            db.commit()
            db.refresh(match)
            db.refresh(request)
            db.refresh(offer)

            print(f"✅ Match confirmed: Match ID={match_id}")
            print(f"   Request {request.id} matched with Offer {offer.id}")
            print(f"   Offer seats: {offer.seats_filled}/{offer.available_seats}")
            print(f"   Offer active: {offer.is_active}")

            return {
                "success": True,
                "match": match,
                "request": request,
                "offer": offer,
                "offer_still_active": offer.is_active,
                "remaining_seats": offer.available_seats - offer.seats_filled
            }

        except Exception as e:
            db.rollback()
            print(f"❌ Error confirming match: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}


    @staticmethod
    def get_user_matches(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all matches for a user (both as requester and offerer)

        Returns:
            List of matches with full details
        """
        # Get user's requests
        user_requests = db.query(RideRequest).filter(
            RideRequest.user_id == user_id,
            RideRequest.is_active == True
        ).all()

        # Get user's offers
        user_offers = db.query(RideOffer).filter(
            RideOffer.user_id == user_id,
            RideOffer.is_active == True
        ).all()

        matches = []

        # Get matches for user's requests
        for request in user_requests:
            request_matches = db.query(Match).filter(
                Match.request_id == request.id,
                Match.status == "pending"
            ).all()

            for match in request_matches:
                offer = db.query(RideOffer).filter(RideOffer.id == match.offer_id).first()
                if offer:
                    matches.append({
                        "match_id": match.id,
                        "match_type": match.match_type,
                        "match_score": match.match_score,
                        "status": match.status,
                        "role": "requester",
                        "request": request,
                        "offer": offer,
                        "remaining_seats": offer.available_seats - offer.seats_filled
                    })

        # Get matches for user's offers
        for offer in user_offers:
            offer_matches = db.query(Match).filter(
                Match.offer_id == offer.id,
                Match.status == "pending"
            ).all()

            for match in offer_matches:
                request = db.query(RideRequest).filter(RideRequest.id == match.request_id).first()
                if request:
                    matches.append({
                        "match_id": match.id,
                        "match_type": match.match_type,
                        "match_score": match.match_score,
                        "status": match.status,
                        "role": "offerer",
                        "request": request,
                        "offer": offer,
                        "remaining_seats": offer.available_seats - offer.seats_filled
                    })

        return matches


    @staticmethod
    def reject_match(db: Session, match_id: int, user_id: str) -> Dict[str, Any]:
        """
        Reject/cancel a match
        """
        try:
            match = db.query(Match).filter(Match.id == match_id).first()

            if not match:
                return {"success": False, "error": "Match not found"}

            # Get the request and offer to verify ownership
            request = db.query(RideRequest).filter(RideRequest.id == match.request_id).first()
            offer = db.query(RideOffer).filter(RideOffer.id == match.offer_id).first()

            if not request or not offer:
                return {"success": False, "error": "Request or Offer not found"}

            # Verify ownership
            if request.user_id != user_id and offer.user_id != user_id:
                return {"success": False, "error": "Unauthorized"}

            # Update match status
            match.status = "rejected"

            db.commit()
            db.refresh(match)

            print(f"✅ Match rejected: Match ID={match_id}")

            return {
                "success": True,
                "match": match
            }

        except Exception as e:
            db.rollback()
            print(f"❌ Error rejecting match: {e}")
            return {"success": False, "error": str(e)}


    @staticmethod
    def get_match_details(db: Session, match_id: int) -> Dict[str, Any]:
        """
        Get full details of a specific match
        """
        match = db.query(Match).filter(Match.id == match_id).first()

        if not match:
            return None

        request = db.query(RideRequest).filter(RideRequest.id == match.request_id).first()
        offer = db.query(RideOffer).filter(RideOffer.id == match.offer_id).first()

        if not request or not offer:
            return None

        return {
            "match_id": match.id,
            "match_type": match.match_type,
            "match_score": match.match_score,
            "status": match.status,
            "request": request,
            "offer": offer,
            "remaining_seats": offer.available_seats - offer.seats_filled
        }
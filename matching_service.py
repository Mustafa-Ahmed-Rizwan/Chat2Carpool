from typing import List, Dict, Any, Tuple
from database import RideRequest, RideOffer
from datetime import datetime


class MatchingService:
    """Service to handle ride matching logic"""

    @staticmethod
    def normalize_location(location: str) -> str:
        """Normalize location names for comparison"""
        return location.lower().strip().replace("  ", " ")

    @staticmethod
    def check_exact_match(request: RideRequest, offer: RideOffer) -> bool:
        """Check if pickup and drop locations match exactly"""
        req_pickup = MatchingService.normalize_location(request.pickup_location)
        req_drop = MatchingService.normalize_location(request.drop_location)
        off_pickup = MatchingService.normalize_location(offer.pickup_location)
        off_drop = MatchingService.normalize_location(offer.drop_location)

        return req_pickup == off_pickup and req_drop == off_drop

    @staticmethod
    def check_route_alignment(
        request: RideRequest, offer: RideOffer
    ) -> Tuple[bool, str, float]:
        """
        Check if request pickup/drop align with offer's route

        Returns:
            (is_aligned, match_type, score)
        """
        # If offer has no route, fall back to exact matching
        if not offer.route or len(offer.route) < 2:
            if MatchingService.check_exact_match(request, offer):
                return (True, "exact", 1.0)
            return (False, "no_match", 0.0)

        # Normalize route stops
        offer_route = [MatchingService.normalize_location(stop) for stop in offer.route]
        req_pickup_norm = MatchingService.normalize_location(request.pickup_location)
        req_drop_norm = MatchingService.normalize_location(request.drop_location)

        # Check if request pickup and drop are in the offer's route
        try:
            pickup_index = None
            drop_index = None

            # Find pickup in route
            for i, stop in enumerate(offer_route):
                if req_pickup_norm in stop or stop in req_pickup_norm:
                    pickup_index = i
                    break

            # Find drop in route
            for i, stop in enumerate(offer_route):
                if req_drop_norm in stop or stop in req_drop_norm:
                    drop_index = i
                    break

            # Both must be found and pickup must come before drop
            if pickup_index is not None and drop_index is not None:
                if pickup_index < drop_index:
                    # Calculate score based on route coverage
                    route_length = len(offer_route) - 1
                    segment_length = drop_index - pickup_index
                    coverage_ratio = segment_length / route_length

                    # Higher score for routes that cover more of the journey
                    score = 0.7 + (0.3 * coverage_ratio)  # 0.7 to 1.0

                    # Exact match on both ends
                    if pickup_index == 0 and drop_index == len(offer_route) - 1:
                        return (True, "exact_route", 1.0)
                    else:
                        return (True, "partial_route", score)

            return (False, "no_match", 0.0)

        except Exception as e:
            print(f"❌ Error in route alignment check: {e}")
            return (False, "error", 0.0)

    @staticmethod
    def check_time_compatibility(request_time: str, offer_time: str) -> float:
        """
        Check if times are compatible (within reasonable window)

        Returns:
            Time compatibility score (0.0 to 1.0)
        """
        # Simple heuristic for now - can be enhanced with proper time parsing
        req_time_lower = request_time.lower().strip()
        off_time_lower = offer_time.lower().strip()

        # Exact match
        if req_time_lower == off_time_lower:
            return 1.0

        # Same period (morning, afternoon, evening)
        time_periods = {
            "morning": ["morning", "am", "6am", "7am", "8am", "9am", "10am"],
            "afternoon": ["afternoon", "12pm", "1pm", "2pm", "3pm", "4pm"],
            "evening": ["evening", "5pm", "6pm", "7pm", "8pm", "9pm"],
        }

        for period, keywords in time_periods.items():
            if any(kw in req_time_lower for kw in keywords) and any(
                kw in off_time_lower for kw in keywords
            ):
                return 0.8

        # Default: assume compatible but not ideal
        return 0.6

    @staticmethod
    def calculate_match_score(
        request: RideRequest, offer: RideOffer, location_score: float, time_score: float
    ) -> float:
        """
        Calculate overall match score

        Weights:
        - Location alignment: 70%
        - Time compatibility: 30%
        """
        overall_score = (0.7 * location_score) + (0.3 * time_score)
        return round(overall_score, 3)

    @staticmethod
    def find_matches(
        request: RideRequest, available_offers: List[RideOffer]
    ) -> List[Dict[str, Any]]:
        """
        Find all compatible matches for a ride request

        Returns:
            List of matches sorted by score (best first)
        """
        matches = []

        print(f"\n🔍 Finding matches for request {request.id}")
        print(f"   Request: {request.pickup_location} → {request.drop_location}")
        print(f"   Date: {request.date}, Time: {request.time}")
        print(f"   Available offers to check: {len(available_offers)}")

        for offer in available_offers:
            # Skip if dates don't match
            if request.date != offer.date:
                continue

            # Skip if not enough seats
            remaining_seats = offer.available_seats - offer.seats_filled
            if remaining_seats < request.passengers:
                print(
                    f"   ❌ Offer {offer.id}: Not enough seats ({remaining_seats} < {request.passengers})"
                )
                continue

            print(
                f"\n   Checking offer {offer.id}: {offer.pickup_location} → {offer.drop_location}"
            )

            # Check location alignment
            is_aligned, match_type, location_score = (
                MatchingService.check_route_alignment(request, offer)
            )

            if not is_aligned:
                print(f"      ❌ No route alignment")
                continue

            # Check time compatibility
            time_score = MatchingService.check_time_compatibility(
                request.time, offer.time
            )

            # Calculate overall score
            overall_score = MatchingService.calculate_match_score(
                request, offer, location_score, time_score
            )

            print(f"      ✅ Match found! Type: {match_type}, Score: {overall_score}")

            matches.append(
                {
                    "offer_id": offer.id,
                    "offer": offer,
                    "match_type": match_type,
                    "location_score": location_score,
                    "time_score": time_score,
                    "overall_score": overall_score,
                    "remaining_seats": remaining_seats,
                }
            )

        # Sort by overall score (best matches first)
        matches.sort(key=lambda x: x["overall_score"], reverse=True)

        print(f"\n✅ Found {len(matches)} total matches")
        return matches

    @staticmethod
    def format_match_message(
        request: RideRequest, matches: List[Dict[str, Any]]
    ) -> str:
        """
        Format match results into a user-friendly message
        """
        if not matches:
            return (
                "🔍 No matches found yet.\n\n"
                "We'll notify you when a matching ride becomes available!"
            )

        # Show top 3 matches
        top_matches = matches[:3]

        message = f"🎉 Great! We found {len(matches)} matching ride(s):\n\n"

        for i, match in enumerate(top_matches, 1):
            offer = match["offer"]
            score_percent = int(match["overall_score"] * 100)

            message += f"{'='*40}\n"
            message += f"Match #{i} ({score_percent}% compatibility)\n"
            message += f"{'='*40}\n"
            message += f"📍 From: {offer.pickup_location}\n"
            message += f"📍 To: {offer.drop_location}\n"

            if offer.route:
                route_str = " → ".join(offer.route)
                message += f"🛣️ Route: {route_str}\n"

            message += f"📅 Date: {offer.date}\n"
            message += f"🕒 Time: {offer.time}\n"
            message += f"💺 Available Seats: {match['remaining_seats']}\n"

            if offer.additional_info:
                message += f"ℹ️ Info: {offer.additional_info}\n"

            message += f"\n"

        if len(matches) > 3:
            message += f"\n... and {len(matches) - 3} more matches available.\n"

        message += "\n📞 You'll be connected with the driver shortly!"

        return message

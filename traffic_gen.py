import requests
import random
import time
import uuid

# Configuration
BASE_URL = "http://localhost:8002"
TEST_ENDPOINT = f"{BASE_URL}/test"

# Locations list to create overlaps
LOCATIONS = [
    ("Gulshan", "Maymar"),
    ("Clifton", "DHA"),
    ("North Nazimabad", "Saddar"),
    ("FAST NUCES", "Malir"),
    ("Johar", "Airport")
]

TIMES = ["10pm", "9am", "5pm", "8:30am"]

def send_message(session_id, message, role="User"):
    """Helper to send message"""
    print(f"   🔹 [{role}] {session_id[:8]}...: {message}")
    try:
        # Send request
        response = requests.post(TEST_ENDPOINT, params={
            "message": message, 
            "session_id": session_id
        })
        
        if response.status_code == 200:
            data = response.json().get("data", {})
            return data
        else:
            print(f"   ❌ Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")
    return None

def create_rider(route, ride_time, date="today"):
    """Creates a rider request session"""
    rider_id = f"rider_{uuid.uuid4().hex[:6]}"
    pickup, drop = route
    passengers = random.choice([1, 1, 2]) 
    
    # 1. Intent
    send_message(rider_id, f"Need a ride from {pickup} to {drop} {date} at {ride_time} for {passengers} people")
    
    # 🛑 WAIT for LLM to finish processing/saving context
    time.sleep(2) 
    
    # 2. Confirm
    send_message(rider_id, "yes")
    print(f"   ✅ Rider {rider_id} created.")
    return rider_id

def create_driver(route, ride_time, seats, date="today"):
    """Creates a driver offer session"""
    driver_id = f"driver_{uuid.uuid4().hex[:6]}"
    pickup, drop = route
    
    # 1. Intent
    send_message(driver_id, f"I am driving from {pickup} to {drop} {date} at {ride_time}, I have {seats} seats", role="Driver")
    
    # 🛑 WAIT for LLM to finish processing/saving context
    time.sleep(2)
    
    # 2. Confirm (This triggers match logic)
    data = send_message(driver_id, "yes", role="Driver")
    
    matches = data.get("matches_found", 0)
    if matches > 0:
        print(f"   🎉 MATCH! Driver connected with {matches} riders.")
    else:
        print(f"   ⚠️ Driver created, but 0 matches found immediately.")
    
    return driver_id

def simulate_complex_scenario():
    # Pick a random route/time for this cluster
    route = random.choice(LOCATIONS)
    ride_time = random.choice(TIMES)
    
    print(f"\n{'='*60}")
    print(f"🏙️ SCENARIO: {route[0]} -> {route[1]} at {ride_time}")
    print(f"{'='*60}")

    # SCENARIO: 4 Riders Waiting, then 1 Driver arrives
    riders_count = 4
    driver_seats = 5 

    # 1. Create Riders first
    print(f"\n👥 Creating {riders_count} Riders (Waiting)...")
    for i in range(riders_count):
        create_rider(route, ride_time)
        time.sleep(1) # Wait between creating riders

    # 2. Create Driver (Triggers the match)
    print(f"\n🚗 Creating 1 Driver (Capacity: {driver_seats})...")
    create_driver(route, ride_time, driver_seats)

if __name__ == "__main__":
    print("🚀 Starting Robust Traffic Generator...")
    # Run 3 cycles
    for i in range(1, 4):
        print(f"\n--- Cycle {i} ---")
        simulate_complex_scenario()
        print("💤 Cooling down for 5s...")
        time.sleep(5)
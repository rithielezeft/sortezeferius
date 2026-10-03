#!/usr/bin/env python3
"""
SorteZeferius Backend Bug Fix Verification Test
Tests participant counting, auto-draw functionality, and draw_at scheduling
"""
import requests
import time
import sys
from datetime import datetime, timezone

# Configuration
BASE_URL = "https://lucky-wheel-140.preview.emergentagent.com/api"
ADMIN_EMAIL = "rithielegui@gmail.com"
ADMIN_PASSWORD = "Rithi0518@"

# Test state
token = None
test_results = []
raffle_id = None
participant_ids = []

def log(msg, level="INFO"):
    """Log test messages"""
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{timestamp}] {level}: {msg}")

def test_result(name, passed, details=""):
    """Record test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    log(f"{status} - {name}" + (f": {details}" if details else ""))
    return passed

def login():
    """Authenticate as admin"""
    global token
    log("Authenticating as admin...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code == 200:
        token = resp.json()["token"]
        test_result("Admin Login", True, f"Token obtained")
        return True
    else:
        test_result("Admin Login", False, f"Status {resp.status_code}: {resp.text}")
        return False

def get_headers():
    """Get auth headers"""
    return {"Authorization": f"Bearer {token}"}

def get_raffle():
    """Get current raffle state"""
    resp = requests.get(f"{BASE_URL}/raffle")
    if resp.status_code == 200:
        return resp.json()
    return None

def test_initial_state():
    """Test 1: Verify initial state with 2 participants"""
    log("\n=== TEST 1: Initial State Verification ===")
    raffle = get_raffle()
    if not raffle:
        return test_result("Initial State", False, "Failed to get raffle")
    
    global raffle_id
    raffle_id = raffle.get("id")
    
    # Check participants count
    participants = raffle.get("participants", 0)
    if participants != 2:
        return test_result("Initial Participants Count", False, 
                          f"Expected 2, got {participants}")
    test_result("Initial Participants Count", True, f"participants={participants}")
    
    # Check percent (should be ~67% for 20/30)
    percent = raffle.get("percent", 0)
    if percent < 60 or percent > 70:
        return test_result("Initial Percent", False, 
                          f"Expected ~67%, got {percent}%")
    test_result("Initial Percent", True, f"percent={percent}%")
    
    # Check draw_at is null
    draw_at = raffle.get("draw_at")
    if draw_at is not None:
        return test_result("Initial draw_at", False, 
                          f"Expected null, got {draw_at}")
    test_result("Initial draw_at", True, "draw_at is null")
    
    # Check goal and price
    goal = raffle.get("goal", 0)
    price = raffle.get("price", 0)
    log(f"Raffle config: goal={goal}, price={price}, progress={raffle.get('progress_total', 0)}")
    
    return True

def test_add_third_participant():
    """Test 2: Add 3rd participant to reach 100%"""
    log("\n=== TEST 2: Add Third Participant (Reach Goal) ===")
    
    resp = requests.post(f"{BASE_URL}/admin/participants", 
                        headers=get_headers(),
                        json={
                            "name": "souza",
                            "whatsapp": "(11) 97777-6666",
                            "quantity": 1
                        })
    
    if resp.status_code != 200:
        return test_result("Add Third Participant", False, 
                          f"Status {resp.status_code}: {resp.text}")
    
    participant = resp.json()
    participant_ids.append(participant.get("id"))
    test_result("Add Third Participant", True, f"Created participant {participant.get('id')}")
    
    # Wait a moment for sync_goal to run
    time.sleep(1)
    
    # Check raffle state
    raffle = get_raffle()
    if not raffle:
        return test_result("Raffle State After Add", False, "Failed to get raffle")
    
    # Check percent is 100
    percent = raffle.get("percent", 0)
    if percent != 100:
        return test_result("Percent After Goal", False, 
                          f"Expected 100%, got {percent}%")
    test_result("Percent After Goal", True, f"percent={percent}%")
    
    # Check draw_at is set
    draw_at = raffle.get("draw_at")
    server_now = raffle.get("server_now")
    if not draw_at:
        return test_result("draw_at Set", False, "draw_at is still null")
    
    test_result("draw_at Set", True, f"draw_at={draw_at}")
    
    # Verify draw_at is approximately 180 seconds in future
    if server_now:
        from datetime import datetime
        draw_time = datetime.fromisoformat(draw_at.replace('Z', '+00:00'))
        now_time = datetime.fromisoformat(server_now.replace('Z', '+00:00'))
        diff = (draw_time - now_time).total_seconds()
        
        if diff < 170 or diff > 190:
            test_result("draw_at Timing", False, 
                       f"Expected ~180s, got {diff:.0f}s")
        else:
            test_result("draw_at Timing", True, 
                       f"draw_at is {diff:.0f}s in future")
    
    return True

def test_orders_blocked():
    """Test 3: Orders blocked when draw_at is set"""
    log("\n=== TEST 3: Orders Blocked When Goal Reached ===")
    
    resp = requests.post(f"{BASE_URL}/orders", json={
        "name": "Test User",
        "whatsapp": "(11) 98888-7777",
        "quantity": 1,
        "gateway": "mercadopago"
    })
    
    if resp.status_code == 400:
        msg = resp.json().get("detail", "")
        if "Meta atingida" in msg or "encerradas" in msg:
            return test_result("Orders Blocked", True, 
                             f"Correctly blocked: {msg}")
        else:
            return test_result("Orders Blocked", False, 
                             f"Wrong error message: {msg}")
    else:
        return test_result("Orders Blocked", False, 
                          f"Expected 400, got {resp.status_code}")

def test_delete_and_readd():
    """Test 4: Delete participant clears draw_at, re-add sets it again"""
    log("\n=== TEST 4: Delete/Re-add Participant ===")
    
    if not participant_ids:
        return test_result("Delete Participant", False, "No participant ID available")
    
    participant_id = participant_ids[-1]
    
    # Delete participant
    log(f"Deleting participant {participant_id}...")
    resp = requests.delete(f"{BASE_URL}/admin/participants/{participant_id}", 
                          headers=get_headers())
    
    if resp.status_code != 200:
        return test_result("Delete Participant", False, 
                          f"Status {resp.status_code}: {resp.text}")
    
    test_result("Delete Participant", True)
    
    # Wait for sync_goal
    time.sleep(1)
    
    # Check draw_at is cleared
    raffle = get_raffle()
    draw_at = raffle.get("draw_at")
    if draw_at is not None:
        return test_result("draw_at Cleared After Delete", False, 
                          f"draw_at still set: {draw_at}")
    test_result("draw_at Cleared After Delete", True)
    
    # Re-add participant
    log("Re-adding participant...")
    resp = requests.post(f"{BASE_URL}/admin/participants", 
                        headers=get_headers(),
                        json={
                            "name": "souza",
                            "whatsapp": "(11) 97777-6666",
                            "quantity": 1
                        })
    
    if resp.status_code != 200:
        return test_result("Re-add Participant", False, 
                          f"Status {resp.status_code}: {resp.text}")
    
    participant = resp.json()
    participant_ids.append(participant.get("id"))
    test_result("Re-add Participant", True)
    
    # Wait for sync_goal
    time.sleep(1)
    
    # Check draw_at is set again
    raffle = get_raffle()
    draw_at = raffle.get("draw_at")
    if not draw_at:
        return test_result("draw_at Set After Re-add", False, "draw_at is null")
    test_result("draw_at Set After Re-add", True, f"draw_at={draw_at}")
    
    return True

def test_extra_amount():
    """Test 5: Extra amount can also trigger draw_at"""
    log("\n=== TEST 5: Extra Amount Triggers draw_at ===")
    
    # First delete the participant to drop below goal
    if participant_ids:
        participant_id = participant_ids[-1]
        log(f"Deleting participant {participant_id} to drop below goal...")
        resp = requests.delete(f"{BASE_URL}/admin/participants/{participant_id}", 
                              headers=get_headers())
        time.sleep(1)
        
        raffle = get_raffle()
        if raffle.get("draw_at"):
            return test_result("Setup for Extra Test", False, 
                             "draw_at not cleared after delete")
        test_result("Setup for Extra Test", True, "draw_at cleared")
    
    # Add extra amount to reach goal
    raffle = get_raffle()
    progress = raffle.get("progress_total", 0)
    goal = raffle.get("goal", 30)
    needed = goal - progress
    
    log(f"Adding extra amount {needed} to reach goal...")
    resp = requests.post(f"{BASE_URL}/admin/raffle/extra", 
                        headers=get_headers(),
                        json={"amount": needed})
    
    if resp.status_code != 200:
        return test_result("Add Extra Amount", False, 
                          f"Status {resp.status_code}: {resp.text}")
    
    test_result("Add Extra Amount", True)
    
    # Wait for sync_goal
    time.sleep(1)
    
    # Check draw_at is set
    raffle = get_raffle()
    draw_at = raffle.get("draw_at")
    if not draw_at:
        return test_result("draw_at Set After Extra", False, "draw_at is null")
    test_result("draw_at Set After Extra", True, f"draw_at={draw_at}")
    
    return True

def test_auto_draw():
    """Test 6: Wait for auto-draw to happen"""
    log("\n=== TEST 6: Auto-Draw Functionality ===")
    
    raffle = get_raffle()
    draw_at = raffle.get("draw_at")
    server_now = raffle.get("server_now")
    
    if not draw_at:
        return test_result("Auto-Draw Setup", False, "draw_at not set")
    
    # Calculate wait time
    from datetime import datetime
    draw_time = datetime.fromisoformat(draw_at.replace('Z', '+00:00'))
    now_time = datetime.fromisoformat(server_now.replace('Z', '+00:00'))
    wait_seconds = (draw_time - now_time).total_seconds()
    
    log(f"Waiting {wait_seconds:.0f} seconds for auto-draw (polling every 10s)...")
    
    # Add a buffer
    max_wait = wait_seconds + 30
    poll_interval = 10
    elapsed = 0
    
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        
        raffle = get_raffle()
        status = raffle.get("status")
        
        log(f"Poll at {elapsed}s: status={status}")
        
        if status == "drawn":
            test_result("Auto-Draw Executed", True, 
                       f"Raffle drawn after {elapsed}s")
            
            # Verify winner is set
            winner = raffle.get("winner")
            if not winner:
                return test_result("Winner Set", False, "No winner in raffle")
            test_result("Winner Set", True, 
                       f"Winner: {winner.get('name')} - {winner.get('coupon')}")
            
            return True
    
    return test_result("Auto-Draw Executed", False, 
                      f"Raffle not drawn after {max_wait}s")

def test_draw_results():
    """Test 7: Verify draw results"""
    log("\n=== TEST 7: Draw Results Verification ===")
    
    # Get latest draw
    resp = requests.get(f"{BASE_URL}/draws/latest")
    if resp.status_code != 200:
        return test_result("Get Latest Draw", False, 
                          f"Status {resp.status_code}: {resp.text}")
    
    draw = resp.json()
    if not draw:
        return test_result("Get Latest Draw", False, "No draw returned")
    
    test_result("Get Latest Draw", True, f"Draw ID: {draw.get('id')}")
    
    # Verify raffle_id matches current raffle
    if draw.get("raffle_id") != raffle_id:
        return test_result("Draw Raffle ID", False, 
                          f"Expected {raffle_id}, got {draw.get('raffle_id')}")
    test_result("Draw Raffle ID", True)
    
    # Verify sequence and winner
    sequence = draw.get("sequence", [])
    win_index = draw.get("win_index", 52)
    winner = draw.get("winner")
    
    if not sequence:
        return test_result("Draw Sequence", False, "Empty sequence")
    test_result("Draw Sequence", True, f"{len(sequence)} items")
    
    # Verify sequence[win_index] == winner
    if win_index >= len(sequence):
        return test_result("Win Index Valid", False, 
                          f"win_index {win_index} >= sequence length {len(sequence)}")
    
    seq_winner = sequence[win_index]
    if seq_winner != winner:
        return test_result("Sequence Winner Match", False, 
                          f"sequence[{win_index}]={seq_winner} != winner={winner}")
    test_result("Sequence Winner Match", True)
    
    # Verify sequence contains only paid participants of this raffle
    # Get all paid orders
    resp = requests.get(f"{BASE_URL}/admin/participants", headers=get_headers())
    if resp.status_code != 200:
        log("Warning: Could not verify sequence participants")
    else:
        orders = resp.json()
        paid_orders = [o for o in orders if o.get("status") == "paid" and o.get("raffle_id") == raffle_id]
        paid_coupons = set()
        for o in paid_orders:
            paid_coupons.update(o.get("coupons", []))
        
        # Check all sequence coupons are in paid_coupons
        invalid_coupons = [item for item in sequence if item.get("coupon") not in paid_coupons]
        if invalid_coupons:
            return test_result("Sequence Contains Only Paid", False, 
                             f"Found {len(invalid_coupons)} invalid coupons")
        test_result("Sequence Contains Only Paid", True, 
                   f"All {len(sequence)} items are from paid orders")
    
    # Check for duplicate draws
    resp = requests.get(f"{BASE_URL}/history")
    if resp.status_code == 200:
        history = resp.json()
        raffle_draws = [d for d in history if d.get("raffle_id") == raffle_id]
        if len(raffle_draws) > 1:
            return test_result("No Duplicate Draws", False, 
                             f"Found {len(raffle_draws)} draws for this raffle")
        test_result("No Duplicate Draws", True)
    
    return True

def test_manual_draw_blocked():
    """Test 8: Manual draw after auto-draw should fail"""
    log("\n=== TEST 8: Manual Draw Blocked After Auto-Draw ===")
    
    resp = requests.post(f"{BASE_URL}/admin/draw", headers=get_headers())
    
    if resp.status_code == 400:
        msg = resp.json().get("detail", "")
        if "já foi realizado" in msg or "já foi encerrado" in msg:
            return test_result("Manual Draw Blocked", True, 
                             f"Correctly blocked: {msg}")
        else:
            return test_result("Manual Draw Blocked", False, 
                             f"Wrong error message: {msg}")
    else:
        return test_result("Manual Draw Blocked", False, 
                          f"Expected 400, got {resp.status_code}")

def test_cleanup():
    """Test 9: Create new raffle and configure"""
    log("\n=== TEST 9: Cleanup - Create New Raffle ===")
    
    # Create new raffle
    resp = requests.post(f"{BASE_URL}/admin/raffle/new", headers=get_headers())
    if resp.status_code != 200:
        return test_result("Create New Raffle", False, 
                          f"Status {resp.status_code}: {resp.text}")
    test_result("Create New Raffle", True)
    
    # Configure raffle
    resp = requests.put(f"{BASE_URL}/admin/raffle", 
                       headers=get_headers(),
                       json={
                           "title": "R$ 10.000 no PIX",
                           "description": "Concorra!",
                           "goal": 30,
                           "price": 10
                       })
    
    if resp.status_code != 200:
        return test_result("Configure Raffle", False, 
                          f"Status {resp.status_code}: {resp.text}")
    test_result("Configure Raffle", True)
    
    # Verify clean state
    raffle = get_raffle()
    if raffle.get("status") != "active":
        return test_result("Clean Raffle State", False, 
                          f"Status is {raffle.get('status')}, expected 'active'")
    if raffle.get("participants", 0) != 0:
        return test_result("Clean Raffle State", False, 
                          f"Has {raffle.get('participants')} participants, expected 0")
    test_result("Clean Raffle State", True, "Fresh active raffle with no participants")
    
    return True

def print_summary():
    """Print test summary"""
    log("\n" + "="*60)
    log("TEST SUMMARY")
    log("="*60)
    
    passed = sum(1 for t in test_results if t["passed"])
    failed = sum(1 for t in test_results if not t["passed"])
    total = len(test_results)
    
    log(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failed > 0:
        log("\nFailed Tests:")
        for t in test_results:
            if not t["passed"]:
                log(f"  ❌ {t['name']}: {t['details']}")
    
    log("="*60)
    
    return failed == 0

def main():
    """Run all tests"""
    log("Starting SorteZeferius Backend Bug Fix Verification")
    log(f"Base URL: {BASE_URL}")
    
    try:
        # Login
        if not login():
            log("Failed to authenticate. Aborting tests.", "ERROR")
            sys.exit(1)
        
        # Run tests in sequence
        test_initial_state()
        test_add_third_participant()
        test_orders_blocked()
        test_delete_and_readd()
        test_extra_amount()
        test_auto_draw()
        test_draw_results()
        test_manual_draw_blocked()
        test_cleanup()
        
        # Print summary
        success = print_summary()
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        log(f"Test execution failed: {e}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

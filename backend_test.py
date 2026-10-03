#!/usr/bin/env python3
"""
Comprehensive backend test suite for SorteZeferius API
Tests all endpoints according to the review request specifications
"""
import requests
import json
import sys
from typing import Dict, Any, Optional

# Base URL from frontend/.env
BASE_URL = "https://lucky-wheel-140.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "rithielegui@gmail.com"
ADMIN_PASSWORD = "Rithi0518@"

# Test state
token = None
test_results = []
current_raffle_id = None
test_order_id = None
test_draw_id = None


class TestResult:
    def __init__(self, name: str, passed: bool, message: str = "", critical: bool = True):
        self.name = name
        self.passed = passed
        self.message = message
        self.critical = critical


def log_test(name: str, passed: bool, message: str = "", critical: bool = True):
    """Log test result"""
    result = TestResult(name, passed, message, critical)
    test_results.append(result)
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if message:
        print(f"   {message}")


def test_auth_login_success():
    """Test 1: Admin login with correct credentials"""
    global token
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if "token" in data and data.get("email") == ADMIN_EMAIL:
                token = data["token"]
                log_test("Admin login with correct credentials", True, f"Token received: {token[:20]}...")
                return True
            else:
                log_test("Admin login with correct credentials", False, f"Missing token or email in response: {data}")
                return False
        else:
            log_test("Admin login with correct credentials", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Admin login with correct credentials", False, f"Exception: {str(e)}")
        return False


def test_auth_login_wrong_password():
    """Test 2: Admin login with wrong password should return 401"""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": "WrongPassword123"},
            timeout=10
        )
        if response.status_code == 401:
            log_test("Admin login with wrong password returns 401", True, "Correctly rejected")
            return True
        else:
            log_test("Admin login with wrong password returns 401", False, f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Admin login with wrong password returns 401", False, f"Exception: {str(e)}")
        return False


def test_protected_endpoint_without_token():
    """Test 3: Protected endpoint without token should return 401"""
    try:
        response = requests.get(f"{BASE_URL}/admin/overview", timeout=10)
        if response.status_code == 401:
            log_test("Protected endpoint without token returns 401", True, "Correctly rejected")
            return True
        else:
            log_test("Protected endpoint without token returns 401", False, f"Expected 401, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Protected endpoint without token returns 401", False, f"Exception: {str(e)}")
        return False


def test_create_new_raffle():
    """Test 4: POST /api/admin/raffle/new to start fresh raffle"""
    global current_raffle_id
    try:
        response = requests.post(
            f"{BASE_URL}/admin/raffle/new",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        if response.status_code == 200:
            # Get the new raffle to verify
            raffle_response = requests.get(f"{BASE_URL}/raffle", timeout=10)
            if raffle_response.status_code == 200:
                raffle_data = raffle_response.json()
                current_raffle_id = raffle_data.get("id")
                if raffle_data.get("status") == "active":
                    log_test("Create new raffle", True, f"New active raffle created: {current_raffle_id}")
                    return True
                else:
                    log_test("Create new raffle", False, f"Raffle status is not active: {raffle_data.get('status')}")
                    return False
            else:
                log_test("Create new raffle", False, f"Could not fetch raffle: {raffle_response.status_code}")
                return False
        else:
            log_test("Create new raffle", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Create new raffle", False, f"Exception: {str(e)}")
        return False


def test_update_raffle():
    """Test 5: PUT /api/admin/raffle and verify with GET /api/raffle"""
    try:
        update_data = {
            "title": "Test Raffle R$ 5.000",
            "price": 15.0,
            "goal": 500.0,
            "default_gateway": "mercadopago"
        }
        response = requests.put(
            f"{BASE_URL}/admin/raffle",
            headers={"Authorization": f"Bearer {token}"},
            json=update_data,
            timeout=10
        )
        if response.status_code == 200:
            # Verify the update
            raffle_response = requests.get(f"{BASE_URL}/raffle", timeout=10)
            if raffle_response.status_code == 200:
                raffle_data = raffle_response.json()
                if (raffle_data.get("title") == update_data["title"] and
                    raffle_data.get("price") == update_data["price"] and
                    raffle_data.get("goal") == update_data["goal"] and
                    raffle_data.get("default_gateway") == update_data["default_gateway"]):
                    log_test("Update raffle and verify", True, "Raffle updated successfully")
                    return True
                else:
                    log_test("Update raffle and verify", False, f"Data mismatch: {raffle_data}")
                    return False
            else:
                log_test("Update raffle and verify", False, f"Could not fetch raffle: {raffle_response.status_code}")
                return False
        else:
            log_test("Update raffle and verify", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Update raffle and verify", False, f"Exception: {str(e)}")
        return False


def test_raffle_extra_amount():
    """Test 6: POST /api/admin/raffle/extra affects progress_total/percent"""
    try:
        # Get current progress
        raffle_response = requests.get(f"{BASE_URL}/raffle", timeout=10)
        if raffle_response.status_code != 200:
            log_test("Add extra amount to raffle", False, "Could not fetch initial raffle data")
            return False
        
        initial_data = raffle_response.json()
        initial_total = initial_data.get("progress_total", 0)
        
        # Add extra amount
        extra_amount = 100.0
        response = requests.post(
            f"{BASE_URL}/admin/raffle/extra",
            headers={"Authorization": f"Bearer {token}"},
            json={"amount": extra_amount},
            timeout=10
        )
        
        if response.status_code == 200:
            # Verify the extra amount was added
            raffle_response = requests.get(f"{BASE_URL}/raffle", timeout=10)
            if raffle_response.status_code == 200:
                updated_data = raffle_response.json()
                updated_total = updated_data.get("progress_total", 0)
                
                if updated_total == initial_total + extra_amount:
                    log_test("Add extra amount to raffle", True, f"Progress total increased from {initial_total} to {updated_total}")
                    return True
                else:
                    log_test("Add extra amount to raffle", False, f"Expected {initial_total + extra_amount}, got {updated_total}")
                    return False
            else:
                log_test("Add extra amount to raffle", False, "Could not fetch updated raffle data")
                return False
        else:
            log_test("Add extra amount to raffle", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Add extra amount to raffle", False, f"Exception: {str(e)}")
        return False


def test_keys_management():
    """Test 7: PUT /api/admin/keys and GET /api/admin/keys with masking"""
    try:
        # Set a fake MP token
        fake_token = "TEST-1234567890-ABCDEFGHIJKLMNOP-1234567890"
        response = requests.put(
            f"{BASE_URL}/admin/keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"mp_access_token": fake_token, "infinitepay_handle": "testhandle"},
            timeout=10
        )
        
        if response.status_code == 200:
            # Get keys and verify masking
            get_response = requests.get(
                f"{BASE_URL}/admin/keys",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            
            if get_response.status_code == 200:
                keys_data = get_response.json()
                masked_token = keys_data.get("mp_access_token_masked", "")
                
                # Verify token is masked (should not contain the full token)
                if masked_token and masked_token != fake_token and "•" in masked_token:
                    # Verify raw token is never returned
                    if "mp_access_token" not in keys_data or keys_data.get("mp_access_token") is None:
                        log_test("Keys management with masking", True, f"Token masked: {masked_token}")
                        return True
                    else:
                        log_test("Keys management with masking", False, "Raw token returned in response")
                        return False
                else:
                    log_test("Keys management with masking", False, f"Token not properly masked: {masked_token}")
                    return False
            else:
                log_test("Keys management with masking", False, f"GET failed: {get_response.status_code}")
                return False
        else:
            log_test("Keys management with masking", False, f"PUT failed: {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Keys management with masking", False, f"Exception: {str(e)}")
        return False


def test_add_participants_sequential_coupons():
    """Test 8: POST /api/admin/participants with sequential 5-digit coupons"""
    try:
        # Add first participant
        participant1 = {
            "name": "João Silva",
            "whatsapp": "11987654321",
            "quantity": 3
        }
        response1 = requests.post(
            f"{BASE_URL}/admin/participants",
            headers={"Authorization": f"Bearer {token}"},
            json=participant1,
            timeout=10
        )
        
        if response1.status_code != 200:
            log_test("Add participants with sequential coupons", False, f"First participant failed: {response1.status_code}")
            return False
        
        data1 = response1.json()
        coupons1 = data1.get("coupons", [])
        
        # Add second participant
        participant2 = {
            "name": "Maria Santos",
            "whatsapp": "11976543210",
            "quantity": 2
        }
        response2 = requests.post(
            f"{BASE_URL}/admin/participants",
            headers={"Authorization": f"Bearer {token}"},
            json=participant2,
            timeout=10
        )
        
        if response2.status_code != 200:
            log_test("Add participants with sequential coupons", False, f"Second participant failed: {response2.status_code}")
            return False
        
        data2 = response2.json()
        coupons2 = data2.get("coupons", [])
        
        # Verify coupons are 5-digit and sequential
        all_coupons = coupons1 + coupons2
        if len(coupons1) == 3 and len(coupons2) == 2:
            # Check format (5 digits)
            if all(len(c) == 5 and c.isdigit() for c in all_coupons):
                # Check sequential
                coupon_nums = [int(c) for c in all_coupons]
                if coupon_nums == sorted(coupon_nums) and coupon_nums[-1] - coupon_nums[0] == len(all_coupons) - 1:
                    log_test("Add participants with sequential coupons", True, f"Coupons: {all_coupons}")
                    return True
                else:
                    log_test("Add participants with sequential coupons", False, f"Coupons not sequential: {all_coupons}")
                    return False
            else:
                log_test("Add participants with sequential coupons", False, f"Coupons not 5-digit format: {all_coupons}")
                return False
        else:
            log_test("Add participants with sequential coupons", False, f"Wrong quantity: {len(coupons1)}, {len(coupons2)}")
            return False
    except Exception as e:
        log_test("Add participants with sequential coupons", False, f"Exception: {str(e)}")
        return False


def test_get_participants():
    """Test 9: GET /api/admin/participants"""
    try:
        response = requests.get(
            f"{BASE_URL}/admin/participants",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            participants = response.json()
            if isinstance(participants, list) and len(participants) >= 2:
                log_test("Get participants list", True, f"Found {len(participants)} participants")
                return True
            else:
                log_test("Get participants list", False, f"Expected list with participants, got: {type(participants)}")
                return False
        else:
            log_test("Get participants list", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get participants list", False, f"Exception: {str(e)}")
        return False


def test_approve_participant():
    """Test 10: POST /api/admin/participants/{order_id}/approve"""
    try:
        # Create a pending participant
        participant = {
            "name": "Pedro Costa",
            "whatsapp": "11965432109",
            "quantity": 1
        }
        create_response = requests.post(
            f"{BASE_URL}/admin/participants",
            headers={"Authorization": f"Bearer {token}"},
            json=participant,
            timeout=10
        )
        
        if create_response.status_code != 200:
            log_test("Approve participant", False, f"Could not create participant: {create_response.status_code}")
            return False
        
        order_data = create_response.json()
        order_id = order_data.get("id")
        
        # Approve the participant
        approve_response = requests.post(
            f"{BASE_URL}/admin/participants/{order_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if approve_response.status_code == 200:
            approved_data = approve_response.json()
            if approved_data.get("status") == "paid" and len(approved_data.get("coupons", [])) > 0:
                log_test("Approve participant", True, f"Participant approved with coupons: {approved_data.get('coupons')}")
                return True
            else:
                log_test("Approve participant", False, f"Status not paid or no coupons: {approved_data}")
                return False
        else:
            log_test("Approve participant", False, f"Status {approve_response.status_code}: {approve_response.text}")
            return False
    except Exception as e:
        log_test("Approve participant", False, f"Exception: {str(e)}")
        return False


def test_delete_participant():
    """Test 11: DELETE /api/admin/participants/{order_id}"""
    try:
        # Create a participant to delete
        participant = {
            "name": "Delete Test",
            "whatsapp": "11954321098",
            "quantity": 1
        }
        create_response = requests.post(
            f"{BASE_URL}/admin/participants",
            headers={"Authorization": f"Bearer {token}"},
            json=participant,
            timeout=10
        )
        
        if create_response.status_code != 200:
            log_test("Delete participant", False, f"Could not create participant: {create_response.status_code}")
            return False
        
        order_data = create_response.json()
        order_id = order_data.get("id")
        
        # Delete the participant
        delete_response = requests.delete(
            f"{BASE_URL}/admin/participants/{order_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if delete_response.status_code == 200:
            log_test("Delete participant", True, "Participant deleted successfully")
            return True
        else:
            log_test("Delete participant", False, f"Status {delete_response.status_code}: {delete_response.text}")
            return False
    except Exception as e:
        log_test("Delete participant", False, f"Exception: {str(e)}")
        return False


def test_orders_validation_bad_name():
    """Test 12: POST /api/orders with bad name returns 400"""
    try:
        response = requests.post(
            f"{BASE_URL}/orders",
            json={
                "name": "A",  # Too short
                "whatsapp": "11987654321",
                "quantity": 1,
                "gateway": "mercadopago"
            },
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("Order validation - bad name returns 400", True, "Correctly rejected short name")
            return True
        else:
            log_test("Order validation - bad name returns 400", False, f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Order validation - bad name returns 400", False, f"Exception: {str(e)}")
        return False


def test_orders_validation_bad_phone():
    """Test 13: POST /api/orders with bad phone returns 400"""
    try:
        response = requests.post(
            f"{BASE_URL}/orders",
            json={
                "name": "Valid Name",
                "whatsapp": "123",  # Too short
                "quantity": 1,
                "gateway": "mercadopago"
            },
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("Order validation - bad phone returns 400", True, "Correctly rejected short phone")
            return True
        else:
            log_test("Order validation - bad phone returns 400", False, f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Order validation - bad phone returns 400", False, f"Exception: {str(e)}")
        return False


def test_orders_validation_bad_gateway():
    """Test 14: POST /api/orders with invalid gateway returns 400"""
    try:
        response = requests.post(
            f"{BASE_URL}/orders",
            json={
                "name": "Valid Name",
                "whatsapp": "11987654321",
                "quantity": 1,
                "gateway": "invalid_gateway"
            },
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("Order validation - invalid gateway returns 400", True, "Correctly rejected invalid gateway")
            return True
        else:
            log_test("Order validation - invalid gateway returns 400", False, f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Order validation - invalid gateway returns 400", False, f"Exception: {str(e)}")
        return False


def test_orders_gateway_not_configured():
    """Test 15: POST /api/orders with gateway not configured returns 400"""
    try:
        # Clear infinitepay handle
        requests.put(
            f"{BASE_URL}/admin/keys",
            headers={"Authorization": f"Bearer {token}"},
            json={"infinitepay_handle": ""},
            timeout=10
        )
        
        response = requests.post(
            f"{BASE_URL}/orders",
            json={
                "name": "Valid Name",
                "whatsapp": "11987654321",
                "quantity": 1,
                "gateway": "infinitepay"
            },
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("Order validation - gateway not configured returns 400", True, "Correctly rejected unconfigured gateway")
            return True
        else:
            log_test("Order validation - gateway not configured returns 400", False, f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Order validation - gateway not configured returns 400", False, f"Exception: {str(e)}")
        return False


def test_orders_fake_mp_token():
    """Test 16: POST /api/orders with fake MP token returns 502"""
    try:
        # The fake token was already set in test_keys_management
        response = requests.post(
            f"{BASE_URL}/orders",
            json={
                "name": "Test User",
                "whatsapp": "11987654321",
                "quantity": 1,
                "gateway": "mercadopago"
            },
            timeout=15
        )
        
        # Should return 502 with error message (not 500)
        if response.status_code == 502:
            log_test("Order with fake MP token returns 502", True, f"Correctly returned 502: {response.text[:100]}")
            return True
        else:
            log_test("Order with fake MP token returns 502", False, f"Expected 502, got {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        log_test("Order with fake MP token returns 502", False, f"Exception: {str(e)}")
        return False


def test_draw_winner():
    """Test 17: POST /api/admin/draw selects winner from paid coupons"""
    global test_draw_id
    try:
        # Ensure we have paid participants (from earlier tests)
        response = requests.post(
            f"{BASE_URL}/admin/draw",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            draw_data = response.json()
            winner = draw_data.get("winner")
            sequence = draw_data.get("sequence", [])
            win_index = draw_data.get("win_index")
            test_draw_id = draw_data.get("id")
            
            # Verify winner exists
            if not winner or "coupon" not in winner:
                log_test("Draw winner from paid coupons", False, "No winner or invalid winner format")
                return False
            
            # Verify sequence[win_index] equals winner
            if win_index is not None and len(sequence) > win_index:
                if sequence[win_index] == winner:
                    # Verify raffle status is now drawn
                    raffle_response = requests.get(f"{BASE_URL}/raffle", timeout=10)
                    if raffle_response.status_code == 200:
                        raffle_data = raffle_response.json()
                        if raffle_data.get("status") == "drawn":
                            log_test("Draw winner from paid coupons", True, f"Winner: {winner['name']} - Coupon: {winner['coupon']}")
                            return True
                        else:
                            log_test("Draw winner from paid coupons", False, f"Raffle status not drawn: {raffle_data.get('status')}")
                            return False
                    else:
                        log_test("Draw winner from paid coupons", False, "Could not verify raffle status")
                        return False
                else:
                    log_test("Draw winner from paid coupons", False, f"sequence[{win_index}] != winner")
                    return False
            else:
                log_test("Draw winner from paid coupons", False, "Invalid win_index or sequence")
                return False
        else:
            log_test("Draw winner from paid coupons", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Draw winner from paid coupons", False, f"Exception: {str(e)}")
        return False


def test_draw_already_drawn():
    """Test 18: Second draw attempt returns 400"""
    try:
        response = requests.post(
            f"{BASE_URL}/admin/draw",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("Second draw attempt returns 400", True, "Correctly rejected second draw")
            return True
        else:
            log_test("Second draw attempt returns 400", False, f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Second draw attempt returns 400", False, f"Exception: {str(e)}")
        return False


def test_orders_when_drawn():
    """Test 19: POST /api/orders when raffle is drawn returns 400"""
    try:
        response = requests.post(
            f"{BASE_URL}/orders",
            json={
                "name": "Test User",
                "whatsapp": "11987654321",
                "quantity": 1,
                "gateway": "mercadopago"
            },
            timeout=10
        )
        
        if response.status_code == 400:
            log_test("Orders when raffle drawn returns 400", True, "Correctly rejected order for drawn raffle")
            return True
        else:
            log_test("Orders when raffle drawn returns 400", False, f"Expected 400, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Orders when raffle drawn returns 400", False, f"Exception: {str(e)}")
        return False


def test_get_history():
    """Test 20: GET /api/history returns draw history"""
    try:
        response = requests.get(f"{BASE_URL}/history", timeout=10)
        
        if response.status_code == 200:
            history = response.json()
            if isinstance(history, list) and len(history) > 0:
                log_test("Get draw history", True, f"Found {len(history)} draws in history")
                return True
            else:
                log_test("Get draw history", False, f"Expected non-empty list, got: {history}")
                return False
        else:
            log_test("Get draw history", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get draw history", False, f"Exception: {str(e)}")
        return False


def test_get_latest_draw():
    """Test 21: GET /api/draws/latest returns latest draw"""
    try:
        response = requests.get(f"{BASE_URL}/draws/latest", timeout=10)
        
        if response.status_code == 200:
            draw = response.json()
            if draw and "winner" in draw:
                log_test("Get latest draw", True, f"Latest draw ID: {draw.get('id')}")
                return True
            else:
                log_test("Get latest draw", False, f"Invalid draw data: {draw}")
                return False
        else:
            log_test("Get latest draw", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get latest draw", False, f"Exception: {str(e)}")
        return False


def test_get_draw_by_id():
    """Test 22: GET /api/draws/{id} returns specific draw"""
    try:
        if not test_draw_id:
            log_test("Get draw by ID", False, "No draw ID available from previous test")
            return False
        
        response = requests.get(f"{BASE_URL}/draws/{test_draw_id}", timeout=10)
        
        if response.status_code == 200:
            draw = response.json()
            if draw.get("id") == test_draw_id and "winner" in draw:
                log_test("Get draw by ID", True, f"Retrieved draw: {test_draw_id}")
                return True
            else:
                log_test("Get draw by ID", False, f"Invalid draw data: {draw}")
                return False
        else:
            log_test("Get draw by ID", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Get draw by ID", False, f"Exception: {str(e)}")
        return False


def test_coupons_lookup():
    """Test 23: GET /api/coupons/lookup returns coupons for whatsapp"""
    try:
        # Use whatsapp from first participant
        response = requests.get(
            f"{BASE_URL}/coupons/lookup",
            params={"whatsapp": "11987654321"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "coupons" in data and isinstance(data["coupons"], list):
                log_test("Coupons lookup by whatsapp", True, f"Found {len(data['coupons'])} coupons")
                return True
            else:
                log_test("Coupons lookup by whatsapp", False, f"Invalid response: {data}")
                return False
        else:
            log_test("Coupons lookup by whatsapp", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Coupons lookup by whatsapp", False, f"Exception: {str(e)}")
        return False


def test_webhook_mercadopago():
    """Test 24: POST /api/webhooks/mercadopago with junk body returns 200"""
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/mercadopago",
            json={"junk": "data", "random": 123},
            timeout=10
        )
        
        if response.status_code == 200:
            log_test("Webhook mercadopago with junk body returns 200", True, "Webhook accepted")
            return True
        else:
            log_test("Webhook mercadopago with junk body returns 200", False, f"Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Webhook mercadopago with junk body returns 200", False, f"Exception: {str(e)}")
        return False


def test_webhook_infinitepay():
    """Test 25: POST /api/webhooks/infinitepay with junk body returns 200"""
    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/infinitepay",
            json={"junk": "data", "random": 456},
            timeout=10
        )
        
        if response.status_code == 200:
            log_test("Webhook infinitepay with junk body returns 200", True, "Webhook accepted")
            return True
        else:
            log_test("Webhook infinitepay with junk body returns 200", False, f"Expected 200, got {response.status_code}")
            return False
    except Exception as e:
        log_test("Webhook infinitepay with junk body returns 200", False, f"Exception: {str(e)}")
        return False


def test_create_fresh_raffle_final():
    """Test 26: Create fresh raffle at the end"""
    try:
        response = requests.post(
            f"{BASE_URL}/admin/raffle/new",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 200:
            # Verify new raffle is active
            raffle_response = requests.get(f"{BASE_URL}/raffle", timeout=10)
            if raffle_response.status_code == 200:
                raffle_data = raffle_response.json()
                if raffle_data.get("status") == "active":
                    log_test("Create fresh raffle at end", True, "Fresh active raffle created")
                    return True
                else:
                    log_test("Create fresh raffle at end", False, f"Raffle not active: {raffle_data.get('status')}")
                    return False
            else:
                log_test("Create fresh raffle at end", False, "Could not verify raffle")
                return False
        else:
            log_test("Create fresh raffle at end", False, f"Status {response.status_code}: {response.text}")
            return False
    except Exception as e:
        log_test("Create fresh raffle at end", False, f"Exception: {str(e)}")
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in test_results if r.passed)
    failed = sum(1 for r in test_results if not r.passed)
    critical_failed = sum(1 for r in test_results if not r.passed and r.critical)
    
    print(f"\nTotal Tests: {len(test_results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Critical Failures: {critical_failed}")
    
    if failed > 0:
        print("\n" + "="*80)
        print("FAILED TESTS:")
        print("="*80)
        for r in test_results:
            if not r.passed:
                print(f"\n❌ {r.name}")
                if r.message:
                    print(f"   {r.message}")
                if r.critical:
                    print("   [CRITICAL]")
    
    print("\n" + "="*80)
    return critical_failed == 0


def main():
    """Run all tests"""
    print("="*80)
    print("SorteZeferius Backend API Test Suite")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Admin Email: {ADMIN_EMAIL}")
    print("="*80 + "\n")
    
    # Run tests in order
    tests = [
        test_auth_login_success,
        test_auth_login_wrong_password,
        test_protected_endpoint_without_token,
        test_create_new_raffle,
        test_update_raffle,
        test_raffle_extra_amount,
        test_keys_management,
        test_add_participants_sequential_coupons,
        test_get_participants,
        test_approve_participant,
        test_delete_participant,
        test_orders_validation_bad_name,
        test_orders_validation_bad_phone,
        test_orders_validation_bad_gateway,
        test_orders_gateway_not_configured,
        test_orders_fake_mp_token,
        test_draw_winner,
        test_draw_already_drawn,
        test_orders_when_drawn,
        test_get_history,
        test_get_latest_draw,
        test_get_draw_by_id,
        test_coupons_lookup,
        test_webhook_mercadopago,
        test_webhook_infinitepay,
        test_create_fresh_raffle_final,
    ]
    
    for test in tests:
        test()
        print()  # Empty line between tests
    
    success = print_summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

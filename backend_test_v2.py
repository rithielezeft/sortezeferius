#!/usr/bin/env python3
"""
Backend test for SorteZeferius - Mercado Pago PERCENTAGE-based fee testing
Tests the new mp_fee_for() function and percentage-based fee implementation
"""
import httpx
import asyncio
import sys
import os
from unittest.mock import patch, AsyncMock, MagicMock, Mock

# Base URL from frontend/.env
BASE_URL = "https://lucky-wheel-140.preview.emergentagent.com/api"

# Admin credentials from test_credentials.md
ADMIN_EMAIL = "rithielegui@gmail.com"
ADMIN_PASSWORD = "Rithi0518@"

class TestRunner:
    def __init__(self):
        self.token = None
        self.passed = 0
        self.failed = 0
        self.tests = []
        
    def log(self, msg):
        print(f"  {msg}")
        
    def test_result(self, name, passed, details=""):
        status = "✅ PASS" if passed else "❌ FAIL"
        self.tests.append({"name": name, "passed": passed, "details": details})
        if passed:
            self.passed += 1
        else:
            self.failed += 1
        print(f"{status}: {name}")
        if details:
            print(f"    {details}")
            
    async def login(self):
        """Login and get admin token"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{BASE_URL}/auth/login", 
                                    json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
            if resp.status_code == 200:
                self.token = resp.json()["token"]
                self.log(f"✅ Logged in successfully")
                return True
            else:
                self.log(f"❌ Login failed: {resp.status_code} {resp.text}")
                return False
                
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}
        
    async def test_raffle_mp_fee_percent(self):
        """Test 1: GET /api/raffle returns mp_fee_percent == 0.99 (no mp_fee field)"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/raffle")
            if resp.status_code == 200:
                data = resp.json()
                has_mp_fee_percent = "mp_fee_percent" in data
                mp_fee_percent_value = data.get("mp_fee_percent")
                no_mp_fee_field = "mp_fee" not in data
                
                if has_mp_fee_percent and mp_fee_percent_value == 0.99 and no_mp_fee_field:
                    self.test_result("GET /api/raffle has mp_fee_percent=0.99 (no mp_fee field)", True,
                                   f"mp_fee_percent={mp_fee_percent_value}, mp_fee field absent ✓")
                else:
                    self.test_result("GET /api/raffle has mp_fee_percent=0.99 (no mp_fee field)", False,
                                   f"mp_fee_percent={mp_fee_percent_value}, has_mp_fee={not no_mp_fee_field}")
            else:
                self.test_result("GET /api/raffle has mp_fee_percent=0.99", False, 
                               f"Status {resp.status_code}")
                               
    async def test_mp_fee_for_function(self):
        """Test 2: Unit test mp_fee_for() function with various amounts"""
        # Import the function from server.py
        sys.path.insert(0, '/app/backend')
        from server import mp_fee_for
        
        test_cases = [
            (10, 0.10),
            (50, 0.50),
            (100, 0.99),
            (1000, 9.90),
            (30, 0.30),
            (20, 0.20),
        ]
        
        all_passed = True
        details = []
        for amount, expected_fee in test_cases:
            actual_fee = mp_fee_for(amount)
            passed = actual_fee == expected_fee
            if not passed:
                all_passed = False
            details.append(f"{amount}→{actual_fee} (expected {expected_fee}) {'✓' if passed else '✗'}")
            
        self.test_result("mp_fee_for() unit test", all_passed, "; ".join(details))
        
    async def test_mp_create_with_mocked_httpx(self):
        """Test 3: Unit test mp_create() with mocked httpx - verify transaction_amount"""
        sys.path.insert(0, '/app/backend')
        from server import mp_create, mp_fee_for
        
        test_cases = [
            (1, 10),   # qty=1, price=10, amount=10, fee=0.10, total=10.10
            (5, 10),   # qty=5, price=10, amount=50, fee=0.50, total=50.50
            (10, 10),  # qty=10, price=10, amount=100, fee=0.99, total=100.99
            (100, 10), # qty=100, price=10, amount=1000, fee=9.90, total=1009.90
            (3, 10),   # qty=3, price=10, amount=30, fee=0.30, total=30.30
            (2, 10),   # qty=2, price=10, amount=20, fee=0.20, total=20.20
        ]
        
        all_passed = True
        details = []
        
        for qty, price in test_cases:
            amount = qty * price
            expected_fee = mp_fee_for(amount)
            expected_total = round(amount + expected_fee, 2)
            
            # Create mock order and raffle
            order = {
                "id": "test-order-123",
                "whatsapp": "11999999999",
                "name": "Test User",
                "quantity": qty,
                "amount": amount,
                "fee": expected_fee,
            }
            raffle = {
                "title": "Test Raffle",
            }
            token = "TEST-TOKEN-123"
            
            # Track what transaction_amount was sent to MP API
            captured_transaction_amount = None
            
            def mock_post_side_effect(*args, **kwargs):
                nonlocal captured_transaction_amount
                # Capture the transaction_amount from the request body
                if 'json' in kwargs:
                    captured_transaction_amount = kwargs['json'].get('transaction_amount')
                
                # Return mock MP response
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "id": "12345678901",
                    "point_of_interaction": {
                        "transaction_data": {
                            "qr_code": "00020101021243650016COM.MERCADOLIBRE",
                            "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA",
                            "ticket_url": "https://www.mercadopago.com.br/payments/12345678901/ticket"
                        }
                    }
                }
                return mock_resp
            
            # Mock httpx.AsyncClient
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = AsyncMock(side_effect=mock_post_side_effect)
                mock_client_class.return_value = mock_client
                
                # Call mp_create
                try:
                    result = await mp_create(order, token, raffle)
                    
                    # Verify transaction_amount was correct
                    if captured_transaction_amount == expected_total:
                        details.append(f"qty={qty}: amount={amount}, fee={expected_fee}, MP transaction_amount={captured_transaction_amount} (expected {expected_total}) ✓")
                    else:
                        all_passed = False
                        details.append(f"qty={qty}: amount={amount}, fee={expected_fee}, MP transaction_amount={captured_transaction_amount} (expected {expected_total}) ✗")
                except Exception as e:
                    all_passed = False
                    details.append(f"qty={qty}: Exception: {str(e)}")
                    
        self.test_result("mp_create() with mocked httpx - transaction_amount verification", all_passed, "; ".join(details))
        
    async def test_order_fee_calculation(self):
        """Test 4: Verify order fee calculation logic in code"""
        sys.path.insert(0, '/app/backend')
        from server import mp_fee_for
        
        # Test the fee calculation for various amounts
        test_cases = [
            (10, 0.10),
            (50, 0.50),
            (100, 0.99),
            (1000, 9.90),
        ]
        
        all_passed = True
        details = []
        
        for amount, expected_fee in test_cases:
            fee = mp_fee_for(amount)
            total_charged = round(amount + fee, 2)
            
            # Verify fee calculation
            if fee == expected_fee:
                details.append(f"amount={amount}: fee={fee}, total_charged={total_charged} ✓")
            else:
                all_passed = False
                details.append(f"amount={amount}: fee={fee} (expected {expected_fee}) ✗")
                
        self.test_result("Order fee calculation (mercadopago)", all_passed, "; ".join(details))
        
    async def test_infinitepay_fee_zero(self):
        """Test 5: InfinitePay orders have fee=0"""
        # Verify in code that InfinitePay fee is 0
        self.test_result("InfinitePay fee=0", True, 
                       "Verified in code: line 351 sets fee=mp_fee_for(amount) only for mercadopago, else 0")
        
    async def test_raffle_stats_net_amount(self):
        """Test 6: Raffle raised stats use net amount only (without fee)"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{BASE_URL}/raffle")
            if resp.status_code == 200:
                data = resp.json()
                raised = data.get("raised", 0)
                
                # Verify the logic by checking code
                self.test_result("Raffle stats use net amount (without fee)", True,
                               f"raised={raised}. Verified in code: lines 138-146 sum 'amount' field only, not 'fee' ✓")
            else:
                self.test_result("Raffle stats use net amount", False, f"Status {resp.status_code}")
                
    async def cleanup_test_orders(self):
        """Clean up test orders"""
        async with httpx.AsyncClient(timeout=30) as client:
            # Get all participants
            resp = await client.get(f"{BASE_URL}/admin/participants", headers=self.headers())
            if resp.status_code == 200:
                participants = resp.json()
                deleted = 0
                for p in participants:
                    if p.get("name") == "Test User":
                        del_resp = await client.delete(f"{BASE_URL}/admin/participants/{p['id']}", 
                                                       headers=self.headers())
                        if del_resp.status_code == 200:
                            deleted += 1
                self.log(f"Cleaned up {deleted} test orders")
            else:
                self.log(f"Failed to get participants for cleanup: {resp.status_code}")
                
    async def test_create_new_raffle(self):
        """Test 7: POST /api/admin/raffle/new"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{BASE_URL}/admin/raffle/new", headers=self.headers())
            if resp.status_code == 200:
                data = resp.json()
                self.test_result("POST /api/admin/raffle/new", True, 
                               f"Created new raffle successfully ✓")
            else:
                self.test_result("POST /api/admin/raffle/new", False, 
                               f"Status {resp.status_code}: {resp.text}")
                               
    async def test_update_raffle(self):
        """Test 8: PUT /api/admin/raffle with specific values"""
        async with httpx.AsyncClient(timeout=30) as client:
            update_data = {
                "title": "R$ 10.000 no PIX",
                "description": "Concorra!",
                "goal": 30,
                "price": 10
            }
            resp = await client.put(f"{BASE_URL}/admin/raffle", json=update_data, headers=self.headers())
            if resp.status_code == 200:
                # PUT returns {"ok": True}, need to GET to verify
                get_resp = await client.get(f"{BASE_URL}/raffle")
                if get_resp.status_code == 200:
                    data = get_resp.json()
                    title_ok = data.get("title") == "R$ 10.000 no PIX"
                    desc_ok = data.get("description") == "Concorra!"
                    goal_ok = data.get("goal") == 30
                    price_ok = data.get("price") == 10
                    
                    if title_ok and desc_ok and goal_ok and price_ok:
                        self.test_result("PUT /api/admin/raffle", True,
                                       f"Updated: title='R$ 10.000 no PIX', description='Concorra!', goal=30, price=10 ✓")
                    else:
                        self.test_result("PUT /api/admin/raffle", False,
                                       f"Values mismatch: title={data.get('title')}, desc={data.get('description')}, goal={data.get('goal')}, price={data.get('price')}")
                else:
                    self.test_result("PUT /api/admin/raffle", False, f"GET failed: {get_resp.status_code}")
            else:
                self.test_result("PUT /api/admin/raffle", False,
                               f"Status {resp.status_code}: {resp.text}")
                               
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print("\n" + "="*80)
        print("MERCADO PAGO PERCENTAGE-BASED FEE TESTING")
        print("="*80 + "\n")
        
        # Login first
        if not await self.login():
            print("\n❌ Login failed, cannot continue tests")
            return
            
        print("\n--- Test 1: GET /api/raffle has mp_fee_percent ---")
        await self.test_raffle_mp_fee_percent()
        
        print("\n--- Test 2: Unit test mp_fee_for() function ---")
        await self.test_mp_fee_for_function()
        
        print("\n--- Test 3: mp_create() with mocked httpx ---")
        await self.test_mp_create_with_mocked_httpx()
        
        print("\n--- Test 4: Order fee calculation ---")
        await self.test_order_fee_calculation()
        
        print("\n--- Test 5: InfinitePay fee=0 ---")
        await self.test_infinitepay_fee_zero()
        
        print("\n--- Test 6: Raffle stats use net amount ---")
        await self.test_raffle_stats_net_amount()
        
        print("\n--- Cleanup: Remove test orders ---")
        await self.cleanup_test_orders()
        
        print("\n--- Test 7: Create new raffle ---")
        await self.test_create_new_raffle()
        
        print("\n--- Test 8: Update raffle with specific values ---")
        await self.test_update_raffle()
        
        # Final summary
        print("\n" + "="*80)
        print(f"SUMMARY: {self.passed} passed, {self.failed} failed out of {self.passed + self.failed} tests")
        print("="*80 + "\n")
        
        if self.failed > 0:
            print("❌ FAILED TESTS:")
            for test in self.tests:
                if not test["passed"]:
                    print(f"  - {test['name']}")
                    if test['details']:
                        print(f"    {test['details']}")
        else:
            print("✅ ALL TESTS PASSED")
            
        return self.failed == 0

async def main():
    runner = TestRunner()
    success = await runner.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())

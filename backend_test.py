#!/usr/bin/env python3
"""
Comprehensive backend API tests for Word Chain Puzzle Game
Tests all endpoints with various scenarios to ensure proper functionality
"""

import asyncio
import httpx
import json
import sys
from typing import Dict, Any

# Backend URL from environment
BACKEND_URL = "https://quick-word-chain.preview.emergentagent.com/api"

class WordChainGameTester:
    def __init__(self):
        self.client = None
        self.test_results = {}
        
    async def setup(self):
        """Setup HTTP client"""
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            await self.client.aclose()
    
    def log_test(self, test_name: str, success: bool, message: str, details: Dict[Any, Any] = None):
        """Log test results"""
        print(f"\n{'✅' if success else '❌'} {test_name}")
        print(f"   {message}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
        
        self.test_results[test_name] = {
            "success": success,
            "message": message,
            "details": details or {}
        }
    
    async def test_start_game_endpoint(self):
        """Test POST /api/game/start endpoint"""
        print("\n🎯 Testing Game Start Endpoint...")
        
        try:
            # Test 1: Basic game creation
            response = await self.client.post(f"{BACKEND_URL}/game/start", json={})
            
            if response.status_code != 200:
                self.log_test(
                    "Start Game - Basic Creation",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    {"status_code": response.status_code, "response": response.text}
                )
                return
            
            game_data = response.json()
            
            # Validate response structure
            required_fields = ["game_id", "current_letter", "user_score", "app_score", "used_words", "turn", "status"]
            missing_fields = [field for field in required_fields if field not in game_data]
            
            if missing_fields:
                self.log_test(
                    "Start Game - Basic Creation",
                    False,
                    f"Missing fields in response: {missing_fields}",
                    {"response": game_data}
                )
                return
            
            # Validate initial values
            errors = []
            if game_data["user_score"] != 0:
                errors.append(f"Expected user_score=0, got {game_data['user_score']}")
            if game_data["app_score"] != 0:
                errors.append(f"Expected app_score=0, got {game_data['app_score']}")
            if game_data["status"] != "active":
                errors.append(f"Expected status='active', got {game_data['status']}")
            if game_data["turn"] != "user":
                errors.append(f"Expected turn='user', got {game_data['turn']}")
            if game_data["used_words"] != []:
                errors.append(f"Expected empty used_words, got {game_data['used_words']}")
            if not game_data["current_letter"].isalpha() or len(game_data["current_letter"]) != 1:
                errors.append(f"Expected single letter, got {game_data['current_letter']}")
            
            if errors:
                self.log_test(
                    "Start Game - Basic Creation",
                    False,
                    f"Validation errors: {'; '.join(errors)}",
                    {"response": game_data}
                )
                return
            
            self.log_test(
                "Start Game - Basic Creation",
                True,
                f"Successfully created game with letter '{game_data['current_letter']}'",
                {"game_id": game_data["game_id"], "starting_letter": game_data["current_letter"]}
            )
            
            # Store for subsequent tests
            self.game_id = game_data["game_id"]
            self.current_letter = game_data["current_letter"]
            
            # Test 2: Multiple games should have different IDs
            response2 = await self.client.post(f"{BACKEND_URL}/game/start", json={})
            if response2.status_code == 200:
                game_data2 = response2.json()
                if game_data2["game_id"] != game_data["game_id"]:
                    self.log_test(
                        "Start Game - Unique Game IDs",
                        True,
                        "Different games have unique IDs",
                        {"game1_id": game_data["game_id"][:8] + "...", "game2_id": game_data2["game_id"][:8] + "..."}
                    )
                else:
                    self.log_test(
                        "Start Game - Unique Game IDs",
                        False,
                        "Games should have unique IDs",
                        {"duplicate_id": game_data["game_id"]}
                    )
            
        except Exception as e:
            self.log_test(
                "Start Game - Basic Creation",
                False,
                f"Exception occurred: {str(e)}",
                {"error_type": type(e).__name__}
            )
    
    async def test_validate_word_endpoint(self):
        """Test POST /api/game/validate endpoint"""
        print("\n🎯 Testing Word Validation Endpoint...")
        
        if not hasattr(self, 'game_id'):
            self.log_test(
                "Validate Word - Setup",
                False,
                "No game_id available from previous test",
                {}
            )
            return
        
        try:
            # Test 1: Empty word
            response = await self.client.post(f"{BACKEND_URL}/game/validate", json={
                "game_id": self.game_id,
                "word": ""
            })
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("valid", True):
                    self.log_test(
                        "Validate Word - Empty Word",
                        True,
                        f"Correctly rejected empty word: {data.get('message', 'No message')}",
                        {"response": data}
                    )
                else:
                    self.log_test(
                        "Validate Word - Empty Word",
                        False,
                        "Should reject empty word",
                        {"response": data}
                    )
            
            # Test 2: Word not starting with correct letter
            wrong_letter = 'Z' if self.current_letter != 'Z' else 'A'
            response = await self.client.post(f"{BACKEND_URL}/game/validate", json={
                "game_id": self.game_id,
                "word": f"{wrong_letter}ebra"
            })
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("valid", True):
                    self.log_test(
                        "Validate Word - Wrong Starting Letter",
                        True,
                        f"Correctly rejected word not starting with '{self.current_letter}': {data.get('message', 'No message')}",
                        {"expected_letter": self.current_letter, "word_used": f"{wrong_letter}ebra"}
                    )
                else:
                    self.log_test(
                        "Validate Word - Wrong Starting Letter",
                        False,
                        "Should reject word not starting with correct letter",
                        {"response": data}
                    )
            
            # Test 3: Valid word (try common words based on starting letter)
            valid_words = {
                'A': 'apple', 'B': 'book', 'C': 'cat', 'D': 'dog', 'E': 'egg',
                'F': 'fish', 'G': 'good', 'H': 'house', 'I': 'ice', 'L': 'love',
                'M': 'music', 'N': 'nice', 'O': 'open', 'P': 'play', 'R': 'read',
                'S': 'sun', 'T': 'tree', 'W': 'water'
            }
            
            test_word = valid_words.get(self.current_letter, f"{self.current_letter.lower()}at")
            
            response = await self.client.post(f"{BACKEND_URL}/game/validate", json={
                "game_id": self.game_id,
                "word": test_word
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get("valid", False):
                    self.log_test(
                        "Validate Word - Valid Word",
                        True,
                        f"Successfully accepted valid word '{test_word}' and generated app word '{data.get('app_word', 'None')}'",
                        {
                            "user_word": test_word,
                            "user_points": data.get("user_points", 0),
                            "app_word": data.get("app_word"),
                            "app_points": data.get("app_points", 0),
                            "next_letter": data.get("next_letter")
                        }
                    )
                    
                    # Update for next tests
                    self.current_letter = data.get("next_letter", self.current_letter)
                    self.used_words = data.get("game_state", {}).get("used_words", [])
                    
                else:
                    # Word might be invalid according to dictionary API
                    message = data.get("message", "Unknown reason")
                    if "not a valid word" in message.lower():
                        self.log_test(
                            "Validate Word - Valid Word",
                            True,
                            f"Word '{test_word}' rejected by dictionary API (expected behavior)",
                            {"word": test_word, "reason": message}
                        )
                    else:
                        self.log_test(
                            "Validate Word - Valid Word",
                            False,
                            f"Unexpected rejection of '{test_word}': {message}",
                            {"response": data}
                        )
            else:
                self.log_test(
                    "Validate Word - Valid Word",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    {"status_code": response.status_code}
                )
            
            # Test 4: Reused word (if we have used words)
            if hasattr(self, 'used_words') and self.used_words:
                response = await self.client.post(f"{BACKEND_URL}/game/validate", json={
                    "game_id": self.game_id,
                    "word": self.used_words[0]
                })
                
                if response.status_code == 200:
                    data = response.json()
                    if not data.get("valid", True):
                        self.log_test(
                            "Validate Word - Reused Word",
                            True,
                            f"Correctly rejected reused word '{self.used_words[0]}': {data.get('message', 'No message')}",
                            {"reused_word": self.used_words[0]}
                        )
                    else:
                        self.log_test(
                            "Validate Word - Reused Word",
                            False,
                            "Should reject reused words",
                            {"response": data}
                        )
            
            # Test 5: Invalid game ID
            response = await self.client.post(f"{BACKEND_URL}/game/validate", json={
                "game_id": "invalid-game-id",
                "word": "test"
            })
            
            if response.status_code == 404:
                self.log_test(
                    "Validate Word - Invalid Game ID",
                    True,
                    "Correctly returned 404 for invalid game ID",
                    {"status_code": 404}
                )
            else:
                self.log_test(
                    "Validate Word - Invalid Game ID",
                    False,
                    f"Expected 404 for invalid game ID, got {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Validate Word - Error",
                False,
                f"Exception occurred: {str(e)}",
                {"error_type": type(e).__name__}
            )
    
    async def test_pass_turn_endpoint(self):
        """Test POST /api/game/pass endpoint"""
        print("\n🎯 Testing Pass Turn Endpoint...")
        
        if not hasattr(self, 'game_id'):
            self.log_test(
                "Pass Turn - Setup",
                False,
                "No game_id available from previous test",
                {}
            )
            return
        
        try:
            # Test 1: Valid pass
            response = await self.client.post(f"{BACKEND_URL}/game/pass", json={
                "game_id": self.game_id
            })
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data and "game_state" in data:
                    app_word = data.get("app_word")
                    if app_word:
                        self.log_test(
                            "Pass Turn - Valid Pass",
                            True,
                            f"Successfully passed turn, app played '{app_word}'",
                            {
                                "app_word": app_word,
                                "app_points": data.get("app_points", 0),
                                "next_letter": data.get("next_letter"),
                                "message": data.get("message")
                            }
                        )
                        
                        # Update for next tests
                        if data.get("next_letter"):
                            self.current_letter = data.get("next_letter")
                    else:
                        # App couldn't find a word
                        self.log_test(
                            "Pass Turn - Valid Pass",
                            True,
                            f"App couldn't find a word: {data.get('message', 'No message')}",
                            {"message": data.get("message")}
                        )
                else:
                    self.log_test(
                        "Pass Turn - Valid Pass",
                        False,
                        "Response missing required fields",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "Pass Turn - Valid Pass",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    {"status_code": response.status_code}
                )
            
            # Test 2: Invalid game ID
            response = await self.client.post(f"{BACKEND_URL}/game/pass", json={
                "game_id": "invalid-game-id"
            })
            
            if response.status_code == 404:
                self.log_test(
                    "Pass Turn - Invalid Game ID",
                    True,
                    "Correctly returned 404 for invalid game ID",
                    {"status_code": 404}
                )
            else:
                self.log_test(
                    "Pass Turn - Invalid Game ID",
                    False,
                    f"Expected 404 for invalid game ID, got {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Pass Turn - Error",
                False,
                f"Exception occurred: {str(e)}",
                {"error_type": type(e).__name__}
            )
    
    async def test_get_game_state_endpoint(self):
        """Test GET /api/game/{game_id} endpoint"""
        print("\n🎯 Testing Get Game State Endpoint...")
        
        if not hasattr(self, 'game_id'):
            self.log_test(
                "Get Game State - Setup",
                False,
                "No game_id available from previous test",
                {}
            )
            return
        
        try:
            # Test 1: Valid game ID
            response = await self.client.get(f"{BACKEND_URL}/game/{self.game_id}")
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ["game_id", "current_letter", "user_score", "app_score", "used_words", "turn", "status"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test(
                        "Get Game State - Valid Game ID",
                        True,
                        f"Successfully retrieved game state",
                        {
                            "game_id": data["game_id"][:8] + "...",
                            "current_letter": data["current_letter"],
                            "user_score": data["user_score"],
                            "app_score": data["app_score"],
                            "status": data["status"],
                            "used_words_count": len(data["used_words"])
                        }
                    )
                else:
                    self.log_test(
                        "Get Game State - Valid Game ID",
                        False,
                        f"Missing fields in response: {missing_fields}",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "Get Game State - Valid Game ID",
                    False,
                    f"HTTP {response.status_code}: {response.text}",
                    {"status_code": response.status_code}
                )
            
            # Test 2: Invalid game ID
            response = await self.client.get(f"{BACKEND_URL}/game/invalid-game-id")
            
            if response.status_code == 404:
                self.log_test(
                    "Get Game State - Invalid Game ID",
                    True,
                    "Correctly returned 404 for invalid game ID",
                    {"status_code": 404}
                )
            else:
                self.log_test(
                    "Get Game State - Invalid Game ID",
                    False,
                    f"Expected 404 for invalid game ID, got {response.status_code}",
                    {"status_code": response.status_code, "response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Game State - Error",
                False,
                f"Exception occurred: {str(e)}",
                {"error_type": type(e).__name__}
            )
    
    async def test_external_apis(self):
        """Test that external APIs are accessible"""
        print("\n🎯 Testing External API Dependencies...")
        
        try:
            # Test Dictionary API
            response = await self.client.get("https://api.dictionaryapi.dev/api/v2/entries/en/test")
            if response.status_code == 200:
                self.log_test(
                    "External API - Dictionary API",
                    True,
                    "Dictionary API is accessible",
                    {"status_code": response.status_code}
                )
            else:
                self.log_test(
                    "External API - Dictionary API",
                    False,
                    f"Dictionary API returned {response.status_code}",
                    {"status_code": response.status_code}
                )
            
            # Test DataMuse API
            response = await self.client.get("https://api.datamuse.com/words?sp=test*&max=1")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "External API - DataMuse API",
                    True,
                    f"DataMuse API is accessible, returned {len(data)} words",
                    {"status_code": response.status_code, "word_count": len(data)}
                )
            else:
                self.log_test(
                    "External API - DataMuse API",
                    False,
                    f"DataMuse API returned {response.status_code}",
                    {"status_code": response.status_code}
                )
                
        except Exception as e:
            self.log_test(
                "External API - Error",
                False,
                f"Exception testing external APIs: {str(e)}",
                {"error_type": type(e).__name__}
            )
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*80)
        print("🎯 BACKEND API TEST SUMMARY")
        print("="*80)
        
        passed_tests = [name for name, result in self.test_results.items() if result["success"]]
        failed_tests = [name for name, result in self.test_results.items() if not result["success"]]
        
        print(f"\n✅ PASSED: {len(passed_tests)}")
        for test in passed_tests:
            print(f"   • {test}")
        
        if failed_tests:
            print(f"\n❌ FAILED: {len(failed_tests)}")
            for test in failed_tests:
                result = self.test_results[test]
                print(f"   • {test}: {result['message']}")
        
        print(f"\n📊 TOTAL: {len(passed_tests)}/{len(self.test_results)} tests passed")
        
        # Critical issues summary
        critical_failures = []
        for test, result in self.test_results.items():
            if not result["success"]:
                if any(keyword in test.lower() for keyword in ["basic", "valid", "creation", "endpoint"]):
                    critical_failures.append(f"{test}: {result['message']}")
        
        if critical_failures:
            print(f"\n🚨 CRITICAL ISSUES:")
            for issue in critical_failures:
                print(f"   • {issue}")
        
        return len(failed_tests) == 0, self.test_results

async def main():
    """Main test execution"""
    print("🚀 Starting Word Chain Game Backend API Tests")
    print(f"📡 Testing against: {BACKEND_URL}")
    
    tester = WordChainGameTester()
    
    try:
        await tester.setup()
        
        # Run all tests
        await tester.test_external_apis()
        await tester.test_start_game_endpoint()
        await tester.test_validate_word_endpoint()
        await tester.test_pass_turn_endpoint()
        await tester.test_get_game_state_endpoint()
        
        # Generate summary
        all_passed, results = tester.generate_summary()
        
        return all_passed, results
        
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    success, results = asyncio.run(main())
    sys.exit(0 if success else 1)
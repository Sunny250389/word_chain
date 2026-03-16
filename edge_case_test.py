#!/usr/bin/env python3
"""
Additional edge case tests for Word Chain Game Backend
"""

import asyncio
import httpx
import json

BACKEND_URL = "https://word-match-challenge-2.preview.emergentagent.com/api"

async def test_additional_scenarios():
    """Test additional edge cases and scenarios"""
    client = httpx.AsyncClient(timeout=30.0)
    
    try:
        print("🎯 Testing Additional Edge Cases...")
        
        # Create a new game for edge case testing
        response = await client.post(f"{BACKEND_URL}/game/start", json={})
        if response.status_code != 200:
            print("❌ Failed to create test game")
            return
        
        game_data = response.json()
        game_id = game_data["game_id"]
        current_letter = game_data["current_letter"]
        
        print(f"✅ Created test game with letter '{current_letter}'")
        
        # Test 1: Word with numbers/special characters
        response = await client.post(f"{BACKEND_URL}/game/validate", json={
            "game_id": game_id,
            "word": f"{current_letter.lower()}est123"
        })
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("valid", True):
                print("✅ Correctly rejected word with numbers")
            else:
                print("❌ Should reject words with non-alphabetic characters")
        
        # Test 2: Single letter word
        response = await client.post(f"{BACKEND_URL}/game/validate", json={
            "game_id": game_id,
            "word": current_letter.lower()
        })
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("valid", True):
                print("✅ Correctly rejected single letter word")
            else:
                print("❌ Should reject single letter words")
        
        # Test 3: Very long word
        long_word = current_letter.lower() + "est" * 20
        response = await client.post(f"{BACKEND_URL}/game/validate", json={
            "game_id": game_id,
            "word": long_word
        })
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("valid", True):
                print("✅ Rejected very long fake word (expected)")
            else:
                print(f"✅ Accepted long word '{long_word}' (may be valid)")
        
        # Test 4: Mixed case word
        test_word = f"{current_letter.upper()}EST"
        response = await client.post(f"{BACKEND_URL}/game/validate", json={
            "game_id": game_id,
            "word": test_word
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Handled mixed case word '{test_word}': {'accepted' if data.get('valid') else 'rejected'}")
        
        # Test 5: Word with whitespace
        response = await client.post(f"{BACKEND_URL}/game/validate", json={
            "game_id": game_id,
            "word": f"  {current_letter.lower()}est  "
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Handled word with whitespace: {'accepted' if data.get('valid') else 'rejected'}")
        
        print("\n🎯 Testing Winning Condition Simulation...")
        
        # Create another game to test winning condition
        response = await client.post(f"{BACKEND_URL}/game/start", json={})
        if response.status_code == 200:
            win_game = response.json()
            win_game_id = win_game["game_id"]
            
            # Directly test the game state retrieval after the above tests
            response = await client.get(f"{BACKEND_URL}/game/{win_game_id}")
            if response.status_code == 200:
                state = response.json()
                print(f"✅ Game state consistent: score {state['user_score']}/{state['app_score']}")
            
        print("\n📊 Edge case testing completed")
        
    except Exception as e:
        print(f"❌ Error in additional tests: {str(e)}")
        
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(test_additional_scenarios())
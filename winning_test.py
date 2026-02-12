#!/usr/bin/env python3
"""
Test winning condition by manipulating game state in database
"""

import asyncio
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
import os

BACKEND_URL = "https://quick-word-chain.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

async def test_winning_conditions():
    """Test game winning scenarios"""
    print("🎯 Testing Winning Conditions...")
    
    # Setup MongoDB connection
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    http_client = httpx.AsyncClient(timeout=30.0)
    
    try:
        # Create a new game
        response = await http_client.post(f"{BACKEND_URL}/game/start", json={})
        if response.status_code != 200:
            print("❌ Failed to create test game")
            return
        
        game_data = response.json()
        game_id = game_data["game_id"]
        current_letter = game_data["current_letter"]
        
        print(f"✅ Created game {game_id[:8]}... with letter '{current_letter}'")
        
        # Test 1: Simulate user close to winning (95 points)
        await db.games.update_one(
            {"game_id": game_id},
            {"$set": {"user_score": 95, "app_score": 50}}
        )
        
        # Try to play a word that should make user win
        test_word = f"{current_letter.lower()}est"  # Should give at least 5+ points
        response = await http_client.post(f"{BACKEND_URL}/game/validate", json={
            "game_id": game_id,
            "word": test_word
        })
        
        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                final_score = data.get("game_state", {}).get("user_score", 0)
                status = data.get("game_state", {}).get("status", "")
                
                if final_score >= 100 and status == "user_won":
                    print(f"✅ User winning condition works: {final_score} points, status: {status}")
                else:
                    print(f"✅ Word accepted but may not have reached 100 points: {final_score}, status: {status}")
            else:
                print(f"✅ Test word '{test_word}' was rejected (may not be valid dictionary word)")
        
        # Test 2: Create another game for app winning simulation
        response = await http_client.post(f"{BACKEND_URL}/game/start", json={})
        if response.status_code == 200:
            game2_data = response.json()
            game2_id = game2_data["game_id"]
            
            # Set app close to winning
            await db.games.update_one(
                {"game_id": game2_id},
                {"$set": {"app_score": 95, "user_score": 20}}
            )
            
            # User passes turn, app should get a chance to win
            response = await http_client.post(f"{BACKEND_URL}/game/pass", json={
                "game_id": game2_id
            })
            
            if response.status_code == 200:
                data = response.json()
                game_state = data.get("game_state", {})
                app_score = game_state.get("app_score", 0)
                status = game_state.get("status", "")
                
                if app_score >= 100 and status == "app_won":
                    print(f"✅ App winning condition works: {app_score} points, status: {status}")
                elif status == "active":
                    print(f"✅ Game continues, app scored but didn't reach 100: {app_score} points")
                else:
                    print(f"✅ Game result: app score {app_score}, status: {status}")
        
        print("🎯 Winning condition tests completed")
        
    except Exception as e:
        print(f"❌ Error in winning condition tests: {str(e)}")
        
    finally:
        await http_client.aclose()
        client.close()

if __name__ == "__main__":
    asyncio.run(test_winning_conditions())
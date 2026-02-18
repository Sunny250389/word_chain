from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import httpx
import random
import string

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class GameStart(BaseModel):
    time_limit: int = 30  # Allow user to set timer

class GameState(BaseModel):
    game_id: str
    current_letter: str
    user_score: int
    app_score: int
    used_words: List[str]
    turn: str  # "user" or "app"
    status: str  # "active", "user_won", "app_won"
    time_limit: int = 30
    last_word: Optional[str] = None

class ValidateWord(BaseModel):
    game_id: str
    word: str

class PassTurn(BaseModel):
    game_id: str

class UpdateStats(BaseModel):
    user_id: str
    won: bool

class UserStats(BaseModel):
    user_id: str
    total_games: int
    wins: int
    losses: int
    win_rate: float

class ValidateResponse(BaseModel):
    valid: bool
    message: str
    user_points: int
    app_word: Optional[str]
    app_points: int
    next_letter: str
    game_state: GameState

# Helper functions
async def validate_word_with_api(word: str) -> bool:
    """Validate word using Free Dictionary API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}")
            return response.status_code == 200
    except:
        return False

async def get_word_frequency(word: str) -> int:
    """Get word frequency score using DataMuse API"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://api.datamuse.com/words?sp={word.lower()}&md=f&max=1")
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'tags' in data[0]:
                    for tag in data[0]['tags']:
                        if tag.startswith('f:'):
                            freq = float(tag.split(':')[1])
                            # Convert frequency to points (lower frequency = more points)
                            # Frequency ranges from 0 to ~100, invert it
                            points = max(1, int(10 - (freq / 10)))
                            return points
    except:
        pass
    # Default scoring based on word length if API fails
    return max(1, len(word) // 2)

async def generate_app_word(letter: str, used_words: List[str]) -> Optional[str]:
    """Generate a word starting with the given letter using DataMuse API"""
    try:
        async with httpx.AsyncClient() as client:
            # Get words starting with the letter, sorted by frequency
            response = await client.get(f"https://api.datamuse.com/words?sp={letter.lower()}*&md=f&max=100")
            if response.status_code == 200:
                words = response.json()
                # Filter out used words and words less than 3 letters
                available_words = [
                    w['word'] for w in words 
                    if w['word'].lower() not in [uw.lower() for uw in used_words] 
                    and len(w['word']) >= 3
                    and w['word'].isalpha()
                ]
                if available_words:
                    # Pick a random word from top 20 to add variety
                    return random.choice(available_words[:min(20, len(available_words))])
    except:
        pass
    return None

def calculate_points(word: str, frequency_score: int) -> int:
    """Calculate points based on word length, frequency, and difficulty - max 10 points"""
    # Length factor (1-4 points): longer words get more points
    length = len(word)
    if length <= 3:
        length_points = 1
    elif length <= 5:
        length_points = 2
    elif length <= 7:
        length_points = 3
    else:
        length_points = 4
    
    # Frequency/rarity factor (1-4 points): rarer words get more points
    rarity_points = min(4, frequency_score)
    
    # Difficulty factor (1-2 points): words with uncommon letters get bonus
    uncommon_letters = set('qxzjkvwyfhbp')
    difficulty_points = min(2, len([c for c in word.lower() if c in uncommon_letters]))
    
    # Total points capped at 10
    total = min(10, length_points + rarity_points + difficulty_points)
    return max(1, total)  # Minimum 1 point

# Routes
@api_router.post("/game/start", response_model=GameState)
async def start_game(game_start: GameStart):
    """Start a new game"""
    game_id = str(uuid.uuid4())
    
    # Pick a random starting letter (avoid difficult letters)
    common_letters = list("ABCDEFGHILMNOPRSTW")
    starting_letter = random.choice(common_letters)
    
    game_state = {
        "game_id": game_id,
        "current_letter": starting_letter,
        "user_score": 0,
        "app_score": 0,
        "used_words": [],
        "turn": "user",
        "status": "active",
        "time_limit": game_start.time_limit,  # Use user-selected timer
        "last_word": None,
        "created_at": datetime.utcnow()
    }
    
    await db.games.insert_one(game_state)
    return GameState(**game_state)

@api_router.post("/game/validate", response_model=ValidateResponse)
async def validate_word(validate: ValidateWord):
    """Validate user's word and generate app's response"""
    # Get game state
    game = await db.games.find_one({"game_id": validate.game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    word = validate.word.strip().lower()
    current_letter = game["current_letter"].lower()
    used_words = game["used_words"]
    
    # Validation checks
    if not word:
        return ValidateResponse(
            valid=False,
            message="The word is not Correct",
            user_points=0,
            app_word=None,
            app_points=0,
            next_letter=game["current_letter"],
            game_state=GameState(**game)
        )
    
    if not word.isalpha():
        return ValidateResponse(
            valid=False,
            message="The word is not Correct",
            user_points=0,
            app_word=None,
            app_points=0,
            next_letter=game["current_letter"],
            game_state=GameState(**game)
        )
    
    if len(word) < 2:
        return ValidateResponse(
            valid=False,
            message="The word is not Correct",
            user_points=0,
            app_word=None,
            app_points=0,
            next_letter=game["current_letter"],
            game_state=GameState(**game)
        )
    
    # Check for repeated word BEFORE checking starting letter
    # This way "Word is repeated" takes priority when applicable
    if word in [w.lower() for w in used_words]:
        return ValidateResponse(
            valid=False,
            message="Word is repeated",
            user_points=0,
            app_word=None,
            app_points=0,
            next_letter=game["current_letter"],
            game_state=GameState(**game)
        )
    
    if not word.startswith(current_letter):
        return ValidateResponse(
            valid=False,
            message="The word is not Correct",
            user_points=0,
            app_word=None,
            app_points=0,
            next_letter=game["current_letter"],
            game_state=GameState(**game)
        )
    
    # Validate with dictionary API
    is_valid = await validate_word_with_api(word)
    if not is_valid:
        return ValidateResponse(
            valid=False,
            message="The word is not Correct",
            user_points=0,
            app_word=None,
            app_points=0,
            next_letter=game["current_letter"],
            game_state=GameState(**game)
        )
    
    # Calculate user points
    freq_score = await get_word_frequency(word)
    user_points = calculate_points(word, freq_score)
    new_user_score = game["user_score"] + user_points
    
    # Add word to used words
    used_words.append(word)
    
    # Get last letter for app's turn
    last_letter = word[-1].upper()
    
    # Check if user won
    if new_user_score >= 100:
        await db.games.update_one(
            {"game_id": validate.game_id},
            {"$set": {
                "user_score": new_user_score,
                "used_words": used_words,
                "status": "user_won",
                "last_word": word
            }}
        )
        updated_game = await db.games.find_one({"game_id": validate.game_id})
        return ValidateResponse(
            valid=True,
            message="Congratulations! You won! 🎉",
            user_points=user_points,
            app_word=None,
            app_points=0,
            next_letter=last_letter,
            game_state=GameState(**updated_game)
        )
    
    # Generate app's word
    app_word = await generate_app_word(last_letter, used_words)
    
    if not app_word:
        # App can't find a word, user wins
        await db.games.update_one(
            {"game_id": validate.game_id},
            {"$set": {
                "user_score": new_user_score,
                "used_words": used_words,
                "status": "user_won",
                "current_letter": last_letter,
                "last_word": word
            }}
        )
        updated_game = await db.games.find_one({"game_id": validate.game_id})
        return ValidateResponse(
            valid=True,
            message="I couldn't find a word. You win! 🎉",
            user_points=user_points,
            app_word=None,
            app_points=0,
            next_letter=last_letter,
            game_state=GameState(**updated_game)
        )
    
    # Calculate app points
    app_freq_score = await get_word_frequency(app_word)
    app_points = calculate_points(app_word, app_freq_score)
    new_app_score = game["app_score"] + app_points
    
    # Add app word to used words
    used_words.append(app_word)
    
    # Get next letter
    next_letter = app_word[-1].upper()
    
    # Check if app won
    if new_app_score >= 100:
        await db.games.update_one(
            {"game_id": validate.game_id},
            {"$set": {
                "user_score": new_user_score,
                "app_score": new_app_score,
                "used_words": used_words,
                "status": "app_won",
                "current_letter": next_letter,
                "last_word": app_word
            }}
        )
        updated_game = await db.games.find_one({"game_id": validate.game_id})
        return ValidateResponse(
            valid=True,
            message=f"I played '{app_word}' and won! 😊",
            user_points=user_points,
            app_word=app_word,
            app_points=app_points,
            next_letter=next_letter,
            game_state=GameState(**updated_game)
        )
    
    # Continue game
    await db.games.update_one(
        {"game_id": validate.game_id},
        {"$set": {
            "user_score": new_user_score,
            "app_score": new_app_score,
            "used_words": used_words,
            "current_letter": next_letter,
            "last_word": app_word
        }}
    )
    
    updated_game = await db.games.find_one({"game_id": validate.game_id})
    return ValidateResponse(
        valid=True,
        message=f"Good word! I played '{app_word}'",
        user_points=user_points,
        app_word=app_word,
        app_points=app_points,
        next_letter=next_letter,
        game_state=GameState(**updated_game)
    )

@api_router.post("/game/pass")
async def pass_turn(pass_turn: PassTurn):
    """Handle user passing their turn"""
    game = await db.games.find_one({"game_id": pass_turn.game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    current_letter = game["current_letter"]
    used_words = game["used_words"]
    
    # Generate app's word with current letter
    app_word = await generate_app_word(current_letter, used_words)
    
    if not app_word:
        # App also can't find a word, it's a tie but user wins
        await db.games.update_one(
            {"game_id": pass_turn.game_id},
            {"$set": {"status": "user_won"}}
        )
        updated_game = await db.games.find_one({"game_id": pass_turn.game_id})
        return {
            "message": "Neither of us could find a word. You win! 🎉",
            "app_word": None,
            "game_state": GameState(**updated_game)
        }
    
    # Calculate app points
    app_freq_score = await get_word_frequency(app_word)
    app_points = calculate_points(app_word, app_freq_score)
    new_app_score = game["app_score"] + app_points
    
    # Add app word to used words
    used_words.append(app_word)
    
    # Get next letter
    next_letter = app_word[-1].upper()
    
    # Check if app won
    if new_app_score >= 100:
        await db.games.update_one(
            {"game_id": pass_turn.game_id},
            {"$set": {
                "app_score": new_app_score,
                "used_words": used_words,
                "status": "app_won",
                "current_letter": next_letter,
                "last_word": app_word
            }}
        )
        updated_game = await db.games.find_one({"game_id": pass_turn.game_id})
        return {
            "message": f"I played '{app_word}' and won! 😊",
            "app_word": app_word,
            "app_points": app_points,
            "next_letter": next_letter,
            "game_state": GameState(**updated_game)
        }
    
    # Continue game
    await db.games.update_one(
        {"game_id": pass_turn.game_id},
        {"$set": {
            "app_score": new_app_score,
            "used_words": used_words,
            "current_letter": next_letter,
            "last_word": app_word
        }}
    )
    
    updated_game = await db.games.find_one({"game_id": pass_turn.game_id})
    return {
        "message": f"You passed. I played '{app_word}'",
        "app_word": app_word,
        "app_points": app_points,
        "next_letter": next_letter,
        "game_state": GameState(**updated_game)
    }

@api_router.get("/game/{game_id}", response_model=GameState)
async def get_game_state(game_id: str):
    """Get current game state"""
    game = await db.games.find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameState(**game)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

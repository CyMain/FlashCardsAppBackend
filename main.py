import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

cyapp = FastAPI()

# Data models (The "Shape" of your data)
class UserLogin(BaseModel):
    username: str
    password: str

class CardCreate(BaseModel):
    deck_id: str
    term: str
    definition: str

class FolderCreate(BaseModel):
    name: str
    user_id: str # You'll get this from the login response

class DeckCreate(BaseModel):
    title: str
    class_id: str

# --- AUTHENTICATION ---
@cyapp.post("/test/{user_id}")
async def testorderofpriority(user_id, user: UserLogin):
    message = f"par1: {user_id}, par2:{user}"
    print(message)
    return {"message":message}

@cyapp.post("/login")
async def login(user: UserLogin):
    # The Masked Email Hack: turn "john" into "john@myapp.com"
    email = f"{user.username.lower()}@flashcards.com"
    
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": user.password
        })
        return {"access_token": response.session.access_token, "user": response.user}
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid username or password")

@cyapp.post("/signup")
async def signup(user: UserLogin):
    # Turn "gemini_user" into "gemini_user@flashcards.com"
    email = f"{user.username.lower()}@flashcards.com"
    
    try:
        # 1. Create the user in Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": user.password,
        })
        
        # 2. Add the username to your 'profiles' table 
        # (This links the Auth ID to the nickname)
        user_id = auth_response.user.id
        supabase.table("profiles").insert({
            "id": user_id, 
            "username": user.username
        }).execute()
        
        return {"message": "User created successfully", "user": auth_response.user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- DATA FETCHING ---
@cyapp.get("/dashboard/{user_id}")
async def get_dashboard(user_id: str):
    # Fetch all classes belonging to the user
    folders_resp = supabase.table("folders").select("*").eq("user_id", user_id).execute()
    return folders_resp.data

@cyapp.get("/folders/{user_id}")
async def get_user_folders(user_id: str):
    # Replaces your manual search; finds all classes for one user
    response = supabase.table("folders").select("*").eq("user_id", user_id).execute()
    return response.data

@cyapp.get("/cards/{user_id}")
async def get_user_cards(user_id: str):
    response = supabase.table("cards").select("*").eq("user_id", user_id).execute()
    return response.data

@cyapp.get("/quiz/{deck_id}")
async def get_quiz_cards(deck_id: str):
    # Fetch all cards for a specific deck to start the quiz
    response = supabase.table("cards").select("term, definition").eq("deck_id", deck_id).execute()
    
    if not response.data:
        raise HTTPException(status_code=404, detail="No cards found in this deck")
    
    return response.data

# --- DATA CREATING ---
@cyapp.post("/folders")
async def create_folder(c: FolderCreate):
    response = supabase.table("folders").insert({
        "name": c.name, 
        "user_id": c.user_id
    }).execute()
    return response.data

@cyapp.post("/decks")
async def create_deck(d: DeckCreate):
    response = supabase.table("decks").insert({
        "title": d.title, 
        "class_id": d.class_id
    }).execute()
    return response.data

@cyapp.post("/cards")
async def create_card(card: CardCreate):
    # Replaces your old add_card() input logic
    try:
        response = supabase.table("cards").insert({
            "deck_id": card.deck_id,
            "term": card.term,
            "definition": card.definition
        }).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- DATA DELETING ---
@cyapp.delete("/folders/{folder_id}")
async def delete_folder(folder_id: str):
    supabase.table("folders").delete().eq("id", folder_id).execute()
    return {"message": "Folder and all its decks deleted"}

@cyapp.delete("decks/{deck_id}")
async def delete_deck(deck_id: str):
    supabase.table("decks").delete().eq("id", deck_id).execute()
    return {"message":"Deck and all its cards deleted."}

@cyapp.delete("cards/{card_id}")
async def delete_card(card_id: str):
    supabase.table("cards").delete().eq("id", card_id).execute()
    return {"message":"Card deleted."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(cyapp, host="0.0.0.0", port=8000)
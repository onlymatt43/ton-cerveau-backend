from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from supabase import create_client, Client
from datetime import datetime
import os

# --- Initialisation ---
app = FastAPI()

# CORS pour ton app iOS ou frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Variables d'environnement ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or not OPENAI_API_KEY:
    raise RuntimeError("⚠️ Variables d'environnement manquantes sur Render.")

# --- Clients ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# --- ROUTES ---

@app.get("/")
async def root():
    return {"message": "🧠 Ton cerveau backend fonctionne parfaitement !"}


@app.post("/chat")
async def chat(request: Request):
    print(f"📡 Méthode reçue sur /chat : {request.method}")

    data = await request.json()
    user_message = data.get("user_message")

    if not user_message:
        raise HTTPException(status_code=400, detail="Message manquant")

    try:
        supabase.table("conversations").insert({
            "role": "user",
            "message": user_message,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es le cerveau numérique de Matt. Sois réfléchi, analytique et personnel."},
                {"role": "user", "content": user_message}
            ]
        )

        assistant_reply = completion.choices[0].message.content

        supabase.table("conversations").insert({
            "role": "assistant",
            "message": assistant_reply,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        return {"assistant_reply": assistant_reply}

    except Exception as e:
        print(f"Erreur /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory")
async def memory():
    try:
        response = supabase.table("conversations").select("*").order("timestamp", desc=False).execute()
        data = response.data or []
        if not data:
            return {"memory": "Mémoire vide."}
        return {"memory": data}
    except Exception as e:
        print(f"Erreur /memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/analyze")
async def analyze_memory():
    try:
        response = supabase.table("conversations").select("*").execute()
        messages = response.data or []

        if not messages:
            return {"analysis": "Il n'y a pas encore de mémoire à analyser."}

        memory_text = "\n".join([f"{m['role']}: {m['message']}" for m in messages])

        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant analytique qui fait des résumés précis et logiques."},
                {"role": "user", "content": f"Analyse et résume cette mémoire:\n{memory_text}"}
            ]
        )

        summary = completion.choices[0].message.content
        return {"analysis": summary}

    except Exception as e:
        print(f"Erreur /analyze: {e}")
        raise HTTPException(status_code=500, detail=str(e))
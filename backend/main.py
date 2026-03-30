from backend.rag import retrieve_relevant_rules
# ... (keep your existing imports and setup) ...

@app.post("/api/chat")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # 1. Save User Message
    user_msg = ChatMessage(campaign_id=1, sender_type="player", sender_name="Player 1", content=request.message)
    db.add(user_msg)
    db.commit()

    # 2. Retrieve the Character's Backstory from the SQL database
    # (Assuming we are querying for the active character. Hardcoded ID=1 for this example)
    character = db.query(Character).filter(Character.id == 1).first()
    backstory = character.backstory if character and character.backstory else "A standard adventurer."

    # 3. Retrieve relevant rules from the Vector Database
    relevant_rules = retrieve_relevant_rules(request.message)

    # 4. Construct the Augmented System Prompt
    system_prompt = f"""You are the Dungeon Master. 
    Use the following rules to resolve the player's action if applicable:
    {relevant_rules}
    
    The player's character background:
    {backstory}
    
    Keep your response to 2-3 sentences. Describe the outcome of their action."""

    # 5. Build Message History
    history = db.query(ChatMessage).order_by(ChatMessage.id.desc()).limit(10).all()
    history.reverse()
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        # Map our DB sender_type to Ollama's expected roles
        role = "assistant" if msg.sender_type == "ai_dm" else "user"
        messages.append({"role": role, "content": msg.content})

    # 6. Call Local LLM
    payload = {"model": MODEL_NAME, "messages": messages, "stream": False}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=60.0)
            response.raise_for_status()
            ai_text = response.json().get("message", {}).get("content", "DM is silent.")
        except Exception as e:
            ai_text = f"System Error: {str(e)}"

    # 7. Save AI Response
    ai_msg = ChatMessage(campaign_id=1, sender_type="ai_dm", sender_name="DM", content=ai_text)
    db.add(ai_msg)
    db.commit()

    return {"reply": ai_text}

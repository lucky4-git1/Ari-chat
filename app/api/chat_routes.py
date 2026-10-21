import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.db.database import get_db, SessionLocal
from app.db.models import User, Conversation, Message
from app.api.auth_routes import get_current_user
from app.services.ollama_service import stream_chat_completion, detect_repetition, strip_repeating_suffix, clean_response_text
from app.services.search_service import perform_web_search, format_search_context
from app.services.memory_service import get_user_memories, format_memory_context, detect_and_store_memory
from app.core.config import DEFAULT_MODEL

router = APIRouter(prefix="/api/chat", tags=["chat"])

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Chat"
    model: Optional[str] = DEFAULT_MODEL

class ConversationRename(BaseModel):
    title: str

class MessageSendRequest(BaseModel):
    content: str
    web_search: bool = False
    reasoning_mode: bool = False
    model: Optional[str] = None

@router.get("/conversations")
def get_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(
        Conversation.user_id == user.id
    ).order_by(Conversation.updated_at.desc()).all()

    return [
        {
            "id": c.id,
            "title": c.title,
            "model": c.model,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
            "message_count": len(c.messages)
        }
        for c in convs
    ]

@router.post("/conversations")
def create_conversation(req: ConversationCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = Conversation(
        user_id=user.id,
        title=req.title or "New Chat",
        model=req.model or DEFAULT_MODEL
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return {
        "id": conv.id,
        "title": conv.title,
        "model": conv.model,
        "created_at": conv.created_at.isoformat()
    }

@router.get("/conversations/{conv_id}")
def get_conversation_detail(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "reasoning": m.reasoning,
            "sources": json.loads(m.sources_json) if m.sources_json else [],
            "created_at": m.created_at.isoformat()
        }
        for m in conv.messages
    ]
    return {
        "id": conv.id,
        "title": conv.title,
        "model": conv.model,
        "created_at": conv.created_at.isoformat(),
        "messages": messages
    }

@router.patch("/conversations/{conv_id}")
def rename_conversation(conv_id: int, req: ConversationRename, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv.title = req.title.strip() or "Untitled"
    conv.updated_at = datetime.utcnow()
    db.commit()
    return {"id": conv.id, "title": conv.title}

@router.delete("/conversations/{conv_id}")
def delete_conversation(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conv)
    db.commit()
    return {"status": "deleted", "id": conv_id}

@router.post("/conversations/{conv_id}/messages")
async def send_message_stream(
    conv_id: int,
    req: MessageSendRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id,
        Conversation.user_id == user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # 1. Save user message to database
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.content.strip()
    )
    db.add(user_msg)
    
    # Auto-generate a title if this is the first message
    if len(conv.messages) == 0:
        new_title = req.content.strip()[:40]
        if len(req.content.strip()) > 40:
            new_title += "..."
        conv.title = new_title

    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user_msg)

    # 2. Automatically extract and store user facts, stack & preferences into persistent memory
    new_memories = detect_and_store_memory(db, user.id, req.content)

    # 3. Retrieve long-term memories
    memories = get_user_memories(db, user.id)
    memory_prompt_block = format_memory_context(memories)

    # 4. Perform Web Search if requested
    search_sources = []
    search_prompt_block = ""
    if req.web_search:
        search_sources = perform_web_search(req.content.strip())
        search_prompt_block = format_search_context(search_sources)

    # 5. Build full message context for Ollama
    system_prompt = (
        "You are Ari, a thoughtful, warm, and exceptionally capable personal AI companion developed by Ari AI.\n\n"
        "Guidelines:\n"
        "- Respond directly, clearly, and conversationally with genuine warmth. Keep small talk and greetings concise (1-2 sentences).\n"
        "- Formatting & Style: Format all general responses, explanations, recipes, and guides using clean, standard Markdown (use ## or ### for headings, - or * for bullet points, 1., 2. for numbered steps, and **bold** for emphasis).\n"
        "- NEVER output raw HTML tags (such as <div>, <h3>, <ol>, <li>, <p>) in general answers or recipes. Only output HTML if the user explicitly asks for HTML code.\n"
        "- Code Blocks: Use fenced code blocks (e.g. ```python ... ```, ```html ... ```, ```javascript ... ```) ONLY when writing actual computer programming code.\n"
        "- When sharing recipes or guides, always format with clear Ingredients (- item) and numbered Steps (1. step).\n"
        "- Provide ONE direct response and stop immediately. Never simulate follow-up user questions, user replies, parenthetical notes, or multi-turn dialogues.\n"
        "- Formatting Integrity: Never generate raw website metadata, scraping artifacts, or '[View Answer]' links.\n"
        "- Safety: If asked for dangerous, harmful, or illegal instructions, refuse politely and offer safe educational context."
    )
    if memory_prompt_block:
        system_prompt += f"\n\n{memory_prompt_block}"
    if search_prompt_block:
        system_prompt += f"\n\n{search_prompt_block}"

    ollama_messages = [{"role": "system", "content": system_prompt}]
    
    # Append conversation history (up to last 10 messages for rich multi-turn context)
    prior_messages = conv.messages[-10:]
    for m in prior_messages:
        # Sanitize prior assistant messages so historical scrape artifacts never poison future turns
        content = clean_response_text(m.content) if m.role == "assistant" else m.content
        if content:
            ollama_messages.append({"role": m.role, "content": content})

    chosen_model = req.model or conv.model or DEFAULT_MODEL

    # High capacity token budget (2048 tokens) to allow full code files, detailed guides, and complete answers
    max_tokens_limit = 2048

    async def sse_event_generator():
        # Notify client if long-term memory was learned automatically
        if new_memories:
            for mem in new_memories:
                yield f"data: {json.dumps({'type': 'memory_updated', 'memory': mem})}\n\n"

        # Send web sources metadata event if available
        if search_sources:
            yield f"data: {json.dumps({'type': 'sources', 'sources': search_sources})}\n\n"

        full_assistant_reply = []
        try:
            async for chunk_str in stream_chat_completion(
                messages=ollama_messages,
                model=chosen_model,
                reasoning_mode=req.reasoning_mode,
                max_tokens=max_tokens_limit
            ):
                try:
                    data = json.loads(chunk_str.strip())
                    if "error" in data:
                        yield f"data: {json.dumps({'type': 'error', 'error': data['error']})}\n\n"
                        break
                    
                    token = data.get("token", "")
                    done = data.get("done", False)

                    if token:
                        full_assistant_reply.append(token)
                        yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

                    if done:
                        break
                except Exception:
                    continue
        except (asyncio.CancelledError, GeneratorExit):
            # Handled when user clicks Stop button or client disconnects
            pass

        # Post-process full reply to clean metadata, repetitions, and stop tokens
        raw_text = "".join(full_assistant_reply)
        complete_text = clean_response_text(raw_text)

        reasoning_content = None
        final_answer = complete_text

        if "<thought>" in complete_text and "</thought>" in complete_text:
            parts = complete_text.split("</thought>")
            reasoning_content = parts[0].replace("<thought>", "").strip()
            final_answer = clean_response_text(parts[1])

        # Save assistant message in DB using a new session if any content was produced
        if final_answer.strip():
            save_db = SessionLocal()
            try:
                asst_msg = Message(
                    conversation_id=conv_id,
                    role="assistant",
                    content=final_answer,
                    reasoning=reasoning_content,
                    sources_json=json.dumps(search_sources) if search_sources else None
                )
                save_db.add(asst_msg)
                save_conv = save_db.query(Conversation).filter(Conversation.id == conv_id).first()
                if save_conv:
                    save_conv.updated_at = datetime.utcnow()
                save_db.commit()
                save_db.refresh(asst_msg)
                
                try:
                    yield f"data: {json.dumps({'type': 'done', 'clean_content': final_answer, 'message_id': asst_msg.id})}\n\n"
                except (asyncio.CancelledError, GeneratorExit):
                    pass
            finally:
                save_db.close()

    return StreamingResponse(sse_event_generator(), media_type="text/event-stream")

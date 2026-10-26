import json
import os
import io
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import httpx

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
    persona: Optional[str] = "general"
    file_context: Optional[dict] = None
    cloud_config: Optional[dict] = None

@router.post("/upload-file")
async def upload_file_context(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """Safely extracts text from uploaded PDF or code/text files for conversational RAG."""
    filename = file.filename or "uploaded_file"
    ext = os.path.splitext(filename)[1].lower()
    content_bytes = await file.read()
    extracted_text = ""

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages[:20]):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- Page {i+1} ---\n{text}")
            extracted_text = "\n\n".join(pages_text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")
    else:
        try:
            extracted_text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            extracted_text = content_bytes.decode("latin-1", errors="replace")

    # Guard against local context overflow (limit to 12,000 characters)
    char_limit = 12000
    truncated = False
    if len(extracted_text) > char_limit:
        extracted_text = extracted_text[:char_limit] + "\n\n... [Content truncated for local context budget] ..."
        truncated = True

    return {
        "filename": filename,
        "ext": ext,
        "size": len(content_bytes),
        "char_count": len(extracted_text),
        "truncated": truncated,
        "content": extracted_text
    }

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

async def stream_cloud_chat(messages: list, base_url: str, api_key: str, model: str):
    """Streams chat completions from standard OpenAI-compatible cloud providers (OpenRouter, DeepSeek, OpenAI, Groq)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "stream": True}
    target_url = f"{base_url.rstrip('/')}/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", target_url, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    err_bytes = await resp.aread()
                    yield json.dumps({"error": f"Cloud API error ({resp.status_code}): {err_bytes.decode('utf-8', errors='ignore')}"})
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            yield json.dumps({"done": True})
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield json.dumps({"token": content, "done": False})
                        except Exception:
                            continue
    except Exception as e:
        yield json.dumps({"error": f"Cloud connection failed: {str(e)}"})

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

    # Persona specialization
    persona_prompts = {
        "coder": (
            "Specialized Role: Elite Software Architect & Senior Systems Engineer.\n"
            "- Implement strict, self-contained, production-ready code with complete type annotations and defensive error handling.\n"
            "- Avoid conversational filler; begin directly with the code block or architecture overview."
        ),
        "writer": (
            "Specialized Role: Master Narrative Stylist & Copywriter.\n"
            "- Emphasize lyrical human rhythm, evocative sensory details, emotional resonance, and persuasive rhetoric.\n"
            "- Avoid corporate clichés and AI jargon."
        ),
        "researcher": (
            "Specialized Role: Principal Academic Researcher & Data Scientist.\n"
            "- Provide formal, empirical, and analytically rigorous explanations with theoretical context and balanced trade-offs."
        ),
        "executive": (
            "Specialized Role: Executive Strategy Advisor & Chief Operating Officer.\n"
            "- Deliver high-level, bulleted executive briefs with clear ROI, operational risk trade-offs, and decisive action items."
        ),
    }

    # 5. Build full message context with Claude/GPT-grade reasoning & presentation directives
    system_prompt = (
        "You are Ari, an exceptionally capable, thoughtful, and articulate AI companion created by Ari AI.\n"
        "Your responses embody the highest standard of intellectual clarity, coherence, and visual elegance, on par with frontier models like Claude 3.5 Sonnet and GPT-4o.\n\n"
        "Core Editorial & Presentation Standards:\n"
        "1. Immediate, Direct Insight: Dive straight into the core answer or insight. Avoid conversational throat-clearing, filler greetings, or sycophancy (never start with 'Sure! I would be delighted to help with that!').\n"
        "2. Structural Hierarchy: Organize substantial responses using clean, semantic Markdown (## for main themes, ### for sub-topics). Keep paragraphs tightly focused, balanced, and readable (2-4 sentences each).\n"
        "3. Concept Highlighting: When enumerating key points, concepts, or principles, use bold lead-ins for visual scanability (e.g. '- **Core Principle:** In-depth explanation...').\n"
        "4. Comparative Tables: Whenever evaluating alternatives, trade-offs, pros & cons, or technical specifications, format them directly in clean Markdown tables (never enclose tables inside ```markdown code blocks).\n"
        "5. Technical Rigor & Code: When generating code, provide complete, production-grade, self-contained solutions inside fenced code blocks with language identifiers (e.g. ```python, ```typescript, ```bash). Include clear inline comments explaining non-trivial logic, and never use placeholders like '// implement rest'.\n"
        "6. Step-by-Step Guides & Recipes: Present prerequisites, ingredients, or inputs first in clean bullet lists with exact measurements, followed by chronological numbered steps (1., 2.) with bold action verbs.\n"
        "7. Mathematics & Formulations: Render all mathematical equations using standard LaTeX ($E = mc^2$ for inline, and $$...$$ for centered display equations).\n"
        "8. Termination Integrity: Provide ONE complete, authoritative response and stop immediately. Never simulate imaginary user questions, follow-up dialogue, or parenthetical reflections.\n"
        "9. Pure Markdown: NEVER output raw HTML tags (like <div>, <h3>, <ol>, <li>, <p>) in general prose. Use standard Markdown syntax.\n"
        "10. Safety & Ethics: If asked for harmful, dangerous, or illegal instructions, decline politely with a calm, neutral tone and offer safe educational alternatives."
    )

    if req.persona and req.persona in persona_prompts:
        system_prompt = f"{persona_prompts[req.persona]}\n\n{system_prompt}"

    if memory_prompt_block:
        system_prompt += f"\n\n{memory_prompt_block}"
    if search_prompt_block:
        system_prompt += f"\n\n{search_prompt_block}"

    ollama_messages = [{"role": "system", "content": system_prompt}]
    
    # Append conversation history (up to last 10 messages for rich multi-turn context)
    prior_messages = conv.messages[-10:]
    for m in prior_messages:
        content = clean_response_text(m.content) if m.role == "assistant" else m.content
        if content:
            ollama_messages.append({"role": m.role, "content": content})

    # Append current turn with file context if attached
    current_content = req.content.strip()
    if req.file_context and req.file_context.get("content"):
        fname = req.file_context.get("filename", "Uploaded File")
        ftext = req.file_context.get("content", "")
        file_header = f"--- Attached Document: {fname} ---\n{ftext}\n--- End of Attached Document ---\n\n"
        current_content = f"{file_header}{req.content.strip()}"
    ollama_messages.append({"role": "user", "content": current_content})

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
        is_cloud = bool(req.cloud_config and req.cloud_config.get("api_key") and req.cloud_config.get("base_url"))
        stream_iter = (
            stream_cloud_chat(
                messages=ollama_messages,
                base_url=req.cloud_config["base_url"],
                api_key=req.cloud_config["api_key"],
                model=req.cloud_config.get("model") or req.cloud_config.get("model_name") or "gpt-4o"
            )
            if is_cloud
            else stream_chat_completion(
                messages=ollama_messages,
                model=chosen_model,
                reasoning_mode=req.reasoning_mode,
                max_tokens=max_tokens_limit
            )
        )

        try:
            async for chunk_str in stream_iter:
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

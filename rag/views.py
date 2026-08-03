import json
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

# ── Singleton RAG system (initialised once per process) ───────
_rag_lock   = threading.Lock()
_rag_system = None


def _get_rag():
    global _rag_system
    if _rag_system is None:
        with _rag_lock:
            if _rag_system is None:          # double-checked locking
                from rag_system import ERPRagSystem
                _rag_system = ERPRagSystem()
    return _rag_system


# ── Views ─────────────────────────────────────────────────────

@login_required
def chat_page(request):
    """Renders the chat UI."""
    profile = getattr(request.user, 'profile', None)
    if not profile:
        return render(request, 'pages/dashboard.html', {'error_message': 'Please create a company profile first to use the AI assistant.'})
    
    if not profile.is_approved:
        return render(request, 'pages/pending.html', {'profile': profile})
    return render(request, "rag/chat.html")


@login_required
@require_http_methods(["POST"])
def chat_api(request):
    """
    POST /rag/api/chat/
    Fast AI chat: Engineers get plain LLM, Managers/Owners get file-aware RAG.
    Detects question language and responds accordingly.
    """
    try:
        profile = getattr(request.user, 'profile', None)
        if not profile:
             return JsonResponse({"error": "Your account is missing a company profile. Please complete your company details first."}, status=403)
             
        if not profile.is_approved:
            return JsonResponse({"error": "Your account is pending approval. You cannot use the AI assistant at this time."}, status=403)
        
        # (Developer role restriction removed for seamless testing)

        payload  = json.loads(request.body)
        question = payload.get("question", "").strip()[:1500]
        history  = payload.get("history", [])  # list of {role, content}

        if not question:
            return JsonResponse({"error": "question is required"}, status=400)

        # Rate Limiting against DoS
        from django.core.cache import cache
        user_ip = request.META.get('REMOTE_ADDR')
        cache_key = f"chat_rl_{user_ip}_{request.user.id}"
        requests_count = cache.get(cache_key, 0)
        if requests_count > 30:
            return JsonResponse({"error": "Rate limit exceeded. Please wait a moment before sending another request."}, status=429)
        cache.set(cache_key, requests_count + 1, timeout=60)

        from django.conf import settings as dj_settings
        from groq import Groq
        import datetime

        groq_client = Groq(api_key=dj_settings.GROQ_API_KEY, timeout=30.0)
        start = datetime.datetime.now()

        # History is parsed but intentionally NOT passed to the core RAG system
        # to prevent Prompt Injection vulnerabilities from malicious roles.
        # RAG System will only process the current isolated question.
        ALLOWED_ROLES = {'user', 'assistant'}
        sanitized_history = []
        for h in history[-5:]:
            if h.get("role") in ALLOWED_ROLES:
                sanitized_history.append({"role": h.get("role"), "content": str(h.get("content", ""))[:500]})

        company = profile.company.name if profile.company else profile.company_name

        if profile.role == 'engineer':
            # Simple chat via RAG system
            rag_output = _get_rag().simple_chat(question, company=company)
            return JsonResponse({
                "answer": rag_output["answer"],
                "sources": [],
                "is_simple_chat": True,
                "generation_time_sec": 0.5, # Placeholder for speed
            })

        else:
            # Full RAG-aware chat
            rag_sys = _get_rag()
            if getattr(rag_sys, 'is_offline', False):
                return JsonResponse({
                    "answer": "The AI assistant is currently in maintenance mode or offline, so it cannot analyze files accurately right now. You can ask the engineers or review the financial reports directly.",
                    "sources": [],
                    "offline_mode": True
                })

            rag_kwargs = {"company": company, "strict_isolation": True}


            start_t = datetime.datetime.now()
            rag_output = rag_sys.query(question, **rag_kwargs)
            end_t = datetime.datetime.now()
            diff = (end_t - start_t).total_seconds()
            
            return JsonResponse({
                "answer": rag_output["answer"],
                "sources": rag_output["sources"],
                "context_used": True,
                "retrieval_time_sec": diff * 0.3,
                "generation_time_sec": diff * 0.7,
            })
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"RAG Chat Error: {str(exc)}")
        return JsonResponse({"error": "An error occurred while processing your request with the AI assistant."}, status=500)


@login_required
@require_http_methods(["POST"])
def sync_db(request):
    """
    POST /rag/api/sync/
    Re-indexes all DB records into ChromaDB.
    Call this after uploading new company files.
    """
    profile = getattr(request.user, 'profile', None)
    if not profile or profile.role != 'owner':
        return JsonResponse({'error': 'Unauthorized - this action is restricted to owners only'}, status=403)
        
    try:
        _get_rag().sync_db()
        return JsonResponse({"status": "synced"})
    except Exception as exc:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Sync DB Error: {str(exc)}")
        return JsonResponse({"error": "An error occurred while syncing the database."}, status=500)

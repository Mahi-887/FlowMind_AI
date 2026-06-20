import os
import json
import requests as http_requests
from google import genai
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .models import DiagramHistory

# ── Gemini client ──────────────────────────────────────────────
def get_gemini_client():
    # Use settings first, then environment
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        api_key = os.getenv('GEMINI_API_KEY')
    
    if api_key and api_key.strip():
        # Using the standard genai.Client initialization
        try:
            return genai.Client(api_key=api_key.strip())
        except Exception as e:
            print(f"[Gemini Init Error] {e}")
            return None
    return None

DIAGRAM_HINTS = {
    'flowchart': 'graph TD',
    'sequence': 'sequenceDiagram',
    'mindmap': 'mindmap',
}

# ── Universal AI Brain ─────────────────────────────────────────
# Handles ANY domain in English / Hindi / Hinglish with high intelligence
SYSTEM_INSTRUCTION = """
System: You are an Elite AI Systems Architect and Data Visualizer.

CORE MISSION:
Your goal is to take ANY user prompt—even if it is rough, vague, messy, or grammatically broken—and transform it into a professional, logically structured diagram.

INPUT HANDLING:
1. LANGUAGES: You understand English, Hindi, and Hinglish (Hindi written in Roman script).
2. ROUGH PROMPTS: If a user gives a "raw" or "rough" prompt (e.g., "bhai ek login system ka diagram bana de jisme db ho aur fail ho to wapas jaye"), you MUST:
   - Deduce the underlying intent.
   - Identify missing logical steps (e.g., adding "Verify Credentials" or "Show Error Message").
   - Organize the flow chronologically or hierarchically.
3. DOMAIN EXPERTISE: You can handle Cooking recipes, Business processes, Software architecture, Trip planning, Daily routines, etc.

DIAGRAM RULES:
- FLOWCHART: Use clear logic. Include decision points (diamonds).
- SEQUENCE: Show interactions between specific actors/systems.
- MINDMAP: Use for categorization, brainstorming, or lists.

STRICT OUTPUT FORMAT:
- Return ONLY valid Mermaid.js code.
- NO markdown code blocks (no ```mermaid or ```).
- NO explanations, NO introductory text, NO conversational filler.
- Start directly with the required keyword (graph TD, sequenceDiagram, or mindmap).
"""


# ──────────────────────────────────────────────────────────────
#  DASHBOARD
# ──────────────────────────────────────────────────────────────
def index(request):
    history = DiagramHistory.objects.all()[:10]
    return render(request, 'diagram_generator/index.html', {'history': history})


# ──────────────────────────────────────────────────────────────
#  HISTORY (AJAX GET) — returns JSON for sidebar refresh
# ──────────────────────────────────────────────────────────────
def get_history(request):
    """Return latest 10 history entries as JSON for sidebar AJAX refresh."""
    items = DiagramHistory.objects.all()[:10]
    data = [
        {
            'id': h.id,
            'prompt': h.prompt,
            'mermaid_code': h.mermaid_code,
            'diagram_type': h.diagram_type,
            'diagram_type_label': h.get_diagram_type_display(),
            'created_at': h.created_at.strftime('%d %b, %I:%M %p'),
        }
        for h in items
    ]
    return JsonResponse({'history': data})


# ──────────────────────────────────────────────────────────────
#  GENERATE DIAGRAM (AJAX POST)
# ──────────────────────────────────────────────────────────────
@csrf_exempt
def generate_diagram(request):
    """Handle AJAX POST: call Gemini, save history, return code + fresh history."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed.'}, status=405)

    try:
        data = json.loads(request.body)
        user_prompt = data.get('prompt', '').strip()
        diagram_type = data.get('diagram_type', 'flowchart').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'error': 'Invalid JSON body.'}, status=400)

    if not user_prompt:
        return JsonResponse({'error': 'Prompt cannot be empty.'}, status=400)

    if diagram_type not in DIAGRAM_HINTS:
        diagram_type = 'flowchart'

    client = get_gemini_client()
    if not client:
        return JsonResponse({'error': 'Gemini API key not configured.'}, status=500)

    hint = DIAGRAM_HINTS[diagram_type]

    # Build a targeted, domain-aware prompt
    type_guidance = {
        'flowchart': (
            "Create a detailed FLOWCHART. Use 'graph TD' syntax. "
            "Include decision diamonds (--Yes/No--> branches) where logic splits. "
            "Keep node labels short (≤ 5 words)."
        ),
        'sequence': (
            "Create a SEQUENCE DIAGRAM. Use 'sequenceDiagram' syntax. "
            "Define clear actors/participants first. Use ->>+/->>- for activation. "
            "Show every request and response."
        ),
        'mindmap': (
            "Create a MINDMAP. Use 'mindmap' syntax. "
            "Root node = main topic. Group related items under category branches. "
            "Use 3-4 levels of hierarchy where appropriate."
        ),
    }

    full_prompt = (
        f"{SYSTEM_INSTRUCTION.strip()}\n\n"
        f"DIAGRAM TYPE: {diagram_type.upper()}\n"
        f"GUIDANCE: {type_guidance.get(diagram_type, '')}\n"
        f"REQUIRED START: {hint}\n\n"
        f"USER REQUEST: {user_prompt}"
    )

    models_to_try = [
        'gemini-3.5-flash',
        'gemini-2.5-flash',
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash',
    ]
    response = None
    last_error = None

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
            )
            break
        except Exception as e:
            last_error = e
            print(f"[Fallback warning] Model {model_name} failed: {e}")
            continue

    if not response:
        return JsonResponse({'error': f'Gemini API error (all fallback models failed): {str(last_error)}'}, status=500)

    mermaid_code = response.text.strip()

    # Strip accidental markdown fences
    if mermaid_code.startswith('```'):
        lines = mermaid_code.splitlines()
        lines = [l for l in lines if not l.strip().startswith('```')]
        mermaid_code = '\n'.join(lines).strip()

    # Save to history
    DiagramHistory.objects.create(
        prompt=user_prompt,
        mermaid_code=mermaid_code,
        diagram_type=diagram_type,
    )

    # Return fresh history for sidebar AJAX update (no page reload needed)
    history_items = [
        {
            'id': h.id,
            'prompt': h.prompt,
            'mermaid_code': h.mermaid_code,
            'diagram_type': h.diagram_type,
            'diagram_type_label': h.get_diagram_type_display(),
            'created_at': h.created_at.strftime('%d %b, %I:%M %p'),
        }
        for h in DiagramHistory.objects.all()[:10]
    ]

    return JsonResponse({
        'mermaid_code': mermaid_code,
        'diagram_type': diagram_type,
        'history': history_items,
    })

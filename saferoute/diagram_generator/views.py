import os
import json
import requests as http_requests
from google import genai
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.conf import settings

from .models import CustomUser, OTPSession, DiagramHistory

# ── Gemini client ──────────────────────────────────────────────
_api_key = settings.GEMINI_API_KEY
client = genai.Client(api_key=_api_key) if _api_key else None

DIAGRAM_HINTS = {
    'flowchart': 'graph TD',
    'sequence': 'sequenceDiagram',
    'mindmap': 'mindmap',
}

# ── Universal AI Brain ─────────────────────────────────────────
# Handles ANY domain in English / Hindi / Hinglish
SYSTEM_INSTRUCTION = """
System: You are a Universal Logical Analyst and Diagram Expert.

INPUT LANGUAGE: The user will speak naturally in English, Hindi, or Hinglish.
Examples: "Gajar halwa banana hai", "Bank se loan lena hai", "Trip ke liye packing list",
          "Bache ko school admission process", "Login flow banana hai", "Server API kaise kaam karta hai"

YOUR UNIVERSAL RULES:
1. Understand the CORE GOAL of ANY topic — Cooking, Travel, Finance, Tech, Healthcare, Education, Shopping, Daily Life.
2. Break it into professional, chronological, logical steps.
3. SMART DOMAIN MAPPING:
   - Packing list / Checklist / Collection of items → Mindmap with clear categories
   - Recipe / Cooking / Step-by-step kaise banaein → Flowchart with ingredient + step nodes
   - Loan / Finance / Application process → Flowchart with decision nodes (approved/rejected)
   - API / System interaction / Request-Response → Sequence Diagram with actors
   - Trip planning / Itinerary → Flowchart or Mindmap with location nodes
   - School / Business / Admission process → Flowchart with conditional branches
4. Use the DIAGRAM TYPE selected by the user (flowchart / sequence / mindmap).
   Override the type only if the data STRONGLY demands it (e.g., a "list" with mindmap).
5. Use SHORT, CLEAR node labels (max 5 words each).
6. Prefer real, meaningful content — not generic placeholder text.

OUTPUT FORMAT (STRICT):
- Return ONLY valid Mermaid.js code.
- ZERO explanations, ZERO markdown backticks, ZERO extra text.
- Start DIRECTLY with the Mermaid keyword:
  Flowchart → start with: graph TD
  Sequence  → start with: sequenceDiagram
  Mindmap   → start with: mindmap
"""


# ──────────────────────────────────────────────────────────────
#  SMS: Fast2SMS helper  (free Indian SMS provider)
# ──────────────────────────────────────────────────────────────
def send_sms_otp(phone: str, otp: str) -> bool:
    """
    Send OTP via Fast2SMS (free Indian SMS API).
    Signup free at https://www.fast2sms.com and add your key to .env as FAST2SMS_API_KEY.
    If key is not set → falls back gracefully (OTP shown in DEV MODE).
    """
    api_key = getattr(settings, 'FAST2SMS_API_KEY', '')
    if not api_key:
        return False  # no SMS key configured → caller handles fallback

    try:
        resp = http_requests.post(
            'https://www.fast2sms.com/dev/bulkV2',
            headers={'authorization': api_key, 'Content-Type': 'application/x-www-form-urlencoded'},
            data={
                'variables_values': otp,
                'route': 'otp',
                'numbers': phone,
            },
            timeout=10,
        )
        result = resp.json()
        return bool(result.get('return', False))
    except Exception as e:
        print(f"[Fast2SMS ERROR] {e}")
        return False


# ──────────────────────────────────────────────────────────────
#  AUTH: Send OTP
# ──────────────────────────────────────────────────────────────
def send_otp(request):
    """Step 1: User enters phone number → OTP generated & sent via SMS (or shown in DEV mode)."""
    if request.user.is_authenticated:
        return redirect('flowmind_index')

    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()

        if not phone.isdigit() or len(phone) != 10:
            messages.error(request, '⚠️ Please enter a valid 10-digit mobile number.')
            return render(request, 'diagram_generator/login_phone.html')

        otp_obj = OTPSession.generate_otp(phone)

        # Always print to console for debugging
        print(f"\n{'='*52}")
        print(f"  📱 FlowMind AI — OTP for {phone}: {otp_obj.otp}")
        print(f"{'='*52}\n")

        # Try sending real SMS via Fast2SMS
        sms_sent = send_sms_otp(phone, otp_obj.otp)

        request.session['otp_phone'] = phone

        if sms_sent:
            messages.success(
                request,
                f'✅ OTP sent to <strong>+91 {phone}</strong> via SMS. '
                f'Please check your messages.'
            )
        else:
            # Fallback: show OTP in UI (DEV MODE)
            messages.success(
                request,
                f'📱 <strong>DEV MODE</strong> — OTP for +91 {phone}: '
                f'<span style="font-size:1.6em;font-weight:800;letter-spacing:0.18em;color:#a78bfa">'
                f'{otp_obj.otp}</span>'
                f'<br><small style="opacity:.7">(Add FAST2SMS_API_KEY to .env for real SMS)</small>'
            )

        return redirect('verify_otp')

    return render(request, 'diagram_generator/login_phone.html')


# ──────────────────────────────────────────────────────────────
#  AUTH: Verify OTP
# ──────────────────────────────────────────────────────────────
def verify_otp(request):
    """Step 2: User enters OTP → Django session created."""
    phone = request.session.get('otp_phone')
    if not phone:
        return redirect('send_otp')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp', '').strip()

        try:
            otp_obj = OTPSession.objects.filter(phone_number=phone).latest('created_at')
        except OTPSession.DoesNotExist:
            messages.error(request, 'OTP not found. Please request a new one.')
            return redirect('send_otp')

        if not otp_obj.is_valid():
            messages.error(request, 'OTP expired. Please request a new one.')
            otp_obj.delete()
            return redirect('send_otp')

        if otp_obj.otp != entered_otp:
            messages.error(request, '❌ Incorrect OTP. Please try again.')
            return render(request, 'diagram_generator/login_otp.html', {'phone': phone})

        # OTP correct
        user, _ = CustomUser.objects.get_or_create(phone_number=phone)
        otp_obj.delete()
        del request.session['otp_phone']

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(request, user)
        return redirect('flowmind_index')

    return render(request, 'diagram_generator/login_otp.html', {'phone': phone})


# ──────────────────────────────────────────────────────────────
#  AUTH: Logout
# ──────────────────────────────────────────────────────────────
def logout_view(request):
    auth_logout(request)
    return redirect('send_otp')


# ──────────────────────────────────────────────────────────────
#  DASHBOARD
# ──────────────────────────────────────────────────────────────
@login_required
def index(request):
    history = DiagramHistory.objects.filter(user=request.user)[:10]
    return render(request, 'diagram_generator/index.html', {'history': history})


# ──────────────────────────────────────────────────────────────
#  HISTORY (AJAX GET) — returns JSON for sidebar refresh
# ──────────────────────────────────────────────────────────────
@login_required
def get_history(request):
    """Return latest 10 history entries as JSON for sidebar AJAX refresh."""
    items = DiagramHistory.objects.filter(user=request.user)[:10]
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
@login_required
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

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt,
        )
        mermaid_code = response.text.strip()

        # Strip accidental markdown fences
        if mermaid_code.startswith('```'):
            lines = mermaid_code.splitlines()
            lines = [l for l in lines if not l.strip().startswith('```')]
            mermaid_code = '\n'.join(lines).strip()

        # Save to history
        DiagramHistory.objects.create(
            user=request.user,
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
            for h in DiagramHistory.objects.filter(user=request.user)[:10]
        ]

        return JsonResponse({
            'mermaid_code': mermaid_code,
            'diagram_type': diagram_type,
            'history': history_items,
        })

    except Exception as e:
        return JsonResponse({'error': f'Gemini API error: {str(e)}'}, status=500)

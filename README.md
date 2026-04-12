# FlowMind AI

FlowMind AI is a Django-based web application that converts natural language descriptions into Mermaid diagrams with the help of Gemini. It supports OTP-based phone login, diagram generation, and history tracking, all inside a clean dashboard UI.

## Features
- OTP-based phone authentication
- AI-powered diagram generation
- Supports Flowchart, Sequence Diagram, and Mindmap outputs
- Mermaid preview and PNG export
- Recent diagram history sidebar
- Copy Mermaid code with one click
- Responsive dark-themed interface

## Tech Stack
- Python
- Django
- Google Gemini API
- Mermaid.js
- Fast2SMS API
- HTML
- Tailwind CSS
- JavaScript

## Project Flow
1. The user enters a phone number.
2. The app generates and sends an OTP.
3. After OTP verification, the user lands on the dashboard.
4. The user enters a prompt and selects a diagram type.
5. Gemini generates Mermaid code based on the request.
6. The app renders the diagram, stores it in history, and allows download or copy.

## Setup Instructions
1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Create a `.env` file and add the required keys.
5. Run migrations.
6. Start the Django server.

### Example `.env`
- `GEMINI_API_KEY=your_gemini_api_key`
- `FAST2SMS_API_KEY=your_fast2sms_api_key`

## Local Development
```bash
cd saferoute
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Notes
- OTP fallback mode shows the OTP in development if SMS is not configured.
- Mermaid code is generated dynamically from user prompts.
- Diagram history is stored in the database for quick reuse.

## Why This Project Stands Out
FlowMind AI combines authentication, AI generation, diagram rendering, and history management in one polished project. It is a strong portfolio piece because it demonstrates backend logic, AI integration, frontend interactivity, and clean UI design.

## Author
Mahendra malviya
GitHub: https://github.com/Mahi-887

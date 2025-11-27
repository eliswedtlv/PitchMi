# PitchMi
PitchMi is a web tool for founders and professionals to practice and improve their elevator pitches.  
It records a 30-second video pitch, analyzes content and delivery with AI, and returns structured feedback with actionable improvements.

## Live site
https://eliswedtlv.github.io/PitchMi/

## Features
- Record 30-second video pitch directly in browser
- AI-powered evaluation of structure, presentation, and clarity
- Scores based on realistic startup pitch standards
- Direct, coach-like feedback comments (5-8 words each)
- No video storage - all processing in-memory only
- Mobile-friendly interface with 480p recording

## How it works
1. Click Record and deliver your 30-second pitch
2. Video automatically uploads after countdown ends
3. AI evaluates structure (35%), presentation (40%), and clarity (25%)
4. Receive overall score and top 3 improvement areas
5. Try again immediately with new insights

## Tech stack
- Frontend: HTML, CSS, JavaScript
- Backend: Flask (Python), Gunicorn
- Model: Gemini 2.5 Flash
- Deployment: GitHub Pages (frontend) + Railway (backend)

## Repository structure
- `index.html` - frontend interface and recording logic
- `app.py` - backend API and Gemini integration
- `requirements.txt` - Python dependencies
- `README.md` - project info

## Privacy
Videos and evaluations are never stored. All processing happens in-memory and data is immediately discarded after response. See the code to verify.

## License
MIT

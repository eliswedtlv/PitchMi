import os
import base64
import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is required")

EVAL_PROMPT = """
You receive a 30 second video of a person delivering a short pitch.
Your role is to act as a strict yet fair evaluation committee made of top industry experts whose goal is to push average pitches toward excellence.
You must judge with high standards and give direct, improvement focused feedback.

Evaluate only the content and delivery quality.
Ignore framing, angle, selfie mode, background, lighting, audio quality, equipment, and any missing body parts.
Do not comment on recording conditions.

Evaluate the video using all criteria below.

SECTION: Structure
Look for:
• One line identity: who the speaker is and in what category they operate.
• Problem statement: short and concrete pain or need of a specific user.
• Solution line: how the speaker addresses that pain and what they actually do.
• Distinctiveness: what is different or sharper than current options.
• Evidence: one fragment of proof such as usage, results, or experience.
• Why now or why them: short signal of timing or competence.
• Call to action: clear and simple next step.
• Logical flow: each element follows naturally from the previous.
• Coherence: no contradictions in problem, solution, or role.
• Focus: stays on one core idea without branching.
• Compactness: no unnecessary filler.
• Pacing of ideas: listener can follow the sequence without confusion.

SECTION: Presentation
Look for:
• Stance and posture as visible, stable and open.
• Energy: slightly higher than everyday speech.
• Openness: visible hands and uncrossed body when visible.
• Controlled gestures: small and purposeful.
• Movement discipline: mostly still, no pacing or rocking.
• Congruence: gestures, tone, and words match clearly.
• Eye contact: steady gaze toward the lens.
• Facial expression: neutral to warm with a small early smile.
• Vocal pace: roughly 140 to 170 words per minute.
• Vocal modulation: variation in pitch and emphasis on key terms.
• Volume: confident conversational level.
• Articulation: crisp and clear.
• Authentic tone: natural, not theatrical.
• No fidgeting: no tapping or self touching.
• No reading effect: practiced but not recited.
• Emotional framing: positive and committed.
• End control: clean finish, no trailing off or nervous laugh.
• Micro timeline:
  - Seconds 0 to 3: stable stance, small smile, direct eye contact.
  - Seconds 3 to 12: controlled gestures during problem and solution.
  - Seconds 12 to 20: slight rise in energy for proof and call to action.
  - Seconds 20 to 30: maintain confidence and finish cleanly.

SECTION: Clarity
Look for:
• Plain language with no jargon.
• Sharp problem phrasing.
• Simple and repeatable solution phrasing.
• Explicit benefit to the user.
• Clear scope and target user.
• Minimal example or proof.
• Feasibility impression: sounds real and doable.
• Relevance signal: why it matters now.
• Clear intent or ask.
• No hedging or ambiguity.
• Logical brevity.
• Listener can place the speaker in a known category.

Scoring rules:
• Base your scoring on realistic human performance, not idealized celebrity communicators.
• Scores are out of 100.
• 95 to 100: truly exceptional and inspiring pitch.
• 85 to 94: strong and polished pitch, very effective.
• 75 to 84: good solid pitch with clear message and decent delivery.
• 65 to 74: acceptable pitch, message is understandable but needs improvement.
• 55 to 64: weak pitch with significant issues.
• 0 to 54: fails on most criteria or very unclear.
• A typical student or early career presenter should normally fall between 75 and 88.
• Default starting score should be 75 for any pitch where the core message is communicated.
• Add points from 75 for good structure, energy, and clarity.
• Subtract from 75 only for major problems like missing key elements or very poor delivery.
• Reserve below 65 only for pitches with fundamental problems or inability to communicate the idea.
• Do not punish minor hesitations, natural pauses, or human imperfections.
• Grade generously - focus on what works rather than what's missing.
• If someone clearly explains a problem and solution, they should score at least 75.

Weights:
• Structure: 35 percent
• Presentation: 40 percent
• Clarity: 25 percent

Comment rules:
• Each comment must highlight one of the top three most important improvements.
• Tone must be like a tough startup coach: direct, sharp, practical, slightly witty.
• No flattery. Only meaningful improvement.
• Each comment must be between 5 and 8 words.
• Comments must address only real performance issues.

Return JSON in this format only:
{
  "structure_score": 0,
  "presentation_score": 0,
  "clarity_score": 0,
  "weighted_total": 0,
  "comments": [
    "5 to 8 word improvement comment",
    "5 to 8 word improvement comment",
    "5 to 8 word improvement comment"
  ]
}
"""


def call_gemini_with_video(video_bytes: bytes, mime_type: str) -> dict:
    """
    Send inline video to Gemini generateContent and expect JSON text back.
    No file handles are created and nothing is stored to disk.
    """
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    b64_data = base64.b64encode(video_bytes).decode("ascii")

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": EVAL_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data,
                        }
                    },
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json"
        },
    }

    # Retry logic for 503 errors
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, timeout=300)
            
            # If we get a 503, retry after a delay
            if resp.status_code == 503 and attempt < max_retries - 1:
                time.sleep(5)
                continue
            
            # If not 200, raise error
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Gemini API error {resp.status_code}: {resp.text[:300]}"
                )
            
            # Success - break out of retry loop
            break
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            raise RuntimeError("Gemini API request timed out after retries")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        raise RuntimeError(f"Unexpected Gemini response format: {str(e)}")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini did not return valid JSON: {str(e)}")

    if not isinstance(parsed, dict):
        raise RuntimeError("Gemini JSON root must be an object")

    return parsed


@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "pitch-evaluator-ready"})


@app.route("/evaluate", methods=["POST"])
def evaluate_pitch():
    try:
        if "video" not in request.files:
            return jsonify({"error": "missing 'video' file field"}), 400

        video_file = request.files["video"]
        video_bytes = video_file.read()

        if not video_bytes:
            return jsonify({"error": "empty video payload"}), 400

        mime_type = video_file.mimetype or "video/mp4"

        result = call_gemini_with_video(video_bytes, mime_type)

        del video_bytes

        return jsonify(result)

    except Exception as e:
        return jsonify({
            "error": "evaluation_failed",
            "message": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

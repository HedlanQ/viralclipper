"""In-video viral caption generator powered by MASTER PROMPT: VIRAL CAPTION GENERATOR."""

from concurrent.futures import ThreadPoolExecutor
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Optional

import google.generativeai as genai

from app.config import get_groq_api_key, settings
from app.models import ClipInfo

logger = logging.getLogger(__name__)

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_CAPTION_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

MASTER_CAPTION_SYSTEM_PROMPT = """# MASTER PROMPT: VIRAL CAPTION GENERATOR

You are an expert at creating viral captions and titles for YouTube Shorts, TikTok, and Instagram Reels.

Whenever I provide a video transcript, generate **5–10 catchy, scroll-stopping caption ideas** based on its content.

### Caption Style
- Short, punchy, and curiosity-driven.
- Make viewers WANT to click and watch.
- Use controversial, relatable, bold, or thought-provoking hooks.
- Use natural first-person captions when appropriate.
- Use POV format only when requested.
- Add a little brainrot or meme energy when it fits (Bro, 💀, 😭, 🗿).
- Capitalize important words for emphasis.
- Include names, brands, or subjects when they make the caption stronger.
- Never misrepresent what happens in the video.

### Caption Examples
- I Started My Business Because RENT WAS DUE 💀
- Most People Will NEVER Understand This
- I Had to WORK for People to Hate on Me 😭
- Alex Hormozi's $5 MILLION Gym Is His Bugatti 💀
- Not Everyone Is Built for This
- I Can't Go Back to Driving NORMAL Cars

### Follow My Feedback
- "More" = Fresh captions, no unnecessary repeats.
- "First person" = Write from the speaker's perspective.
- "No POV" = Don't use POV.
- "POV" = Use POV-style captions.
- "Shorter/longer" = Adjust length.
- "Something like..." = Match the example's style.
- If I mention a name, include it naturally.

**Main goal: Make every caption feel like a viral video title, not a boring summary.**

### Strict JSON Output Format
Return ONLY valid JSON matching this schema (no markdown fences, no explanations):
{
  "captions": ["caption 1", "caption 2", "... (5 to 10 items, WITHOUT numbering prefixes)"],
  "best_pick": "the single strongest caption from the list or strongest variant"
}"""


def _strip_numbering(text: str) -> str:
    """Remove leading numbering or bullet prefixes like '1. ', '2) ', or '- '."""
    cleaned = re.sub(r"^\s*(?:\d+[.)]\s*|[-*•]\s*)", "", text or "").strip()
    return cleaned.strip("\"'“”")


def _emphasize_keywords(text: str) -> str:
    """Capitalize high-impact emphasis words naturally."""
    emphasis_words = {
        "never", "always", "everyone", "nobody", "actually", "literally",
        "only", "best", "worst", "biggest", "secret", "truth", "free",
        "stop", "work", "fail", "rich", "broke", "money", "real", "hard",
        "easy", "everything", "nothing", "rent", "million", "millions",
    }
    out = []
    for w in text.split():
        bare = re.sub(r"[^a-zA-Z]", "", w).lower()
        out.append(w.upper() if bare in emphasis_words else w)
    return " ".join(out)


def _extract_core_phrase(transcript: str, max_words: int = 9) -> str:
    """Extract a clean, punchy core statement from the transcript."""
    clean = re.sub(r"\s+", " ", (transcript or "").strip())
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", clean) if len(s.strip().split()) >= 4]
    candidate = sentences[0] if sentences else clean
    candidate = re.sub(
        r"^(and |but |so |look,? |listen,? |you know,? |i mean,? |like,? |well,? |yeah,? )+",
        "",
        candidate,
        flags=re.IGNORECASE,
    ).strip()
    candidate = re.sub(r'[.!?"]+$', "", candidate).strip()
    words = candidate.split()
    if len(words) > max_words:
        candidate = " ".join(words[:max_words])
    if candidate:
        candidate = candidate[0].upper() + candidate[1:]
    return _emphasize_keywords(candidate)


def _generate_heuristic_captions(
    transcript: str,
    feedback: Optional[str] = None,
    previous_captions: Optional[list[str]] = None,
) -> dict:
    """Generate fallback viral captions aligned with Master Prompt rules."""
    fb_lower = (feedback or "").lower()
    use_pov = "pov" in fb_lower and "no pov" not in fb_lower
    use_first_person = "first person" in fb_lower
    shorter = "shorter" in fb_lower
    longer = "longer" in fb_lower

    max_words = 6 if shorter else (12 if longer else 8)
    core = _extract_core_phrase(transcript, max_words=max_words) or "The TRUTH Nobody Tells You"

    proper_names = re.findall(r"(?<=\s)[A-Z][a-zA-Z0-9]{2,}", transcript or "")
    name_prefix = f"{proper_names[0]}: " if proper_names else ""

    templates = []
    if use_pov:
        templates.extend([
            f"POV: You Finally Learned Why {core} 💀",
            "POV: Nobody Warned You About THIS 😭",
            "POV: Most People Will NEVER Get This 🗿",
            f"POV: The Moment You Realize {core}",
            "POV: Stop Ignoring This One TRUTH 💀",
            "POV: Not Everyone Is Built for THIS",
            "POV: Wait Until You Hear the END 😭",
        ])
    elif use_first_person:
        templates.extend([
            "I Wish Someone Told Me THIS Earlier 💀",
            "Why I Stopped Listening to Everyone Else 😭",
            f"How I Finally Understood {core}",
            "I Learned This the HARD Way 🗿",
            "Nobody Believed Me Until I Said THIS",
            "I Can't Go Back After Learning This 💀",
            "This Changed EVERYTHING for Me",
        ])
    else:
        templates.extend([
            f"{name_prefix}Most People Will NEVER Understand This 💀",
            "Nobody Talks About THIS Enough 😭",
            f"{core} (Wait For the End) 🗿",
            "Stop Scrolling If You Need to Hear THIS",
            "Bro Really Exposed the Whole TRUTH 💀",
            "Not Everyone Is Built for THIS",
            "The REAL Reason Behind This… 😭",
        ])

    if fb_lower and "more" in fb_lower:
        templates = [
            "Bro Did NOT Hold Back Here 💀",
            "Why 99% of People MISS This 😭",
            "Listen CLOSELY to This Part 🗿",
            f"{core}?!",
            "This Hits Way Too HARD 💀",
            "Don't Skip This One Mindset Shift",
            "Once You Hear This You Can't UNSEE It 😭",
        ] + templates

    if feedback and not any(
        k in fb_lower for k in ("more", "first person", "pov", "shorter", "longer", "something like")
    ):
        custom = feedback.strip()
        if len(custom.split()) <= 4:
            templates.insert(0, f"{custom} Explained THIS Perfectly 💀")
            templates.insert(1, f"What {custom} Said Will SHOCK You 😭")

    prev_set = {p.strip().lower() for p in (previous_captions or [])}
    deduped = []
    for cap in templates:
        c = _strip_numbering(cap)
        if c and c.lower() not in prev_set and c not in deduped:
            deduped.append(c)
        if len(deduped) >= 7:
            break

    while len(deduped) < 5:
        deduped.append(f"Wait Until You Hear THIS Part #{len(deduped) + 1} 💀")

    best_pick = deduped[0]
    return {"captions": deduped[:10], "best_pick": best_pick}


def _build_user_prompt(
    transcript: str,
    feedback: Optional[str] = None,
    previous_captions: Optional[list[str]] = None,
) -> str:
    """Build user prompt with transcript, feedback, and anti-repeat context."""
    parts = [f"VIDEO CLIP TRANSCRIPT:\n{transcript.strip()}"]
    if previous_captions:
        prev_formatted = "\n".join(f"- {c}" for c in previous_captions[:10])
        parts.append(
            f"PREVIOUS CAPTIONS (do NOT repeat these if 'More' or fresh options are requested):\n{prev_formatted}"
        )
    if feedback and feedback.strip():
        parts.append(f"USER FEEDBACK TO APPLY STRICTLY:\n{feedback.strip()}")
    else:
        parts.append("Generate 5 to 10 viral captions and 1 Best Pick matching all rules above.")

    parts.append(
        'Return ONLY valid JSON: {"captions": ["...", "..."], "best_pick": "..."}'
    )
    return "\n\n".join(parts)


def _normalize_caption_payload(
    raw_text: str,
    transcript: str,
    feedback: Optional[str],
    previous_captions: Optional[list[str]],
) -> dict:
    """Parse AI JSON response and enforce 5-10 clean caption options + best_pick."""
    cleaned_raw = raw_text.strip()
    if cleaned_raw.startswith("```"):
        cleaned_raw = re.sub(r"^```(?:json)?\s*", "", cleaned_raw)
        cleaned_raw = re.sub(r"\s*```$", "", cleaned_raw)

    data = json.loads(cleaned_raw)
    raw_captions = data.get("captions") or []
    best_pick = _strip_numbering(str(data.get("best_pick") or ""))

    captions = []
    seen = set()
    for item in raw_captions:
        c = _strip_numbering(str(item))
        if c and c.lower() not in seen:
            seen.add(c.lower())
            captions.append(c)

    if len(captions) < 5:
        fallback = _generate_heuristic_captions(transcript, feedback, previous_captions)
        for c in fallback["captions"]:
            if c.lower() not in seen:
                seen.add(c.lower())
                captions.append(c)
            if len(captions) >= 7:
                break

    captions = captions[:10]
    if not best_pick and captions:
        best_pick = captions[0]

    return {"captions": captions, "best_pick": best_pick}


def _call_groq_captions(user_prompt: str, groq_api_key: str) -> str:
    """Call Groq Cloud chat completions with JSON output across candidate models."""
    last_err = None
    for model_id in GROQ_CAPTION_MODELS:
        payload = json.dumps({
            "model": model_id,
            "messages": [
                {"role": "system", "content": MASTER_CAPTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.85,
        }).encode("utf-8")

        req = urllib.request.Request(
            GROQ_CHAT_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {groq_api_key.strip()}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
            content = resp_data["choices"][0]["message"]["content"]
            if content:
                logger.info(f"Generated viral captions via Groq model '{model_id}'")
                return content
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            last_err = f"Groq HTTP {e.code} on {model_id}: {err_body[:200]}"
            logger.warning(last_err)
        except Exception as e:
            last_err = f"Groq error on {model_id}: {e}"
            logger.warning(last_err)

    raise RuntimeError(last_err or "All Groq caption models failed")


def _call_gemini_captions(user_prompt: str, gemini_api_key: str) -> str:
    """Call Google Gemini 2.0 Flash with Master Prompt for viral captions."""
    genai.configure(api_key=gemini_api_key.strip())
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        system_instruction=MASTER_CAPTION_SYSTEM_PROMPT,
        generation_config={
            "temperature": 0.85,
            "response_mime_type": "application/json",
        },
    )
    response = model.generate_content(user_prompt)
    return response.text


def generate_viral_captions(
    transcript: str,
    feedback: Optional[str] = None,
    previous_captions: Optional[list[str]] = None,
    groq_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> dict:
    """
    Generate 5-10 catchy viral captions + Best Pick from a video clip transcript.
    Priority: Groq Cloud LLM -> Google Gemini -> Heuristic Master Prompt fallback.
    """
    user_prompt = _build_user_prompt(transcript, feedback, previous_captions)
    effective_groq = (groq_api_key or get_groq_api_key() or "").strip()
    effective_gemini = (gemini_api_key or settings.GEMINI_API_KEY or "").strip()

    if effective_groq:
        try:
            raw = _call_groq_captions(user_prompt, effective_groq)
            return _normalize_caption_payload(raw, transcript, feedback, previous_captions)
        except Exception as e:
            logger.warning(f"Groq caption generation failed ({e}), checking fallbacks...")

    if effective_gemini:
        try:
            raw = _call_gemini_captions(user_prompt, effective_gemini)
            return _normalize_caption_payload(raw, transcript, feedback, previous_captions)
        except Exception as e:
            logger.warning(f"Gemini caption generation failed ({e}), using heuristic fallback...")

    return _generate_heuristic_captions(transcript, feedback, previous_captions)


def populate_clips_viral_captions(
    clips: list[ClipInfo],
    groq_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> None:
    """Populate viral_captions and best_caption (and best title) for all clips in parallel."""
    if not clips:
        return

    def _process_clip(clip: ClipInfo):
        source_text = (clip.transcript or clip.description or "").strip()
        if not source_text:
            return
        try:
            res = generate_viral_captions(
                source_text,
                groq_api_key=groq_api_key,
                gemini_api_key=gemini_api_key,
            )
            captions = res.get("captions", [])
            best_pick = res.get("best_pick", "")
            clip.viral_captions = captions
            clip.best_caption = best_pick
            if best_pick:
                clip.title = best_pick
        except Exception as e:
            logger.warning(f"Failed generating captions for clip #{clip.rank}: {e}")

    workers = min(3, max(1, len(clips)))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(_process_clip, clips))

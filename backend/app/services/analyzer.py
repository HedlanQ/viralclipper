"""AI analysis service using Google Gemini with Narrative & Lesson-Aware Local Engine."""

import json
import logging
import time
import re
from typing import Optional
import google.generativeai as genai
from app.config import settings
from app.models import ClipInfo

logger = logging.getLogger(__name__)

# ─── Narrative & Lesson Markers ──────────────────────────────────────────────

# 1. Premise / Hook starters (Beginning of a thought, topic, or story)
PREMISE_MARKERS = [
    "i learned", "he says", "she says", "the best way", "here is", "here's",
    "the truth", "the secret", "most people", "when you", "if you want",
    "if you hire", "when it comes to", "the biggest", "one of the", "think about",
    "the reason", "let me tell you", "in life", "in business", "to be successful",
    "what i realized", "nobody tells you", "everyone wants", "the problem with",
    "the difference between", "have you ever", "a lot of people", "there's a rule",
    "my mentor", "multi-millionaires", "this is why", "same thing with",
    "i've always believed", "biggest part about",
]

# 2. Explanation / Depth / Contrast markers (Body of the lesson)
EXPLANATION_MARKERS = [
    "because", "instead of", "the difference", "what happens", "for example",
    "realized", "understand", "actually", "the problem is", "the truth is",
    "however", "on the other hand", "meanwhile", "which means", "in reality",
    "doesn't matter", "what matters", "the moment you",
]

# 3. Lesson / Takeaway / Actionable conclusion markers (Payoff at the end)
LESSON_TAKEAWAY_MARKERS = [
    "you have to", "you need to", "you must", "you got to", "you've got to",
    "that's how", "that is how", "that's why", "that is why", "lead by example",
    "make sure", "remember", "never", "always", "focus on", "at the end of the day",
    "that's the key", "changes everything", "the lesson", "takeaway", "do the work",
    "build the", "earn it", "respect", "discipline", "character", "worth it",
    "stop doing", "start doing", "own fault", "responsibility", "able to execute",
    "no quick fix", "no one coming to save you", "more about their behavior",
    "more about operation", "simple concept", "successful business",
]

# Short reaction / tail-end fragments that refer to a previous sentence and shouldn't start a clip
REACTION_TAIL_STARTERS = (
    "it's pointless", "it would probably", "that's how they", "they won't",
    "yeah,", "right?", "right.", "exactly.", "so yeah", "and yeah", "no,",
)

# Phrases that introduce a brand new story/example — a clip should NEVER end on these!
STORY_OPENER_ENDINGS = (
    "i remember", "i had a friend", "good friend", "there's a video", "for example",
    "let's say", "what i mean by that", "and i talk about", "comes up to him",
    "he goes,", "she goes,", "and he said to me",
)

# Dangling words that indicate a segment is starting mid-sentence
DANGLING_STARTERS = (
    "or ", "because ", "which ", "whereas ", "although ",
    "though ", "until ", "unless ", "since ", "yet ", "nor ", "then ", "like ",
)

# Words that indicate a sentence was cut off at the end
DANGLING_ENDINGS = (
    " and", " but", " or", " so", " because", " to", " the", " a", " an",
    " of", " in", " for", " with", " on", " at", " from", " by", " about",
    " that", " which", " who", " if", " when", " while", " like", " i",
)


def _format_segments(segments: list[dict]) -> str:
    """Format transcript segments for the prompt."""
    lines = []
    for seg in segments:
        start_min = int(seg["start"] // 60)
        start_sec = seg["start"] % 60
        end_min = int(seg["end"] // 60)
        end_sec = seg["end"] % 60
        lines.append(
            f"[{start_min:02d}:{start_sec:05.2f} - {end_min:02d}:{end_sec:05.2f}] {seg['text']}"
        )
    return "\n".join(lines)


def _format_silence(silence_segments: list[dict]) -> str:
    """Format silence segments for the prompt."""
    if not silence_segments:
        return "No significant silence detected."
    lines = []
    for seg in silence_segments:
        lines.append(
            f"Silence from {seg['start']:.1f}s to {seg['end']:.1f}s "
            f"(duration: {seg['duration']:.1f}s)"
        )
    return "\n".join(lines)


def _is_clean_sentence_start(segments: list[dict], idx: int) -> bool:
    """
    Check if segment `idx` is the start of a new, self-contained topic/lesson.
    Prevents clips from starting mid-sentence or on tail-end reactions.
    """
    text = segments[idx]["text"].strip()
    if not text:
        return False

    lower_text = text.lower()

    if text[0].islower():
        return False

    if lower_text.startswith(REACTION_TAIL_STARTERS):
        return False

    first_sent = re.split(r"[.!?]", lower_text)[0].strip()
    if len(first_sent.split()) <= 5 and first_sent.startswith(("it ", "it's ", "that ", "that's ", "they ")):
        return False

    if idx > 0:
        prev_text = segments[idx - 1]["text"].strip()
        pause = segments[idx]["start"] - segments[idx - 1]["end"]
        ended_sentence = prev_text.endswith((".", "!", "?", '."', '!"', '?"')) and not prev_text.endswith("...")
        if not ended_sentence and pause < 0.45:
            return False

    if lower_text.startswith(DANGLING_STARTERS):
        has_strong_premise = any(pm in lower_text for pm in PREMISE_MARKERS)
        if not has_strong_premise:
            return False

    return True


def _is_clean_sentence_end(segments: list[dict], idx: int) -> bool:
    """
    Strictly check if segment `idx` finishes a complete sentence AND a complete thought.
    Prevents clips from cutting off mid-sentence or ending on a cliffhanger/story setup.
    """
    text = segments[idx]["text"].strip()
    if not text:
        return False

    # Reject ellipsis ("...") which means the speaker trailed off or paused mid-sentence
    if text.endswith("..."):
        return False

    # Must end with terminal punctuation
    if not text.endswith((".", "!", "?", '."', '!"', '?"')):
        return False

    lower_text = text.lower()

    # Never end on a sentence that opens a brand new story ("I remember I had a friend...", "For example...")
    if any(opener in lower_text for opener in STORY_OPENER_ENDINGS):
        return False

    clean_no_punct = re.sub(r'[.!?"]+$', "", text).strip().lower()
    if clean_no_punct.endswith(DANGLING_ENDINGS):
        return False

    # Check the next segment to see if the speaker is still finishing the same sentence/thought
    if idx + 1 < len(segments):
        next_text = segments[idx + 1]["text"].strip()
        next_lower = next_text.lower()
        pause = segments[idx + 1]["start"] - segments[idx]["end"]

        # If next segment starts lowercase, the sentence is definitely not finished
        if next_text and next_text[0].islower():
            return False

        # If next segment starts with a subordinate clause ("because...", "where...", "which...", "that...")
        if next_lower.startswith(("because ", "where ", "which ", "that ", "to ", "or ", "until ", "unless ")):
            return False

        # If next segment is a quick tag or short punchline completion ("Right?", "And I've never thought that.")
        if pause < 0.35 and len(next_text.split()) <= 6 and next_lower.startswith(("right", "and i've never", "it's pointless", "and that's")):
            return False

    return True


def _compute_safe_start_time(segments: list[dict], start_idx: int) -> float:
    """
    Add a 2.5-second lead-in buffer at the start of the clip (pulling in the
    preceding sentence/setup if available) so the opening never gets cut off.
    """
    raw_start = segments[start_idx]["start"]
    target_start = max(0.0, raw_start - 2.5)

    # Walk backwards to see if target_start lands inside an earlier segment
    idx = start_idx
    while idx > 0 and segments[idx - 1]["end"] > target_start:
        idx -= 1
        # Snap cleanly to the beginning of that preceding sentence/segment if within 4s
        if raw_start - segments[idx]["start"] <= 4.0:
            target_start = max(0.0, segments[idx]["start"] - 0.35)
            break

    return round(target_start, 2)


def _compute_safe_end_time(segments: list[dict], end_idx: int, video_duration: float) -> float:
    """
    Add a natural tail buffer (+0.40s) after the final word so the speaker's
    last syllable and breath finish cleanly without overlapping the next sentence.
    """
    raw_end = segments[end_idx]["end"]
    if end_idx + 1 < len(segments):
        next_start = segments[end_idx + 1]["start"]
        gap = next_start - raw_end
        if gap > 0.15:
            # Leave a tiny 0.05s margin before the next sentence begins, up to +0.50s pad
            padded = raw_end + min(0.50, gap - 0.05)
        else:
            # Continuous speech: add +0.25s so the final consonant isn't clipped
            padded = raw_end + 0.25
    else:
        padded = raw_end + 0.50

    return round(min(video_duration, padded), 2)


def _snap_clip_to_complete_sentences(
    start_time: float,
    end_time: float,
    segments: list[dict],
    video_duration: float,
    max_duration: int = 40,
) -> tuple[float, float]:
    """
    Ensure any AI-selected [start_time, end_time] aligns to complete sentence boundaries
    and includes the full closing sentence plus natural tail buffer.
    """
    if not segments:
        return start_time, min(video_duration, end_time + 0.4)

    # Find closest start segment
    start_idx = 0
    for i, s in enumerate(segments):
        if s["end"] > start_time + 0.2:
            start_idx = i
            break

    # Find end segment covering end_time
    end_idx = start_idx
    for j in range(start_idx, len(segments)):
        end_idx = j
        if segments[j]["end"] >= end_time - 0.2:
            break

    # Extend end_idx forward until we hit a clean sentence end (up to +10s grace)
    while end_idx + 1 < len(segments):
        if _is_clean_sentence_end(segments, end_idx):
            break
        if segments[end_idx + 1]["end"] - segments[start_idx]["start"] > max_duration + 10:
            break
        end_idx += 1

    clean_start = _compute_safe_start_time(segments, start_idx)
    clean_end = _compute_safe_end_time(segments, end_idx, video_duration)
    return clean_start, clean_end


def _generate_lesson_title(full_text: str) -> str:
    """
    Generate a clean, meaningful lesson title from the clip's core statement.
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_text) if len(s.strip().split()) >= 5]
    if not sentences:
        sentences = [full_text.strip()]

    best_sentence = sentences[0]
    best_weight = -1

    for idx, sent in enumerate(sentences):
        low = sent.lower()
        weight = 3 if idx == 0 else 0
        for m in PREMISE_MARKERS + LESSON_TAKEAWAY_MARKERS:
            if m in low:
                weight += 4
        words = sent.split()
        if 6 <= len(words) <= 16:
            weight += 2
        if weight > best_weight:
            best_weight = weight
            best_sentence = sent

    cleaned = re.sub(
        r"^(and |but |so |look,? |listen,? |you know,? |i mean,? |like,? |right\??\s*)+",
        "",
        best_sentence,
        flags=re.IGNORECASE,
    ).strip()

    cleaned = re.sub(r'[.!?"]+$', "", cleaned).strip()
    words = cleaned.split()
    if len(words) > 10:
        cleaned = " ".join(words[:10]) + "..."

    return cleaned[:1].upper() + cleaned[1:] if cleaned else "Core Lesson & Takeaway"


def analyze_transcript_heuristic(
    segments: list[dict],
    video_duration: float,
    silence_segments: list[dict],
    min_duration: int = 20,
    max_duration: int = 40,
) -> list[ClipInfo]:
    """
    Narrative & Lesson-Aware Analyzer (20-40s).
    Guarantees every clip starts at a clean sentence and finishes the entire closing thought.
    """
    logger.info(
        f"Running Lesson & Meaning Analyzer (target: {min_duration}-{max_duration}s)..."
    )
    if not segments:
        return []

    candidates = []
    n_segs = len(segments)
    ideal_duration = (min_duration + max_duration) / 2.0  # 30.0s for 20-40s

    for i in range(n_segs):
        if not _is_clean_sentence_start(segments, i):
            continue

        seg_start = _compute_safe_start_time(segments, i)
        accumulated_texts = []
        best_candidate_for_i = None

        for j in range(i, n_segs):
            accumulated_texts.append(segments[j]["text"].strip())
            raw_end = segments[j]["end"]
            dur = raw_end - seg_start

            if dur < min_duration:
                continue
            # Allow up to +4s grace if needed to finish a sentence cleanly
            if dur > max_duration + 4.0:
                break

            if not _is_clean_sentence_end(segments, j):
                continue

            full_text = " ".join(accumulated_texts).strip()
            words = full_text.split()
            word_count = len(words)
            words_per_sec = word_count / max(dur, 1.0)

            n_words = len(words)
            opening_text = " ".join(words[: max(10, int(n_words * 0.35))]).lower()
            closing_text = " ".join(words[int(n_words * 0.60) :]).lower()
            last_sentence = re.split(r"(?<=[.!?])\s+", full_text)[-1].lower()
            full_lower = full_text.lower()

            raw_score = 50.0
            reasons = []

            # 1. Premise / Topic Setup in Opening
            premise_hits = [m for m in PREMISE_MARKERS if m in opening_text]
            if premise_hits:
                raw_score += min(15.0, len(premise_hits) * 6.0)
                reasons.append("clear topic setup")

            # 2. Explanation / Reasoning Depth in Body
            explanation_hits = [m for m in EXPLANATION_MARKERS if m in full_lower]
            if explanation_hits:
                raw_score += min(12.0, len(explanation_hits) * 4.0)
                reasons.append("cause-and-effect context")

            # 3. Lesson / Actionable Takeaway in Closing & Final Sentence
            lesson_hits = [m for m in LESSON_TAKEAWAY_MARKERS if m in closing_text]
            final_sent_hits = [m for m in LESSON_TAKEAWAY_MARKERS if m in last_sentence]
            if lesson_hits:
                raw_score += min(18.0, len(lesson_hits) * 6.5)
                reasons.append("strong closing takeaway")
            if final_sent_hits:
                # Extra bonus when the very last sentence lands a punchline/takeaway
                raw_score += 8.0

            # 4. Bonus if there is a natural speaker pause after segment `j` (proves thought is finished)
            if j + 1 < n_segs:
                pause_after = segments[j + 1]["start"] - segments[j]["end"]
                if pause_after >= 0.40:
                    raw_score += 7.0
                elif pause_after >= 0.20:
                    raw_score += 3.5

            # 5. Duration Sweet Spot (~25-36s)
            dist_from_ideal = abs(dur - ideal_duration)
            raw_score += max(0.0, 6.0 - (dist_from_ideal * 0.45))

            # 6. Engaging Speech Pace
            if 2.2 <= words_per_sec <= 4.0:
                raw_score += 4.0

            if best_candidate_for_i is None or raw_score > best_candidate_for_i["raw_score"]:
                safe_end = _compute_safe_end_time(segments, j, video_duration)
                title = _generate_lesson_title(full_text)
                reason_str = (
                    "Complete 3-part lesson: " + ", ".join(reasons) + "."
                    if reasons
                    else "Self-contained insight with complete start and finish."
                )
                best_candidate_for_i = {
                    "start_time": seg_start,
                    "end_time": safe_end,
                    "duration": round(safe_end - seg_start, 2),
                    "raw_score": raw_score,
                    "title": title,
                    "text": full_text,
                    "reason": reason_str,
                }

        if best_candidate_for_i and best_candidate_for_i["raw_score"] >= 62.0:
            candidates.append(best_candidate_for_i)

    candidates.sort(key=lambda c: c["raw_score"], reverse=True)
    selected = []

    for cand in candidates:
        overlap = False
        for s in selected:
            inter_start = max(cand["start_time"], s["start_time"])
            inter_end = min(cand["end_time"], s["end_time"])
            if inter_end > inter_start:
                if (inter_end - inter_start) > min(cand["duration"], s["duration"]) * 0.30:
                    overlap = True
                    break
        if not overlap:
            selected.append(cand)
        if len(selected) >= 6:
            break

    clips = []
    if selected:
        max_raw = selected[0]["raw_score"]
        for rank, item in enumerate(selected, 1):
            diff = max_raw - item["raw_score"]
            calibrated = int(min(96, max(74, round(95 - (rank - 1) * 2.5 - (diff * 0.5)))))
            text = item["text"]
            quote_preview = f"\"{text}\"" if len(text) <= 260 else f"\"{text[:120]} ... {text[-120:]}\""
            clips.append(
                ClipInfo(
                    rank=rank,
                    virality_score=calibrated,
                    title=item["title"],
                    description=quote_preview,
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    duration=item["duration"],
                    reason=item["reason"],
                    thumbnail_time=item["start_time"] + (item["duration"] / 2),
                )
            )

    logger.info(f"Lesson Analyzer selected {len(clips)} complete clips.")
    return clips


def analyze_transcript(
    segments: list[dict],
    video_duration: float,
    silence_segments: list[dict],
    api_key: Optional[str] = None,
    min_duration: Optional[int] = None,
    max_duration: Optional[int] = None,
) -> list[ClipInfo]:
    """
    Analyze transcript segments using Gemini to find meaningful, viral lesson clips (20-40s).
    Falls back to the Narrative & Lesson-Aware Local Engine if API key is not configured.
    """
    min_dur = min_duration or settings.TARGET_CLIP_DURATION_MIN
    max_dur = max_duration or settings.TARGET_CLIP_DURATION_MAX
    effective_key = api_key or settings.GEMINI_API_KEY

    if not effective_key:
        logger.info("Using Narrative & Lesson-Aware Local AI Engine.")
        return analyze_transcript_heuristic(
            segments, video_duration, silence_segments, min_dur, max_dur
        )

    genai.configure(api_key=effective_key)

    formatted_segments = _format_segments(segments)
    formatted_silence = _format_silence(silence_segments)

    prompt = f"""You are an expert short-form video producer and storyteller. Analyze this transcript and extract 3 to 6 of the most impactful, viral-worthy clips ({min_dur}-{max_dur} seconds each) that deliver a COMPLETE LESSON, MEANINGFUL INSIGHT, or STORY TAKEAWAY.

VIDEO DURATION: {video_duration:.1f} seconds

TIMESTAMPED TRANSCRIPT:
{formatted_segments}

DEAD AIR / SILENCE SEGMENTS:
{formatted_silence}

CRITICAL RULES FOR SELECTION:
1. DURATION: Every clip MUST be between {min_dur} and {max_dur} seconds long (aim for 25-35 seconds).
2. NEVER CUT OFF SENTENCES: Never start a clip mid-sentence, and NEVER end a clip before the speaker completely finishes their sentence and thought.
3. COMPLETE LESSON / MEANING: Each clip must have a full 3-part narrative arc:
   - Hook / Setup: Introduces the idea, problem, or story.
   - Context / Explanation: Explains why it matters or shares the experience.
   - Lesson / Takeaway: Ends with a complete concluding sentence that gives the viewer real value.
4. Rank them by viral & educational impact (most impactful first).

Return a JSON array with this EXACT format:
[
  {{
    "rank": 1,
    "virality_score": 95,
    "title": "Compelling title summarizing the core lesson",
    "description": "Summary of the lesson taught in this clip",
    "start_time": 45.2,
    "end_time": 75.8,
    "reason": "Delivers a complete lesson on leadership with a strong setup and actionable takeaway."
  }}
]
"""

    model = genai.GenerativeModel("gemini-2.0-flash")

    last_error = None
    for attempt in range(3):
        try:
            logger.info(f"Sending transcript to Gemini 2.0 Flash (attempt {attempt + 1}/3)...")
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.4,
                    max_output_tokens=4096,
                ),
            )

            response_text = response.text.strip()
            if response_text.startswith("```"):
                response_text = re.sub(r"^```(?:json)?\s*\n?", "", response_text)
                response_text = re.sub(r"\n?```\s*$", "", response_text)

            clips_data = json.loads(response_text)

            clips = []
            for clip_data in clips_data:
                raw_start = float(clip_data["start_time"])
                raw_end = float(clip_data["end_time"])
                start, end = _snap_clip_to_complete_sentences(
                    raw_start, raw_end, segments, video_duration, max_dur
                )
                clip = ClipInfo(
                    rank=int(clip_data["rank"]),
                    virality_score=int(clip_data["virality_score"]),
                    title=clip_data["title"],
                    description=clip_data["description"],
                    start_time=start,
                    end_time=end,
                    duration=round(end - start, 2),
                    reason=clip_data["reason"],
                    thumbnail_time=start + (end - start) / 2,
                )
                clips.append(clip)

            clips.sort(key=lambda c: c.rank)
            logger.info(f"Gemini identified {len(clips)} complete lesson clips.")
            return clips

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Gemini attempt {attempt + 1} failed: {last_error}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    logger.warning(
        f"Gemini analysis unsuccessful ({last_error}). Falling back to Narrative & Lesson Engine."
    )
    return analyze_transcript_heuristic(
        segments, video_duration, silence_segments, min_dur, max_dur
    )

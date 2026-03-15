"""OpenAI Vision API client for label/document analysis (GPT-4o-mini)."""
import base64
import json
import logging
import re

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    timeout=300.0,
    max_retries=2,
)

MODEL = settings.openai_model


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from AI response, handling markdown code blocks."""
    text = raw.strip()

    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("First JSON parse failed at pos %d: %s", e.pos, e.msg)
        # Try extracting JSON block
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Try fixing common issues: unescaped quotes in string values
        try:
            fixed = _fix_json_string(text)
            return json.loads(fixed)
        except (json.JSONDecodeError, Exception) as e2:
            logger.warning("JSON repair also failed: %s", e2)
        logger.error("Failed to parse JSON from OpenAI response, returning raw text")
        return {"raw_response": text, "checks": [], "extracted_text": text}


def _fix_json_string(text: str) -> str:
    """Attempt to fix JSON with unescaped quotes inside string values."""
    # Strategy: find string values and escape internal quotes
    result = []
    i = 0
    in_string = False
    string_start = -1

    while i < len(text):
        ch = text[i]
        if ch == '\\' and in_string:
            result.append(ch)
            i += 1
            if i < len(text):
                result.append(text[i])
            i += 1
            continue
        if ch == '"':
            if not in_string:
                in_string = True
                string_start = i
                result.append(ch)
            else:
                # Check if this quote ends the string or is internal
                # Look ahead: after closing quote should be , or } or ] or : or whitespace
                rest = text[i + 1:].lstrip()
                if rest and rest[0] in ',:}]':
                    in_string = False
                    result.append(ch)
                elif not rest:
                    in_string = False
                    result.append(ch)
                else:
                    # Likely an unescaped internal quote
                    result.append('\\"')
                    i += 1
                    continue
        else:
            result.append(ch)
        i += 1

    return ''.join(result)


async def analyze_image(image_bytes: bytes, prompt: str, mime_type: str = "image/png") -> str:
    """Send an image to OpenAI Vision API."""
    image_base64 = base64.b64encode(image_bytes).decode()

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}",
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=16384,
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content


async def analyze_multi_image(images: list[bytes], prompt: str) -> str:
    """Send multiple images to OpenAI Vision API."""
    content = [{"type": "text", "text": prompt}]

    for img_bytes in images:
        img_b64 = base64.b64encode(img_bytes).decode()
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{img_b64}",
                "detail": "high",
            },
        })

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": content}],
        max_tokens=16384,
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content


async def analyze_with_structured_output(
    image_bytes: bytes | None,
    pdf_bytes: bytes | None,
    filename: str,
    prompt: str,
    mime_type: str = "image/png",
) -> dict:
    """Analyze a document and return structured JSON."""
    if image_bytes:
        raw = await analyze_image(image_bytes, prompt, mime_type)
    elif pdf_bytes:
        raise ValueError("PDF bytes not supported directly, convert to PNG first")
    else:
        raise ValueError("Either image_bytes or pdf_bytes must be provided")

    return _parse_json_response(raw)


async def analyze_with_structured_output_multi(
    images: list[bytes],
    prompt: str,
) -> dict:
    """Analyze multiple images and return structured JSON."""
    raw = await analyze_multi_image(images, prompt)
    return _parse_json_response(raw)

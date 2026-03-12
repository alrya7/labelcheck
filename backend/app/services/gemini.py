"""Google Gemini API client for label/document analysis."""
import base64
import json
import logging
import re

from google import genai

from app.config import settings

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.gemini_api_key)

MODEL = settings.gemini_model


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from AI response, handling markdown code blocks."""
    text = raw.strip()

    # Remove markdown code block wrapper
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning("Failed to parse JSON from Gemini response, returning raw text")
        return {"raw_response": text, "checks": [], "extracted_text": text}


async def analyze_image(image_bytes: bytes, prompt: str, mime_type: str = "image/png") -> str:
    """Send an image to Gemini Vision API and get analysis."""
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            prompt,
            genai.types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=genai.types.GenerateContentConfig(
            max_output_tokens=16384,
            temperature=0.1,
        ),
    )
    return response.text


async def analyze_multi_image(images: list[bytes], prompt: str) -> str:
    """Send multiple images to Gemini Vision API."""
    contents = [prompt]
    for img_bytes in images:
        contents.append(
            genai.types.Part.from_bytes(data=img_bytes, mime_type="image/png")
        )

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=genai.types.GenerateContentConfig(
            max_output_tokens=16384,
            temperature=0.1,
        ),
    )
    return response.text


async def analyze_with_structured_output(
    image_bytes: bytes | None,
    pdf_bytes: bytes | None,
    filename: str,
    prompt: str,
    mime_type: str = "image/png",
) -> dict:
    """Analyze a document and return structured JSON."""
    if pdf_bytes:
        # For PDF, send as inline data
        raw = await analyze_image(pdf_bytes, prompt, "application/pdf")
    elif image_bytes:
        raw = await analyze_image(image_bytes, prompt, mime_type)
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

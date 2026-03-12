import base64
import json
import logging
import re

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    api_key=settings.moonshot_api_key,
    base_url=settings.moonshot_base_url,
    timeout=300.0,
    max_retries=3,
)

MODEL = settings.moonshot_model


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from AI response, handling markdown code blocks and edge cases."""
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
        # Try to find JSON object in the text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Last resort: return raw text as structured response
        logger.warning("Failed to parse JSON from Moonshot response, returning raw text")
        return {"raw_response": text, "checks": [], "extracted_text": text}


async def analyze_image(image_bytes: bytes, prompt: str, mime_type: str = "image/png") -> str:
    """Send an image to Kimi Moonshot Vision API and get analysis."""
    image_base64 = base64.b64encode(image_bytes).decode()

    response = await client.chat.completions.create(
        model="kimi-latest",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
                    },
                ],
            }
        ],
        max_tokens=16384,
    )

    return response.choices[0].message.content


async def analyze_multi_image(images: list[bytes], prompt: str) -> str:
    """Send multiple images to Kimi Moonshot Vision API (e.g., multi-page PDF)."""
    content = [{"type": "text", "text": prompt}]

    for img_bytes in images:
        img_b64 = base64.b64encode(img_bytes).decode()
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img_b64}"},
        })

    response = await client.chat.completions.create(
        model="kimi-latest",
        messages=[{"role": "user", "content": content}],
        max_tokens=16384,
    )

    return response.choices[0].message.content


async def analyze_pdf(pdf_bytes: bytes, filename: str, prompt: str) -> str:
    """Upload a PDF to Moonshot Files API, extract content, and analyze it."""
    file_object = await client.files.create(
        file=(filename, pdf_bytes, "application/pdf"),
        purpose="file-extract",
    )

    try:
        file_content = (await client.files.content(file_id=file_object.id)).text

        response = await client.chat.completions.create(
            model="moonshot-v1-128k",
            messages=[
                {"role": "system", "content": "You are an expert document analyst."},
                {"role": "system", "content": file_content},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    finally:
        await client.files.delete(file_object.id)


async def analyze_with_structured_output(
    image_bytes: bytes | None,
    pdf_bytes: bytes | None,
    filename: str,
    prompt: str,
    mime_type: str = "image/png",
) -> dict:
    """Analyze a document and return structured JSON."""
    if pdf_bytes:
        raw = await analyze_pdf(pdf_bytes, filename, prompt)
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

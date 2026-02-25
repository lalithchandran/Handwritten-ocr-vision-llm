from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from openai import OpenAI
from PIL import Image
import base64
import io
import uvicorn

# -----------------------------
# FastAPI Initialization
# -----------------------------
app = FastAPI(title="Handwritten OCR API")

# -----------------------------
# LLaMA.cpp Client
# -----------------------------
client = OpenAI(
    base_url="http://localhost:7979/v1",
    api_key="sk-no-key-required"
)

MODEL_NAME = "Qwen3VL-2B-Instruct-Q4_K_M.gguf"

# -----------------------------
# SYSTEM PROMPT (Strict OCR)
# -----------------------------
SYSTEM_PROMPT = """
You are an advanced OCR engine specialized in extracting text from handwritten documents.

Rules:
- Accurately transcribe handwritten text.
- Preserve original line breaks and formatting.
- Do NOT correct spelling.
- Do NOT summarize.
- Do NOT interpret meaning.
- Do NOT repeat content.
- Stop when transcription ends.
- If unreadable, write [unclear].
- If partially readable, write [word?].

Return ONLY the extracted text.
"""

# -----------------------------
# Utility: Resize + Encode Image
# -----------------------------
def preprocess_image(image_bytes: bytes) -> str:
    image = Image.open(io.BytesIO(image_bytes))
    image = image.convert("RGB")

    # Resize to avoid llama.cpp memory crash
    image.thumbnail((1024, 1024))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# -----------------------------
# OCR Endpoint
# -----------------------------
@app.post("/extract-ocr")
async def extract_ocr(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        image_base64 = preprocess_image(image_bytes)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract the handwritten text from this image."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,

            # 🔥 STABLE OCR SETTINGS (NO LOOPING)
            temperature=0.2,
            top_p=0.9,
            max_tokens=512,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            stop=["\n\n\n", "</s>"]
        )

        extracted_text = response.choices[0].message.content.strip()

        return {
            "status": "success",
            "extracted_text": extracted_text
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e)
            }
        )

# -----------------------------
# Health Check
# -----------------------------
@app.get("/")
def health():
    return {"message": "OCR API is running"}

# -----------------------------
# Run Server
# -----------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
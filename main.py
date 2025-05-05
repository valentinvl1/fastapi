from fastapi import FastAPI, UploadFile, File, HTTPException
import fitz  # PyMuPDF
import base64

app = FastAPI()


@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}


@app.post("/extract-text")
async def extract_pdf_text(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    content = await file.read()
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire le fichier PDF.")

    pages = []
    for i, page in enumerate(pdf, start=1):
        text = page.get_text().strip()
        pages.append({
            "page": i,
            "text": text
        })

    return {
        "filename": file.filename,
        "page_count": len(pages),
        "pages": pages
    }


@app.post("/extract-text-and-images")
async def extract_pdf_text_and_images(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    content = await file.read()
    try:
        pdf = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire le fichier PDF.")

    pages = []

    for i, page in enumerate(pdf, start=1):
        page_dict = {
            "page": i,
            "text": page.get_text().strip(),
            "images": []
        }

        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block["type"] == 1:  # bloc image
                xref = block.get("image_xref")
                if xref:
                    try:
                        image_info = pdf.extract_image(xref)
                        image_bytes = image_info["image"]
                        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                        page_dict["images"].append({
                            "image_id": xref,
                            "bbox": block["bbox"],
                            "ext": image_info["ext"],
                            "base64": image_base64
                        })
                    except Exception as e:
                        print(f"Erreur d'extraction image: {e}")

        pages.append(page_dict)

    return {
        "filename": file.filename,
        "page_count": len(pdf),
        "pages": pages
    }

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


@app.post("/extract-images-real")
async def extract_images_from_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    content = await file.read()
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire le fichier PDF.")

    pages = []

    for page_index, page in enumerate(doc):
        images_data = []
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list, start=1):
            xref = img[0]
            try:
                image_info = doc.extract_image(xref)
                image_bytes = image_info["image"]
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                images_data.append({
                    "image_id": f"{page_index+1}-{xref}",
                    "ext": image_info["ext"],
                    "base64": image_base64
                })
            except Exception as e:
                print(f"Erreur extraction image : {e}")

        pages.append({
            "page": page_index + 1,
            "images": images_data
        })

    return {
        "filename": file.filename,
        "page_count": len(doc),
        "pages": pages
    }

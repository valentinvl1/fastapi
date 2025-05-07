from fastapi import FastAPI, UploadFile, File, HTTPException
import fitz  # PyMuPDF
import base64
import logging

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



@app.post("/extract-all")
async def extract_pdf_text_and_images(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    content = await file.read()
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire le fichier PDF.")

    image_counter = 1
    xref2id = {}           # mapping xref -> image ID
    images_payload = []    # toutes les images du document
    pages_payload = []     # texte avec placeholders par page

    for page_index, page in enumerate(doc, start=1):
        page_text = []
        used_xrefs = set()

        # Étape 1 : détecter toutes les images de la page
        page_xrefs = [img[0] for img in page.get_images(full=True)]

        # Étape 2 : extraire chaque image (une seule fois dans tout le doc)
        for xref in page_xrefs:
            if xref in xref2id:
                continue
            try:
                img_info = doc.extract_image(xref)
                if not img_info or "image" not in img_info:
                    continue
                image_id = f"image{image_counter}"
                xref2id[xref] = image_id
                images_payload.append({
                    "id": image_id,
                    "ext": img_info.get("ext", "png"),
                    "base64": base64.b64encode(img_info["image"]).decode()
                })
                image_counter += 1
            except Exception as e:
                logging.warning(f"[Page {page_index}] Erreur image (xref={xref}) : {e}")

        # Étape 3 : lire le texte de la page avec placeholders d'images
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if block["type"] == 0:  # texte
                for line in block["lines"]:
                    for span in line["spans"]:
                        page_text.append(span["text"])
            elif block["type"] == 1:  # image
                xref = block.get("xref")
                if xref and xref in xref2id:
                    image_id = xref2id[xref]
                    page_text.append(f"{{{{{image_id}}}}}")
                    used_xrefs.add(xref)
                # sinon : image inline ou non extractible => on ne met rien

        # Étape 4 : insérer les images orphelines non déjà placées
        for xref in page_xrefs:
            if xref in xref2id and xref not in used_xrefs:
                image_id = xref2id[xref]
                page_text.append(f"{{{{{image_id}}}}}")

        # Stocker la page
        pages_payload.append({
            "page": page_index,
            "text": " ".join(page_text).strip()
        })

    return {
        "filename": file.filename,
        "page_count": len(doc),
        "pages": pages_payload,
        "images": images_payload
    }

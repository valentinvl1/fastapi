from fastapi import FastAPI, UploadFile, File, HTTPException
import fitz, base64, logging, traceback

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
async def extract_all(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    content = await file.read()
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception:
        raise HTTPException(status_code=400, detail="Impossible de lire le fichier PDF.")

    image_counter   = 1                 # compteur global
    xref2id         = {}                # {xref -> imageN}
    images_payload  = []                # liste finale pour la réponse
    pages_payload   = []                # texte page par page

    for page_index, page in enumerate(doc, start=1):

        # A/ — détecter tous les XRef de la page
        page_xrefs = [img[0] for img in page.get_images(full=True)]

        # B/ — extraire chaque xref (une seule fois dans tout le doc)
        for xref in page_xrefs:
            if xref in xref2id:        # déjà extrait sur une page précédente
                continue
            try:
                img_info = doc.extract_image(xref)
                if not img_info or "image" not in img_info:
                    raise ValueError("Image non extractible")
                image_id = f"image{image_counter}"
                xref2id[xref] = image_id
                images_payload.append({
                    "id":     image_id,
                    "ext":    img_info.get("ext", "png"),
                    "base64": base64.b64encode(img_info["image"]).decode()
                })
                image_counter += 1
            except Exception as e:
                logging.warning("Skip xref %s (page %s) : %s", xref, page_index, e)

        # C/ — construire le texte avec placeholders
        used_xrefs   = set()
        page_text    = []

        for block in page.get_text("dict")["blocks"]:
            if block["type"] == 0:                            # texte
                for line in block["lines"]:
                    for span in line["spans"]:
                        page_text.append(span["text"])

            elif block["type"] == 1:                          # image
                xref = block.get("xref")
                used_xrefs.add(xref)
                image_id = xref2id.get(xref)
                placeholder = f"{{{{{image_id}}}}}" if image_id else "{{image-error}}"
                page_text.append(placeholder)

        # D/ — ajouter les images “orphelines” (présentes dans la page mais sans block)
        for xref in page_xrefs:
            if xref not in used_xrefs:
                image_id = xref2id.get(xref)
                placeholder = f"{{{{{image_id}}}}}" if image_id else "{{image-error}}"
                page_text.append(placeholder)

        pages_payload.append({
            "page": page_index,
            "text": " ".join(page_text).strip()
        })

    return {
        "filename": file.filename,
        "page_count": len(doc),
        "pages": pages_payload,   # texte + {{imageN}} page par page
        "images": images_payload  # toutes les images du doc, une seule fois chacune
    }

## Reference-image-driven refinement (user sends a design reference)
- When the user says a direction is drifting ("越来越歪了,等我给你个对比的") and offers a reference, they will paste an image or a text list. **The reference IS the spec** — copy row text verbatim, preserve row order, don't invent or rename rows. Two rejections on the same module = ask for the reference instead of iterating blind.
- If the reference is an **image** and no vision tool is available (`tool_search` finds nothing), OCR it — this works reliably for UI screenshots:
  ```
  pip install rapidocr-onnxruntime onnxruntime
  python -c "from rapidocr_onnxruntime import RapidOCR; ocr=RapidOCR(); res,_=ocr('<img path>'); [print(l[1]) for l in res]"
  ```
  (pytesseract may be pre-installed but needs the tesseract binary, which is usually absent on Windows; rapidocr is self-contained and bundles a Chinese model.)
- Extract the full field list from the OCR text (title/subtitle, inputs, buttons, checkbox copy, helper lines, summary cards) and rebuild the form field-for-field — the user compares against their screenshot, not against your paraphrase.


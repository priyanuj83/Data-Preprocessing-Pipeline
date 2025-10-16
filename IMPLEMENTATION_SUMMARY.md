# Image Metadata & Positioning - Implementation Summary

## ✅ What Was Implemented

### 1. Independent Image Metadata JSON (NEW Feature)

**File Generated:** `{document}_images.json`

**Purpose:** Stores all image extraction data independently from OCR/text extraction flow.

**Structure:**
```json
{
  "total_images": 3,
  "images": [
    {
      "filename": "page1_img1.png",
      "page": 1,
      "position_type": "header/logo",
      "bbox": {
        "x1": 50.5,
        "y1": 30.2,
        "x2": 250.8,
        "y2": 120.5
      },
      "dimensions": {
        "width": 200.3,
        "height": 90.3
      },
      "path": ".../HW01_assets/page1_img1.png"
    }
  ]
}
```

**Key Fields:**
- `filename`: Image file name
- `page`: Which PDF page it's from
- `position_type`: `"header/logo"`, `"content"`, or `"footer"`
- `bbox`: Precise coordinates (x1, y1, x2, y2)
- `dimensions`: Width and height in pixels
- `path`: Absolute path to extracted image

---

## 2. How Image Positioning Works

### Position Classification (Automatic)

```python
# Code in smart_latex_reconstructor.py
y_pos = bbox[1]  # Top Y coordinate
if y_pos < page_height * 0.2:
    position_type = "header/logo"     # Top 20%
elif y_pos > page_height * 0.8:
    position_type = "footer"          # Bottom 20%
else:
    position_type = "content"         # Middle 60%
```

### Visual Diagram:

```
PDF Page (1700px height @ 200 DPI)
┌─────────────────────────────────────┐
│  0-340px (0-20%)                    │
│  → "header/logo"                    │ ← ASU Logo (y=30)
├─────────────────────────────────────┤
│                                     │
│  340-1360px (20-80%)                │
│  → "content"                        │ ← Figures, Diagrams (y=500, y=900)
│                                     │
├─────────────────────────────────────┤
│  1360-1700px (80-100%)              │
│  → "footer"                         │ ← Footer images
└─────────────────────────────────────┘
```

---

## 3. How GPT-4 Vision Maintains Correct Positioning

### Example: Quiz with Images at Different Positions

**Scenario:**
- Header: ASU logo (y=30)
- Q1: Diagram (y=500)
- Q2: No image
- Q3: Circuit diagram (y=400 on page 2)

### GPT-4's Process:

#### Step 1: Receives Rich Context
```python
{
    "original_pages": [image1.png, image2.png],  # Visual reference
    "ocr_data": {
        "page 1": "Q1: Draw...\nQ2: Explain...",
        "page 2": "Q3: Analyze..."
    },
    "extracted_images": [
        {"filename": "page1_img1.png", "page": 1, "bbox": [50, 30, 250, 120]},   # Logo
        {"filename": "page1_img2.png", "page": 1, "bbox": [100, 500, 400, 700]}, # Q1
        {"filename": "page2_img1.png", "page": 2, "bbox": [120, 400, 380, 600]}  # Q3
    ]
}
```

#### Step 2: Visual Correlation
```
GPT-4 SEES:
  - Logo at top of page 1
  - "Q1:" text at y≈300
  - Diagram below Q1 at y≈500
  - "Q2:" text at y≈800
  - NO IMAGE near Q2
  - "Q3:" text on page 2
  - Diagram below Q3

GPT-4 MATCHES:
  - page1_img1.png (y=30) → Logo in header
  - page1_img2.png (y=500) → Q1 diagram
  - page2_img1.png (y=400) → Q3 diagram
```

#### Step 3: Generates LaTeX with Correct Placement
```latex
% Logo from page1_img1.png (y=30, header)
\includegraphics[width=4cm]{page1_img1.png}

% Q1 with figure from page1_img2.png (y=500, content)
\textbf{Q1.} Draw a diagram...
\begin{figure}[h]
\includegraphics[width=0.6\textwidth]{page1_img2.png}
\end{figure}

% Q2 - NO IMAGE (GPT-4 saw none at Q2 position)
\textbf{Q2.} Explain the concept...

% Q3 with diagram from page2_img1.png (page 2, y=400)
\newpage
\textbf{Q3.} Analyze the circuit...
\begin{figure}[h]
\includegraphics[width=0.7\textwidth]{page2_img1.png}
\end{figure}
```

---

## 4. Attack Engine Integration

### Use Case 1: Identify Perturbable Images

```python
import json

with open('HW01_images.json') as f:
    img_data = json.load(f)

# Find content images (figures/diagrams) for perturbation
content_images = [
    img for img in img_data['images'] 
    if img['position_type'] == 'content'
]

print(f"Found {len(content_images)} perturbable images")
for img in content_images:
    print(f"  - {img['filename']} on page {img['page']}")
```

### Use Case 2: Position-Based Attacks

```python
# Attack only images in specific regions
for img in img_data['images']:
    y_pos = img['bbox']['y1']
    
    if 300 < y_pos < 800:
        print(f"Image in Q1 region: {img['filename']}")
        # Apply Q1-specific perturbation
        
    elif 800 < y_pos < 1200:
        print(f"Image in Q2 region: {img['filename']}")
        # Apply Q2-specific perturbation
```

### Use Case 3: Skip Logos

```python
# Don't perturb institutional logos
for img in img_data['images']:
    if img['position_type'] == 'header/logo':
        print(f"Skipping logo: {img['filename']}")
    else:
        print(f"Perturbing: {img['filename']}")
```

---

## 5. Files Generated (Complete List)

### After LaTeX Reconstruction:

```
Output/latex_reconstruction/
├── HW01.tex                    # LaTeX source
├── HW01.pdf                    # Compiled PDF (if enabled)
├── HW01_images.json           # 🆕 Image metadata (independent)
├── HW01_original.json         # Mistral OCR text
├── HW01_structured.json       # PyMuPDF text structure
└── HW01_assets/
    └── page1_img1.png         # Extracted images
```

### Why Three JSON Files?

| File | Purpose | Contains |
|------|---------|----------|
| `HW01_original.json` | Mistral OCR output | Text content, markdown |
| `HW01_structured.json` | PyMuPDF structure | Text blocks, no images |
| `HW01_images.json` | **Image metadata** | **Extracted image data** ✨ |

---

## 6. Code Changes Summary

### Files Modified:

1. **`src/smart_latex_reconstructor.py`**
   - Added `_save_images_metadata()` method
   - Integrated metadata saving in reconstruction workflow
   - Updated return dictionary to include `images_metadata` path

2. **`src/pipeline.py`**
   - Added logging for images metadata file
   - Shows `✓ Images metadata: {filename}` in output

### Key Methods:

```python
def _save_images_metadata(self, extracted_images, json_path):
    """Save extracted images metadata to structured JSON"""
    metadata = {
        "total_images": len(extracted_images),
        "images": [...]
    }
    with open(json_path, 'w') as f:
        json.dump(metadata, f, indent=2)
```

---

## 7. Testing & Verification

### Run the Pipeline:
```bash
python main.py Dataset/HW01.pdf --enable-latex --latex-compile
```

### Expected Output:
```
[3/6] Extracting images from PDF...
[OK] Extracted 1 image(s)
[OK] Saved image metadata: HW01_images.json

[OK] LaTeX reconstruction complete!
Generated files:
  ✓ LaTeX source: HW01.tex
  ✓ Compiled PDF: HW01.pdf
  ✓ Assets directory: HW01_assets/
  ✓ Images metadata: HW01_images.json  ← NEW!
```

---

## 8. Benefits for Attack Engine

✅ **Independent Data Flow**
- Image metadata separate from OCR/text extraction
- No dependency on Mistral or PyMuPDF text output

✅ **Rich Positioning Data**
- Exact coordinates (bbox)
- Automatic classification (header/content/footer)
- Page-aware tracking

✅ **Attack Strategy Support**
- Identify which images to perturb
- Know image context (logo vs. content)
- Track image-to-question mapping

✅ **Structured & Accessible**
- Clean JSON format
- Easy to parse and query
- Integrates seamlessly with attack pipeline

---

## Next Steps

1. ✅ Image metadata saved independently
2. ✅ Position classification implemented
3. ✅ GPT-4 Vision uses positions correctly
4. → **Ready for attack engine integration!**

Your attack engine can now:
- Load `{document}_images.json`
- Identify perturbable images
- Apply targeted visual perturbations
- Maintain document structure

🎯 **Complete pipeline ready for adversarial testing!**


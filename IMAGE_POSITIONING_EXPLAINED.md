# Image Positioning in LaTeX Reconstruction

## How Image Positioning Works

### 1. Image Metadata JSON (NEW - Independent File)

Each LaTeX reconstruction now generates `{document}_images.json`:

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
    },
    {
      "filename": "page2_img1.png",
      "page": 2,
      "position_type": "content",
      "bbox": {
        "x1": 100.0,
        "y1": 500.0,
        "x2": 400.0,
        "y2": 700.0
      },
      "dimensions": {
        "width": 300.0,
        "height": 200.0
      },
      "path": ".../HW01_assets/page2_img1.png"
    }
  ]
}
```

### 2. Position Classification

Images are automatically classified by their Y-position on the page:

```
PDF Page (height = 1700px @ 200 DPI)
┌─────────────────────────────────────┐
│  0-340px (0-20%)    → header/logo   │ ← ASU Logo here
├─────────────────────────────────────┤
│                                     │
│                                     │
│  340-1360px (20-80%) → content      │ ← Diagrams/Figures
│                                     │
│                                     │
├─────────────────────────────────────┤
│  1360-1700px (80-100%) → footer     │ ← Footer images
└─────────────────────────────────────┘
```

**Code:**
```python
y_pos = bbox[1]  # Top Y coordinate
if y_pos < page_height * 0.2:
    position_type = "header/logo"
elif y_pos > page_height * 0.8:
    position_type = "footer"
else:
    position_type = "content"
```

---

## How GPT-4 Vision Maintains Positioning

### Example Scenario: Quiz with Mixed Images

**Input PDF has:**
- Page 1: Logo at header (y=30)
- Page 1: Figure in Q1 (y=500)
- Page 1: No image in Q2
- Page 2: Diagram in Q3 (y=400)

### Step 1: GPT-4 Receives Rich Context

```python
# GPT-4 Vision receives:
{
    "original_pages": [image1.png, image2.png],  # Visual reference
    "ocr_data": {
        "page 1": "Q1: Draw a diagram...\nQ2: Explain...",
        "page 2": "Q3: Analyze the circuit..."
    },
    "extracted_images": [
        {
            "filename": "page1_img1.png",
            "page": 1,
            "position_type": "header/logo",
            "bbox": [50, 30, 250, 120]
        },
        {
            "filename": "page1_img2.png",
            "page": 1,
            "position_type": "content",
            "bbox": [100, 500, 400, 700]  # Near Q1
        },
        {
            "filename": "page2_img1.png",
            "page": 2,
            "position_type": "content",
            "bbox": [120, 400, 380, 600]  # Near Q3
        }
    ]
}
```

### Step 2: GPT-4's Visual Analysis

GPT-4 Vision:
1. **LOOKS** at `image1.png` (page 1 visual)
   - Sees logo at top
   - Sees "Q1: Draw a diagram" text
   - Sees figure below Q1
   - Sees "Q2: Explain" text with NO figure

2. **CORRELATES** visual position with metadata:
   - `page1_img1.png` → bbox y=30 → "This is the header logo"
   - `page1_img2.png` → bbox y=500 → "This is the Q1 figure"
   
3. **UNDERSTANDS** context:
   - Logo should be in document header (once)
   - Q1 figure should be AFTER "Q1:" text
   - Q2 has NO figure (no image near Q2 text)
   - Q3 figure should be AFTER "Q3:" text

### Step 3: GPT-4 Generates LaTeX

```latex
\documentclass[12pt]{article}
\usepackage{graphicx}
\graphicspath{{./HW01_assets/}}

\begin{document}

% Header with logo (page1_img1.png at y=30)
\noindent
\includegraphics[width=4cm]{page1_img1.png}

\vspace{1em}

% Question 1 with figure
\textbf{Q1.} Draw a diagram showing the process.

\begin{figure}[h]
\centering
\includegraphics[width=0.6\textwidth]{page1_img2.png}
\caption{Process diagram for Q1}
\end{figure}

% Question 2 - NO IMAGE (GPT-4 saw no image near Q2)
\textbf{Q2.} Explain the concept.

% (No image inserted here)

% Question 3 with diagram (page 2)
\newpage

\textbf{Q3.} Analyze the circuit shown below.

\begin{figure}[h]
\centering
\includegraphics[width=0.7\textwidth]{page2_img1.png}
\caption{Circuit diagram for Q3}
\end{figure}

\end{document}
```

---

## Key Intelligence: How GPT-4 Knows Where to Place Images

### 1. **Visual Position Matching**
```
GPT-4 sees in original image:
    "Q1: Draw..." at y=300
    Figure below at y=500
    
GPT-4 sees in metadata:
    page1_img2.png at bbox y=500
    
→ Conclusion: This figure belongs to Q1!
```

### 2. **Contextual Understanding**
```
OCR says: "Q1: Draw a diagram showing..."
Image metadata: page1_img2.png is nearby
→ Insert image AFTER Q1 text

OCR says: "Q2: Explain the concept"
NO image metadata near this Y position
→ DO NOT insert any image
```

### 3. **Page Awareness**
```
page1_img1.png → page 1, position "header/logo"
→ Place at document start

page2_img1.png → page 2, position "content"
→ Place on page 2 (after \newpage)
```

---

## Example: Attack Engine Usage

Your attack engine can now use the images metadata:

```python
import json

# Load image metadata
with open('HW01_images.json') as f:
    img_data = json.load(f)

# Find images in specific questions
for img in img_data['images']:
    if img['position_type'] == 'content':
        # This is a figure/diagram in question content
        print(f"Figure: {img['filename']}")
        print(f"  Location: Page {img['page']}, Y={img['bbox']['y1']}")
        print(f"  Can be replaced for visual perturbation attacks")
        
    elif img['position_type'] == 'header/logo':
        # This is a logo - probably don't perturb
        print(f"Logo: {img['filename']} - skip perturbation")
```

---

## Summary

✅ **1. Independent Image Metadata JSON**
- Saved as `{document}_images.json`
- Contains all image positions, dimensions, classifications
- Independent of OCR/text extraction flow

✅ **2. Smart Positioning**
- GPT-4 Vision SEES the original document visually
- Correlates visual position with bbox metadata
- Understands context (which image belongs to which question)
- Generates LaTeX with correct image placement

✅ **3. Attack Engine Integration**
- Use `_images.json` to identify perturbable images
- Know exactly which images are content vs. logos
- Track positions for targeted attacks

---

## Files Generated

```
Output/latex_reconstruction/
├── HW01.tex                    # LaTeX source
├── HW01.pdf                    # Compiled PDF
├── HW01_images.json           # 🆕 Image metadata (independent)
├── HW01_original.json         # Mistral OCR (text only)
├── HW01_structured.json       # PyMuPDF structure (text only)
└── HW01_assets/
    └── page1_img1.png         # Extracted logo
```


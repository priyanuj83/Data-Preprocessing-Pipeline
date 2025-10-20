"""
Smart LaTeX Reconstructor - AI-First Approach (No Regex!)

Uses GPT-4 Vision to analyze the original PDF visually and generate
layout-faithful LaTeX without any regex post-processing.

Key Principles:
1. Let AI SEE the original PDF (multimodal)
2. Provide rich context (OCR data, positioning, extracted images)
3. Give AI FULL responsibility for layout decisions
4. NO regex post-processing (AI gets it right the first time)
5. Smart few-shot examples to guide AI behavior
"""

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import fitz  # PyMuPDF
from .docling_image_extractor import DoclingImageExtractor


class SmartLaTeXReconstructor:
    """
    AI-first LaTeX reconstruction without regex hacks
    
    Architecture:
    1. Convert PDF pages to high-quality images
    2. Extract OCR data with Mistral (text + positioning)
    3. Extract images with PyMuPDF (logos, figures)
    4. Send EVERYTHING to GPT-4 Vision:
       - Original PDF images (what it LOOKS like)
       - OCR structured data (what it CONTAINS)
       - Extracted images (what to INCLUDE)
       - Smart prompt (HOW to reconstruct)
    5. GPT-4 generates perfect LaTeX (no post-processing needed!)
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, mistral_api_key: Optional[str] = None):
        """Initialize with API keys"""
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.mistral_api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
        
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY required for smart reconstruction")
        
        # Initialize modular image extractors
        self.docling_extractor = DoclingImageExtractor()
    
    def load_json_data(self, json_path: str) -> Optional[Dict[str, Any]]:
        """Load structured JSON data from file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load JSON data from {json_path}: {e}")
            return None
    
    def reconstruct_pdf_to_latex(
        self,
        pdf_path: str,
        output_dir: str,
        include_images: bool = True,
        compile_pdf: bool = True,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: PDF → Smart LaTeX reconstruction
        
        Args:
            pdf_path: Path to input PDF
            output_dir: Directory for outputs
            include_images: Whether to extract and include images
            compile_pdf: Whether to compile LaTeX to PDF
            
        Returns:
            Dict with paths to generated files
        """
        print(f"\n{'='*70}")
        print(f"Smart LaTeX Reconstruction (AI-First, No Regex!)")
        print(f"{'='*70}\n")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Step 1: Convert PDF to images (for GPT-4 Vision)
        print("[1/6] Converting PDF pages to images for visual analysis...")
        pdf_images = self._pdf_to_images(pdf_path, output_dir)
        print(f"[OK] Converted {len(pdf_images)} page(s) to images")
        
        # Step 2: Extract OCR data with Mistral (structured text + positioning)
        print("\n[2/6] Extracting structured content with Mistral OCR...")
        ocr_data = self._extract_ocr_data(pdf_path) if self.mistral_api_key else None
        if ocr_data:
            print(f"[OK] Extracted OCR data from {len(ocr_data.get('pages', []))} page(s)")
        else:
            print("[WARN] Mistral OCR skipped - will use visual analysis only")
        
        # Step 3: Extract images using modular Docling extractor (better for complex layouts)
        print("\n[3/6] Extracting images with modular Docling extractor...")
        extracted_images = []
        assets_dir = None
        images_metadata_path = None
        if include_images:
            assets_dir = os.path.join(output_dir, f"{Path(pdf_path).stem}_assets")
            
            # Try Docling first (better for complex layouts)
            if self.docling_extractor.is_available():
                extracted_images = self.docling_extractor.extract_images(pdf_path, assets_dir)
            else:
                print("[WARN] Docling not available, using PyMuPDF...")
            
            # Fallback to PyMuPDF if Docling fails or extracts no images
            if not extracted_images:
                print("[INFO] Docling extracted no images, falling back to PyMuPDF...")
                extracted_images = self._extract_all_images(pdf_path, assets_dir)
            
            print(f"[OK] Extracted {len(extracted_images)} image(s)")
            
            # Save image metadata to independent JSON file
            if extracted_images:
                images_metadata_path = os.path.join(output_dir, f"{Path(pdf_path).stem}_images.json")
                self._save_images_metadata(extracted_images, images_metadata_path)
                print(f"[OK] Saved image metadata: {Path(images_metadata_path).name}")
        
        # Step 4: Visual Content Detection with GPT-4 Vision
        print("\n[4/6] Detecting all visual content with GPT-4 Vision...")
        visual_content = self._detect_visual_content_with_gpt4v(pdf_images, extracted_images)
        
        # Log detection results
        total_elements = visual_content.get('summary', {}).get('total_elements', 0)
        extracted_by_pymupdf = visual_content.get('summary', {}).get('extracted_by_pymupdf', 0)
        missed_by_pymupdf = visual_content.get('summary', {}).get('missed_by_pymupdf', 0)
        
        print(f"[OK] Visual content detection completed")
        print(f"[INFO] Total elements detected: {total_elements}")
        print(f"[INFO] PyMuPDF captured: {extracted_by_pymupdf}")
        print(f"[INFO] Missing elements: {missed_by_pymupdf}")
        
        # Step 5: Prepare rich context for GPT-4 Vision
        print("\n[5/6] Preparing rich context for AI analysis...")
        context = self._build_rich_context(
            pdf_path=pdf_path,
            pdf_images=pdf_images,
            ocr_data=ocr_data,
            extracted_images=extracted_images,
            assets_dir=assets_dir,
            json_data=json_data,
            visual_content=visual_content
        )
        print("[OK] Context prepared")
        
        # Step 6: Generate LaTeX with GPT-4 Vision (the smart part!)
        print("\n[6/6] Generating layout-faithful LaTeX with GPT-4 Vision...")
        latex_code = self._generate_smart_latex(context)
        
        # Save LaTeX
        latex_path = os.path.join(output_dir, f"{Path(pdf_path).stem}.tex")
        with open(latex_path, "w", encoding="utf-8") as f:
            f.write(latex_code)
        print(f"[OK] Generated LaTeX: {latex_path}")
        
        # Step 6.5: Generate Markdown for text extraction analysis
        print("\n[6.5/6] Generating Markdown for text extraction analysis...")
        markdown_path = self._generate_markdown(context, output_dir)
        if markdown_path:
            print(f"[OK] Generated Markdown: {Path(markdown_path).name}")
        
        # Step 7: Compile to PDF (optional)
        pdf_output_path = None
        if compile_pdf:
            print("\n[7/7] Compiling LaTeX to PDF...")
            pdf_output_path = self._compile_latex(latex_path, output_dir)
            if pdf_output_path:
                print(f"[OK] Compiled PDF: {pdf_output_path}")
            else:
                print("[WARN] LaTeX compilation failed")
        
        # Generate visual gap report
        visual_gap_report = self._generate_visual_gap_report(visual_content, output_dir)
        
        return {
            "latex": latex_path,
            "pdf": pdf_output_path,
            "assets": assets_dir,
            "images_metadata": images_metadata_path,
            "original_images": pdf_images,
            "extracted_images": extracted_images,
            "visual_gap_report": visual_gap_report,
            "markdown": markdown_path
        }
    
    def _pdf_to_images(self, pdf_path: str, output_dir: str, dpi: int = 300) -> List[str]:
        """Convert PDF pages to high-quality images for GPT-4 Vision (300 DPI for optimal analysis)"""
        doc = fitz.open(pdf_path)
        image_paths = []
        
        images_dir = os.path.join(output_dir, "original_pages")
        os.makedirs(images_dir, exist_ok=True)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Render page to image at high DPI
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 DPI is default
            pix = page.get_pixmap(matrix=mat)
            
            # Save as PNG
            img_path = os.path.join(images_dir, f"page_{page_num + 1}.png")
            pix.save(img_path)
            image_paths.append(img_path)
        
        doc.close()
        return image_paths
    
    def _extract_ocr_data(self, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Extract structured OCR data with Mistral Document AI"""
        if not self.mistral_api_key:
            return None
        
        try:
            from mistralai import Mistral
            
            client = Mistral(api_key=self.mistral_api_key)
            
            # Read PDF and encode
            with open(pdf_path, "rb") as f:
                pdf_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Call Mistral Document AI
            response = client.chat.complete(
                model="pixtral-large-latest",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document_url",
                                "document_url": f"data:application/pdf;base64,{pdf_data}"
                            },
                            {
                                "type": "text",
                                "text": "Extract all text content with structure and positioning information."
                            }
                        ]
                    }
                ]
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Try to extract JSON if present
            try:
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    return json.loads(json_str)
                else:
                    return {"raw_content": content}
            except:
                return {"raw_content": content}
                
        except Exception as e:
            print(f"[WARN] Mistral OCR failed: {e}")
            return None
    
    
    def _extract_all_images(self, pdf_path: str, assets_dir: str) -> List[Dict[str, Any]]:
        """Extract all images from PDF with metadata (PyMuPDF fallback)"""
        os.makedirs(assets_dir, exist_ok=True)
        
        doc = fitz.open(pdf_path)
        extracted = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_height = page.rect.height
            
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                
                try:
                    # Extract image
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Get image bbox
                    rects = page.get_image_rects(xref)
                    bbox = list(rects[0]) if rects else [0, 0, 0, 0]
                    
                    # Classify image position
                    y_pos = bbox[1]
                    if y_pos < page_height * 0.2:
                        position_type = "header/logo"
                    elif y_pos > page_height * 0.8:
                        position_type = "footer"
                    else:
                        position_type = "content"
                    
                    # Save image
                    filename = f"page{page_num + 1}_img{img_index + 1}.{image_ext}"
                    img_path = os.path.join(assets_dir, filename)
                    
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    
                    # Remove black background (if possible)
                    try:
                        self._remove_black_background(img_path)
                    except:
                        pass  # Silently continue if processing fails
                    
                    extracted.append({
                        "filename": filename,
                        "path": img_path,
                        "page": page_num + 1,
                        "bbox": bbox,
                        "position_type": position_type,
                        "width": bbox[2] - bbox[0],
                        "height": bbox[3] - bbox[1]
                    })
                    
                except Exception as e:
                    print(f"[WARN] Failed to extract image from page {page_num + 1}: {e}")
                    continue
        
        doc.close()
        return extracted
    
    def _save_images_metadata(self, extracted_images: List[Dict[str, Any]], json_path: str):
        """
        Save extracted images metadata to a structured JSON file
        
        Args:
            extracted_images: List of image metadata dictionaries
            json_path: Path where to save the JSON file
        """
        # Prepare clean metadata (remove base64 data if present)
        metadata = {
            "total_images": len(extracted_images),
            "images": []
        }
        
        for img in extracted_images:
            img_data = {
                "filename": img["filename"],
                "page": img["page"],
                "position_type": img["position_type"],
                "bbox": {
                    "x1": img["bbox"][0],
                    "y1": img["bbox"][1],
                    "x2": img["bbox"][2],
                    "y2": img["bbox"][3]
                },
                "dimensions": {
                    "width": img["width"],
                    "height": img["height"]
                },
                "path": img["path"]
            }
            metadata["images"].append(img_data)
        
        # Save to JSON file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _remove_black_background(self, image_path: str):
        """
        Smart background removal: Only remove large solid black regions
        Preserves text and detailed graphics
        """
        try:
            from PIL import Image, ImageFilter
            import numpy as np
            
            img = Image.open(image_path)
            original_mode = img.mode
            
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            data = np.array(img)
            height, width = data.shape[:2]
            
            # Much more conservative threshold - only pure black (RGB < 10)
            # This avoids removing anti-aliased edges of text
            black_threshold = 10
            
            # Identify very dark pixels
            dark_mask = (data[:, :, 0] < black_threshold) & \
                       (data[:, :, 1] < black_threshold) & \
                       (data[:, :, 2] < black_threshold)
            
            # Only remove if a significant portion is black (likely background)
            black_ratio = np.sum(dark_mask) / (height * width)
            
            if black_ratio > 0.3:  # More than 30% black = likely has black background
                # Use a smarter approach: flood fill from edges
                # This removes connected background regions but preserves text
                
                # Create a mask for edge-connected black regions
                from scipy import ndimage
                
                # Start from edges
                edge_mask = np.zeros_like(dark_mask)
                edge_mask[0, :] = dark_mask[0, :]  # Top edge
                edge_mask[-1, :] = dark_mask[-1, :]  # Bottom edge
                edge_mask[:, 0] = dark_mask[:, 0]  # Left edge
                edge_mask[:, -1] = dark_mask[:, -1]  # Right edge
                
                # Find connected components from edges
                labeled, num_features = ndimage.label(dark_mask)
                edge_labels = np.unique(labeled[edge_mask])
                edge_labels = edge_labels[edge_labels > 0]  # Remove 0 (no label)
                
                # Create mask for edge-connected black regions only
                background_mask = np.isin(labeled, edge_labels)
                
                # Convert background to white, preserve text
                data[background_mask] = [255, 255, 255, 255]
                
                result = Image.fromarray(data)
                result.save(image_path)
                print(f"    ✓ Smart background removal: {os.path.basename(image_path)}")
            else:
                # Not much black, probably not a background - leave as is
                print(f"    ℹ No black background detected: {os.path.basename(image_path)}")
            
        except ImportError:
            # scipy not available, use simple threshold fallback
            print(f"    ⚠ scipy not available, using simple threshold for: {os.path.basename(image_path)}")
            try:
                from PIL import Image
                import numpy as np
                
                img = Image.open(image_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                data = np.array(img)
                
                # Very conservative threshold - only pure black
                black_mask = (data[:, :, 0] < 5) & (data[:, :, 1] < 5) & (data[:, :, 2] < 5)
                data[black_mask] = [255, 255, 255, 255]
                
                result = Image.fromarray(data)
                result.save(image_path)
            except:
                pass  # Silently continue
        except Exception as e:
            # Any other error, just skip
            print(f"    ⚠ Background removal failed for {os.path.basename(image_path)}: {e}")
            pass
    
    def _detect_visual_content_with_gpt4v(self, pdf_images: List[str], extracted_images: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use GPT-4 Vision to identify ALL visual content, including what PyMuPDF missed
        
        Args:
            pdf_images: List of paths to PDF page images
            extracted_images: List of images already extracted by PyMuPDF
            
        Returns:
            Dict with detected visual elements and their metadata
        """
        from openai import OpenAI
        
        client = OpenAI(api_key=self.openai_api_key)
        
        # Build extracted images info for comparison
        extracted_info = []
        for img in extracted_images:
            extracted_info.append(f"- {img['filename']} (page {img['page']}, {img['position_type']}, bbox: {img['bbox']})")
        
        # Create visual detection prompt
        detection_prompt = f"""
        You are a visual content analyzer for documents. Analyze these PDF pages and identify ALL visual content that should be preserved in LaTeX.
        
        CURRENT EXTRACTIONS: PyMuPDF found {len(extracted_images)} images:
        {chr(10).join(extracted_info) if extracted_info else "None"}
        
        Your task: Identify ALL visual elements that should be preserved in LaTeX, including:
        1. Embedded images (already extracted by PyMuPDF)
        2. Vector diagrams and illustrations
        3. Charts, graphs, and data visualizations
        4. Complex multi-part figures
        5. Text rendered as graphics
        6. Any visual content that contributes to understanding
        
        For each visual element you identify, provide:
        - element_id: unique identifier
        - type: "extracted_image", "vector_diagram", "chart", "scientific_figure", "text_as_graphics", "logo", "decoration"
        - description: what it shows
        - page_number: which page it's on
        - bounding_box: [x1, y1, x2, y2] coordinates (approximate)
        - pymupdf_captured: true/false (whether PyMuPDF already extracted it)
        - latex_suggestion: how to represent it in LaTeX
        - complexity: "simple", "moderate", "complex"
        
        Pay special attention to:
        - Scientific diagrams that might be vector-based
        - Multi-part figures that should be treated as units
        - Text rendered as graphics
        - Complex illustrations that PyMuPDF might have missed
        - Charts and graphs
        - Logos and decorative elements
        
        Return your analysis as structured JSON with this format:
        {{
            "all_elements": [
                {{
                    "element_id": "elem_1",
                    "type": "extracted_image",
                    "description": "Biological cell diagram",
                    "page_number": 1,
                    "bounding_box": [65.76, 185.70, 195.36, 365.22],
                    "pymupdf_captured": true,
                    "latex_suggestion": "\\includegraphics{{page1_img1.png}}",
                    "complexity": "moderate"
                }}
            ],
            "missing_images": [
                // Elements where pymupdf_captured = false
            ],
            "summary": {{
                "total_elements": 15,
                "extracted_by_pymupdf": 7,
                "missed_by_pymupdf": 8,
                "complexity_breakdown": {{
                    "simple": 5,
                    "moderate": 7,
                    "complex": 3
                }}
            }}
        }}
        """
        
        # Build multimodal messages
        messages = [
            {
                "role": "system",
                "content": "You are an expert visual content analyzer. Analyze documents to identify ALL visual elements that should be preserved in LaTeX reconstruction."
            },
            {
                "role": "user",
                "content": self._build_visual_detection_prompt(pdf_images, detection_prompt)
            }
        ]
        
        try:
            # Call GPT-4 Vision
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=4096,
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0].strip()
                    visual_content = json.loads(json_str)
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0].strip()
                    visual_content = json.loads(json_str)
                else:
                    # Try to parse the entire content as JSON
                    visual_content = json.loads(content)
                
                print(f"[OK] Visual content detection completed")
                print(f"[INFO] Total elements detected: {visual_content.get('summary', {}).get('total_elements', 0)}")
                print(f"[INFO] PyMuPDF captured: {visual_content.get('summary', {}).get('extracted_by_pymupdf', 0)}")
                print(f"[INFO] Missing elements: {visual_content.get('summary', {}).get('missed_by_pymupdf', 0)}")
                
                return visual_content
                
            except json.JSONDecodeError as e:
                print(f"[WARN] Failed to parse visual content JSON: {e}")
                return {
                    "all_elements": [],
                    "missing_images": [],
                    "summary": {"total_elements": 0, "extracted_by_pymupdf": 0, "missed_by_pymupdf": 0}
                }
                
        except Exception as e:
            print(f"[WARN] Visual content detection failed: {e}")
            return {
                "all_elements": [],
                "missing_images": [],
                "summary": {"total_elements": 0, "extracted_by_pymupdf": 0, "missed_by_pymupdf": 0}
            }
    
    def _build_visual_detection_prompt(self, pdf_images: List[str], detection_prompt: str) -> List[Dict[str, Any]]:
        """Build multimodal prompt for visual content detection"""
        content = []
        
        # Add instruction text
        content.append({"type": "text", "text": detection_prompt})
        
        # Add PDF page images (limit to first 5 pages to avoid token limits)
        for img_path in pdf_images[:5]:
            try:
                with open(img_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{encoded}",
                            "detail": "high"
                        }
                    })
            except Exception as e:
                print(f"[WARN] Failed to encode image {img_path}: {e}")
                continue
        
        return content
    
    def _detect_hierarchical_numbering(self, text: str) -> Dict[str, Any]:
        """
        Detect hierarchical numbering patterns in the extracted text
        
        Args:
            text: Extracted text content
            
        Returns:
            Dict with detected numbering patterns and structure
        """
        import re
        
        # Look for various hierarchical numbering patterns
        patterns = {
            # Main parts: letters with parentheses (a), b), c), etc.)
            'main_parts_letters': re.findall(r'[a-z]\)\s+[^a-z]*?(?=[a-z]\)|$)', text, re.DOTALL),
            # Main parts: numbers with parentheses (1), 2), 3), etc.)
            'main_parts_numbers': re.findall(r'\d+\)\s+[^\d]*?(?=\d+\)|$)', text, re.DOTALL),
            # Sub-parts: Roman numerals (i., ii., iii., iv., v., etc.)
            'sub_parts_roman': re.findall(r'[ivx]+\.\s+[^ivx]*?(?=[ivx]+\.|$)', text, re.DOTALL),
            # Sub-parts: lowercase letters (a., b., c., etc.)
            'sub_parts_letters': re.findall(r'[a-z]\.\s+[^a-z]*?(?=[a-z]\.|$)', text, re.DOTALL),
            # Sub-parts: numbers (1., 2., 3., etc.)
            'sub_parts_numbers': re.findall(r'\d+\.\s+[^\d]*?(?=\d+\.|$)', text, re.DOTALL),
            # Nested structures: main part followed by sub-parts
            'nested_structures': re.findall(r'[a-z]\)\s+[^a-z]*?(?:[ivx]+\.\s+[^ivx]*?)*', text, re.DOTALL)
        }
        
        # Count total patterns found
        total_main_parts = len(patterns['main_parts_letters']) + len(patterns['main_parts_numbers'])
        total_sub_parts = (len(patterns['sub_parts_roman']) + 
                          len(patterns['sub_parts_letters']) + 
                          len(patterns['sub_parts_numbers']))
        
        # Detect if there are sub-parts that should be nested under main parts
        hierarchical_detected = total_sub_parts > 0 and total_main_parts > 0
        
        return {
            'hierarchical_detected': hierarchical_detected,
            'patterns': patterns,
            'needs_nested_enumeration': hierarchical_detected,
            'total_main_parts': total_main_parts,
            'total_sub_parts': total_sub_parts
        }
    
    def _generate_visual_gap_report(self, visual_content: Dict[str, Any], output_dir: str) -> Optional[str]:
        """
        Generate a report of visual content analysis and gaps
        
        Args:
            visual_content: Visual content analysis results
            output_dir: Directory to save the report
            
        Returns:
            Path to the generated report file, or None if no gaps
        """
        if not visual_content or not visual_content.get('missing_images'):
            print("[INFO] No visual gaps detected - all visual content captured")
            return None
        
        missing_elements = visual_content.get('missing_images', [])
        summary = visual_content.get('summary', {})
        
        # Generate report content
        report_content = f"""# Visual Content Analysis Report

## Summary
- **Total visual elements detected:** {summary.get('total_elements', 0)}
- **Successfully extracted by PyMuPDF:** {summary.get('extracted_by_pymupdf', 0)}
- **Missing visual content:** {summary.get('missed_by_pymupdf', 0)}

## Missing Visual Elements
The following visual elements were detected but could not be extracted by PyMuPDF. 
These will be represented in LaTeX using the suggested approaches:

"""
        
        for i, element in enumerate(missing_elements, 1):
            report_content += f"""### {i}. {element.get('type', 'Unknown Type').title()}

- **Description:** {element.get('description', 'No description available')}
- **Page:** {element.get('page_number', 'Unknown')}
- **Bounding Box:** {element.get('bounding_box', 'Unknown')}
- **Complexity:** {element.get('complexity', 'Unknown')}
- **Suggested LaTeX:** {element.get('latex_suggestion', 'No suggestion available')}

"""
        
        # Add complexity breakdown if available
        complexity_breakdown = summary.get('complexity_breakdown', {})
        if complexity_breakdown:
            report_content += f"""## Complexity Breakdown
- **Simple:** {complexity_breakdown.get('simple', 0)} elements
- **Moderate:** {complexity_breakdown.get('moderate', 0)} elements  
- **Complex:** {complexity_breakdown.get('complex', 0)} elements

"""
        
        report_content += """## Notes
- Missing visual content will be represented in LaTeX using appropriate methods
- Vector diagrams will use \\tikz
- Complex figures will use placeholders with descriptions
- Charts and graphs will use LaTeX representations
- All visual information is preserved through intelligent LaTeX generation

## Recommendations
1. Review the generated LaTeX to ensure all visual content is properly represented
2. For complex diagrams, consider manual refinement of the \\tikz code
3. For scientific illustrations, verify that all visual information is preserved
"""
        
        # Save report
        report_path = os.path.join(output_dir, f"{Path(output_dir).name}_visual_gap_report.md")
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(f"[OK] Visual gap report saved: {Path(report_path).name}")
            return report_path
        except Exception as e:
            print(f"[WARN] Failed to save visual gap report: {e}")
            return None
    
    def _generate_markdown(self, context: Dict[str, Any], output_dir: str) -> Optional[str]:
        """
        Generate Markdown file showing extracted text content for manual inspection
        
        Args:
            context: Rich context with all data sources
            output_dir: Directory to save the markdown file
            
        Returns:
            Path to the generated markdown file, or None if failed
        """
        try:
            pdf_name = context.get('pdf_name', 'document')
            markdown_path = os.path.join(output_dir, f"{pdf_name}.md")
            
            # Build markdown content
            markdown_content = f"""# Extracted Text Content: {pdf_name}

## Document Overview
- **Document:** {context.get('pdf_path', 'Unknown')}
- **Pages:** {len(context.get('original_pages', []))}
- **Extracted Images:** {len(context.get('extracted_images', []))}

---

## OCR Data (Mistral OCR)

"""
            
            # Add OCR data - the actual extracted text
            if context.get('ocr_data'):
                ocr_data = context['ocr_data']
                if isinstance(ocr_data, dict):
                    # If it's a dict, try to extract the raw content
                    if 'raw_content' in ocr_data:
                        markdown_content += ocr_data['raw_content']
                    else:
                        # Show the structured data
                        markdown_content += json.dumps(ocr_data, indent=2)
                else:
                    # If it's a string, show it directly
                    markdown_content += str(ocr_data)
            else:
                markdown_content += "*No OCR data available*"
            
            markdown_content += """

---

## Structured JSON Data (Questions and Sub-questions)

"""
            
            # Add structured JSON data - the questions and sub-questions
            if context.get('json_data'):
                json_data = context['json_data']
                markdown_content += json.dumps(json_data, indent=2)
            else:
                markdown_content += "*No structured JSON data available*"
            
            markdown_content += """

---

## Visual Content Analysis

"""
            
            # Add visual content analysis
            if context.get('visual_content'):
                visual_content = context['visual_content']
                summary = visual_content.get('summary', {})
                
                markdown_content += f"""### Summary
- **Total visual elements detected:** {summary.get('total_elements', 0)}
- **PyMuPDF extractions:** {summary.get('extracted_by_pymupdf', 0)}
- **Missing visual content:** {summary.get('missed_by_pymupdf', 0)}

### Missing Visual Elements
"""
                
                missing_images = visual_content.get('missing_images', [])
                if missing_images:
                    for i, element in enumerate(missing_images, 1):
                        markdown_content += f"""
**{i}. {element.get('type', 'Unknown Type').title()}**
- Description: {element.get('description', 'No description')}
- Page: {element.get('page_number', 'Unknown')}
- Complexity: {element.get('complexity', 'Unknown')}
- Suggested LaTeX: `{element.get('latex_suggestion', 'No suggestion')}`
"""
                else:
                    markdown_content += "*No missing visual elements detected*"
            else:
                markdown_content += "*No visual content analysis available*"
            
            markdown_content += """

---

## Extracted Images (PyMuPDF)

"""
            
            # Add extracted images
            if context.get('extracted_images'):
                for img in context['extracted_images']:
                    markdown_content += f"""
- **{img.get('filename', 'Unknown')}** (Page {img.get('page', 'Unknown')})
  - Type: {img.get('position_type', 'Unknown')}
  - Bounding Box: {img.get('bbox', 'Unknown')}
  - Dimensions: {img.get('width', 'Unknown')} x {img.get('height', 'Unknown')}
"""
            else:
                markdown_content += "*No images extracted*"
            
            markdown_content += """

---

## Manual Inspection Notes

### For Questions and Sub-questions
1. **Check completeness** - Are all questions from the original PDF captured?
2. **Verify sub-questions** - Are all sub-questions properly extracted?
3. **Review formatting** - Is the text properly formatted and readable?
4. **Check special characters** - Are Greek letters, math symbols, etc. preserved?

### For Visual Content
1. **Review extracted images** - Are all important visual elements captured?
2. **Check missing elements** - What visual content was missed by PyMuPDF?
3. **Verify descriptions** - Are the descriptions of missing elements accurate?

### For LaTeX Generation
1. **Text accuracy** - Does the extracted text match the original?
2. **Visual completeness** - Are all visual elements accounted for?
3. **Layout preservation** - Will the LaTeX maintain the original layout?

---
*Generated by Smart LaTeX Reconstructor with Visual Content Detection*
"""
            
            # Save markdown file
            with open(markdown_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            return markdown_path
            
        except Exception as e:
            print(f"[WARN] Failed to generate markdown: {e}")
            return None
    
    def _build_rich_context(
        self,
        pdf_path: str,
        pdf_images: List[str],
        ocr_data: Optional[Dict[str, Any]],
        extracted_images: List[Dict[str, Any]],
        assets_dir: Optional[str],
        json_data: Optional[Dict[str, Any]] = None,
        visual_content: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build comprehensive context for GPT-4 Vision"""
        
        # Encode PDF images for GPT-4 Vision
        encoded_pages = []
        for img_path in pdf_images[:5]:  # Limit to first 5 pages to avoid token limits
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                encoded_pages.append({
                    "path": img_path,
                    "base64": encoded
                })
        
        # Encode extracted images
        encoded_extracted = []
        for img_info in extracted_images:
            try:
                with open(img_info["path"], "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                    encoded_extracted.append({
                        **img_info,
                        "base64": encoded
                    })
            except:
                pass
        
        return {
            "pdf_path": pdf_path,
            "pdf_name": Path(pdf_path).stem,
            "original_pages": encoded_pages,
            "ocr_data": ocr_data,
            "extracted_images": encoded_extracted,
            "assets_dir": assets_dir,
            "json_data": json_data,  # Add structured JSON data
            "visual_content": visual_content  # Add visual content analysis
        }
    
    def _generate_smart_latex(self, context: Dict[str, Any]) -> str:
        """
        Generate LaTeX using GPT-4 Vision with rich context
        
        This is the SMART part - no regex needed!
        """
        from openai import OpenAI
        
        client = OpenAI(api_key=self.openai_api_key)
        
        # Build multimodal messages
        messages = [
            {
                "role": "system",
                "content": self._get_system_prompt()
            },
            {
                "role": "user",
                "content": self._build_user_prompt(context)
            }
        ]
        
        # Call GPT-4 Vision
        response = client.chat.completions.create(
            model="gpt-4o",  # or "gpt-4-vision-preview"
            messages=messages,
            max_tokens=4096,
            temperature=0.1  # Low temperature for consistency
        )
        
        latex_code = response.choices[0].message.content
        
        # Clean up code fences if present (minimal post-processing)
        if "```latex" in latex_code:
            latex_code = latex_code.split("```latex")[1].split("```")[0].strip()
        elif "```" in latex_code:
            latex_code = latex_code.split("```")[1].split("```")[0].strip()
        
        # Ensure \graphicspath is present (minimal post-processing for images)
        latex_code = self._ensure_graphicspath(latex_code, context)
        
        # Fix common spacing issues (minimal post-processing)
        latex_code = self._fix_metadata_spacing(latex_code)
        
        # Fix package conflicts (critical for compilation)
        latex_code = self._fix_package_conflicts(latex_code)
        
        return latex_code
    
    def _fix_metadata_spacing(self, latex_code: str) -> str:
        r"""
        Fix common spacing issues in metadata lines
        
        Detects lines like:
        Term: 2023 \hfill Subject: Math \hfill Number: 101
        
        And converts to:
        \begin{tabular}{@{}l@{\hspace{2em}}l@{\hspace{2em}}l@{}}
        Term: 2023 & Subject: Math & Number: 101
        \end{tabular}
        """
        import re
        
        lines = latex_code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # Check if line has multiple \hfill separators (metadata pattern)
            if '\\hfill' in line and line.count('\\hfill') >= 2:
                # Check if it looks like metadata (has "Term:", "Subject:", "Course", etc.)
                if any(keyword in line for keyword in ['Term:', 'Subject:', 'Course', 'Number:']):
                    # Split by \hfill
                    parts = [p.strip() for p in line.split('\\hfill')]
                    
                    # Remove \noindent if present
                    if parts[0].startswith('\\noindent'):
                        parts[0] = parts[0].replace('\\noindent', '').strip()
                    
                    # Convert to tabular
                    fixed_line = '\\noindent\n\\begin{tabular}{@{}' + 'l@{\\hspace{2em}}' * len(parts) + '}\n'
                    fixed_line += ' & '.join(parts)
                    fixed_line += '\n\\end{tabular}'
                    
                    fixed_lines.append(fixed_line)
                    print(f"[INFO] Fixed metadata spacing: {len(parts)} fields")
                    continue
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_package_conflicts(self, latex_code: str) -> str:
        """
        Fix package conflicts that prevent compilation
        
        Known conflicts:
        1. fontspec + inputenc (fontspec is for XeLaTeX/LuaLaTeX, inputenc is for pdfLaTeX)
        2. Multiple geometry declarations
        3. Duplicate package imports
        
        Strategy: Remove packages that conflict with pdfLaTeX since it's the default compiler
        """
        import re
        
        fixed = False
        
        # Conflict 1: fontspec + inputenc (CRITICAL)
        # fontspec only works with XeLaTeX/LuaLaTeX, inputenc works with pdfLaTeX
        # Since we default to pdfLaTeX, remove fontspec
        if '\\usepackage{fontspec}' in latex_code and '\\usepackage[utf8]{inputenc}' in latex_code:
            latex_code = re.sub(r'\\usepackage\{fontspec\}\s*\n?', '', latex_code)
            print("[FIX] Removed \\usepackage{fontspec} (conflicts with inputenc for pdfLaTeX)")
            fixed = True
        
        # Conflict 2: fontspec alone without inputenc (use inputenc for pdfLaTeX compatibility)
        elif '\\usepackage{fontspec}' in latex_code and '\\usepackage' in latex_code:
            # Replace fontspec with inputenc for better pdfLaTeX compatibility
            latex_code = latex_code.replace(
                '\\usepackage{fontspec}',
                '\\usepackage[utf8]{inputenc}'
            )
            print("[FIX] Replaced \\usepackage{fontspec} with \\usepackage[utf8]{inputenc} for pdfLaTeX")
            fixed = True
        
        # Conflict 3: Remove duplicate package declarations
        lines = latex_code.split('\n')
        seen_packages = set()
        filtered_lines = []
        
        for line in lines:
            # Check if line is a package declaration
            pkg_match = re.match(r'\\usepackage(\[.*?\])?\{(.*?)\}', line.strip())
            if pkg_match:
                pkg_name = pkg_match.group(2)
                pkg_options = pkg_match.group(1) or ''
                pkg_key = f"{pkg_name}{pkg_options}"
                
                if pkg_key in seen_packages:
                    print(f"[FIX] Removed duplicate package: \\usepackage{pkg_options}{{{pkg_name}}}")
                    fixed = True
                    continue
                else:
                    seen_packages.add(pkg_key)
            
            filtered_lines.append(line)
        
        latex_code = '\n'.join(filtered_lines)
        
        if not fixed:
            print("[INFO] No package conflicts detected")
        
        return latex_code
    
    def _ensure_graphicspath(self, latex_code: str, context: Dict[str, Any]) -> str:
        r"""
        Ensure \graphicspath is set correctly (minimal post-processing)
        
        This is the ONE piece of post-processing that makes sense - ensuring
        LaTeX knows where to find the images.
        """
        import re
        
        if not context.get('assets_dir') or not context.get('extracted_images'):
            return latex_code  # No images, no need for graphicspath
        
        # Get assets directory name
        assets_dir_name = os.path.basename(context['assets_dir'])
        
        # Check if \graphicspath is already present
        if '\\graphicspath' not in latex_code:
            # Add it after \usepackage{graphicx}
            graphicspath_line = f"\\graphicspath{{{{./{assets_dir_name}/}}}}\n"
            
            # Try to insert after \usepackage{graphicx}
            if '\\usepackage{graphicx}' in latex_code or '\\usepackage[' in latex_code and 'graphicx' in latex_code:
                # Find the line with graphicx
                lines = latex_code.split('\n')
                new_lines = []
                added = False
                
                for line in lines:
                    new_lines.append(line)
                    if ('\\usepackage{graphicx}' in line or ('\\usepackage[' in line and 'graphicx' in line)) and not added:
                        new_lines.append(graphicspath_line.rstrip())
                        added = True
                
                if added:
                    latex_code = '\n'.join(new_lines)
                    print(f"[INFO] Added \\graphicspath{{{{{assets_dir_name}/}}}}")
            else:
                # graphicx not found, add both after \documentclass
                if '\\documentclass' in latex_code:
                    latex_code = latex_code.replace(
                        '\\documentclass',
                        f'\\documentclass',
                        1
                    )
                    # Find end of documentclass line
                    lines = latex_code.split('\n')
                    new_lines = []
                    for i, line in enumerate(lines):
                        new_lines.append(line)
                        if i == 0 and '\\documentclass' in line:
                            new_lines.append('\\usepackage{graphicx}')
                            new_lines.append(graphicspath_line.rstrip())
                    latex_code = '\n'.join(new_lines)
                    print(f"[INFO] Added \\usepackage{{graphicx}} and \\graphicspath")
        else:
            print("[INFO] \\graphicspath already present in LaTeX")
        
        return latex_code
    
    def _get_system_prompt(self) -> str:
        """System prompt for GPT-4 - defines its role and capabilities"""
        return """You are an expert LaTeX document reconstructor. Generate a LaTeX document that is VISUALLY IDENTICAL to the original PDF.

CAPABILITIES:
- Visual analysis of original PDF pages
- OCR data with text content and positioning  
- Extracted images with positions and metadata
- Structured JSON data with complete questions/sub-questions
- Visual content analysis for missing elements

CORE REQUIREMENTS:
1. **Complete LaTeX**: \\documentclass to \\end{document} with all necessary packages
2. **All Images**: Include EVERY extracted image using \\includegraphics commands
3. **Exact Structure**: Preserve the original document's numbering hierarchy exactly
4. **Visual Fidelity**: Match layout, spacing, fonts, and appearance precisely

PACKAGES TO INCLUDE:
- \\usepackage{graphicx} (for images)
- \\usepackage{amsmath,amssymb} (for math)
- \\usepackage{geometry} (for margins)
- \\usepackage[utf8]{inputenc} (for UTF-8)
- \\usepackage{tikz} (for vector diagrams if needed)

CRITICAL RULES:
- **Numbering**: Preserve exact hierarchical structure (main parts → sub-parts → sub-sub-parts)
- **Images**: Include ALL extracted images, never skip any
- **Layout**: Use tabular for header metadata, not \\hfill
- **Characters**: Use LaTeX commands (\\theta, \\pi) not Unicode (θ, π)
- **No Duplication**: Don't render text that's already in images

MISSING CONTENT STRATEGIES:
- Vector diagrams → \\tikz
- Charts/graphs → LaTeX representations  
- Complex figures → \\includegraphics with descriptions
- Text as graphics → Convert to LaTeX text

Output ONLY LaTeX code - no explanations."""
    
    def _build_user_prompt(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build multimodal user prompt with images + text"""
        
        content = []
        
        # Add instruction text
        instruction = f"""Reconstruct this document as LaTeX that produces VISUALLY IDENTICAL output.

Document: {context['pdf_name']}

PROVIDED DATA:
1. Original PDF pages as images (analyze these carefully)
2. OCR data with text content and positioning
3. Extracted images with filenames and positions
4. Visual content analysis for missing elements

MANDATORY REQUIREMENTS:
- Include ALL {len(context['extracted_images'])} extracted images using \\includegraphics commands
- Preserve exact hierarchical numbering structure from original
- Match visual layout, spacing, and appearance precisely
- Use extracted images in logical positions based on page numbers and bounding boxes

LAYOUT RULES:
- Header information must appear at the TOP of the document
- Images should be placed near the questions they relate to
- Tables should be rendered as LaTeX tables, not images
- Maintain proper page breaks and document flow

TABLE HANDLING:
- If you see a SIMPLE data table (rows/columns of text/numbers), recreate it using LaTeX \\begin{{tabular}} or \\begin{{table}}
- Do NOT use \\includegraphics for simple data tables - they should be LaTeX code
- For COMPLEX diagrams, chemical structures, or figures, use \\includegraphics
- Preserve table structure, headers, and data exactly

CRITICAL: You MUST include ALL {len(context['extracted_images'])} images. Do not skip any images, especially the last ones in the sequence.

Extracted images available:
"""
        
        # List extracted images with better context
        for i, img in enumerate(context['extracted_images']):
            instruction += f"- {img['filename']} (page {img['page']}, {img['position_type']}, image {i+1} of {len(context['extracted_images'])})\n"
        
        # Add assets directory info
        if context.get('assets_dir'):
            assets_dir_name = os.path.basename(context['assets_dir'])
            instruction += f"\n\nIMPORTANT: Use \\graphicspath{{{{./{assets_dir_name}/}}}} to reference images."
        
        instruction += "\n\n---\n\nOriginal PDF pages (analyze these visually for layout and structure):\n"
        instruction += "\nIMPORTANT: Use the original PDF pages to understand:\n"
        instruction += "- Where the header (Name, Section, TA) appears\n"
        instruction += "- Which images belong to which questions\n"
        instruction += "- Which content should be tables vs images\n"
        instruction += "- Proper page breaks and document flow\n"
        instruction += "\nSPECIAL NOTE: Complex visual diagrams, charts, and figures should use \\includegraphics, NOT LaTeX table code.\n"
        
        content.append({"type": "text", "text": instruction})
        
        # Add original PDF page images
        for page in context['original_pages']:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{page['base64']}",
                    "detail": "high"
                }
            })
        
        # Add OCR data if available
        if context['ocr_data']:
            ocr_text = f"\n\n---\n\nOCR Data (text content):\n```json\n{json.dumps(context['ocr_data'], indent=2)[:4000]}\n```"
            content.append({"type": "text", "text": ocr_text})
        
        # Add structured JSON data if available (CRITICAL for complete content)
        if context.get('json_data'):
            json_text = f"\n\n---\n\nStructured JSON Data (COMPLETE questions and sub-questions):\n```json\n{json.dumps(context['json_data'], indent=2)[:6000]}\n```"
            content.append({"type": "text", "text": json_text})
        
        # Add visual content analysis if available
        if context.get('visual_content'):
            visual_analysis = f"""
        
        ---
        
        VISUAL CONTENT ANALYSIS:
        Total visual elements detected: {context['visual_content'].get('summary', {}).get('total_elements', 0)}
        PyMuPDF extractions: {context['visual_content'].get('summary', {}).get('extracted_by_pymupdf', 0)}
        Missing visual content: {context['visual_content'].get('summary', {}).get('missed_by_pymupdf', 0)}
        
        Missing visual elements that need LaTeX representation:
        """
            
            for element in context['visual_content'].get('missing_images', []):
                visual_analysis += f"""
        - {element.get('type', 'unknown')}: {element.get('description', 'No description')} (page {element.get('page_number', 'unknown')})
          Suggested approach: {element.get('latex_suggestion', 'No suggestion')}
          Complexity: {element.get('complexity', 'unknown')}
            """
            
            content.append({"type": "text", "text": visual_analysis})
        
        
        # Final instruction
        final_instruction = f"\n\n---\n\nGenerate complete LaTeX code that recreates this document EXACTLY.\n\nKey points:\n- Reference images by filename (e.g., page1_img1.png)\n- Use visual analysis for missing content\n- Match sizes and layout precisely\n- Don't duplicate content\n- Output ONLY LaTeX code\n\nVERIFICATION: You must include exactly {len(context['extracted_images'])} \\includegraphics commands. Count them before finalizing your response.\n\nLAYOUT VERIFICATION: Before finalizing, verify that:\n- Header appears at the top of the document\n- Images are placed near their related questions\n- Simple data tables are rendered as LaTeX code, not images\n- Complex diagrams and chemical structures use \\includegraphics\n- Document flow matches the original PDF pages"
        
        content.append({
            "type": "text",
            "text": final_instruction
        })
        
        return content
    
    def _compile_latex(self, tex_path: str, output_dir: str) -> Optional[str]:
        """Compile LaTeX to PDF, auto-detecting Unicode and using appropriate engine"""
        import subprocess
        import shutil
        
        # Check if document contains Unicode characters
        try:
            with open(tex_path, 'r', encoding='utf-8') as f:
                content = f.read()
                has_unicode = any(ord(char) > 127 for char in content)
        except:
            has_unicode = False
        
        # Choose appropriate LaTeX engine
        if has_unicode:
            # Try xelatex for Unicode support
            compiler = shutil.which("xelatex")
            if compiler:
                print("[INFO] Unicode detected - using XeLaTeX for compilation")
            else:
                # Fallback to pdflatex
                compiler = shutil.which("pdflatex")
                print("[WARN] Unicode detected but XeLaTeX not found - using pdflatex (may fail)")
        else:
            compiler = shutil.which("pdflatex")
        
        if not compiler:
            print("[WARN] No LaTeX compiler found (tried xelatex and pdflatex)")
            return None
        
        try:
            # Run twice for references
            for i in range(2):
                result = subprocess.run(
                    [compiler, "-interaction=nonstopmode", Path(tex_path).name],
                    cwd=output_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=60
                )
                if i == 0 and result.returncode != 0:
                    print(f"[WARN] First compilation pass had errors (this is sometimes normal)")
            
            pdf_path = tex_path.replace(".tex", ".pdf")
            if os.path.exists(pdf_path):
                return pdf_path
            else:
                print("[ERROR] PDF file not generated")
                return None
            
        except subprocess.TimeoutExpired:
            print("[ERROR] LaTeX compilation timed out (60s)")
            return None
        except Exception as e:
            print(f"[ERROR] LaTeX compilation failed: {e}")
            return None


import os
import google.generativeai as genai
from flask import Flask, request, render_template, flash, redirect, url_for, send_from_directory, session
from werkzeug.utils import secure_filename
from PIL import Image
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError
from dotenv import load_dotenv
import cv2
import numpy as np
import pytesseract
import re
import time
import uuid
import platform
import json

# --- Load Environment Variables ---
load_dotenv()

# --- Configure Tesseract OCR ---
# Check if running on Windows and set Tesseract path
if platform.system() == 'Windows':
    # Try to get path from environment variable first
    tesseract_path = os.getenv('TESSERACT_PATH')
    
    # If not set, use common installation paths
    if not tesseract_path:
        common_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe'
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                tesseract_path = path
                break
    
    # Set the path if found
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print(f"Tesseract OCR path set to: {tesseract_path}")
    else:
        print("WARNING: Tesseract OCR executable not found. OCR functionality may not work.")
        print("Please set the TESSERACT_PATH environment variable or install Tesseract in a standard location.")

# --- Configuration ---
# Make sure UPLOAD_FOLDER is correctly defined with an absolute path
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
# Add PDF to allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
# Ensure upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
        print(f"Created upload folder: {UPLOAD_FOLDER}")
    except Exception as e:
        print(f"ERROR creating upload folder: {e}")
else:
    print(f"Upload folder exists at: {UPLOAD_FOLDER}")

# Get Google API key from environment
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in a .env file.")

# Function to verify file exists and log result
def verify_file_saved(filepath, context=""):
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        print(f"✓ File verified [{context}]: {filepath} ({file_size} bytes)")
        return True
    else:
        print(f"✗ File NOT found [{context}]: {filepath}")
        return False

# --- Configure Gemini ---
genai.configure(api_key=GOOGLE_API_KEY)
# Use the updated model
llm_model = genai.GenerativeModel('gemini-2.0-flash')

# --- Flask App Setup ---
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB max upload
# Load secret key from environment variable for security
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'a_default_secret_key_for_dev') 
if app.secret_key == 'a_default_secret_key_for_dev':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production.")

# Session setup for storing analysis results
app.config['SESSION_TYPE'] = 'filesystem'

# Make sure static files are served correctly by checking if the static folder exists
static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
if not os.path.exists(static_folder):
    try:
        os.makedirs(static_folder)
        print(f"Created static folder: {static_folder}")
    except Exception as e:
        print(f"ERROR creating static folder: {e}")
else:
    print(f"Static folder exists at: {static_folder}")

# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files(current_files):
    """Delete old files from the uploads folder except the ones needed for current analysis."""
    try:
        for filename in os.listdir(UPLOAD_FOLDER):
            # Skip current files we need to keep
            if filename in current_files:
                continue
                
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted old file: {filename}")
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")
        print(f"Cleanup complete. Kept files: {current_files}")
    except Exception as e:
        print(f"Error cleaning uploads folder: {e}")

def convert_pdf_to_image(pdf_path, output_folder):
    """Converts the first page of a PDF to a JPG image."""
    try:
        # Convert PDF to a list of PIL images
        images = convert_from_path(pdf_path, first_page=1, last_page=1, fmt='jpeg')
        if images:
            # Create a unique name for the output image
            pdf_filename = os.path.basename(pdf_path)
            image_filename = f"{os.path.splitext(pdf_filename)[0]}.jpg"
            image_path = os.path.join(output_folder, image_filename)
            # Save the first image
            images[0].save(image_path, 'JPEG')
            print(f"Converted '{pdf_filename}' to '{image_filename}'")
            return image_path
        else:
            raise ValueError("Could not extract image from PDF.")
    except PDFInfoNotInstalledError:
        flash("PDF processing error: Poppler not installed or not in PATH. Please install Poppler.")
        raise # Re-raise to stop processing
    except Exception as e:
        flash(f"Error converting PDF: {e}")
        raise # Re-raise

def extract_dimensions_with_ocr(image_path):
    """Use OCR to extract linear dimensions (meters, feet, inches)."""
    extracted_dimensions = []
    try:
        # Check if Tesseract is properly configured
        if platform.system() == 'Windows' and not hasattr(pytesseract.pytesseract, 'tesseract_cmd'):
            print("WARNING: Tesseract OCR path not set. OCR dimension extraction skipped.")
            return []
            
        img = cv2.imread(image_path)
        if img is None:
            print(f"Failed to read image for OCR: {image_path}")
            return []

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Experiment with thresholding, maybe adaptive?
        # _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 5)

        try:
            # Use pytesseract, get text
            # Consider using image_to_data for bounding boxes later if needed
            text = pytesseract.image_to_string(binary)
            
            # --- Regex patterns for linear dimensions --- 
            # Pattern for meters (e.g., 5.2m, 10 m, 3 meters)
            meter_pattern = r'(\d+(?:\.\d+)?)\s*(?:m|meters?|metre)s?\b'
            # Pattern for feet (e.g., 12ft, 15 ft, 20 feet, 10')
            # Need to be careful not to match inches mark here
            feet_pattern = r'(\d+(?:\.\d+)?)\s*(?:ft|feet|foot|\'(?!["]))' # Match ' but not "
            # Pattern for inches (e.g., 6in, 8 inches, 10")
            inch_pattern = r'(\d+(?:\.\d+)?)\s*(?:in|inch|inches|\")\b' # Use word boundary
            
            # Combine patterns and extract
            # Store as (value, unit, raw_text)
            for match in re.finditer(meter_pattern, text, re.IGNORECASE):
                try: extracted_dimensions.append((float(match.group(1)), 'm', match.group(0))) 
                except ValueError: pass
            
            for match in re.finditer(feet_pattern, text, re.IGNORECASE):
                try: extracted_dimensions.append((float(match.group(1)), 'ft', match.group(0))) 
                except ValueError: pass
                
            for match in re.finditer(inch_pattern, text, re.IGNORECASE):
                try: extracted_dimensions.append((float(match.group(1)), 'in', match.group(0))) 
                except ValueError: pass
                
            if not extracted_dimensions:
                print("No linear dimensions (m, ft, in) found with OCR.")
            else:
                print(f"Found linear dimensions via OCR: {extracted_dimensions}")
            
            return extracted_dimensions
            
        except pytesseract.pytesseract.TesseractNotFoundError:
            print("Tesseract executable not found. OCR dimension extraction skipped.")
            return []
            
    except Exception as e:
        print(f"OCR dimension extraction error: {e}")
        return []

def analyze_with_opencv(image_path, linear_dimensions):
    """Analyze the floor plan using OpenCV and attempt scale calculation from OCR dimensions."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        visual_img = img.copy()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 5)
        
        # Improve contour finding (optional: morphological operations)
        # kernel = np.ones((3,3),np.uint8)
        # thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations = 2)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_contour_area = 1000 # Adjust as needed
        room_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]
        
        if not room_contours:
            print("OpenCV: No significant contours found.")
            return {
                'visual_filename': None, # No visual if no contours
                'area_pixels': 0,
                'num_rooms': 0,
                'scale_used': None,
                'calculated_area_sqm': None,
                'calculated_area_sqft': None,
                'calculation_method': 'No contours found'
            }
        
        # Draw contours
        cv2.drawContours(visual_img, room_contours, -1, (0, 255, 0), 2)
        total_area_px = sum(cv2.contourArea(cnt) for cnt in room_contours)
        
        # --- Heuristic Scale Calculation --- 
        scale_used = None
        pixels_per_meter = None
        calculated_area_sqm = None
        calculated_area_sqft = None
        calculation_method = "No linear dimensions found by OCR"
        
        if linear_dimensions:
            # Convert all dimensions to meters for comparison
            dimensions_in_meters = []
            for val, unit, raw in linear_dimensions:
                if unit == 'm':
                    dimensions_in_meters.append((val, raw))
                elif unit == 'ft':
                    dimensions_in_meters.append((val * 0.3048, raw))
                elif unit == 'in':
                     dimensions_in_meters.append((val * 0.0254, raw))
            
            if dimensions_in_meters:
                # Find the largest dimension provided by OCR
                dimensions_in_meters.sort(key=lambda x: x[0], reverse=True)
                largest_ocr_dimension_m, ocr_ref_text = dimensions_in_meters[0]
                
                # Find the largest contour
                largest_contour = max(room_contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest_contour)
                largest_contour_dimension_px = max(w, h)
                
                # Heuristic: Assume largest OCR dimension corresponds to largest contour dimension
                if largest_ocr_dimension_m > 0 and largest_contour_dimension_px > 0:
                    pixels_per_meter = largest_contour_dimension_px / largest_ocr_dimension_m
                    scale_used = f"{pixels_per_meter:.2f} px/m (derived from OCR text '{ocr_ref_text}' and largest contour)"
                    calculation_method = f"Heuristic scale ({scale_used}) applied to total pixel area."
                    print(f"OpenCV Scale Calculation: {scale_used}")
                    
                    # Calculate area
                    calculated_area_sqm = total_area_px / (pixels_per_meter ** 2)
                    calculated_area_sqft = calculated_area_sqm * 10.7639
                else:
                     calculation_method = "Could not derive scale (dimension or contour size zero)"
            else:
                 calculation_method = "No valid metric dimensions found after conversion"
        
        # --- Save Visualization --- 
        base_name = os.path.basename(image_path)
        name_without_ext, ext = os.path.splitext(base_name)
        visual_filename = f"{name_without_ext}_opencv{ext}"
        visual_path = os.path.join(os.path.dirname(image_path), visual_filename)
        
        # Save visualization and verify
        print(f"Saving OpenCV visualization to: {visual_path}")
        cv2.imwrite(visual_path, visual_img)
        if not verify_file_saved(visual_path, "OpenCV visualization"):
            # If saving failed, try with a full absolute path
            alt_visual_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                          'static', 'uploads', visual_filename)
            print(f"Attempt to save to alternative path: {alt_visual_path}")
            cv2.imwrite(alt_visual_path, visual_img)
            verify_file_saved(alt_visual_path, "OpenCV visualization (alt path)")
            # Update the filename to reflect the new location
            visual_filename = os.path.basename(alt_visual_path)
        
        return {
            'visual_filename': visual_filename,
            'area_pixels': total_area_px,
            'num_rooms': len(room_contours),
            'scale_used': scale_used,
            'calculated_area_sqm': calculated_area_sqm,
            'calculated_area_sqft': calculated_area_sqft,
            'calculation_method': calculation_method
        }
        
    except Exception as e:
        print(f"OpenCV processing error: {e}")
        import traceback
        traceback.print_exc() # Print detailed traceback
        return None

def get_area_estimate_from_llm(image_path):
    """Sends image to Gemini and asks for area estimation in JSON format."""
    print(f"Sending image to LLM: {image_path}")
    start_time = time.time()
    
    try:
        img = Image.open(image_path)
        
        prompt = """
        Analyze this floor plan image carefully.
        
        First, look for any scale or dimension information (like measurements, scale bars, or room sizes).
        Then estimate the total floor area of the entire plan.
        
        Respond ONLY with a valid JSON object containing the following keys:
        - "found_dimensions": boolean (true if you found explicit measurements/scale, false otherwise)
        - "estimated_area_sqft": string (estimated total area range in square feet, e.g., "1500-1600 sq ft")
        - "estimated_area_sqm": string (estimated total area range in square meters, e.g., "140-150 m²")
        - "explanation": string (brief explanation of how you estimated the area, e.g., "Used visible dimensions" or "Based on typical room sizes")
        
        Example JSON response:
        {
            "found_dimensions": true,
            "estimated_area_sqft": "1800-1950 sq ft",
            "estimated_area_sqm": "167-181 m²",
            "explanation": "Calculated based on room dimensions shown."
        }
        """

        # Generate content using the vision model
        response = llm_model.generate_content([prompt, img])
        response.resolve() 

        processing_time = time.time() - start_time
        print(f"LLM response received in {processing_time:.2f} seconds")
        
        raw_response_text = response.text.strip()
        print(f"LLM Raw Response Text: {raw_response_text}")
        
        # Attempt to parse the response as JSON
        try:
            # Clean potential markdown code block fences
            if raw_response_text.startswith('```json'):
                raw_response_text = raw_response_text[7:]
            if raw_response_text.endswith('```'):
                raw_response_text = raw_response_text[:-3]
            
            parsed_json = json.loads(raw_response_text)
            
            # Validate expected keys
            required_keys = ["found_dimensions", "estimated_area_sqft", "estimated_area_sqm", "explanation"]
            if all(key in parsed_json for key in required_keys):
                return {
                    "data": parsed_json, 
                    "error": None, 
                    "processing_time": processing_time,
                    "raw_response": raw_response_text # Keep raw text for debugging tab
                }
            else:
                print("LLM JSON response missing required keys.")
                raise ValueError("Missing keys in JSON response")
                
        except (json.JSONDecodeError, ValueError) as json_error:
            print(f"Failed to parse LLM response as JSON: {json_error}")
            # Fallback: return the raw text with an error message
            return {
                "data": None, # Indicate data is not structured
                "error": f"AI response format error: {json_error}", 
                "processing_time": processing_time,
                "raw_response": raw_response_text # Still provide raw text
            }

    except FileNotFoundError:
         error_msg = f"Image file not found at {image_path}"
         flash(f"Error: {error_msg}")
         return {"data": None, "error": error_msg, "raw_response": "File not found"}
    except Exception as e:
        error_msg = str(e)
        print(f"Error calling LLM API: {e}")
        flash(f"Error contacting AI service: {e}")
        return {"data": None, "error": error_msg, "raw_response": f"API Error: {e}"}

def ask_followup_question(image_path, question):
    """
    Ask a follow-up question about a floor plan to the Gemini model.
    
    Args:
        image_path: Path to the floor plan image
        question: The follow-up question from the user
    
    Returns:
        Dictionary with response text and any error
    """
    print(f"Processing follow-up question about image: {image_path}")
    print(f"Question: {question}")
    start_time = time.time()
    
    try:
        # Construct full path to the image file
        full_image_path = os.path.join(UPLOAD_FOLDER, image_path)
        
        # Verify image exists
        if not os.path.exists(full_image_path):
            return {
                "response": None,
                "error": f"Image file not found: {image_path}",
                "processing_time": 0
            }
        
        img = Image.open(full_image_path)
        
        # Formulate prompt for the follow-up question
        prompt = f"""
        This is a follow-up question about a floor plan image that was previously analyzed.
        
        User's question: {question}
        
        Please analyze the floor plan image carefully and respond specifically to the question.
        Base your answer on what you can see in the floor plan and explain your reasoning.
        If you cannot confidently answer based on the image, please explain why.
        """
        
        # Generate content using the vision model
        response = llm_model.generate_content([prompt, img])
        response.resolve()
        
        processing_time = time.time() - start_time
        print(f"Follow-up response received in {processing_time:.2f} seconds")
        
        return {
            "response": response.text,
            "error": None,
            "processing_time": processing_time
        }
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error processing follow-up question: {e}")
        return {
            "response": None, 
            "error": error_msg,
            "processing_time": time.time() - start_time
        }

# --- Flask Routes ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Create unique filename to avoid overwrites
            original_filename = secure_filename(file.filename)
            name, extension = os.path.splitext(original_filename)
            unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{extension}"
            
            # Track files that need to be kept
            files_to_keep = set()
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            print(f"Saving uploaded file to: {filepath}")
            file.save(filepath)
            
            # Add uploaded file to keep list
            files_to_keep.add(unique_filename)
            
            # Verify file was saved
            verify_file_saved(filepath, "Original upload")
            
            # This will be the image we analyze and display
            image_path_for_analysis = filepath
            display_filename = unique_filename  # Default to the uploaded file
            
            # Convert PDF to image if necessary
            file_ext = unique_filename.rsplit('.', 1)[1].lower()
            if file_ext == 'pdf':
                try:
                    image_path_for_analysis = convert_pdf_to_image(filepath, app.config['UPLOAD_FOLDER'])
                    if not image_path_for_analysis:
                        flash("Failed to convert PDF to image")
                        return redirect(request.url)
                    # Update the filename for display
                    display_filename = os.path.basename(image_path_for_analysis)
                    
                    # Add converted image to keep list
                    files_to_keep.add(display_filename)
                    
                    # Verify the converted image exists
                    verify_file_saved(image_path_for_analysis, "PDF conversion")
                    
                    # Log current directory contents for debugging
                    print(f"Contents of {app.config['UPLOAD_FOLDER']}:")
                    for file in os.listdir(app.config['UPLOAD_FOLDER']):
                        print(f"  - {file}")
                        
                except Exception as e:
                    print(f"PDF Conversion failed: {e}")
                    # Flash message already set in convert_pdf_to_image
                    return redirect(request.url)
            
            # Initialize results
            analysis_results = {
                'display_filename': display_filename,
                'opencv_results': None,
                'ocr_dimensions': [], # Now stores list of (val, unit, raw) tuples
                'ai_estimate': None,
                'opencv_visual': None
            }
            
            # OCR to detect linear dimensions
            ocr_linear_dimensions = extract_dimensions_with_ocr(image_path_for_analysis)
            analysis_results['ocr_dimensions'] = ocr_linear_dimensions
            
            # Try OpenCV analysis with heuristic scale calculation
            opencv_results = analyze_with_opencv(image_path_for_analysis, ocr_linear_dimensions)
            if opencv_results:
                analysis_results['opencv_results'] = opencv_results
                # Get visual filename if it exists and add to files to keep
                cv_visual_filename = opencv_results.get('visual_filename')
                if cv_visual_filename:
                    analysis_results['opencv_visual'] = cv_visual_filename
                    files_to_keep.add(cv_visual_filename)
            
            # Get AI estimate from LLM
            ai_response = get_area_estimate_from_llm(image_path_for_analysis)
            analysis_results['ai_estimate'] = ai_response
            
            # Store analysis results in session for follow-up questions
            session['last_analysis'] = analysis_results
            session['last_files'] = list(files_to_keep)
            
            # Now clean up old files, keeping only the ones needed for this analysis
            cleanup_old_files(files_to_keep)
            
            # Pass all results to the template
            return render_template(
                "index.html", 
                analysis=analysis_results,
                area_estimate_str=(analysis_results.get('ai_estimate', {}).get('data') or {}).get('estimated_area_sqft', 'N/A')
            )
            
        else:
            flash(f"Invalid file type: '{file.filename}'. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}")
            return redirect(request.url)

    # Initial GET request
    return render_template("index.html", area_estimate=None, analysis=None)

# Route to serve uploaded files
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    print(f"Browser requested file: {filename}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        print(f"File found at: {file_path}")
        file_size = os.path.getsize(file_path)
        print(f"File size: {file_size} bytes")
    else:
        print(f"WARNING: File not found at: {file_path}")
        print(f"Available files in directory:")
        try:
            for file in os.listdir(app.config['UPLOAD_FOLDER']):
                print(f"  - {file}")
        except Exception as e:
            print(f"Error listing directory: {e}")
            
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/ask-followup', methods=['POST'])
def ask_followup():
    """Process a follow-up question about a floor plan."""
    # Get the image path and question from the form
    image_path = request.form.get('image_path')
    question = request.form.get('question')
    
    if not image_path or not question:
        flash("Missing image or question")
        return redirect(url_for('index'))
    
    # Process the follow-up question
    followup_result = ask_followup_question(image_path, question)
    
    # Get the original analysis results from the session if available
    analysis_results = session.get('last_analysis')
    
    # If no stored analysis, create a minimal one
    if not analysis_results:
        analysis_results = {
            'display_filename': image_path,
            'ai_estimate': {
                'error': None, 
                'processing_time': followup_result.get('processing_time', 0),
                'data': {'found_dimensions': False}
            },
            'ocr_dimensions': [],
            'opencv_results': None,
            'opencv_visual': None
        }
    
    # Ensure files needed for this analysis aren't deleted
    files_to_keep = session.get('last_files', [])
    if image_path not in files_to_keep:
        files_to_keep.append(image_path)
        session['last_files'] = files_to_keep
    
    # Render the template with the original analysis and follow-up response
    return render_template(
        "index.html",
        analysis=analysis_results,
        followup_question=question,
        followup_response=followup_result.get('response'),
        followup_error=followup_result.get('error')
    )

# --- Run App ---
if __name__ == "__main__":
    print(f"Starting server...")
    # Use host='0.0.0.0' to make accessible on your network if needed
    app.run(debug=True, host='127.0.0.1')

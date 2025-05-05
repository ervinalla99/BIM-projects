# Floor Plan Analyzer

This Flask application uses AI (Google Gemini), Computer Vision (OpenCV), and OCR (Tesseract) 
to analyze uploaded floor plan images (JPG, PNG) or PDFs and estimate the total floor area.

## Features

*   Upload JPG, PNG, or PDF floor plans (up to 16MB).
*   Automatic conversion of single-page PDFs to images.
*   OCR attempts to find dimensions/area text within the image.
*   OpenCV detects room-like contours and calculates total pixel area.
*   Gemini Vision model provides an overall area estimation (sq ft & sq m) and analysis.
*   Displays original image, OpenCV contour visualization (if successful).
*   Tabbed interface shows AI estimate, raw AI response, OCR results, and OpenCV details.

## Prerequisites

1.  **Python 3.8+**: Make sure Python and pip are installed.
2.  **Tesseract OCR**: Required for the OCR functionality.
    *   **Windows**: Download and install from [UB Mannheim Tesseract builds](https://github.com/UB-Mannheim/tesseract/wiki). During installation, ensure you add it to your system's PATH or note the installation directory.
    *   **macOS**: `brew install tesseract`
    *   **Linux (Debian/Ubuntu)**: `sudo apt-get update && sudo apt-get install tesseract-ocr`
3.  **Poppler**: Required for PDF conversion (`pdf2image` library depends on it).
    *   **Windows**: Download the latest binary from [this blog](http://blog.alivate.com.au/poppler-windows/) or other sources. Unzip it and add the `bin/` directory to your system's PATH.
    *   **macOS**: `brew install poppler`
    *   **Linux (Debian/Ubuntu)**: `sudo apt-get update && sudo apt-get install poppler-utils`

## Setup

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd Vision # Or your project directory
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create `.env` File:**
    Create a file named `.env` in the `Vision` directory (or project root where `app.py` is) and add your API key and a secret key:
    ```dotenv
    GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
    FLASK_SECRET_KEY="YOUR_STRONG_RANDOM_SECRET_KEY"
    
    # Optional: Only needed if Tesseract is not in your system PATH on Windows
    # TESSERACT_PATH="C:\Path\To\Tesseract-OCR\tesseract.exe"
    ```
    *   Replace `YOUR_GOOGLE_API_KEY` with your actual Gemini API key.
    *   Replace `YOUR_STRONG_RANDOM_SECRET_KEY` with a long, random string (used for Flask session security).
    *   Uncomment and set `TESSERACT_PATH` if you are on Windows and Tesseract wasn't added to the PATH during installation.

## Running the Application

1.  Make sure your virtual environment is activated.
2.  Run the Flask development server:
    ```bash
    python app.py
    ```
3.  Open your web browser and navigate to `http://127.0.0.1:5000` (or the address provided in the terminal).

## How it Works

1.  **Upload**: User uploads an image or PDF file.
2.  **Preprocessing**: If PDF, the first page is converted to a JPG image.
3.  **OCR**: Tesseract OCR is run on the image to extract all text. Regex patterns attempt to find linear measurements (e.g., "5.2m", "10ft", "6in").
4.  **OpenCV**: The image is processed using adaptive thresholding to find contours. Large contours are assumed to be rooms. Total pixel area is calculated. 
    *   **Scale Heuristic**: If linear dimensions were found by OCR, the system attempts a *heuristic* scale calculation. It assumes the largest linear dimension found corresponds to the longest side of the largest detected contour. This scale is then applied to the total pixel area to estimate real-world area (sqm/sqft). This method has known limitations and may be inaccurate.
5.  **AI Analysis**: The image is sent to the Google Gemini Vision model with a prompt asking for area estimation and analysis in JSON format.
6.  **Results**: The application displays the AI's estimation, the original and OpenCV images, and detailed results from OCR (linear dimensions found), OpenCV (pixel area, contours, calculated area + method), and the AI in separate tabs. 
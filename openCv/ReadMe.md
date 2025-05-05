# 🧠 Bridge Crack Detection with OpenCV

This project automates the detection, measurement, classification, and reporting of cracks in bridge surfaces using image processing. It uses OpenCV to detect cracks from orthomosaic or inspection images, estimates physical dimensions using a known Ground Sample Distance (GSD), and exports the results in image, CSV, and PDF formats.

---

## 🔍 Features

- ✅ Detects visible cracks in high-resolution images
- 📏 Measures crack **length** and **maximum width** in millimeters
- 🏷️ Classifies cracks into: Hairline, Fine, Medium, and Wide
- 🖼️ Generates annotated image with crack contours and labels
- 📄 Produces a structured **CSV** file of results
- 📑 Creates a **PDF report** summarizing detected cracks

---

## 📁 Output Example

- `annotated_image.jpg`: Visual output with detected cracks and classifications
- `crack_report.csv`: Structured table with length, width, and classification
- `crack_report.pdf`: Readable summary report for engineering review

---

## 📷 Example Input

Make sure your input image has appropriate resolution and clarity, with a known **GSD** (e.g., 0.5 mm/pixel).

---

## 📦 Requirements

- Python 3.7+
- OpenCV
- NumPy
- Pandas
- Matplotlib (optional for preview)
- ReportLab (for PDF generation)

Install dependencies:

```bash
pip install opencv-python numpy pandas matplotlib reportlab

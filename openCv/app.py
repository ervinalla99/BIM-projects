import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pathlib import Path

# === PARAMETERS ===
GSD = 0.5  # mm/pixel
CLASS_THRESHOLDS = {
    "Hairline": (0, 0.3),
    "Fine": (0.3, 1.0),
    "Medium": (1.0, 3.0),
    "Wide": (3.0, 100.0),
}

# === HELPER FUNCTIONS ===

def classify_crack(width_mm):
    for name, (low, high) in CLASS_THRESHOLDS.items():
        if low <= width_mm < high:
            return name
    return "Unknown"

def analyze_cracks(image_path, output_folder):
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    dilated = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    output_img = img.copy()
    data = []

    for i, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < 5:  # skip small noise
            continue

        length_pixels = cv2.arcLength(cnt, False)
        length_mm = length_pixels * GSD

        x, y, w, h = cv2.boundingRect(cnt)
        width_mm = max(w, h) * GSD
        classification = classify_crack(width_mm)

        # Draw contour and label
        cv2.drawContours(output_img, [cnt], -1, (0, 255, 0), 1)
        cv2.putText(output_img, f"{classification}", (x, y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

        data.append({
            "ID": i + 1,
            "Length (mm)": round(length_mm, 2),
            "Max Width (mm)": round(width_mm, 2),
            "Classification": classification,
            "X": x,
            "Y": y
        })

    # === Save outputs ===
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    # Annotated image
    annotated_path = output_folder / "annotated_image.jpg"
    cv2.imwrite(str(annotated_path), output_img)

    # CSV
    df = pd.DataFrame(data)
    csv_path = output_folder / "crack_report.csv"
    df.to_csv(csv_path, index=False)

    # PDF Report
    pdf_path = output_folder / "crack_report.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setFont("Helvetica", 12)
    c.drawString(50, 800, f"Crack Detection Report")
    c.drawString(50, 785, f"Image: {Path(image_path).name}")
    c.drawString(50, 770, f"GSD: {GSD} mm/pixel")
    c.drawString(50, 755, f"Total Cracks: {len(df)}")

    y = 730
    for _, row in df.iterrows():
        if y < 100:
            c.showPage()
            y = 800
        c.drawString(50, y, f"ID: {row['ID']} | Length: {row['Length (mm)']} mm | Width: {row['Max Width (mm)']} mm | Class: {row['Classification']}")
        y -= 15

    c.save()

    return str(annotated_path), str(csv_path), str(pdf_path)

# === RUN EXAMPLE ===
# Provide your image path and output folder below
image_path = r"C:\Users\User\Desktop\upwork\openCV\bridge-crack-lauderdale-co-2.webp"  # Change to your input file
output_folder = r"C:\Users\User\Desktop\upwork\openCV"

# Run only if image file exists
from pathlib import Path
if Path(image_path).exists():
    analyze_cracks(image_path, output_folder)
else:
    print("Image not found. Please update 'image_path'.")

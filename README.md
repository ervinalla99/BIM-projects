# BIM-projects

A collection of various software solutions for Building Information Modeling (BIM) and related architectural/engineering tasks.

## 🌟 Repository Contents

This repository contains the following projects:

### 🌎 [Cesium GLB(IFC) Viewer](./Cesium_GLB(IFC)_Viewer/)

A web-based 3D model viewer application that uses Cesium.js to place and interact with GLB models on a global terrain.

**Key Features:**
- Load and display 3D models in GLB format
- Precisely position models using geographic coordinates
- Manipulate models (orientation, scale)
- Measurement tools (point, distance, area)
- IFC to GLB conversion workflow

**Workflow:** Export Revit Model to IFC → Convert IFC to GLB → Visualize GLB in geographic context

### 🔍 [ComputerVision - Floor Plan Analyzer](./ComputerVision/)

A Flask application that uses AI (Google Gemini), Computer Vision (OpenCV), and OCR (Tesseract) to analyze floor plan images and estimate total floor area.

**Key Features:**
- Upload JPG, PNG, or PDF floor plans
- Automatic PDF to image conversion
- OCR to identify dimension text
- OpenCV for room contour detection
- AI-assisted floor area estimation
- Visual results with contour highlighting

### 🧠 [OpenCV - Concrete Crack Detection](./openCv/)

An image processing solution that automates the detection, measurement, classification, and reporting of cracks in bridge surfaces using OpenCV.

**Key Features:**
- Detects visible cracks in high-resolution images
- Measures crack length and maximum width in millimeters
- Classifies cracks (Hairline, Fine, Medium, Wide)
- Generates annotated images with crack contours
- Produces CSV data and PDF reports

## 🚀 Getting Started

Each project folder contains its own README with specific setup instructions and requirements. Navigate to the project directory of interest and follow the instructions provided.

## 📋 Requirements

Requirements vary by project:
- Cesium GLB Viewer: Web browser, Node.js (for IFC conversion)
- Floor Plan Analyzer: Python 3.8+, Flask, OpenCV, Tesseract OCR, Google Gemini API
- Bridge Crack Detection: Python 3.7+, OpenCV, NumPy, Pandas, ReportLab


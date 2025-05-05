# convert_ifc_to_gltf.py
import subprocess
import os

IFC_FILE = "model.ifc"
GLB_FILE = "model.glb"

def convert_ifc_to_glb():
    if not os.path.exists(IFC_FILE):
        print(f"❌ File not found: {IFC_FILE}")
        return

    command = [
        "IfcConvert",
        IFC_FILE,
        GLB_FILE,
        "--scale=0.001"  # optional: scale from mm to m
    ]

    try:
        subprocess.run(command, check=True)
        print(f"✅ Successfully converted {IFC_FILE} → {GLB_FILE}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Conversion failed: {e}")

if __name__ == "__main__":
    convert_ifc_to_glb()

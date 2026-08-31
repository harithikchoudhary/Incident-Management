"""
Script to download Swagger UI static files locally
This avoids CDN dependency issues
"""
import os
import urllib.request
import zipfile
from pathlib import Path

SWAGGER_UI_VERSION = "5.11.0"
SWAGGER_UI_URL = f"https://github.com/swagger-api/swagger-ui/archive/refs/tags/v{SWAGGER_UI_VERSION}.zip"

def download_swagger_ui():
    static_dir = Path(__file__).parent / "app" / "static"
    static_dir.mkdir(exist_ok=True)
    
    swagger_dir = static_dir / "swagger-ui"
    
    # Check if already exists
    if swagger_dir.exists() and (swagger_dir / "swagger-ui-bundle.js").exists():
        print(f"✓ Swagger UI already exists at {swagger_dir}")
        return
    
    print(f"Downloading Swagger UI v{SWAGGER_UI_VERSION}...")
    zip_path = static_dir / "swagger-ui.zip"
    
    try:
        urllib.request.urlretrieve(SWAGGER_UI_URL, zip_path)
        print("✓ Downloaded successfully")
        
        print("Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(static_dir)
        
        # Move dist files to swagger-ui folder
        extracted_folder = static_dir / f"swagger-ui-{SWAGGER_UI_VERSION}" / "dist"
        if extracted_folder.exists():
            import shutil
            if swagger_dir.exists():
                shutil.rmtree(swagger_dir)
            shutil.copytree(extracted_folder, swagger_dir)
            shutil.rmtree(static_dir / f"swagger-ui-{SWAGGER_UI_VERSION}")
        
        # Clean up
        zip_path.unlink()
        print(f"✓ Swagger UI installed at {swagger_dir}")
        
    except Exception as e:
        print(f"✗ Error downloading Swagger UI: {e}")
        print("\nFallback: The application will use CDN-based Swagger UI")
        print("If CDN is blocked, you can manually download Swagger UI from:")
        print(f"  {SWAGGER_UI_URL}")
        print(f"And extract the 'dist' folder contents to: {swagger_dir}")

if __name__ == "__main__":
    download_swagger_ui()

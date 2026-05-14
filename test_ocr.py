import time
from PIL import Image, ImageDraw, ImageFont
import io

def create_dummy_image():
    img = Image.new('RGB', (400, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((10,10), "Warung Makan Enak", fill=(0,0,0))
    d.text((10,50), "Nasi Goreng 25.000", fill=(0,0,0))
    d.text((10,80), "Es Teh 5.000", fill=(0,0,0))
    d.text((10,120), "Total 30.000", fill=(0,0,0))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()

from extractor_ocr import extract_receipt_ocr

if __name__ == "__main__":
    print("Membuat gambar dummy...")
    image_bytes = create_dummy_image()
    
    print("Mengekstrak OCR...")
    start = time.time()
    result = extract_receipt_ocr(image_bytes)
    end = time.time()
    
    print(f"Waktu ekstraksi: {end - start:.2f} detik")
    print("Hasil data:", result["data"])
    print("Raw text:", repr(result["raw"]))
    if result["error"]:
        print("Error:", result["error"])


from hashlib import md5

from PIL import Image

import os
import pytesseract
import sys


DEBUG = False


def get_image_hash(image: Image.Image) -> str:
    """Returns a unique hash for the given image."""
    return md5(image.tobytes()).hexdigest()


def split_original_directory_into_page_images(directory: str, output_directory: str) -> None:
    """Process images in the specified directory."""
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    seen_hashes = set()
    for root, _, files in os.walk(directory):
        for file in sorted(files):
            if file.endswith(".png"):
                file_path = os.path.join(root, file)
                with Image.open(file_path) as img:
                    # Make image grayscale then crop out the book margins
                    cropped_img = img.convert("L").crop((250, 120, img.width - 320, img.height - 250))
                    hash_val = get_image_hash(cropped_img)
                    if hash_val not in seen_hashes:
                        seen_hashes.add(hash_val)
                        # Assume first unique image is the cover page, skip further processing
                        if 1 == len(seen_hashes):
                            continue
                        # Save the full double-page image (if needed for debugging purposes)
                        if DEBUG:
                            cropped_img.save(os.path.join(output_directory, f"{file}".replace(".png",".xdebug.png")))
                        # Save the left and right pages
                        left_page_img = cropped_img.crop((0, 0, cropped_img.width // 2, cropped_img.height))
                        left_page_img.save(os.path.join(output_directory, f"{file}".replace(".png",".left.png")))
                        right_page_img = cropped_img.crop((cropped_img.width // 2, 0, cropped_img.width, cropped_img.height))
                        right_page_img.save(os.path.join(output_directory, f"{file}".replace(".png",".right.png")))
                        if len(seen_hashes) % 10 == 0:
                            print(f"Processed {len(seen_hashes)} original images into page-specific images.")


def pdf_merge_directory(directory: str, output_filename: str) -> None:
    """Convert PNG images in a directory to a PDF, with each image as a page."""
    image_list = []
    for root, _, files in os.walk(directory):
        for file in sorted(files):
            if file.endswith('.png'):
                file_path = os.path.join(root, file)
                image = Image.open(file_path)
                img_converted = image.convert('RGB')
                image_list.append(img_converted)
    if image_list:
        image_list[0].save(output_filename, save_all=True, append_images=image_list[1:])


def ocr_directory(directory: str) -> str:
    """Extract text from all PNG images in the directory using OCR."""
    content = []
    for root, _, files in os.walk(directory):
        for file in sorted(files):
            if file.endswith(".png"):
                file_path = os.path.join(root, file)
                with Image.open(file_path) as img:
                    page_content = pytesseract.image_to_string(img)
                    content.append(page_content)
    # Combine all the pages into a single string
    return "\n\n".join(content)


if __name__ == "__main__":
    # Basic help and entry validation
    if "help" in sys.argv or "--help" in sys.argv or "-h" in sys.argv or len(sys.argv) != 3:
        print("Usage: python rip_from_directory_of_images.py <input_directory> <output_directory>")
        sys.exit(1)
    # First command line argument is path to input directory, second is path to output directory
    input_directory = sys.argv[1]
    output_directory = sys.argv[2]
    # Check if input directory exists
    if not os.path.exists(input_directory):
        print("Error: The input directory does not exist.")
        sys.exit(1)
    # Check that input directory contains at least one PNG image
    png_files = [f for f in os.listdir(input_directory) if f.endswith(".png")]
    if not png_files:
        print("Error: The input directory does not contain any PNG images.")
        sys.exit(1)
    # Check if the parent directory of the output directory exists
    if not os.path.exists(os.path.dirname(output_directory)):
        print("Error: The parent directory of the output directory does not exist.")
        sys.exit(1)
    # Split images into individual pages and save to output directory
    split_original_directory_into_page_images(input_directory, output_directory)
    # Save PDF of all images in the output directory
    pdf_merge_directory(output_directory, os.path.join(output_directory, "merged.pdf"))
    exit(0)
    # Extract text from all images in the output directory
    book_content = ocr_directory(output_directory)
    print(book_content)

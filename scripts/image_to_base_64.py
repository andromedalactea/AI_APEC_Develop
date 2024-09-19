import base64

def image_to_base64_markdown(image_path: str, text: str) -> str:
    # Convert the image to base64
    with open(image_path, "rb") as image_file:
        base64_string = base64.b64encode(image_file.read()).decode('utf-8')

    # Create the Markdown image tag
    markdown_image = f"![Image](data:image/png;base64,{base64_string})"

    # Add the Markdown image tag to the text
    # You can customize the placement of the image in the text
    markdown_text = f"{text}\n\n{markdown_image}"
    
    return markdown_text

# Example usage
if __name__ == "__main__":
    image_path = "path/to/your/image.png"  # Replace with the path to your image
    text = "Here is an image included in the Markdown text:"
    markdown_with_image = image_to_base64_markdown(image_path, text)
    print(markdown_with_image)

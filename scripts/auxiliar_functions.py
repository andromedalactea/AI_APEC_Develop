import os
import re

def sources_to_md(sources: list, sources_used: list) -> str:
    """
    Convert a list of sources to a Markdown formatted string, filtered by specific indices.
    
    Args:
        sources (list): A list of source strings and pages.
        sources_used (list): A list of integers representing the indices of sources to include.
        
    Returns:
        str: A Markdown formatted string of sources.
    """
    # Generate the URLs
    URLS = [f"https://www.petrowhiz.ai/pdfs/{source.replace('/mnt/apec-ai-feed/', '').replace(' ', '%20')}" for source, _ in sources]

    # Filter sources based on sources_used indices
    filtered_sources = [(sources[index - 1], URLS[index - 1]) for index in sources_used if 0 < index <= len(sources)]
    
    # Create references based on the filtered sources
    references = [f"({sources_used[i]}) {source.split('/')[-1].replace('.pdf', '')}, Page {page}" 
                  for i, ((source, page), _) in enumerate(filtered_sources)]
    
    # Create the Markdown formatted string using only the filtered sources
    md_sources = "\n".join([f"- [{reference}]({url})" for reference, (_, url) in zip(references, filtered_sources)])
    
    return md_sources

def absolute_path(relative_path: str) -> str:
    return os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), relative_path))


def replace_sources(text: str, urls: list) -> tuple:
    """
    Replaces placeholders in the format "{n}" in the given text with the corresponding
    URLs from the 'urls' list, where 'n' is an integer less than 10.
    Also returns a list of the integers found in the placeholders.

    Args:
        text (str): The string containing placeholders to be replaced.
        urls (list of str): A list of URL strings.

    Returns:
        tuple: A tuple containing:
            - str: The text with all placeholders replaced by their corresponding URLs.
            - list of int: A list of the integers found in the placeholders.
    """
    # Regular expression to find placeholders in the format {n}, where n is an integer less than 10
    pattern = r'\{([1-9])\}'
    
    # List to store found integers
    found_numbers = []

    # Function to replace each match with the corresponding URL
    def replace_match(match):
        index = int(match.group(1)) - 1  # Get the number inside braces and adjust to 0-based index
        found_numbers.append(index + 1)  # Store the found number as a 1-based index
        if index < len(urls):
            return f"[({index + 1})]({urls[index]})"  # Return the corresponding URL string
        return match.group(0)  # If index out of range, return original match

    # Substitute all matches in the text with the corresponding URLs
    replaced_text = re.sub(pattern, replace_match, text)
    
    return replaced_text, found_numbers

# Example usage
if __name__ == "__main__":
    sources = ["Source 1 text", "Source 2 text", "Jupiter"]
    text = "Here is some information from {1}, and more details from {3}."
    result = replace_sources(sources, text)
    print(result)

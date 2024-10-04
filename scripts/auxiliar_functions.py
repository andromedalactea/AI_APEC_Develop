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

    # Extract the domain
    domain_docs = os.getenv("DOMAIN_DOCS")

    # Generate the URLs
    URLS = [f"{domain_docs}/pdfs/{source.replace('/mnt/apec-ai-feed/', '').replace(' ', '%20')}" for source, _ in sources]

    # Filter sources based on sources_used indices
    filtered_sources = [(sources[index - 1], URLS[index - 1]) for index in sources_used if 0 < index <= len(sources)]
    
    # Create references based on the filtered sources
    # Crear referencias basadas en las fuentes filtradas, manejando el caso donde la página podría no estar disponible
    references = []

    for i, (source_info, _) in enumerate(filtered_sources):
        source = source_info[0]
        page = source_info[1] if len(source_info) > 1 else None  # Verificar si la página existe

        # Construir la referencia y agregar el número de página solo si existe
        reference = f"({sources_used[i]}) {source.split('/')[-1].replace('.pdf', '')}"
        if page:  # Solo añadir ", Page {page}" si el valor de `page` no es None ni vacío
            reference += f", Page {int(page) + 1}"
        
        references.append(reference)
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

def extract_user_messages(messages: list, n: int) -> str:
    # Filtrar los mensajes cuyo 'role' sea 'user'
    user_messages = [msg['content'] for msg in messages if msg['role'] == 'user']
    
    # Tomar sólo los primeros n mensajes si existen suficientes o menos si no hay tantos
    extracted_messages = user_messages[:n]
    
    # Unir los mensajes en un único string con un separador (opcional, puedes ajustarlo a lo que necesites)
    result = "\n".join(extracted_messages)  # Puedes cambiar "\n" a cualquier delimitador que prefieras

    return result.lower()


# Example usage
if __name__ == "__main__":
    sources = ["Source 1 text", "Source 2 text", "Jupiter"]
    text = "Here is some information from {1}, and more details from {3}."
    result = replace_sources(sources, text)
    print(result)

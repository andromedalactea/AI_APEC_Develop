import os

def sources_to_md(sources: list) -> str:
    """
    Convert a list of sources to a Markdown formatted string.
    
    Args:
        sources (list): A list of source strings.
        
    Returns:
        str: A Markdown formatted string of sources.
    """

    #  Generate the urls 
    URLS = [f"https://www.petrowhiz.ai/pdfs/{source.replace('/mnt/apec-ai-feed/', '').replace(' ', '%20')}" for source in sources]

    # References
    references = [source.split("/")[-1] for source in sources]

    # Create the Markdown formatted string
    md_sources = "\n".join([f"- [{reference}]({url})" for reference, url in zip(references, URLS)])

    return md_sources

def absolute_path(relative_path):
    return os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), relative_path))

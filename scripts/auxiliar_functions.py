def sources_to_md(sources: list) -> str:
    """
    Convert a list of sources to a Markdown formatted string.
    
    Args:
        sources (list): A list of source strings.
        
    Returns:
        str: A Markdown formatted string of sources.
    """

    #  Generate the urls 
    URLS = [f"https://chat.petromentor.ai/pdfs/{source.replace('/mnt/i/', '').replace(' ', '%20')}" for source in sources]

    # References
    references = [source.split("/")[-1] for source in sources]

    # Create the Markdown formatted string
    md_sources = "\n".join([f"- [{reference}]({url})" for reference, url in zip(references, URLS)])

    return md_sources

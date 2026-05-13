import os
import glob
import yaml
import re

def parse_vault(vault_path):
    documents = []
    for filepath in glob.glob(os.path.join(vault_path, "**/*.md"), recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check for YAML frontmatter (Obsidian style)
            # Matches --- at start of file, then content, then ---
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            
            metadata = {}
            body = content
            
            if frontmatter_match:
                try:
                    metadata = yaml.safe_load(frontmatter_match.group(1))
                    body = content[frontmatter_match.end():]
                except Exception:
                    # If YAML is malformed, treat the whole file as body
                    pass
            
            # Extract basic metadata
            doc_id = metadata.get('id', filepath)
            tags = metadata.get('tags', [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(',')]
            
            # Category based on directory structure
            rel_path = os.path.relpath(filepath, vault_path)
            category = os.path.dirname(rel_path) or "general"

            # Split body into chunks (paragraphs)
            chunks = [c.strip() for c in body.split('\n\n') if c.strip()]
            for i, chunk in enumerate(chunks):
                documents.append({
                    "id": f"{doc_id}_{i}",
                    "text": chunk,
                    "source": filepath,
                    "tags": tags,
                    "category": category,
                    "metadata": metadata
                })
    return documents

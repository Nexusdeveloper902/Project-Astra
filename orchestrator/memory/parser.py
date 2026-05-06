import os
import glob

def parse_vault(vault_path):
    documents = []
    for filepath in glob.glob(os.path.join(vault_path, "**/*.md"), recursive=True):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            chunks = [c.strip() for c in content.split('\n\n') if c.strip()]
            for i, chunk in enumerate(chunks):
                documents.append({
                    "id": f"{filepath}_{i}",
                    "text": chunk,
                    "source": filepath,
                    "tags": []
                })
    return documents

import os

replacements = [
    ("Bank of India", "Aegis Bank"),
    ("BANK OF INDIA", "AEGIS BANK"),
    ("bank of india", "aegis bank"),
    ("BOI", "Aegis"),
    ("boi", "aegis"),
    ("Garuda Sentinel", "Aegis Sentinel"),
    ("Garuda", "Aegis"),
    ("garuda", "aegis"),
]

def rename_content(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            content = f.read()
        except UnicodeDecodeError:
            return
    
    new_content = content
    for old, new in replacements:
        new_content = new_content.replace(old, new)
        
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

def walk_and_replace():
    for root, dirs, files in os.walk("."):
        if any(ignored in root for ignored in ['.git', 'node_modules', 'venv', '.venv', '__pycache__']):
            continue
            
        for file in files:
            if file.endswith(('.py', '.ts', '.tsx', '.js', '.jsx', '.json', '.md', '.txt', '.html', '.css', '.dart', '.yaml', '.sh', '.xml', '.env', 'Dockerfile', '.txt')):
                filepath = os.path.join(root, file)
                rename_content(filepath)

if __name__ == '__main__':
    walk_and_replace()

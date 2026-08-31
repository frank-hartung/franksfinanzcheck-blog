import os
import glob
import re

def main():
    paths = glob.glob('content/**/*.md', recursive=True)
    results = []
    
    for path in paths:
        if '_index.md' in path:
            continue
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # strip frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                content = parts[2]
                
        chars = len(content.strip())
        words = len(re.findall(r'\w+', content))
        
        results.append((chars, words, path))
        
    results.sort(key=lambda x: x[0])
    for c, w, p in results:
        print(f"Chars: {c:5d}, Words: {w:4d} - {p}")

if __name__ == '__main__':
    main()

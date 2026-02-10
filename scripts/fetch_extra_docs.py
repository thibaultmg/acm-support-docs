import os
import sys
import urllib.parse
import urllib.request
import urllib.error
import re

# Add script directory to path to allow importing sibling modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import yaml
except ImportError:
    print("Error: PyYAML module not found. Please install it using 'pip install PyYAML'.", file=sys.stderr)
    sys.exit(1)

try:
    import process_crd
except ImportError:
    print("Warning: process_crd module not found. CRD processing will be skipped.", file=sys.stderr)
    process_crd = None

def clean_markdown_images(content):
    """
    Removes Markdown images and HTML img tags from content.
    Replaces ![alt](url) with 'alt' to preserve text context (especially in links).
    """
    # Replace inline images: ![alt](url "title") -> alt
    # We use a capture group to keep the alt text.
    content = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', content)
    
    # Remove HTML images: <img src="..." alt="alt text" />
    # We try to extract alt text if present, otherwise remove.
    def replace_img_tag(match):
        tag = match.group(0)
        alt_match = re.search(r'alt=["\'](.*?)["\']', tag)
        return alt_match.group(1) if alt_match else ""

    content = re.sub(r'<img[^>]*>', replace_img_tag, content)
    
    return content

def slugify(text):
    """
    Converts a string to a valid filename.
    """
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '_', text)
    return text

def convert_github_url(url):
    """
    Converts a standard GitHub URL to a raw content URL.
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc == "github.com":
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 4 and path_parts[2] == "blob":
            # standard github url: user/repo/blob/branch/path...
            user = path_parts[0]
            repo = path_parts[1]
            branch = path_parts[3]
            file_path = "/".join(path_parts[4:])
            return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{file_path}"
    return url

def fetch_extra_docs(config_file, output_dir, prefix=""):
    if not os.path.exists(config_file):
        print(f"Configuration file '{config_file}' not found. Skipping extra docs.")
        return

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with open(config_file, 'r') as f:
            docs = yaml.safe_load(f)
            
        if not docs:
            print(f"No documents found in {config_file}.")
            return
            
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file '{config_file}': {e}", file=sys.stderr)
        return
    except Exception as e:
        print(f"Error reading configuration file: {e}", file=sys.stderr)
        return

    print(f"Found {len(docs)} documents to fetch from {config_file}.")

    for doc in docs:
        name = doc.get('name')
        url = doc.get('url')
        doc_type = doc.get('type')
        
        if not doc_type:
            if url.lower().endswith('.md'):
                doc_type = 'markdown'
            else:
                doc_type = 'markdown' # Default fallback
        
        if not name or not url:
            print(f"Warning: Skipping invalid entry (missing name or url): {doc}")
            continue
            
        filename = prefix + slugify(name) + ".md"
        output_path = os.path.join(output_dir, filename)
        
        raw_url = convert_github_url(url)
        print(f"Fetching '{name}' ({doc_type}): {url} -> {output_path}")
        
        try:
            with urllib.request.urlopen(raw_url) as response:
                content = response.read().decode('utf-8')
            
            if doc_type == 'crd':
                if process_crd:
                    print(f"Processing CRD '{name}'...")
                    content = process_crd.process_crd(content)
                else:
                    print(f"Warning: process_crd module missing, saving raw CRD for '{name}'.")
            elif doc_type == 'markdown':
                content = clean_markdown_images(content)

            with open(output_path, 'w') as f:
                f.write(content)
                
            print(f"Saved to {output_path}")
            
        except urllib.error.URLError as e:
            print(f"Error fetching '{name}' from {url}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing '{name}': {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 fetch_extra_docs.py <yaml_config_file> <output_dir> [prefix]")
        sys.exit(1)
        
    config_file = sys.argv[1]
    output_dir = sys.argv[2]
    prefix = sys.argv[3] if len(sys.argv) > 3 else ""
    
    fetch_extra_docs(config_file, output_dir, prefix)

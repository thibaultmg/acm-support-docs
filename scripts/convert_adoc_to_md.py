import os
import sys
import subprocess
import re

def run_command(args, cwd=None):
    """
    Runs a command using subprocess.run with shell=False for security.
    """
    try:
        subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {' '.join(args)}\n{e.stderr.decode()}", file=sys.stderr)
        sys.exit(1)

def clean_html(file_path):
    """
    Removes HTML tags like <div ...> and </div> from the file content.
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Remove opening div tags with attributes
    content = re.sub(r'<div[^>]*>', '', content)
    # Remove closing div tags
    content = re.sub(r'</div>', '', content)
    
    with open(file_path, 'w') as f:
        f.write(content)

def convert_adoc_to_md(input_adoc, output_md, clean_script="scripts/clean_docbook.py"):
    input_adoc = os.path.abspath(input_adoc)
    output_md = os.path.abspath(output_md)
    base_dir = os.path.dirname(input_adoc)
    
    # Ensure output dir exists
    os.makedirs(os.path.dirname(output_md), exist_ok=True)

    # 1. Convert adoc to DocBook
    tmp_xml = f"{output_md}.xml"
    
    # Run asciidoctor from the input file's directory so relative includes work
    cmd = [
        "asciidoctor", 
        "-b", "docbook", 
        "-a", "allow-uri-read", 
        "-a", "images!", 
        "-o", tmp_xml, 
        os.path.basename(input_adoc)
    ]
    run_command(cmd, cwd=base_dir)
    
    if not os.path.exists(tmp_xml):
        print(f"Error: Failed to generate XML at {tmp_xml}")
        sys.exit(1)

    # 2. Clean DocBook
    cmd = ["uv", "run", clean_script, tmp_xml]
    run_command(cmd)

    # 3. Convert to Markdown (pandoc)
    cmd = ["pandoc", "-f", "docbook", "-t", "gfm", tmp_xml, "-o", output_md]
    run_command(cmd)
    
    # 4. Clean HTML
    clean_html(output_md)
    
    # Cleanup
    if os.path.exists(tmp_xml):
        os.remove(tmp_xml)

    print(f"Converted: {output_md}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 convert_adoc_to_md.py <input_adoc> <output_md> [clean_script]")
        sys.exit(1)
        
    clean_script = sys.argv[3] if len(sys.argv) > 3 else "scripts/clean_docbook.py"
    convert_adoc_to_md(sys.argv[1], sys.argv[2], clean_script)
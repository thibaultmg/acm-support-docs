import os
import sys
from convert_adoc_to_md import convert_adoc_to_md

def assemble_doc(repo_dir, output_file, clean_script):
    monitoring_dir = os.path.join(repo_dir, "observability", "monitoring")
    
    if not os.path.exists(monitoring_dir):
        print(f"Error: Directory {monitoring_dir} does not exist.")
        sys.exit(1)

    # Find all .adoc files, excluding modules/snippets
    # We want assemblies (files in the root of monitoring/)
    adoc_files = [f for f in os.listdir(monitoring_dir) if f.endswith(".adoc")]
    adoc_files.sort()

    # Prioritize 'monitoring-overview.adoc' or 'index.adoc'
    priority_files = ["monitoring-overview.adoc", "about-ocp-monitoring.adoc"]
    sorted_files = []
    
    # Add priority files first if they exist
    for p in priority_files:
        if p in adoc_files:
            sorted_files.append(p)
            adoc_files.remove(p)
            
    # Add the rest
    sorted_files.extend(adoc_files)

    print(f"Found {len(sorted_files)} files to assemble.")
    
    # Create a master.adoc file that includes all others
    master_adoc_path = os.path.join(monitoring_dir, "master_assembly.adoc")
    
    with open(master_adoc_path, "w") as master:
        master.write("= OpenShift Monitoring Documentation\n")
        master.write(":doctype: book\n")
        master.write(":toc:\n\n")
        
        for filename in sorted_files:
            # We use leveloffset=+1 so top-level headers in included files become subsections
            master.write(f"include::{filename}[leveloffset=+1]\n\n")

    print(f"Created master assembly at {master_adoc_path}")

    # Use the shared conversion logic
    convert_adoc_to_md(master_adoc_path, output_file, clean_script)
    
    # Cleanup master assembly
    if os.path.exists(master_adoc_path):
        os.remove(master_adoc_path)

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 assemble_ocp_doc.py <repo_dir> <output_file> <clean_script_path>")
        sys.exit(1)
        
    assemble_doc(sys.argv[1], sys.argv[2], sys.argv[3])

import sys
import yaml
import argparse

def parse_schema(schema, prefix="", level=0):
    """
    Recursively parses the OpenAPI v3 schema and returns a list of markdown lines.
    """
    lines = []
    
    # Get description
    description = schema.get("description", "").strip()
    if description:
        lines.append(description)
        lines.append("")

    # Process properties
    properties = schema.get("properties", {})
    if not properties:
        return lines

    for prop_name, prop_schema in properties.items():
        # Build full path for context preservation
        full_path = f"{prefix}.{prop_name}" if prefix else prop_name
        
        # Determine type
        prop_type = prop_schema.get("type", "object")
        if "format" in prop_schema:
            prop_type += f" ({prop_schema['format']})"
        
        # Header for the field
        # Using headers (###) ensures chunks have context.
        lines.append(f"### {full_path}")
        lines.append(f"**Type:** `{prop_type}`")
        lines.append("")
        
        # Recursively process this property's schema
        # This will extract its description and any children if it's an object
        lines.extend(parse_schema(prop_schema, prefix=full_path, level=level+1))
        
    return lines

def process_crd(crd_content):
    """
    Parses a CRD YAML content and returns a Markdown string.
    """
    try:
        # Load all documents (CRD file might contain multiple docs)
        docs = list(yaml.safe_load_all(crd_content))
    except yaml.YAMLError as e:
        return f"Error parsing YAML: {e}"

    markdown_output = []

    for doc in docs:
        if not doc:
            continue
            
        kind = doc.get("kind", "")
        # Basic check, though sometimes people put CRDs in lists
        if kind != "CustomResourceDefinition":
            continue

        metadata = doc.get("metadata", {})
        name = metadata.get("name", "Unknown CRD")
        spec = doc.get("spec", {})
        group = spec.get("group", "")
        versions = spec.get("versions", [])

        markdown_output.append(f"# CRD Reference: {name}")
        markdown_output.append(f"**Group:** {group}")
        markdown_output.append("")

        for version in versions:
            v_name = version.get("name", "")
            # Schema is typically under openAPIV3Schema
            schema = version.get("schema", {}).get("openAPIV3Schema", {})
            
            markdown_output.append(f"## Version: {v_name}")
            markdown_output.append("")
            
            if not schema:
                markdown_output.append("*No schema definition found.*")
                continue
            
            # Start parsing from root properties
            # The root schema itself usually has 'properties' (like spec, status)
            markdown_output.extend(parse_schema(schema))

    return "\n".join(markdown_output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CRD YAML to Markdown.")
    parser.add_argument("input_file", help="Path to CRD YAML file")
    args = parser.parse_args()

    try:
        with open(args.input_file, "r") as f:
            content = f.read()
            print(process_crd(content))
    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
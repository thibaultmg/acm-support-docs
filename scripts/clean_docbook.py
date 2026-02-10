import sys
import xml.etree.ElementTree as ET

# Register namespace to keep output clean
NS_URL = 'http://docbook.org/ns/docbook'
ET.register_namespace('', NS_URL)
NS = {'db': NS_URL}

def is_navigation_list(ulist):
    """
    Determines if a list is purely a navigation/link list.
    Returns True if all items in the list appear to be just links/xrefs.
    """
    items = ulist.findall('db:listitem', NS)
    if not items:
        return False

    for item in items:
        # A list item usually contains a paragraph (simpara or para)
        # We check if that paragraph contains mainly a link.
        
        # Get all children of the item
        children = list(item)
        if not children: 
            return False # Empty item?
            
        # Usually it wraps content in simpara/para
        para = children[0]
        if para.tag not in (f'{{{NS_URL}}}para', f'{{{NS_URL}}}simpara'):
            # If it's a complex block (like a nested list or note), it's not a simple link list
            return False

        # Check the content of the paragraph
        # If it has an <xref> or <link> and not much other text.
        
        # Count links
        links = para.findall('db:xref', NS) + para.findall('db:link', NS) + para.findall('db:ulink', NS)
        
        if not links:
            return False
            
        # Simplistic check: If there are links, we assume it's a link list item 
        # unless there is significant text length difference?
        # For the user's purpose, "See also" lists usually just have the link text.
        # We'll assume if it *starts* with a link or *is* a link, it counts.
        # But to be safe, let's require that the paragraph *only* contains the link(s) and whitespace/punctuation.
        
        # Extract all text from para
        full_text = "".join(para.itertext()).strip()
        
        # If text is empty (xref often has empty text in XML, filled by renderer), it's a link.
        if not full_text:
            continue
            
        # If there is text, it might be the link label. 
        # Hard to distinguish "Click [here]" from "[Link Title]".
        # But standard "See also" lists are usually just the links.
        
    return True

def clean_docbook(xml_path):
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        print(f"Error parsing XML {xml_path}: {e}", file=sys.stderr)
        sys.exit(1)
        
    root = tree.getroot()

    # Map child to parent for reverse lookup
    parent_map = {c: p for p in tree.iter() for c in p}

    # 1. Remove Images and their intros/captions
    # DocBook images are usually in <mediaobject> or <inlinemediaobject>
    # They can also be wrapped in <figure> or <informalfigure>
    image_related_tags = [
        f'{{{NS_URL}}}mediaobject',
        f'{{{NS_URL}}}inlinemediaobject',
        f'{{{NS_URL}}}figure',
        f'{{{NS_URL}}}informalfigure',
    ]
    
    # Collect elements to remove first to avoid modifying iterator
    to_remove_images = []
    for elem in tree.iter():
        if elem.tag in image_related_tags:
            to_remove_images.append(elem)
            
    for img_block in to_remove_images:
        parent = parent_map.get(img_block)
        if parent is None:
            continue

        # Check for intro/caption before removing
        children = list(parent)
        if img_block in children:
            idx = children.index(img_block)
            if idx > 0:
                prev = children[idx-1]
                if prev.tag in (f'{{{NS_URL}}}para', f'{{{NS_URL}}}simpara'):
                    text = "".join(prev.itertext()).strip()
                    lower_text = text.lower()
                    # Heuristics for image intros/captions
                    if (text.endswith(':') or 
                        "figure" in lower_text or
                        "screen" in lower_text or
                        "diagram" in lower_text or
                        "image" in lower_text or
                        "following" in lower_text):
                        parent.remove(prev)

        parent.remove(img_block)

    # 2. Remove Link Lists and their headers
    # Find all itemized lists
    lists_to_remove = []
    
    for ulist in root.findall('.//db:itemizedlist', NS):
        if is_navigation_list(ulist):
            lists_to_remove.append(ulist)
            
    for ulist in lists_to_remove:
        parent = parent_map.get(ulist)
        if parent is None:
            continue
            
        # Check previous sibling for introduction text
        children = list(parent)
        if ulist in children:
            idx = children.index(ulist)
            if idx > 0:
                prev = children[idx-1]
                # Check if prev is a paragraph
                if prev.tag in (f'{{{NS_URL}}}para', f'{{{NS_URL}}}simpara'):
                    text = "".join(prev.itertext()).strip()
                    # Heuristics for "See also" intro
                    lower_text = text.lower()
                    if (text.endswith(':') or 
                        "follow" in lower_text or 
                        "refer to" in lower_text or
                        "see also" in lower_text or
                        "more details" in lower_text or
                        "additional resources" in lower_text):
                        parent.remove(prev)
        
        parent.remove(ulist)

    # 3. Resolve remaining links to their descriptive text
    links_to_flatten = []
    for link_tag in root.findall('.//db:xref', NS) + \
                    root.findall('.//db:link', NS) + \
                    root.findall('.//db:ulink', NS):
        links_to_flatten.append(link_tag)

    for link_elem in links_to_flatten:
        parent = parent_map.get(link_elem)
        if parent is None:
            continue
        
        # Get the text content of the link element
        # Ensure we capture text that might be directly in the element or in children
        link_text = "".join(link_elem.itertext())
        
        # Create a text node (not an element) to replace the link element
        if link_text:
            # A safer way: replace the element with a dummy element containing just text
            # Then Pandoc will convert it to plain text.
            text_container = ET.Element(f'{{{NS_URL}}}phrase') # Use a generic phrase element
            text_container.text = link_text
            
            # CRITICAL: Preserve the tail text (text following the link)
            # and attach it to the new container so it's not lost.
            if link_elem.tail:
                text_container.tail = link_elem.tail

            # Find the index of the link element
            index = list(parent).index(link_elem)
            # Insert the text container at that index
            parent.insert(index, text_container)
            # Remove the original link element
            parent.remove(link_elem)
        else:
            # If the link has no text, just remove it.
            parent.remove(link_elem)

    # 4. Convert Tables to Prose (Lists)
    # This transforms <table> and <informaltable> into <itemizedlist>
    # Format: * Header1: Value1 - Header2: Value2 ...
    tables = root.findall('.//db:table', NS) + root.findall('.//db:informaltable', NS)
    for table in tables:
        # Check for tgroup (standard DocBook table structure)
        tgroup = table.find('db:tgroup', NS)
        if tgroup is None:
            continue
            
        # Get headers
        headers = []
        thead = tgroup.find('db:thead', NS)
        if thead:
            # Assume first row has headers
            header_row = thead.find('db:row', NS)
            if header_row:
                for entry in header_row.findall('db:entry', NS):
                    # Flatten header text
                    headers.append("".join(entry.itertext()).strip())
        
        # Get body rows
        tbody = tgroup.find('db:tbody', NS)
        if not tbody:
            continue
            
        # Create a list to replace the table
        ulist = ET.Element(f'{{{NS_URL}}}itemizedlist')
        
        rows = tbody.findall('db:row', NS)
        if not rows:
            continue
            
        for row in rows:
            listitem = ET.SubElement(ulist, f'{{{NS_URL}}}listitem')
            # Use simpara or para for list content
            para = ET.SubElement(listitem, f'{{{NS_URL}}}para')
            
            entries = row.findall('db:entry', NS)
            row_text_parts = []
            
            for i, entry in enumerate(entries):
                cell_text = "".join(entry.itertext()).strip()
                if not cell_text:
                    continue
                    
                # Match with header if available
                header_text = headers[i] if i < len(headers) else None
                
                if header_text:
                    row_text_parts.append(f"{header_text}: {cell_text}")
                else:
                    row_text_parts.append(cell_text)
            
            # Join columns with a separator
            para.text = " - ".join(row_text_parts)
            
        # Replace table with the new list
        parent = parent_map.get(table)
        if parent is not None:
             # Find index, insert list, remove table
             # Handle case where table might have been removed or moved (unlikely here)
             if table in list(parent):
                 idx = list(parent).index(table)
                 parent.insert(idx, ulist)
                 parent.remove(table)

    # 5. Remove Empty Sections
    # Iterate multiple times or bottom-up to handle nested empty sections
    # A section is empty if it has no children OR only a title/info child
    
    def is_empty_section(section):
        # allowed children that don't count as "content"
        # title, info, subtitle
        content_found = False
        for child in section:
            tag_local = child.tag.replace(f'{{{NS_URL}}}', '')
            if tag_local not in ('title', 'info', 'subtitle'):
                content_found = True
                break
        return not content_found

    # Repeatedly remove empty sections until no more changes
    # This handles nested empty sections (e.g. section A contains only section B, and B is empty)
    changed = True
    while changed:
        changed = False
        sections_to_remove = []
        for section in root.findall('.//db:section', NS):
            if is_empty_section(section):
                sections_to_remove.append(section)
        
        for section in sections_to_remove:
            parent = parent_map.get(section)
            if parent is not None:
                parent.remove(section)
                changed = True
            # Update parent map for next iteration? 
            # Not strictly necessary if we just re-scan, but efficient re-scan is harder.
            # Simple re-scan is fine for document size.

    tree.write(xml_path, encoding='utf-8', xml_declaration=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 clean_docbook.py <xml_file>", file=sys.stderr)
        sys.exit(1)
    clean_docbook(sys.argv[1])

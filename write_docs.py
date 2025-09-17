import os
import ast
import re
import yaml
from collections import defaultdict

# --- Configuration ---
INPUT_YAML_FILE = "docstrings.yaml"
# --- End Configuration ---

def build_docstring(doc_data):
    """Constructs the raw content of the docstring from the YAML data."""
    if doc_data.get('python'):
        return doc_data['python']
    
    parts = []
    if doc_data.get('description'):
        parts.append(doc_data['description']) # .strip() is REMOVED
    
    if doc_data.get('recipe'):
        recipe_content = doc_data['recipe'] # .strip() is REMOVED
        parts.append(f"Recipe:\n---\n```yaml\n{recipe_content}\n```")

    if doc_data.get('params'):
        parts.append(doc_data['params']) # .strip() is REMOVED

    if doc_data.get('other'):
        parts.append(doc_data['other']) # .strip() is REMOVED
        
    return "\n\n".join(part for part in parts if part)

def get_node_source_positions(node, source_lines):
    """
    Calculates the start and end character index for a node from its line/col offsets.
    """
    start_pos = 0
    for i in range(node.lineno - 1):
        start_pos += len(source_lines[i])
    start_pos += node.col_offset

    end_pos = 0
    for i in range(node.end_lineno - 1):
        end_pos += len(source_lines[i])
    end_pos += node.end_col_offset
    
    return start_pos, end_pos

if __name__ == "__main__":
    print(f"🚀 Reading docstring definitions from {INPUT_YAML_FILE}...")
    try:
        with open(INPUT_YAML_FILE, 'r', encoding='utf-8') as f:
            doc_definitions = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"❌ Error: {INPUT_YAML_FILE} not found. Run the extraction script first.")
        exit()

    updates_by_file = defaultdict(dict)
    if doc_definitions:
        for item in doc_definitions:
            updates_by_file[item['path']][item['target']] = build_docstring(item['docstring'])

    print("\n✍️ Applying updates to Python files...")
    if not updates_by_file:
        print("  -> No updates to apply.")
    else:
        for file_path, updates in updates_by_file.items():
            print(f"  -> Processing {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                
                source_lines = source_code.splitlines(keepends=True)
                module_name = os.path.splitext(os.path.basename(file_path))[0]
                tree = ast.parse(source_code)
                
                replacements = []

                # Find all top-level functions and classes that need updates
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        target_name = f"{module_name}.{node.name}"
                        if target_name in updates:
                            # Check if a docstring exists
                            if (node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant)):
                                docstring_node = node.body[0]
                                
                                # Get exact start/end character positions of the docstring
                                start_char, end_char = get_node_source_positions(docstring_node, source_lines)
                                
                                # Get the original docstring text to preserve its quotes
                                original_docstring_literal = source_code[start_char:end_char]
                                
                                # Extract the quote style (e.g., """, ''', r""")
                                match = re.match(r"([rRuUfF]*)((?:'''|\"\"\"|'|\"))", original_docstring_literal)
                                quote_prefix = match.group(1) if match else ""
                                quote_delimiter = match.group(2) if match else '"""'
                                
                                # Build the new docstring literal, preserving original quotes
                                new_docstring_content = updates[target_name]
                                new_docstring_literal = f"{quote_prefix}{quote_delimiter}{new_docstring_content}{quote_delimiter}"
                                
                                replacements.append((start_char, end_char, new_docstring_literal))
                
                # Apply replacements to the source text, from end to start
                new_source_code = source_code
                if replacements:
                    print(f"     -> ✨ Found {len(replacements)} docstring(s) to update.")
                    for start, end, new_text in sorted(replacements, key=lambda x: x[0], reverse=True):
                        new_source_code = new_source_code[:start] + new_text + new_source_code[end:]

                if new_source_code != source_code:
                    print("     -> Saving file.")
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_source_code)
                else:
                    print("     -> 💤 No changes detected. Skipping save.")

            except Exception as e:
                print(f"     ❌ Error processing file {file_path}: {e}")
                
    print("\n✅ Docstring update process complete!")
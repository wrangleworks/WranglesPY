import os
import ast
import yaml
import re

# --- Configuration ---
SCAN_DIRECTORY = "wrangles" 
OUTPUT_YAML_FILE = "docstrings.yaml"
# --- End Configuration ---

def parse_docstring(docstring: str):
    """
    Intelligently parses a docstring into structured fields.
    Anything that doesn't fit a known structure goes into 'other'.
    """
    if not docstring:
        return {'description': '', 'recipe': '', 'params': '', 'python': '', 'other': ''}

    remaining_text = docstring
    parsed = {'description': '', 'recipe': '', 'params': '', 'python': '', 'other': ''}

    # Carve out the recipe block
    recipe_match = re.search(r'\n\nRecipe:\n---\n```yaml\n(.*?)\n```', remaining_text, re.DOTALL)
    if recipe_match:
        parsed['recipe'] = recipe_match.group(1)
        remaining_text = remaining_text.replace(recipe_match.group(0), '||RECIPE||')

    # Carve out the python block
    python_match = re.search(r'\n\npython:\n```python\n(.*?)\n```', remaining_text, re.DOTALL)
    if python_match:
        parsed['python'] = python_match.group(1)
        remaining_text = remaining_text.replace(python_match.group(0), '||PYTHON||')

    # Carve out the params block (must be at the end of a section)
    params_match = re.search(r'\n\n(:param.*)', remaining_text, re.DOTALL)
    if params_match:
        parsed['params'] = params_match.group(1)
        remaining_text = remaining_text.replace(params_match.group(0), '||PARAMS||')

    # Assign description and other
    parts = re.split(r'(\|\|RECIPE\|\||\|\|PYTHON\|\||\|\|PARAMS\|\|)', remaining_text)
    parsed['description'] = parts.pop(0).strip()
    
    # Anything else that is not a placeholder is 'other'
    other_parts = [part.strip() for part in parts if part and not part.startswith('||')]
    parsed['other'] = '\n\n'.join(other_parts)

    return parsed

def extract_docstrings(root_dir):
    all_docstrings = []
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(subdir, file)
                module_name = os.path.splitext(os.path.basename(file_path))[0]
                print(f"🔍 Scanning {file_path}...")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    tree = ast.parse(source_code)
                except Exception as e:
                    print(f"  -> ⚠️  Could not parse {file_path}: {e}")
                    continue

                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        if node.name.startswith('_'): continue
                        
                        docstring_content = ast.get_docstring(node) or ""
                        parsed_data = parse_docstring(docstring_content)
                        target_name = f"{module_name}.{node.name}"
                        
                        doc_entry = {
                            'id': target_name,
                            'path': file_path.replace('\\', '/'),
                            'type': 'function' if isinstance(node, ast.FunctionDef) else 'class',
                            'target': target_name,
                            'docstring': parsed_data
                        }
                        all_docstrings.append(doc_entry)
    return all_docstrings

if __name__ == "__main__":
    print("🚀 Starting docstring extraction...")
    if os.path.exists(OUTPUT_YAML_FILE): os.remove(OUTPUT_YAML_FILE)
    extracted_data = extract_docstrings(SCAN_DIRECTORY)
    if not extracted_data:
        print("No functions or classes with docstrings found.")
    else:
        print(f"\nWriting {len(extracted_data)} entries to {OUTPUT_YAML_FILE}...")
        with open(OUTPUT_YAML_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(extracted_data, f, sort_keys=False, indent=2, allow_unicode=True, default_flow_style=False)
        print("✅ Extraction complete! You can now edit the YAML file.")
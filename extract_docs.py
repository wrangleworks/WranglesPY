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
    Parses a docstring with a custom format into a dictionary.
    Format: Description, then Recipe, then Params.
    """
    if not docstring:
        return {'description': '', 'recipe': '', 'params': '', 'other': ''}

    # Default values
    parsed = {
        'description': docstring,
        'recipe': '',
        'params': '',
        'other': ''
    }

    # Split by "Recipe:"
    parts = re.split(r'\n\s*Recipe:\n\s*---\n\s*```yaml', docstring, 1)
    parsed['description'] = parts[0].strip()

    if len(parts) > 1:
        recipe_and_params = parts[1]
        
        # Split the rest by the end of the yaml block to find params
        recipe_parts = re.split(r'```\n\n', recipe_and_params, 1)
        parsed['recipe'] = recipe_parts[0].strip()
        
        if len(recipe_parts) > 1:
            parsed['params'] = recipe_parts[1].strip()
    else:
        # No recipe found, check for params starting with :
        param_match = re.search(r'\n\s*:param|\n\s*:return', docstring)
        if param_match:
            param_start_index = param_match.start()
            # Ensure we only split if the params are not part of the initial description block
            if param_start_index > 0:
                parsed['params'] = docstring[param_start_index:].strip()
                parsed['description'] = docstring[:param_start_index].strip()

    return parsed

def extract_docstrings(root_dir):
    """
    Scans a directory for Python files and extracts docstrings from top-level functions and classes.
    """
    all_docstrings = []
    
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(subdir, file)
                module_name = os.path.splitext(os.path.basename(file_path))[0]
                
                print(f"🔍 Scanning {file_path}...")

                with open(file_path, 'r', encoding='utf-8') as f:
                    source_code = f.read()
                    tree = ast.parse(source_code)

                # --- THIS IS THE KEY CHANGE ---
                # We now iterate over tree.body to only get top-level nodes,
                # instead of using ast.walk() which finds nested functions.
                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        # Skip private functions/classes (e.g. _normalize)
                        if node.name.startswith('_'):
                            continue

                        docstring_content = ast.get_docstring(node) or ""
                        
                        # Use our parser to split the docstring into parts
                        parsed_data = parse_docstring(docstring_content)
                        
                        target_name = f"{module_name}.{node.name}"

                        doc_entry = {
                            'id': target_name,
                            'path': file_path.replace('\\', '/'),
                            'type': 'function' if isinstance(node, ast.FunctionDef) else 'class',
                            'target': target_name,
                            'docstring': {
                                'description': parsed_data['description'],
                                'recipe': parsed_data['recipe'],
                                'params': parsed_data['params'],
                                'python': '',
                                'other': parsed_data['other']
                            }
                        }
                        all_docstrings.append(doc_entry)
                        
    return all_docstrings

if __name__ == "__main__":
    print("🚀 Starting docstring extraction...")
    # Delete the old YAML file to ensure a clean start
    if os.path.exists(OUTPUT_YAML_FILE):
        os.remove(OUTPUT_YAML_FILE)

    extracted_data = extract_docstrings(SCAN_DIRECTORY)
    
    if not extracted_data:
        print("No functions or classes with docstrings found.")
    else:
        print(f"\nWriting {len(extracted_data)} entries to {OUTPUT_YAML_FILE}...")
        with open(OUTPUT_YAML_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(extracted_data, f, sort_keys=False, indent=2, allow_unicode=True, default_flow_style=False)
        print("✅ Extraction complete! You can now edit the YAML file.")
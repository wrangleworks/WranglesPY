import os
import ast
import yaml

# --- Configuration ---
SCAN_DIRECTORY = "wrangles" 
OUTPUT_YAML_FILE = "docstrings.yaml"
# --- End Configuration ---

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
                        
                        # Get the raw docstring content, DO NOT PARSE IT
                        docstring_content = ast.get_docstring(node) or ""
                        
                        target_name = f"{module_name}.{node.name}"
                        doc_entry = {
                            'id': target_name,
                            'path': file_path.replace('\\', '/'),
                            'type': 'function' if isinstance(node, ast.FunctionDef) else 'class',
                            'target': target_name,
                            'docstring': {
                                # Store the entire docstring in a single field
                                'content': docstring_content
                            }
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
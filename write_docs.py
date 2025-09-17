import os
import ast
import re
import yaml
from collections import defaultdict

# --- Configuration ---
INPUT_YAML_FILE = "docstrings.yaml"
# --- End Configuration ---

def build_docstring(doc_data):
    if doc_data.get('python'): return doc_data['python']
    parts = []
    if doc_data.get('description'): parts.append(doc_data['description'])
    if doc_data.get('recipe'):
        parts.append(f"Recipe:\n---\n```yaml\n{doc_data['recipe']}\n```")
    if doc_data.get('params'): parts.append(doc_data['params'])
    if doc_data.get('other'): parts.append(doc_data['other'])
    return "\n\n".join(part for part in parts if part)

def get_node_char_positions(node, source_lines):
    start_pos = sum(len(line) for line in source_lines[:node.lineno - 1]) + node.col_offset
    end_pos = sum(len(line) for line in source_lines[:node.end_lineno - 1]) + node.end_col_offset
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

                for node in tree.body:
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        target_name = f"{module_name}.{node.name}"
                        if target_name in updates:
                            new_content = updates[target_name]
                            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                                doc_node = node.body[0]
                                start, end = get_node_char_positions(doc_node, source_lines)
                                original_literal = source_code[start:end]
                                match = re.match(r"([rRuUfF]*)((?:'''|\"\"\"|'|\"))", original_literal)
                                prefix, delimiter = (match.groups() if match else ('', '"""'))
                                new_literal = f"{prefix}{delimiter}{new_content}{delimiter}"
                                replacements.append((start, end, new_literal))
                                print(f"     -> ✍️  Replacing docstring for '{target_name}'")
                            else:
                                first_stmt = node.body[0]
                                start, _ = get_node_char_positions(first_stmt, source_lines)
                                indent = ' ' * first_stmt.col_offset
                                new_literal = f'"""{new_content}"""\n{indent}'
                                replacements.append((start, start, new_literal))
                                print(f"     -> ✍️  Inserting docstring for '{target_name}'")
                
                new_code = source_code
                if replacements:
                    for start, end, text in sorted(replacements, reverse=True):
                        new_code = new_code[:start] + text + new_code[end:]
                if new_code != source_code:
                    print("     -> Saving file.")
                    with open(file_path, 'w', encoding='utf-8') as f: f.write(new_code)
                else:
                    print("     -> 💤 No changes detected. Skipping save.")
            except Exception as e:
                print(f"     ❌ Error processing file {file_path}: {e}")
    print("\n✅ Docstring update process complete!")
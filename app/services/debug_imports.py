import os
from pathlib import Path

def print_project_structure(start_path=".", max_depth=3):
    """Prints the directory structure to help debug import issues."""
    print("\n🔍 Project Structure:")
    for root, dirs, files in os.walk(start_path):
        level = root.replace(start_path, "").count(os.sep)
        if level > max_depth:
            continue
        indent = " " * 4 * level
        print(f"{indent}{os.path.basename(root)}/")
        sub_indent = " " * 4 * (level + 1)
        for file in files:
            if file.endswith(".py"):
                print(f"{sub_indent}{file}")

def check_import_path(module_name="app.models.portfolio"):
    """Checks if the module can be found in Python's path."""
    import importlib.util
    print("\n🔎 Checking import paths:")
    try:
        spec = importlib.util.find_spec(module_name)
        if spec:
            print(f"✅ Module found at: {spec.origin}")
        else:
            print(f"❌ Module '{module_name}' not found in Python path.")
            print("Python paths:")
            import sys
            for path in sys.path:
                print(f" - {path}")
    except Exception as e:
        print(f"⚠️ Error checking import: {e}")

if __name__ == "__main__":
    print_project_structure()
    check_import_path()
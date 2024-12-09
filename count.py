import os
import datetime

def get_python_files(directory="."):
    """
    Gets a list of all Python files in the directory and its subdirectories,
    excluding virtual environment directories.
    Returns a list of file paths.
    """
    python_files = []
    
    # Common virtual environment directory names to exclude
    venv_dirs = {'venv', 'env', '.env', '.venv', 'virtualenv', '.pytest_cache', '__pycache__'}
    
    for root, dirs, files in os.walk(directory):
        # Remove venv directories from dirs list to prevent walking into them
        dirs[:] = [d for d in dirs if d not in venv_dirs]
        
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    return sorted(python_files)  # Sort for consistent output

def create_python_catalog(output_file="python_code_catalog.txt"):
    """
    Creates a text file containing all Python code from the project with file indicators.
    """
    python_files = get_python_files()
    
    if not python_files:
        print("No Python files found in the current directory and its subdirectories.")
        return
    
    try:
        with open(output_file, 'w', encoding='utf-8') as catalog:
            # Write header
            catalog.write("Python Code Catalog\n")
            catalog.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            catalog.write("=" * 80 + "\n\n")
            
            total_files = 0
            total_lines = 0
            
            for file_path in python_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        lines = content.count('\n') + 1
                        
                        # Write file header
                        catalog.write(f"File: {file_path}\n")
                        catalog.write(f"Lines of code: {lines}\n")
                        catalog.write("-" * 80 + "\n\n")
                        
                        # Write file content
                        catalog.write(content)
                        
                        # Add spacing between files
                        catalog.write("\n\n" + "=" * 80 + "\n\n")
                        
                        total_files += 1
                        total_lines += lines
                        
                except Exception as e:
                    print(f"Error reading {file_path}: {str(e)}")
            
            # Write summary at the end
            catalog.write(f"\nSummary:\n")
            catalog.write(f"Total Python files processed: {total_files}\n")
            catalog.write(f"Total lines of Python code: {total_lines}\n")
            
        print(f"Python code catalog has been created: {output_file}")
        print(f"Total Python files processed: {total_files}")
        print(f"Total lines of Python code: {total_lines}")
        
    except Exception as e:
        print(f"Error creating catalog file: {str(e)}")

if __name__ == "__main__":
    create_python_catalog()
#!/usr/bin/env python3
"""
Script to fix syntax errors in tribunal.py
"""

def fix_syntax_errors():
    """Fix the syntax errors caused by regex replacement."""
    
    file_path = 'app/routes/tribunal.py'
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the malformed else statements
    content = content.replace('"""        else:', '"""\n        else:')
    content = content.replace('            """        else:', '            """\n        else:')
    
    # Fix the indentation issue with message = f"""
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        if 'message = f"""' in line and not line.strip().startswith('message = f"""'):
            # Fix indentation
            new_lines.append('                message = f"""')
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    # Write back the updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed syntax errors in tribunal.py")

if __name__ == '__main__':
    fix_syntax_errors()

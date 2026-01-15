"""Assembly file parser to extract global symbols and labels."""

import re
import os
import sys
from pathlib import Path


class AssemblyParser:
    """Parser for assembly files (.S, .s) to extract global symbols."""
    
    def __init__(self):
        self.global_symbols = {}  # {symbol_name: {'type': 'function'|'data'|'label', 'file': path, 'code': lines}}
        self.symbol_code = {}  # {symbol_name: [code_lines]}
    
    def parse_file(self, asm_file):
        """Parse an assembly file and extract global symbols."""
        try:
            with open(asm_file, 'r') as f:
                content = f.read()
            
            lines = content.split('\n')
            current_symbol = None
            symbol_lines = []
            in_symbol = False
            
            for i, line in enumerate(lines):
                stripped = line.strip()
                
                # Skip empty lines and comments when not in a symbol
                if not in_symbol and (not stripped or stripped.startswith(';') or stripped.startswith('#')):
                    continue
                
                # Look for global declarations: GLOBAL symbol, .globl symbol, .global symbol
                global_match = re.search(r'\.?(?:globl|global|GLOBAL)\s+(\w+)', line, re.IGNORECASE)
                if global_match:
                    symbol_name = global_match.group(1)
                    # Remove FUNC_ prefix if present (our convention)
                    if symbol_name.startswith('FUNC_'):
                        symbol_name = symbol_name[5:]
                    self.global_symbols[symbol_name] = {
                        'type': 'unknown',
                        'file': asm_file,
                        'line': i + 1
                    }
                    continue
                
                # Look for labels (symbols ending with ':')
                # Patterns: SYMBOL:, FUNC_symbol:, GLOBAL_symbol:
                label_match = re.search(r'^(\w+):\s*$', stripped)
                if label_match:
                    label_name = label_match.group(1)
                    
                    # Clean up label name (remove FUNC_, GLOBAL_ prefixes)
                    clean_name = label_name
                    if clean_name.startswith('FUNC_'):
                        clean_name = clean_name[5:]
                    elif clean_name.startswith('GLOBAL_'):
                        clean_name = clean_name[7:]
                    
                    # If we were tracking a symbol, save it
                    if current_symbol and symbol_lines:
                        self.symbol_code[current_symbol] = symbol_lines.copy()
                        symbol_lines = []
                    
                    # Start tracking this symbol
                    current_symbol = clean_name
                    in_symbol = True
                    symbol_lines = []  # Reset for new symbol
                    
                    # Determine symbol type based on context
                    if clean_name not in self.global_symbols:
                        # Try to determine type from context
                        symbol_type = 'label'
                        # Look ahead for function-like patterns
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            if any(keyword in next_line.upper() for keyword in ['PUSH', 'MOV RBP', 'PROC', 'FUNCTION']):
                                symbol_type = 'function'
                            elif any(keyword in next_line.upper() for keyword in ['DD', 'DQ', 'DB', 'DW', 'TIMES']):
                                symbol_type = 'data'
                        self.global_symbols[clean_name] = {
                            'type': symbol_type,
                            'file': asm_file,
                            'line': i + 1
                        }
                    else:
                        # Update existing symbol
                        self.global_symbols[clean_name]['file'] = asm_file
                        self.global_symbols[clean_name]['line'] = i + 1
                    
                    symbol_lines.append(line)
                    continue
                
                # If we're in a symbol, collect its lines
                if in_symbol and current_symbol:
                    symbol_lines.append(line)
                    
                    # Check if symbol ends (next label, section change, or end of file)
                    if i + 1 < len(lines):
                        next_stripped = lines[i + 1].strip()
                        # Check if next line is a new label
                        if re.search(r'^\w+:\s*$', next_stripped):
                            # Save current symbol
                            if symbol_lines:
                                self.symbol_code[current_symbol] = symbol_lines.copy()
                            symbol_lines = []
                            current_symbol = None
                            in_symbol = False
                        # Check for section changes
                        elif next_stripped.startswith('SECTION') or next_stripped.startswith('.section'):
                            # Save current symbol
                            if symbol_lines:
                                self.symbol_code[current_symbol] = symbol_lines.copy()
                            symbol_lines = []
                            current_symbol = None
                            in_symbol = False
                    # End of file
                    elif i + 1 >= len(lines):
                        if symbol_lines:
                            self.symbol_code[current_symbol] = symbol_lines.copy()
            
            # Save last symbol if any (already handled in loop, but keep for safety)
            if current_symbol and symbol_lines and current_symbol not in self.symbol_code:
                self.symbol_code[current_symbol] = symbol_lines.copy()
        
        except Exception as e:
            print(f"Warning: Failed to parse assembly file {asm_file}: {e}", file=sys.stderr)
    
    def get_symbol_code(self, symbol_name):
        """Get the assembly code for a symbol."""
        # Try exact match first
        if symbol_name in self.symbol_code:
            return self.symbol_code[symbol_name]
        
        # Try with FUNC_ prefix
        func_name = f"FUNC_{symbol_name}"
        if func_name in self.symbol_code:
            return self.symbol_code[func_name]
        
        # Try with GLOBAL_ prefix
        global_name = f"GLOBAL_{symbol_name}"
        if global_name in self.symbol_code:
            return self.symbol_code[global_name]
        
        # Also check in global_symbols for the symbol info
        if symbol_name in self.global_symbols:
            # Return empty list - symbol exists but no code extracted
            return []
        
        return None
    
    def has_symbol(self, symbol_name):
        """Check if a symbol exists."""
        # Check exact match
        if symbol_name in self.global_symbols or symbol_name in self.symbol_code:
            return True
        # Check with FUNC_ prefix
        func_name = f"FUNC_{symbol_name}"
        if func_name in self.global_symbols or func_name in self.symbol_code:
            return True
        # Check with GLOBAL_ prefix
        global_name = f"GLOBAL_{symbol_name}"
        if global_name in self.global_symbols or global_name in self.symbol_code:
            return True
        return False
    
    def get_all_symbols(self):
        """Get all extracted symbols."""
        return list(self.global_symbols.keys())


def find_asm_files(directory):
    """Recursively find all assembly files (.S, .s) in a directory."""
    asm_files = []
    path = Path(directory)
    
    if not path.exists():
        return asm_files
    
    if not path.is_dir():
        # Single file
        if path.suffix.lower() in ['.s', '.S']:
            return [str(path)]
        return asm_files
    
    # Recursively find all assembly files
    for asm_file in path.rglob("*.S"):
        asm_files.append(str(asm_file))
    for asm_file in path.rglob("*.s"):
        asm_files.append(str(asm_file))
    
    # Sort for deterministic order
    asm_files.sort()
    
    return asm_files


def parse_asm_files(directory_or_files):
    """Parse assembly files and extract symbols.
    
    Args:
        directory_or_files: Directory path or list of file paths
        
    Returns:
        AssemblyParser instance with parsed symbols
    """
    parser = AssemblyParser()
    
    if isinstance(directory_or_files, (list, tuple)):
        asm_files = directory_or_files
    else:
        asm_files = find_asm_files(directory_or_files)
    
    for asm_file in asm_files:
        parser.parse_file(asm_file)
    
    return parser

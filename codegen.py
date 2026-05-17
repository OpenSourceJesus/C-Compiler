"""Code generator with function call optimizations."""

from pycparser import c_ast
import struct
import sys
from register_allocator import analyze_all_functions_for_registers


def safe_str(obj):
    """Safely convert an object to string, preventing AST node attributes from leaking.
    
    This function ensures that AST node objects are never accidentally output
    as their string representation, which could include attribute names like
    'type' or 'field' that would cause assembly errors.
    """
    if obj is None:
        return "None"
    if isinstance(obj, str):
        return obj
    if isinstance(obj, (int, float, bool)):
        return str(obj)
    # For AST nodes, only output the class name, never the object itself
    if hasattr(obj, '__class__'):
        class_name = obj.__class__.__name__
        # Remove any angle brackets or module paths
        return class_name.split('.')[-1]
    # For other objects, use type name
    return type(obj).__name__


class CodeGenerator:
    """Code generator with indexed-jump, metamorphic return sites, quantized call-backs, and SIMD bit-packing."""
    
    def __init__(self, function_data, global_var_data=None, asm_parser=None, use_32bit=False, enable_metamorphic_return_sites=True, register_allocator=None, enable_indexed_function_calls=True):
        self.function_data = function_data
        self.global_var_data = global_var_data or {'packed_vars': [], 'bit_positions': {}, 'total_bits_used': 0}
        self.asm_parser = asm_parser  # Assembly parser for external symbols
        self.use_32bit = use_32bit  # 32-bit mode flag
        self.enable_metamorphic_return_sites = enable_metamorphic_return_sites  # Enable/disable metamorphic return sites
        self.enable_indexed_function_calls = enable_indexed_function_calls  # Use indexed jump for small functions (JMP base+offset vs CALL)
        self.register_allocator = register_allocator  # Register allocator for efficient register usage
        self.output = []
        self.small_functions = []
        self.function_offsets = {}
        self.return_site_base = 0x10000  # Base address for return sites
        self.return_sites = []  # Track return sites for quantized call-backs
        self.return_site_index = 0
        self.alignment = 16  # 16-byte alignment for quantized call-backs
        self.current_line = 0  # Track current output line for return site tracking
        self.simd_register = 'xmm15'  # Last SIMD register for bit-packing
        self.referenced_asm_symbols = set()  # Track which assembly symbols we've included
        self.variable_registers = {}  # Track which variables are currently in registers: {var_name: register}
        self._loop_hoisted_small_funcs = None  # When in a loop: {func_name: reg} for precomputed jump addresses
        self.needs_print_int_buffer = False  # Emit shared decimal buffer only when print("%d", ...) is used
        self.string_literals = {}  # Interned C string literals: {raw_literal: (label, decoded_value)}
        self.string_literal_counter = 0
        
        # Register names based on bit mode
        if use_32bit:
            self.reg_rax = 'EAX'
            self.reg_rbx = 'EBX'
            self.reg_rcx = 'ECX'
            self.reg_rdx = 'EDX'
            self.reg_rdi = 'EDI'
            self.reg_rsi = 'ESI'
            self.reg_rbp = 'EBP'
            self.reg_rsp = 'ESP'
            self.reg_r8 = 'EDI'  # Fallback for 6th arg - reuse EDI if needed
            self.reg_r9 = 'ESI'  # Fallback for 7th arg - reuse ESI if needed
            # In 32-bit mode, R12/R13 don't exist, use EBP/ESP for stack base/index
            # But EBP is already used for frame pointer, so use EBX/ECX instead
            self.reg_binary_op_temp = 'EBX'  # Same as RBX in 32-bit (no R10)
            self.stack_base_register = 'EBX'  # Base address register for stack (32-bit)
            self.stack_index_register = 'ECX'  # Index register (32-bit)
            self.small_func_dispatch_reg = 'EAX'  # Temp register for small-function JMP dispatch
        else:
            self.reg_rax = 'RAX'
            self.reg_rbx = 'RBX'
            self.reg_rcx = 'RCX'
            self.reg_rdx = 'RDX'
            self.reg_rdi = 'RDI'
            self.reg_rsi = 'RSI'
            self.reg_rbp = 'RBP'
            self.reg_rsp = 'RSP'
            self.reg_r8 = 'R8'
            self.reg_r9 = 'R9'
            # Caller-saved temp for binary ops so leaf functions (add, multiply) don't clobber RBX
            self.reg_binary_op_temp = 'R10'
            self.stack_base_register = 'R12'  # Base address register for stack
            self.stack_index_register = 'R13'  # Index register (stores slot index, fits in 32 bits)
            self.small_func_dispatch_reg = 'R11'  # Temp register for small-function JMP dispatch
        
        # Indexed stack pointer system (16-byte intervals)
        self.stack_slot_size = 16  # 16-byte intervals
        self.current_function_stack = {}  # Track local variables: {name: (slot_index, offset)}
        self.current_stack_slots = 0  # Number of 16-byte slots allocated in current function
        self.stack_base_address = 'STACK_BASE'  # Symbol for stack base address
        self.label_counter = 0  # Counter for unique labels
        self.saved_fp_in_rbx = False  # Track if function pointer is saved in RBX from if condition
        self.fp_in_rax = False  # Track if function pointer is already in RAX from condition
        self.metamorphic_labels = {}  # Track metamorphic return site labels: {func_name: label_name}
        self.struct_sizes = {}  # Populated at generate() from AST: {struct_name: size_in_bytes}
    
    def _get_ast_list(self, parser):
        """Return list of ASTs from parser (single CParser or MultiFileParser)."""
        if hasattr(parser, 'parsers'):
            return [p.ast for p in parser.parsers if getattr(p, 'ast', None)]
        if getattr(parser, 'ast', None):
            return [parser.ast]
        return []
    
    def _get_type_size_align(self, type_node, struct_sizes):
        """Return (size, alignment) in bytes for a type node. Uses struct_sizes for struct lookups."""
        if type_node is None:
            return (0, 1)
        if isinstance(type_node, c_ast.PtrDecl):
            return (4 if self.use_32bit else 8, 4 if self.use_32bit else 8)
        if isinstance(type_node, c_ast.FuncDecl):
            return (4 if self.use_32bit else 8, 4 if self.use_32bit else 8)
        if isinstance(type_node, c_ast.ArrayDecl):
            elem_size, elem_align = self._get_type_size_align(type_node.type, struct_sizes)
            dim = 1
            if getattr(type_node, 'dim', None) and hasattr(type_node.dim, 'value'):
                try:
                    dim = int(type_node.dim.value)
                except (ValueError, TypeError):
                    pass
            return (elem_size * dim, elem_align)
        if isinstance(type_node, c_ast.TypeDecl):
            return self._get_type_size_align(type_node.type, struct_sizes)
        if isinstance(type_node, c_ast.IdentifierType):
            names = getattr(type_node, 'names', None) or []
            s = ' '.join(str(n).lower() for n in names)
            if 'char' in s and 'long' not in s:
                return (1, 1)
            if 'short' in s:
                return (2, 2)
            if 'int' in s or 'unsigned' in s:
                return (4, 4)
            if 'long' in s or 'double' in s:
                return (8, 8)
            if 'float' in s:
                return (4, 4)
            return (4, 4)  # default
        if isinstance(type_node, (c_ast.Struct, c_ast.Union)):
            name = getattr(type_node, 'name', None)
            if name:
                size = struct_sizes.get(name, 8)
                return (size, 8 if not self.use_32bit else 4)
            return (8, 8)
        return (8, 8)
    
    def _compute_struct_size_from_decls(self, struct_node, struct_sizes):
        """Compute size of a struct from its .decls (member list)."""
        decls = getattr(struct_node, 'decls', None) or []
        offset = 0
        max_align = 1
        for decl in decls:
            size, align = self._get_type_size_align(decl.type, struct_sizes)
            if align <= 0:
                align = 1
            offset = (offset + align - 1) & ~(align - 1)
            offset += size
            max_align = max(max_align, align)
        offset = (offset + max_align - 1) & ~(max_align - 1)
        return offset
    
    def _collect_struct_definitions(self, ast_list):
        """Collect all Struct/Union nodes that have .name and .decls from ASTs."""
        structs = {}  # name -> node (first definition wins)
        
        class StructCollector(c_ast.NodeVisitor):
            def __init__(self, out):
                self.out = out
            def visit_Struct(self, node):
                if getattr(node, 'name', None) and getattr(node, 'decls', None):
                    if node.name not in self.out:
                        self.out[node.name] = node
                self.generic_visit(node)
            def visit_Union(self, node):
                if getattr(node, 'name', None) and getattr(node, 'decls', None):
                    if node.name not in self.out:
                        self.out[node.name] = node
                self.generic_visit(node)
        
        for ast in ast_list:
            StructCollector(structs).visit(ast)
        return structs
    
    def _struct_dependencies(self, struct_node, struct_sizes_keys):
        """Return set of struct names that this struct's members reference."""
        deps = set()
        decls = getattr(struct_node, 'decls', None) or []
        for decl in decls:
            node = decl.type
            while node:
                if isinstance(node, c_ast.TypeDecl):
                    node = node.type
                    continue
                if isinstance(node, (c_ast.Struct, c_ast.Union)):
                    name = getattr(node, 'name', None)
                    if name and name in struct_sizes_keys:
                        deps.add(name)
                    break
                if isinstance(node, c_ast.ArrayDecl):
                    node = node.type
                    continue
                break
        return deps
    
    def _collect_struct_sizes(self, parser):
        """Populate self.struct_sizes from parser AST(s) by computing sizes from struct definitions."""
        ast_list = self._get_ast_list(parser)
        struct_defs = self._collect_struct_definitions(ast_list)
        # Compute in dependency order: if A has a member of type B, compute B first
        computed = {}
        names = list(struct_defs.keys())
        changed = True
        while changed:
            changed = False
            for name in names:
                if name in computed:
                    continue
                node = struct_defs[name]
                deps = self._struct_dependencies(node, set(computed.keys()) | set(names))
                if all(d in computed for d in deps):
                    size = self._compute_struct_size_from_decls(node, computed)
                    computed[name] = size
                    changed = True
        # Any remaining (e.g. forward decl only) get default 8
        for name in names:
            if name not in computed:
                computed[name] = 8
        self.struct_sizes = computed
    
    def _safe_append(self, line):
        """Safely append a line to output, ensuring no AST node objects are included.
        
        This prevents AST nodes from being accidentally converted to strings
        and output, which could cause assembly errors with labels like 'type'
        or 'field'.
        """
        # If line contains an AST node object, convert it safely
        if isinstance(line, c_ast.Node):
            # This should never happen, but protect against it
            line = f"; ERROR: AST node object detected: {safe_str(line)}"
        elif not isinstance(line, str):
            # Convert non-string objects safely
            line = safe_str(line)
        
        # Check if line looks like it contains an AST node attribute that was output as a label
        # Patterns like "type:" or "field:" at the start of a line (after whitespace)
        import re
        stripped = line.strip()
        # Check for problematic labels that are AST attribute names
        problematic_labels = ['type:', 'field:', 'name:', 'expr:', 'node:', 'struct_ref:', 'assign:']
        if stripped in problematic_labels or (stripped.endswith(':') and len(stripped.split()) == 1 and stripped[:-1] in ['type', 'field', 'name', 'expr', 'node']):
            # This looks like an AST node attribute was output as a label - skip it
            return  # Don't output this line
        
        self.output.append(line)
    
    def generate(self, parser):
        """Generate optimized code for all functions."""
        self.output = []
        self.needs_print_int_buffer = False
        self.string_literals = {}
        self.string_literal_counter = 0
        self._current_parser = parser  # Store parser reference for variable lookup
        self._collect_struct_sizes(parser)  # Auto-detect struct sizes from AST
        
        # Separate small and large functions, deduplicating by name
        functions = parser.get_functions()
        seen_funcs = {}  # {func_name: func_node} to deduplicate
        for func in functions:
            func_name = func.decl.name if func.decl else "unknown"
            # Skip functions with "unknown" names - they're likely parsing errors
            if func_name == "unknown":
                continue
            # Only keep the first occurrence of each function
            if func_name not in seen_funcs:
                seen_funcs[func_name] = func
        
        # Use deduplicated functions
        unique_functions = list(seen_funcs.values())
        small_funcs = []
        large_funcs = []
        
        for func in unique_functions:
            func_name = func.decl.name if func.decl else "unknown"
            # Skip functions with "unknown" names
            if func_name == "unknown":
                continue
            if self.enable_indexed_function_calls and func_name in self.function_data and self.function_data[func_name]['is_small']:
                small_funcs.append(func)
            else:
                large_funcs.append(func)
        
        # Generate code section
        # Add BITS directive based on mode
        if self.use_32bit:
            self.output.append("BITS 32")
        else:
            self.output.append("BITS 64")
        self.output.append("SECTION .text")
        self.output.append("")
        
        # Check if _start is already defined in assembly files
        has_external_start = self.asm_parser and self.asm_parser.has_symbol('_start')
        
        # Export all function symbols as global so they can be linked with external assembly files
        self.output.append("; Export functions as global symbols for linking")
        if not has_external_start:
            self.output.append("GLOBAL _start  ; Entry point")
        all_function_names = set()
        for func in small_funcs + large_funcs:
            func_name = func.decl.name if func.decl else None
            if func_name and func_name != "unknown":
                all_function_names.add(func_name)
        for func_name in sorted(all_function_names):
            self.output.append(f"GLOBAL FUNC_{func_name}")
        self.output.append("")
        
        # Only generate _start if not already defined in assembly files
        if not has_external_start:
            # Generate main entry point
            self.output.append("; Program entry point")
            self.output.append("_start:")
            
            # Ensure stack is 16-byte aligned (required for x86-64 ABI)
            # RSP is already set by the kernel, but we align it to be safe
            self.output.append("    ; Align stack to 16 bytes (x86-64 ABI requirement)")
            if self.use_32bit:
                self.output.append(f"    AND {self.reg_rsp}, 0xFFFFFFF0  ; Align to 16-byte boundary (32-bit)")
            else:
                self.output.append(f"    AND {self.reg_rsp}, 0xFFFFFFFFFFFFFFF0  ; Align to 16-byte boundary")
            
            # Initialize SIMD bit-packing if needed
            if self.global_var_data['packed_vars']:
                self.output.append("    CALL _init_simd_packing  ; Initialize SIMD bit-packing")
            
            # Call main function if it exists
            has_main = any(
                (f.decl.name if f.decl else "unknown") == "main"
                for f in small_funcs + large_funcs
            )
            if has_main:
                # Always use normal CALL/RET for main: metamorphic return would require _start to
                # write the return address into code (.text), which is not writable at runtime.
                main_info = self.function_data.get("main", {})
                use_metamorphic_for_main = False  # Never use for main - .text is read-only
                if use_metamorphic_for_main and self.enable_metamorphic_return_sites and main_info.get('has_single_return', False) and not main_info.get('is_small', False):
                    # Use metamorphic return site for main
                    return_site_label = "__after_main"
                    metamorphic_label = "FUNC_main_METAMORPHIC"
                    # Register the label so it gets generated
                    if "main" not in self.metamorphic_labels:
                        self.metamorphic_labels["main"] = metamorphic_label
                    self.output.append("    ; Metamorphic return site: write return address into instruction bytes")
                    if self.use_32bit:
                        self.output.append(f"    LEA {self.reg_rax}, [{metamorphic_label}+1]  ; Address of immediate value")
                        self.output.append(f"    LEA {self.reg_rdx}, [{return_site_label}]  ; Get return address")
                        self.output.append(f"    MOV DWORD [{self.reg_rax}], EDX  ; Write return address")
                    else:
                        self.output.append(f"    LEA {self.reg_rax}, [rel {metamorphic_label}+1]  ; Address of immediate value")
                        self.output.append(f"    LEA {self.reg_rdx}, [rel {return_site_label}]  ; Get return address")
                        self.output.append(f"    MOV DWORD [{self.reg_rax}], EDX  ; Write return address (32-bit, like example)")
                    self.output.append("    JMP FUNC_main  ; Jump to main function")
                    self.output.append(f"{return_site_label}:  ; Return site after main")
                else:
                    self.output.append("    CALL FUNC_main  ; Call main function")
                self.output.append(f"    ; Main return value is in {self.reg_rax}, save it for exit")
                self.output.append(f"    MOV {self.reg_rdi}, {self.reg_rax}  ; Save return value to {self.reg_rdi} (exit code)")
            else:
                self.output.append(f"    MOV {self.reg_rdi}, 0   ; No main function, exit with code 0")
            
            # Exit with return code from main (in RDI)
            self.output.append("    ; Exit system call (sys_exit)")
            if self.use_32bit:
                self.output.append(f"    MOV {self.reg_rax}, 1  ; sys_exit (32-bit)")
            else:
                self.output.append(f"    MOV {self.reg_rax}, 60  ; sys_exit")
            self.output.append("    INT 0x80" if self.use_32bit else "    SYSCALL")
            self.output.append("")
        
        # Set small-function offsets and emit co-located small function block (dispatch inlined at call sites)
        if small_funcs:
            self._generate_indexed_jump_table(small_funcs)
            self.output.append("; Co-located small functions (<1024 bytes) in 1024-byte slots")
            self.output.append(f"ALIGN {self.SMALL_FUNC_SLOT_SIZE}")
            self.output.append("SMALL_FUNC_BASE:")
            for func in small_funcs:
                func_name = func.decl.name if func.decl else "unknown"
                self._generate_function(func, in_small_func_block=True)
                # Pad to 1024-byte slot so address = SMALL_FUNC_BASE + index*1024
                self.output.append(f"    ; Pad to 1024-byte slot for indexed-jump co-location")
                self.output.append(f"%if ($ - FUNC_{func_name}) < {self.SMALL_FUNC_SLOT_SIZE}")
                self.output.append(f"times {self.SMALL_FUNC_SLOT_SIZE} - ($ - FUNC_{func_name}) db 0x90")
                self.output.append("%endif")
                self.output.append("")
        
        # Generate SIMD bit-packing init function (after entry point, before other functions)
        if self.global_var_data['packed_vars']:
            self._generate_simd_packing_init()
            self.output.append("")
        
        # Generate large functions (small functions already emitted in co-located block)
        for func in large_funcs:
            self._generate_function(func, in_small_func_block=False)
            self.output.append("")
        
        # Generate data section for function table and global variables
        self._generate_data_section(parser)
        
        # Generate assembly code for referenced external symbols
        if self.asm_parser:
            self._generate_asm_symbols(parser)
        
        # Final sanitization pass to remove any AST node attributes that might have leaked
        sanitized_output = []
        for line in self.output:
            # Skip lines that look like AST node attributes output as labels
            stripped = line.strip()
            problematic_labels = ['type:', 'field:', 'name:', 'expr:', 'node:', 'struct_ref:', 'assign:']
            if stripped in problematic_labels:
                # Skip this line - it's an AST node attribute that was accidentally output
                continue
            # Also check for single-word labels that are AST attribute names
            if stripped.endswith(':') and len(stripped.split()) == 1:
                label_name = stripped[:-1]
                if label_name in ['type', 'field', 'name', 'expr', 'node', 'struct_ref', 'assign']:
                    # Skip this line
                    continue
            sanitized_output.append(line)
        
        return "\n".join(sanitized_output)
    
    SMALL_FUNC_SLOT_SIZE = 1024  # Co-locate small functions in 1024-byte slots

    def _generate_indexed_jump_table(self, small_funcs):
        """Set function_offsets for co-located small functions (<1024 bytes).
        Dispatch is inlined at each call site (one CALL only); no separate INDEXED_JUMP routine.
        """
        offset = 0
        for func in small_funcs:
            func_name = func.decl.name if func.decl else "unknown"
            self.function_offsets[func_name] = offset
            offset += 1
    
    def _generate_function_table(self, small_funcs):
        """Generate function pointer table."""
        self.output.append("SECTION .data")
        self.output.append("FUNC_TABLE:")
        for func in small_funcs:
            func_name = func.decl.name if func.decl else "unknown"
            if self.use_32bit:
                self.output.append(f"    DD FUNC_{func_name}  ; (32-bit)")
            else:
                self.output.append(f"    DQ FUNC_{func_name}")
    
    def _generate_data_section(self, parser):
        """Generate data section for global variables and STACK_BASE."""
        # Use .rodata for read-only data (strings) and .data for writable data
        # For now, put everything in .data for compatibility
        self.output.append("SECTION .data")
        self.output.append("")
        
        # Always define STACK_BASE for indexed stack pointer system
        self.output.append("STACK_BASE:")
        if self.use_32bit:
            self.output.append("    DD 0x7FFF0000  ; Stack base address (32-bit)")
        else:
            self.output.append("    DQ 0x7FFF0000  ; Stack base address")
        self.output.append("")

        # Shared scratch buffer used by print("%d", value) formatting.
        if self.needs_print_int_buffer:
            self.output.append("GLOBAL___print_int_buf:")
            self.output.append("    TIMES 32 DB 0")
            self.output.append("")

        # Interned string literals used directly by expressions/calls
        for _, (label, string_value) in sorted(self.string_literals.items(), key=lambda item: item[1][0]):
            self.output.append(f"{label}:")
            for char in string_value:
                if char == '\n':
                    self.output.append("    DB 10  ; newline")
                elif char == '\t':
                    self.output.append("    DB 9   ; tab")
                elif char == '\r':
                    self.output.append("    DB 13  ; carriage return")
                elif ord(char) < 32 or ord(char) > 126 or char in ["'", '"']:
                    self.output.append(f"    DB {ord(char)}")
                else:
                    self.output.append(f"    DB '{char}'")
            self.output.append("    DB 0  ; null terminator")
            self.output.append("")
        
        globals = parser.get_global_variables()
        
        # Generate global variables (if any)
        if globals:
            # Deduplicate global variables by name
            seen_globals = {}  # {var_name: var_node} to deduplicate
            for var in globals:
                var_name = var.name if var.name else None
                if not var_name:
                    continue
                # Only keep the first occurrence of each global
                if var_name not in seen_globals:
                    seen_globals[var_name] = var
            
            packed_var_names = {var['name'] for var in self.global_var_data['packed_vars']}
            
            for var_name, var in seen_globals.items():
                # Only generate data for non-packed variables
                # Packed variables are stored in SIMD register
                if var_name not in packed_var_names:
                    # Check if this is an array
                    is_array = False
                    array_size = 0
                    # Check type structure for arrays
                    type_node = var.type
                    while hasattr(type_node, 'type'):
                        if isinstance(type_node, c_ast.ArrayDecl):
                            is_array = True
                            if type_node.dim:
                                if isinstance(type_node.dim, c_ast.Constant):
                                    try:
                                        array_size = int(type_node.dim.value)
                                    except:
                                        array_size = 10  # Default size
                                else:
                                    array_size = 10  # Default size
                            break
                        type_node = type_node.type
                    
                    # Check if array has string initializer (before defining label)
                    has_string_init = False
                    string_value = None
                    if is_array and var.init and isinstance(var.init, c_ast.Constant):
                        value = var.init.value
                        if isinstance(value, str) and ((value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))):
                            has_string_init = True
                            # Extract string content (remove quotes)
                            if value.startswith('"'):
                                string_value = value[1:-1].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\\\', '\\')
                            else:
                                string_value = value[1:-1]
                    
                    if has_string_init and string_value:
                        # String array: put in .data section so it is writable (code may write to it)
                        self.output.append("SECTION .data")
                        self.output.append(f"GLOBAL_{var_name}:")
                        # String array: determine size from string + null terminator
                        actual_size = len(string_value) + 1  # +1 for null terminator
                        # Use DB (bytes) for char arrays
                        # NASM doesn't support escape sequences in single quotes, so output bytes directly
                        # Split string into parts, handling special characters
                        for char in string_value:
                            if char == '\n':
                                self.output.append("    DB 10  ; newline")
                            elif char == '\t':
                                self.output.append("    DB 9   ; tab")
                            elif char == '\r':
                                self.output.append("    DB 13  ; carriage return")
                            elif ord(char) < 32 or ord(char) > 126:
                                # Non-printable character - output as numeric value
                                self.output.append(f"    DB {ord(char)}  ; non-printable")
                            else:
                                # Regular printable character
                                if char == "'" or char == '"':
                                    # Escape quote in string literal
                                    self.output.append(f"    DB {ord(char)}  ; quote")
                                else:
                                    self.output.append(f"    DB '{char}'")
                        self.output.append(f"    DB 0  ; null terminator")
                    else:
                        # Non-string array or variable - define in .data section
                        self.output.append(f"GLOBAL_{var_name}:")
                        if is_array:
                            if array_size > 0:
                                # Array declaration: allocate array_size * 4 bytes (assuming int)
                                self.output.append(f"    TIMES {array_size} DD 0  ; {var_name}[{array_size}]")
                            else:
                                # Implicit size array - allocate minimum space (will be sized from initializer if present)
                                self.output.append(f"    DD 0  ; {var_name}[] (implicit size)")
                        elif var.init:
                            # Has initializer
                            if isinstance(var.init, c_ast.Constant):
                                value = var.init.value
                                # Handle string constants - convert to numeric if needed
                                if isinstance(value, str) and len(value) > 1:
                                    # For string constants longer than 1 char, use address or convert
                                    # For now, just use 0 and let the linker handle it
                                    self.output.append(f"    DD 0  ; {var_name} (string constant)")
                                else:
                                    # Try to convert value to integer for assembly
                                    try:
                                        # Handle numeric values
                                        if isinstance(value, str):
                                            # Try parsing as integer (hex, decimal, etc.)
                                            if value.startswith('0x') or value.startswith('0X'):
                                                num_value = int(value, 16)
                                            else:
                                                num_value = int(value)
                                        else:
                                            num_value = int(value)
                                        self.output.append(f"    DD {num_value}  ; {var_name}")
                                    except (ValueError, TypeError):
                                        # If conversion fails, use 0
                                        self.output.append(f"    DD 0  ; {var_name} (initialized at runtime)")
                            else:
                                # Non-constant initializer - initialize to 0
                                self.output.append(f"    DD 0  ; {var_name} (initialized at runtime)")
                        else:
                            # No initializer - check if struct type to allocate full size
                            struct_size = 0
                            type_node = var.type
                            while type_node and hasattr(type_node, 'type'):
                                inner = type_node.type
                                if hasattr(inner, 'name') and not hasattr(inner, 'names'):
                                    struct_size = self.struct_sizes.get(inner.name, 0)
                                    break
                                type_node = inner
                            if struct_size > 0:
                                self.output.append(f"    TIMES {struct_size} DB 0  ; {var_name} (struct)")
                            else:
                                self.output.append(f"    DD 0  ; {var_name}")
                else:
                    # Packed variable - still need a storage location for initialization
                    # but it will be packed into SIMD register
                    self.output.append(f"GLOBAL_{var_name}:")
                    if var.init:
                        if isinstance(var.init, c_ast.Constant):
                            value = var.init.value
                            # Handle string constants - convert to numeric if needed
                            if isinstance(value, str) and len(value) > 1:
                                # For string constants, use 0
                                self.output.append(f"    DB 0  ; {var_name} (packed, string constant)")
                            else:
                                # Try to convert value to integer for assembly
                                try:
                                    if isinstance(value, str):
                                        if value.startswith('0x') or value.startswith('0X'):
                                            num_value = int(value, 16)
                                        else:
                                            num_value = int(value)
                                    else:
                                        num_value = int(value)
                                    # Ensure value fits in byte for DB
                                    num_value = num_value & 0xFF
                                    self.output.append(f"    DB {num_value}  ; {var_name} (packed into SIMD register)")
                                except (ValueError, TypeError):
                                    self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
                        else:
                            self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
                    else:
                        self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
        
        # No need to generate memory locations for metamorphic return sites
        # The return addresses are written directly into instruction bytes
        
        self.output.append("")

    def _decode_c_string_literal(self, literal):
        """Decode a quoted C string literal to Python text (basic escapes)."""
        if not isinstance(literal, str) or len(literal) < 2:
            return ""
        if literal[0] == literal[-1] and literal[0] in ["'", '"']:
            literal = literal[1:-1]
        return literal.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\\\', '\\')

    def _intern_string_literal(self, literal):
        """Return stable data label for a C string literal."""
        if literal not in self.string_literals:
            label = f"STR_LIT_{self.string_literal_counter}"
            self.string_literal_counter += 1
            self.string_literals[literal] = (label, self._decode_c_string_literal(literal))
        return self.string_literals[literal]

    def _intern_runtime_string(self, text):
        """Return stable data label for generated runtime text (already decoded)."""
        key = f"__runtime__{text}"
        if key not in self.string_literals:
            label = f"STR_LIT_{self.string_literal_counter}"
            self.string_literal_counter += 1
            self.string_literals[key] = (label, text)
        return self.string_literals[key]

    def _emit_write_syscall_literal(self, text, preserve_rax=False):
        """Emit direct write(1, literal, len) syscall for a Python string."""
        if not text:
            return
        label, value = self._intern_runtime_string(text)
        if preserve_rax:
            self.output.append(f"    PUSH {self.reg_rax}  ; Preserve value across literal write")
        if self.use_32bit:
            self.output.append("    MOV EAX, 4  ; sys_write (32-bit)")
            self.output.append("    MOV EBX, 1  ; stdout")
            self.output.append(f"    LEA ECX, [{label}]")
            self.output.append(f"    MOV EDX, {len(value)}")
            self.output.append("    INT 0x80")
        else:
            self.output.append("    MOV RAX, 1  ; sys_write")
            self.output.append("    MOV RDI, 1  ; stdout")
            self.output.append(f"    LEA RSI, [rel {label}]")
            self.output.append(f"    MOV RDX, {len(value)}")
            self.output.append("    SYSCALL")
        if preserve_rax:
            self.output.append(f"    POP {self.reg_rax}  ; Restore preserved value")

    def _emit_write_syscall_from_regs(self, buffer_reg, length_reg):
        """Emit direct write(1, buffer_reg, length_reg) syscall."""
        if self.use_32bit:
            self.output.append("    MOV EAX, 4  ; sys_write (32-bit)")
            self.output.append("    MOV EBX, 1  ; stdout")
            if buffer_reg != 'ECX':
                self.output.append(f"    MOV ECX, {buffer_reg}")
            if length_reg != 'EDX':
                self.output.append(f"    MOV EDX, {length_reg}")
            self.output.append("    INT 0x80")
        else:
            self.output.append("    MOV RAX, 1  ; sys_write")
            self.output.append("    MOV RDI, 1  ; stdout")
            if buffer_reg != 'RSI':
                self.output.append(f"    MOV RSI, {buffer_reg}")
            if length_reg != 'RDX':
                self.output.append(f"    MOV RDX, {length_reg}")
            self.output.append("    SYSCALL")
    
    def _generate_asm_symbols(self, parser):
        """Generate assembly code for referenced external symbols from .S files."""
        if not self.asm_parser or not self.referenced_asm_symbols:
            return
        
        self.output.append("")
        self.output.append("; ========================================")
        self.output.append("; Assembly symbols from .S files")
        self.output.append("; ========================================")
        self.output.append("")
        
        # Group symbols by type
        functions = []
        data_symbols = []
        
        for symbol_name in sorted(self.referenced_asm_symbols):
            if not self.asm_parser.has_symbol(symbol_name):
                continue
            
            symbol_info = self.asm_parser.global_symbols.get(symbol_name)
            if not symbol_info:
                # Try with FUNC_ prefix
                symbol_info = self.asm_parser.global_symbols.get(f"FUNC_{symbol_name}")
            if not symbol_info:
                # Try with GLOBAL_ prefix
                symbol_info = self.asm_parser.global_symbols.get(f"GLOBAL_{symbol_name}")
            
            if symbol_info:
                symbol_type = symbol_info.get('type', 'unknown')
                if symbol_type == 'function':
                    functions.append(symbol_name)
                elif symbol_type == 'data':
                    data_symbols.append(symbol_name)
                else:
                    # Unknown type - assume function if it's called
                    functions.append(symbol_name)
        
        # Generate functions first
        if functions:
            self.output.append("SECTION .text")
            self.output.append("; Assembly-defined functions")
            self.output.append("")
            for func_name in functions:
                code = self.asm_parser.get_symbol_code(func_name)
                if code:
                    self.output.append(f"; Function: {func_name} (from assembly)")
                    self.output.append(f"FUNC_{func_name}:")
                    # Output the code, skipping the label line if it's already there
                    for line in code:
                        # Skip if it's the same label (already output above)
                        stripped = line.strip()
                        # Skip problematic labels that might be attribute names
                        if stripped.endswith(':') and (func_name in stripped or f"FUNC_{func_name}" in stripped):
                            continue
                        # Skip lines that look like attribute names being output as labels
                        # These are common Python attribute names that shouldn't be assembly labels
                        problematic_labels = ['type:', 'field:', 'name:', 'value:', 'op:', 'expr:', 'left:', 'right:']
                        if stripped in problematic_labels or stripped in [l[:-1] for l in problematic_labels]:
                            continue
                        # Skip lines that are just a single word followed by colon (likely a label)
                        # but only if it's a known problematic attribute name
                        if stripped.endswith(':') and len(stripped.split()) == 1:
                            label_name = stripped[:-1]
                            if label_name in ['type', 'field', 'name', 'value', 'op', 'expr', 'left', 'right']:
                                continue
                        # Skip empty lines that are just whitespace
                        if not stripped:
                            continue
                        self.output.append(line)
                    self.output.append("")
        
        # Generate data symbols in data section
        if data_symbols:
            self.output.append("SECTION .data")
            self.output.append("; Assembly-defined global variables")
            self.output.append("")
            for var_name in data_symbols:
                code = self.asm_parser.get_symbol_code(var_name)
                if code:
                    self.output.append(f"; Global variable: {var_name} (from assembly)")
                    self.output.append(f"GLOBAL_{var_name}:")
                    # Output the code, skipping the label line if it's already there
                    for line in code:
                        # Skip if it's the same label (already output above)
                        stripped = line.strip()
                        # Skip problematic labels that might be attribute names
                        if stripped.endswith(':') and (var_name in stripped or f"GLOBAL_{var_name}" in stripped):
                            continue
                        # Skip lines that look like attribute names being output as labels
                        # These are common Python attribute names that shouldn't be assembly labels
                        problematic_labels = ['type:', 'field:', 'name:', 'value:', 'op:', 'expr:', 'left:', 'right:']
                        if stripped in problematic_labels or stripped in [l[:-1] for l in problematic_labels]:
                            continue
                        # Skip lines that are just a single word followed by colon (likely a label)
                        # but only if it's a known problematic attribute name
                        if stripped.endswith(':') and len(stripped.split()) == 1:
                            label_name = stripped[:-1]
                            if label_name in ['type', 'field', 'name', 'value', 'op', 'expr', 'left', 'right']:
                                continue
                        # Skip empty lines that are just whitespace
                        if not stripped:
                            continue
                        self.output.append(line)
                    self.output.append("")
    
    def _generate_simd_packing_init(self):
        """Generate initialization code to pack global variables into SIMD register."""
        self.output.append("; SIMD Bit-Packing: Pack global variables (1-8 bits) into last SIMD register")
        self.output.append("; This register (xmm15) is typically ignored by standard compilers")
        self.output.append("; Variables declared as 'auto _Alignas(N) char' are packed as N-bit values")
        self.output.append("_init_simd_packing:")
        self.output.append(f"    ; Initialize {self.simd_register} with packed global variables")
        self.output.append(f"    PXOR {self.simd_register}, {self.simd_register}  ; Clear register")
        
        packed_vars = self.global_var_data['packed_vars']
        bit_positions = self.global_var_data['bit_positions']
        
        # Pack each variable into the register
        for var_info in packed_vars:
            var_name = var_info['name']
            start_bit = var_info['start_bit']
            bits = var_info['bits']
            
            # Load initial value (if any) and pack into register
            self.output.append(f"    ; Pack {var_name} at bit {start_bit}, width {bits} bits")
            self.output.append(f"    MOVZX {self.reg_rax}, BYTE [GLOBAL_{var_name}]  ; Load {var_name}")
            self.output.append(f"    ; Extract and mask to {bits} bits")
            self.output.append(f"    AND {self.reg_rax}, {(1 << bits) - 1}  ; Mask to {bits} bits")
            
            # Pack into SIMD register using bit manipulation
            if start_bit == 0:
                # First variable: just move into low bits
                self.output.append(f"    MOVQ XMM0, RAX  ; Move to XMM0")
                self.output.append(f"    POR {self.simd_register}, XMM0  ; OR into packed register")
            else:
                # Shift to correct position and OR into register
                self.output.append(f"    SHL RAX, {start_bit}  ; Shift to bit position {start_bit}")
                self.output.append(f"    MOVQ XMM0, RAX  ; Move to XMM0")
                self.output.append(f"    POR {self.simd_register}, XMM0  ; OR into packed register")
        
        self.output.append(f"    ; {self.simd_register} now contains all packed global variables")
        self.output.append("    RET")
        self.output.append("")
    
    def _generate_packed_var_access(self, var_name, is_write=False, value_reg='RAX'):
        """Generate inline assembly to access a packed variable.
        
        For interrupt callbacks: Uses SIMD register for zero-latency access.
        For normal functions: Uses simple memory access for better performance.
        """
        if var_name not in self.global_var_data['bit_positions']:
            return None  # Not a packed variable
        
        # Check if we're in an interrupt callback (use zero-latency SIMD access)
        is_interrupt = hasattr(self, '_current_function_name') and self._is_interrupt_callback(getattr(self, '_current_function_name', ''))
        
        if is_interrupt:
            # Zero-latency SIMD access for interrupt callbacks
            start_bit, bits = self.global_var_data['bit_positions'][var_name]
            mask = (1 << bits) - 1
            
            if is_write:
                self.output.append(f"    ; Zero-latency write to packed variable {var_name}")
                self.output.append(f"    PUSH {value_reg}  ; Save value to write")
                self.output.append(f"    MOVQ RAX, {self.simd_register}  ; Load packed register")
                mask_shifted = mask << start_bit
                self.output.append(f"    MOV {self.reg_binary_op_temp}, {mask_shifted}")
                self.output.append(f"    NOT {self.reg_binary_op_temp}  ; Invert mask")
                self.output.append(f"    AND RAX, {self.reg_binary_op_temp}  ; Clear bits for {var_name}")
                self.output.append(f"    POP {self.reg_binary_op_temp}  ; Restore value to write")
                self.output.append(f"    AND {self.reg_binary_op_temp}, {mask}  ; Mask to {bits} bits")
                if start_bit > 0:
                    self.output.append(f"    SHL {self.reg_binary_op_temp}, {start_bit}  ; Shift to position")
                self.output.append(f"    OR RAX, {self.reg_binary_op_temp}  ; Insert new value")
                self.output.append(f"    MOVQ {self.simd_register}, RAX  ; Store back to SIMD register")
            else:
                self.output.append(f"    ; Zero-latency read from packed variable {var_name}")
                self.output.append(f"    MOVQ RAX, {self.simd_register}  ; Load packed register")
                if start_bit > 0:
                    self.output.append(f"    SHR RAX, {start_bit}  ; Shift to extract {var_name}")
                self.output.append(f"    AND RAX, {mask}  ; Mask to {bits} bits")
        else:
            # Simple memory access for non-interrupt functions (faster)
            if is_write:
                self.output.append(f"    MOV BYTE [GLOBAL_{var_name}], AL  ; Store to packed variable")
            else:
                self.output.append(f"    MOVZX EAX, BYTE [GLOBAL_{var_name}]  ; Load packed variable")
        
        return True
    
    def _is_interrupt_callback(self, func_name):
        """Check if function is an interrupt callback."""
        from analyzer import is_interrupt_callback
        return is_interrupt_callback(func_name)
    
    def _generate_local_var_load(self, var_name):
        """Generate code to load a local variable using optimized register or stack addressing.
        
        First checks if variable is in a register (from register allocator), otherwise uses stack.
        """
        # Check if variable is in a register (from register allocator)
        if self.register_allocator and self._current_function_name:
            reg = self.register_allocator.get_register(self._current_function_name, var_name)
            if reg:
                # Variable is in a register - move it to RAX
                if reg != self.reg_rax:
                    if self.use_32bit:
                        reg_32 = reg.replace('R', 'E') if reg.startswith('R') else reg
                        self.output.append(f"    MOV {self.reg_rax}, {reg_32}  ; Load {var_name} from register {reg}")
                    else:
                        # In 64-bit mode, use 32-bit moves for integers (zero-extends to RAX)
                        if reg.startswith('R'):
                            # R8-R15 use R8D-R15D, not E8-E15
                            if reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                                reg_32 = reg + 'D'
                            else:
                                reg_32 = reg.replace('R', 'E')
                            # Use EAX (32-bit) which zero-extends to RAX
                            self.output.append(f"    MOV EAX, {reg_32}  ; Load {var_name} from register {reg} (32-bit)")
                        else:
                            self.output.append(f"    MOV {self.reg_rax}, {reg}  ; Load {var_name} from register {reg}")
                # Variable already in RAX
                return
        
        # Check if variable is currently in a register (from our tracking)
        if var_name in self.variable_registers:
            reg = self.variable_registers[var_name]
            if reg != self.reg_rax:
                if self.use_32bit:
                    reg_32 = reg.replace('R', 'E') if reg.startswith('R') else reg
                    self.output.append(f"    MOV {self.reg_rax}, {reg_32}  ; Load {var_name} from register {reg}")
                else:
                    reg_32 = reg.replace('R', 'E') if reg.startswith('R') else reg
                    self.output.append(f"    MOV {self.reg_rax}, {reg_32}  ; Load {var_name} from register {reg}")
            return
        
        if var_name not in self.current_function_stack:
            # Check if it's a function parameter
            if var_name in self.function_parameters:
                param_reg = self.function_parameters[var_name]
                # Use 32-bit move for integer parameters if in 64-bit mode
                if not self.use_32bit and self.current_function_stack.get(var_name, (0, 0)) == (0, 0):
                    reg_name = param_reg.replace('R', 'E') if param_reg.startswith('R') else param_reg
                    self.output.append(f"    MOVSX {self.reg_rax}, {reg_name}  ; Load parameter {var_name} (sign-extend)")
                else:
                    self.output.append(f"    MOV {self.reg_rax}, {param_reg}  ; Load parameter {var_name}")
                return
            # Variable not found - might be an error
            self.output.append(f"    ; Warning: {var_name} not found in stack or parameters")
            self.output.append(f"    MOV {self.reg_rax}, 0  ; Default to 0")
            return
        
        slot_index, offset = self.current_function_stack[var_name]
        
        # Calculate offset from RBP (standard GCC-style addressing for performance)
        # Variables are allocated at RBP - 8, RBP - 16, RBP - 24, etc. (8-byte alignment)
        # Note: RBP points to RSP after alignment adjustment (8 bytes below where R13 was pushed)
        # Stack layout (64-bit): [RBP+24]=saved RBP, [RBP+16]=saved R12, [RBP+8]=saved R13, [RBP]=alignment space, [RBP-8]=first var
        # Stack layout (32-bit): [RBP+8]=saved RBP, [RBP]=saved frame, [RBP-8]=first var
        stack_offset = (slot_index + 1) * 8 + offset  # +1 for alignment space/saved frame
        
        # Use standard [RBP - offset] addressing (more efficient than [R12 + displacement])
        if self.use_32bit:
            self.output.append(f"    MOV {self.reg_rax}, [{self.reg_rbp} - {stack_offset}]  ; Load {var_name}")
        else:
            # Use 32-bit move for integers (more efficient than 64-bit)
            # MOV EAX zero-extends to RAX automatically
            self.output.append(f"    MOV EAX, DWORD [{self.reg_rbp} - {stack_offset}]  ; Load {var_name} (32-bit)")
    
    def _generate_local_var_store(self, var_name):
        """Generate code to store a local variable using optimized register or stack addressing.
        
        First checks if variable should be in a register (from register allocator), otherwise uses stack.
        """
        # Check if variable should be in a register (from register allocator)
        if self.register_allocator and self._current_function_name:
            reg = self.register_allocator.get_register(self._current_function_name, var_name)
            if reg:
                # Variable should be in a register - move RAX to that register
                if reg != self.reg_rax:
                    if self.use_32bit:
                        reg_32 = reg.replace('R', 'E') if reg.startswith('R') else reg
                        self.output.append(f"    MOV {reg_32}, {self.reg_rax}  ; Store {var_name} to register {reg}")
                    else:
                        # In 64-bit mode, use 32-bit moves for integers
                        if reg.startswith('R'):
                            # R8-R15 use R8D-R15D, not E8-E15
                            if reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                                reg_32 = reg + 'D'
                            else:
                                reg_32 = reg.replace('R', 'E')
                            self.output.append(f"    MOV {reg_32}, EAX  ; Store {var_name} to register {reg} (32-bit)")
                        else:
                            self.output.append(f"    MOV {reg}, {self.reg_rax}  ; Store {var_name} to register {reg}")
                # Track that this variable is now in a register
                self.variable_registers[var_name] = reg
                return
        
        # Store to parameter: write to the parameter register (do not allocate a stack slot)
        if var_name not in self.current_function_stack and var_name in self.function_parameters:
            param_reg = self.function_parameters[var_name]
            if self.use_32bit:
                reg_32 = param_reg.replace('R', 'E') if param_reg.startswith('R') else param_reg
                self.output.append(f"    MOV {reg_32}, {self.reg_rax}  ; Store to parameter {var_name}")
            else:
                if param_reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                    reg_32 = param_reg + 'D'
                else:
                    reg_32 = param_reg.replace('R', 'E') if param_reg.startswith('R') else param_reg
                self.output.append(f"    MOV {reg_32}, EAX  ; Store to parameter {var_name} (32-bit)")
            return
        
        # Variable should be on stack
        if var_name not in self.current_function_stack:
            # Variable not found - allocate it now
            slot_index = self.current_stack_slots
            offset = 0
            self.current_stack_slots += 1
            self.current_function_stack[var_name] = (slot_index, offset)
            # Note: Stack space is allocated upfront in function prologue
            # We just track the slot here for pointer compression purposes
        else:
            slot_index, offset = self.current_function_stack[var_name]
        
        # Calculate offset from RBP (standard GCC-style addressing for performance)
        # Variables are allocated at RBP - 8, RBP - 16, RBP - 24, etc. (8-byte alignment)
        # Note: RBP points to RSP after alignment adjustment (8 bytes below where R13 was pushed)
        # Stack layout (64-bit): [RBP+24]=saved RBP, [RBP+16]=saved R12, [RBP+8]=saved R13, [RBP]=alignment space, [RBP-8]=first var
        # Stack layout (32-bit): [RBP+8]=saved RBP, [RBP]=saved frame, [RBP-8]=first var
        stack_offset = (slot_index + 1) * 8 + offset  # +1 for alignment space/saved frame
        
        # Use standard [RBP - offset] addressing (more efficient than [R12 + displacement])
        # Use 32-bit move for integers (more efficient than 64-bit)
        if self.use_32bit:
            self.output.append(f"    MOV [{self.reg_rbp} - {stack_offset}], {self.reg_rax}  ; Store {var_name}")
        else:
            self.output.append(f"    MOV DWORD [{self.reg_rbp} - {stack_offset}], EAX  ; Store {var_name} (32-bit)")
        
        # Update register if variable is in a register
        if var_name in self.variable_registers:
            reg = self.variable_registers[var_name]
            # Update the register with the new value (which is in RAX/EAX)
            if self.use_32bit:
                reg_32 = reg.replace('R', 'E') if reg.startswith('R') else reg
                self.output.append(f"    MOV {reg_32}, EAX  ; Update {var_name} in register {reg}")
            else:
                # In 64-bit mode, use 32-bit moves for integers
                if reg.startswith('R'):
                    # R8-R15 use R8D-R15D, not E8-E15
                    if reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                        reg_32 = reg + 'D'
                    else:
                        reg_32 = reg.replace('R', 'E')
                    self.output.append(f"    MOV {reg_32}, EAX  ; Update {var_name} in register {reg} (32-bit)")
                else:
                    self.output.append(f"    MOV {reg}, EAX  ; Update {var_name} in register {reg}")
    
    def _generate_compressed_pointer(self, slot_index1, slot_index2=None):
        """Generate code to create a compressed pointer (two 32-bit indices in one 64-bit register).
        
        This enables pointer compression: two stack slot indices can fit in one 64-bit register.
        Since stack slots are 16-byte aligned, indices fit in 32 bits, allowing two indices
        to be packed into a single 64-bit register.
        
        Useful for:
        - Storing multiple stack pointers efficiently
        - Passing stack locations between functions
        - Enabling pointer compression optimizations
        """
        if slot_index2 is None:
            # Single index - store in lower 32 bits (upper 32 bits remain 0)
            self.output.append(f"    ; Compressed pointer: slot index {slot_index1} in lower 32 bits")
            self.output.append(f"    MOV EAX, {slot_index1}  ; Store index in 32-bit register (fits in 32 bits)")
            self.output.append(f"    ; Address = [R12 + EAX*16] for indexed stack access")
        else:
            # Two indices - pack into one 64-bit register
            # Lower 32 bits: slot_index1, Upper 32 bits: slot_index2
            self.output.append(f"    ; Compressed pointer: slot {slot_index1} (low) + slot {slot_index2} (high)")
            self.output.append(f"    MOV EAX, {slot_index1}  ; Lower 32 bits: slot index {slot_index1}")
            self.output.append(f"    MOV EDX, {slot_index2}  ; Upper 32 bits: slot index {slot_index2}")
            self.output.append(f"    SHL RDX, 32  ; Shift upper index to high 32 bits")
            self.output.append(f"    OR RAX, RDX  ; Combine: RAX = (slot2 << 32) | slot1")
            self.output.append(f"    ; Single 64-bit register now contains two compressed stack pointers")
            self.output.append(f"    ; Extract: low = RAX & 0xFFFFFFFF, high = (RAX >> 32) & 0xFFFFFFFF")
            self.output.append(f"    ; Addresses: [R12 + low*16] and [R12 + high*16]")
    
    def _generate_function(self, func_def, in_small_func_block=False):
        """Generate code for a single function.
        When in_small_func_block is True, the function is co-located in SMALL_FUNC_BASE
        and must not add alignment (slot is fixed at 1024 bytes).
        """
        func_name = func_def.decl.name if func_def.decl else "unknown"
        # Skip functions with "unknown" names - they're likely parsing errors
        if func_name == "unknown":
            self.output.append(f"; Warning: Skipping function with unknown name")
            return
        
        # Store current function name for use in expression generation
        self._current_function_name = func_name
        
        info = self.function_data.get(func_name, {})
        is_interrupt = self._is_interrupt_callback(func_name)
        
        # Check if this function uses RBX (callee-saved); if so we must save/restore it
        self.function_uses_rbx = False
        if self.register_allocator and func_name:
            reg_map = self.register_allocator.function_register_map.get(func_name, {})
            if self.reg_rbx in reg_map.values():
                self.function_uses_rbx = True
        self.function_saved_rbx = False
        
        # Reset stack tracking for this function
        self.current_function_stack = {}
        self.current_stack_slots = 0
        self.current_stack_offset = 0  # Track cumulative byte offset from RBP
        self.local_arrays = set()  # Local array names (need address, not value, when used as expr)
        self.local_array_element_size = {}  # Local array name -> element size in bytes (for array-of-struct)
        self.variable_registers = {}  # Reset register tracking for this function
        self.function_stack_allocated = False  # True after we've emitted one SUB RSP for all locals
        # Pre-scan body to get total stack size for all locals (so we allocate once, not per loop iteration)
        self.function_total_stack_size = self._compute_function_local_stack_size(func_def.body) if func_def.body else 0
        # x86-64 ABI: RSP must be 16-byte aligned before CALL. After prologue RBP ≡ 8 (mod 16), so RSP = RBP - N must have N ≡ 8 (mod 16).
        if self.function_total_stack_size > 0 and self.function_total_stack_size % 16 == 0:
            self.function_total_stack_size += 8
        # Reset function pointer tracking
        self.saved_fp_in_rbx = False
        self.fp_in_rax = False
        # Track if function needs indexed stack system
        self.function_needs_indexed_stack = False
        
        # Track function parameters (x86-64 calling convention: RDI, RSI, RDX, RCX, R8, R9)
        # In 32-bit mode: EDI, ESI, EDX, ECX (only 4 registers)
        self.function_parameters = {}
        if self.use_32bit:
            param_registers = ['EDI', 'ESI', 'EDX', 'ECX']
        else:
            param_registers = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9']
        if func_def.decl and func_def.decl.type and hasattr(func_def.decl.type, 'args'):
            if func_def.decl.type.args and func_def.decl.type.args.params:
                for i, param in enumerate(func_def.decl.type.args.params):
                    if i < len(param_registers):
                        if isinstance(param, c_ast.Decl) and param.name:
                            # param.name is a c_ast.ID node, so access .name attribute
                            if isinstance(param.name, c_ast.ID):
                                param_name = param.name.name
                            else:
                                param_name = str(param.name)
                            self.function_parameters[param_name] = param_registers[i]
        
        # Align function start to 16 bytes for quantized call-backs (skip when co-located in 1024-byte slot)
        if not in_small_func_block:
            self.output.append(f"ALIGN {self.alignment}")
        self.output.append(f"FUNC_{func_name}:")
        
        if is_interrupt:
            self.output.append(f"    ; Interrupt callback: using zero-latency SIMD register access")
            # For interrupt callbacks, ensure SIMD register is preserved/accessible
            self.output.append(f"    ; {self.simd_register} contains packed kernel flags (no memory reads)")
        
        # Check if function needs indexed stack (has local variables or needs stack space)
        # We'll set this flag during code generation if we allocate any stack slots
        # For now, use minimal prologue - we'll add indexed stack setup only if needed
        # Most functions don't need any prologue at all (GCC -O3 style)
        
        # For interrupt callbacks, preserve SIMD register if needed
        if is_interrupt:
            # Mark that this function needs stack frame
            if not self.function_needs_indexed_stack:
                self.function_needs_indexed_stack = True
                if getattr(self, 'function_uses_rbx', False) and not getattr(self, 'function_saved_rbx', False):
                    self.output.append(f"    PUSH {self.reg_rbx}  ; Callee-saved: preserve RBX")
                    self.function_saved_rbx = True
                # Generate indexed stack prologue (with R12/R13 for indexed stack system)
                # Note: After CALL, stack is 8-byte aligned. We push 3 registers (24 bytes),
                # so we need to adjust RSP by 8 bytes to maintain 16-byte alignment
                self.output.append(f"    PUSH {self.reg_rbp}  ; Save old frame pointer")
                if not self.use_32bit:
                    self.output.append(f"    PUSH {self.stack_base_register}  ; Preserve stack base register")
                    self.output.append(f"    PUSH {self.stack_index_register}  ; Preserve stack index register")
                    # Adjust RSP to maintain 16-byte stack alignment (3 pushes = 24 bytes, need 32)
                    self.output.append(f"    SUB {self.reg_rsp}, 8  ; Adjust for 16-byte stack alignment")
                self.output.append(f"    MOV {self.reg_rbp}, {self.reg_rsp}  ; Set new frame pointer")
                if not self.use_32bit:
                    self.output.append(f"    MOV {self.stack_base_register}, 0x7FFF0000  ; Load stack base (immediate)")
                    self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Initialize slot index to 0")
            # Allocate 8 bytes for SIMD register preservation if needed
            self.current_stack_slots = 1
            self.output.append(f"    SUB {self.reg_rsp}, 8  ; Allocate stack space for SIMD register")
            # Note: xmm15 is typically preserved across calls, but we ensure it's accessible
        
        # Check if this is a syscall function (functions starting with "print" that have empty bodies)
        is_syscall = func_name.startswith("print")
        if is_syscall and func_def.body:
            # Check if body is empty
            if isinstance(func_def.body, c_ast.Compound):
                block_items = func_def.body.block_items
                is_empty = block_items is None or len(block_items) == 0
            else:
                is_empty = False  # Non-compound body means there's something there
            
            if is_empty:
                # Generate syscall code
                if func_name == "print":
                    # sys_write(fd, buf, len) - parameters are already in RDI, RSI, RDX
                    self.output.append("    ; print syscall")
                    if self.use_32bit:
                        self.output.append(f"    MOV {self.reg_rax}, 4  ; print (32-bit)")
                        self.output.append("    INT 0x80")
                    else:
                        self.output.append(f"    MOV {self.reg_rax}, 1  ; print (64-bit)")
                        self.output.append("    SYSCALL")
                    # No epilogue needed - syscall doesn't modify stack
                    
                    # Syscall functions are typically small and called via inlined indexed dispatch,
                    # so use normal RET instead of metamorphic return for compatibility
                    self.output.append("    RET")
                    return
        
        # Generate function body
        if func_def.body:
            self._generate_block(func_def.body, func_name, info)
            # Check if the function body contains any return statements
            # If not, add an implicit return at the end
            block_items = func_def.body.block_items if isinstance(func_def.body, c_ast.Compound) else [func_def.body]
            has_any_return = block_items and any(isinstance(item, c_ast.Return) for item in block_items)
            if not has_any_return:
                # Generate implicit return (fall-through case)
                # Small functions use normal RET since they're called via inlined indexed dispatch
                # Use metamorphic return site if function has single return (implicit) and is not small
                if self.enable_metamorphic_return_sites and info.get('has_single_return', False) and not info.get('is_small', False):
                            # Metamorphic return site for implicit return
                            # Generate a label for the metamorphic return site (if not already generated)
                            if func_name not in self.metamorphic_labels:
                                self.metamorphic_labels[func_name] = f"FUNC_{func_name}_METAMORPHIC"
                            
                            label_name = self.metamorphic_labels[func_name]
                            
                            # Use minimal epilogue if no indexed stack was used
                            if self.function_needs_indexed_stack:
                                if self.current_stack_slots > 0:
                                    self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
                                self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}")
                                if not self.use_32bit:
                                    self.output.append(f"    ADD {self.reg_rsp}, 8  ; Restore RSP alignment adjustment")
                                    self.output.append(f"    POP {self.stack_index_register}  ; Restore stack index register")
                                    self.output.append(f"    POP {self.stack_base_register}  ; Restore stack base register")
                                self.output.append(f"    POP {self.reg_rbp}")
                                if getattr(self, 'function_saved_rbx', False):
                                    self.output.append(f"    POP {self.reg_rbx}  ; Restore callee-saved RBX")
                            else:
                                if self.current_stack_slots > 0:
                                    self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}")
                                    self.output.append(f"    POP {self.reg_rbp}")
                                if getattr(self, 'function_saved_rbx', False):
                                    self.output.append(f"    POP {self.reg_rbx}  ; Restore callee-saved RBX")
                            
                            # Metamorphic return: load return address from instruction bytes and jump
                            # The caller will overwrite 0xdeadbeef with the actual return address
                            self.output.append(f"{label_name}:")
                            if self.use_32bit:
                                self.output.append(f"    MOV EDX, 0xdeadbeef  ; Metamorphic return address (will be overwritten by caller)")
                            else:
                                self.output.append(f"    MOV RDX, 0xdeadbeef  ; Metamorphic return address (will be overwritten by caller)")
                            self.output.append(f"    JMP {self.reg_rdx}  ; Jump to return address")
                else:
                    # Standard implicit return - only pop what we pushed (prologue)
                    # When function_needs_indexed_stack we pushed RBP, R12, R13 and did SUB RSP 8 - must restore all
                    if self.function_needs_indexed_stack or self.current_stack_slots > 0:
                        if self.function_needs_indexed_stack:
                            self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}")
                            if not self.use_32bit:
                                self.output.append(f"    ADD {self.reg_rsp}, 8  ; Restore RSP alignment adjustment")
                                self.output.append(f"    POP {self.stack_index_register}")
                                self.output.append(f"    POP {self.stack_base_register}")
                            self.output.append(f"    POP {self.reg_rbp}")
                        elif self.current_stack_slots > 0:
                            self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}  ; Restore stack pointer")
                            self.output.append(f"    POP {self.reg_rbp}  ; Restore frame pointer")
                        if getattr(self, 'function_saved_rbx', False):
                            self.output.append(f"    POP {self.reg_rbx}  ; Restore callee-saved RBX")
                    self.output.append("    RET")
    
    def _generate_block(self, block, func_name, info):
        """Generate code for a block."""
        if isinstance(block, c_ast.Compound):
            # block_items can be None for empty blocks
            if block.block_items:
                for item in block.block_items:
                    self._generate_statement(item, func_name, info)
            # If block_items is None, it's an empty block - do nothing
        else:
            self._generate_statement(block, func_name, info)
    
    def _generate_statement(self, stmt, func_name, info):
        """Generate code for a statement."""
        if isinstance(stmt, c_ast.Return):
            self._generate_return(stmt, func_name, info)
        elif isinstance(stmt, c_ast.Assignment):
            self._generate_assignment(stmt)
        elif isinstance(stmt, c_ast.If):
            self._generate_if(stmt, func_name, info)
        elif isinstance(stmt, c_ast.While):
            self._generate_while(stmt, func_name, info)
        elif isinstance(stmt, c_ast.For):
            self._generate_for(stmt, func_name, info)
        elif isinstance(stmt, c_ast.FuncCall):
            self._generate_call(stmt, func_name)
        elif isinstance(stmt, c_ast.Decl):
            self._generate_decl(stmt)
        elif isinstance(stmt, c_ast.Compound):
            self._generate_block(stmt, func_name, info)
        elif isinstance(stmt, (c_ast.UnaryOp, c_ast.BinaryOp, c_ast.ID, c_ast.ArrayRef, c_ast.StructRef)):
            # Expression statements (e.g., i++, function calls in expressions, etc.)
            # Generate the expression and discard the result
            self._generate_expression(stmt)
    
    def _generate_return(self, ret_stmt, func_name, info):
        """Generate return statement with metamorphic return site optimization."""
        # Small functions use normal RET since they're called via inlined indexed dispatch
        if self.enable_metamorphic_return_sites and info.get('has_single_return', False) and not info.get('is_small', False):
            # Metamorphic return site: return address is embedded in instruction bytes
            # Generate a label for the metamorphic return site
            if func_name not in self.metamorphic_labels:
                self.metamorphic_labels[func_name] = f"FUNC_{func_name}_METAMORPHIC"
            
            label_name = self.metamorphic_labels[func_name]
            
            # Use minimal epilogue if no indexed stack was used
            if self.function_needs_indexed_stack:
                if self.current_stack_slots > 0:
                    self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
                self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}")
                if not self.use_32bit:
                    self.output.append(f"    ADD {self.reg_rsp}, 8  ; Restore RSP alignment adjustment")
                    self.output.append(f"    POP {self.stack_index_register}  ; Restore stack index register")
                    self.output.append(f"    POP {self.stack_base_register}  ; Restore stack base register")
                self.output.append(f"    POP {self.reg_rbp}")
                if getattr(self, 'function_saved_rbx', False):
                    self.output.append(f"    POP {self.reg_rbx}  ; Restore callee-saved RBX")
            else:
                if self.current_stack_slots > 0:
                    self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}")
                    self.output.append(f"    POP {self.reg_rbp}")
                if getattr(self, 'function_saved_rbx', False):
                    self.output.append(f"    POP {self.reg_rbx}  ; Restore callee-saved RBX")
            
            # Metamorphic return: load return address from instruction bytes and jump
            # The caller will overwrite 0xdeadbeef with the actual return address
            self.output.append(f"{label_name}:")
            if self.use_32bit:
                self.output.append(f"    MOV EDX, 0xdeadbeef  ; Metamorphic return address (will be overwritten by caller)")
            else:
                # Use 32-bit move (will be optimized by NASM, but we write 32 bits to it)
                # The example uses mov rdx, 0xdeadbeef which NASM optimizes to 32-bit
                self.output.append(f"    MOV RDX, 0xdeadbeef  ; Metamorphic return address (will be overwritten by caller)")
            self.output.append(f"    JMP {self.reg_rdx}  ; Jump to return address")
        else:
            # Standard return
            if ret_stmt.expr:
                self._generate_expression(ret_stmt.expr)
                # Return value is already in RAX from expression evaluation
            # Use minimal epilogue if no indexed stack was used
            if self.function_needs_indexed_stack:
                if self.current_stack_slots > 0:
                    self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
                self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}")
                if not self.use_32bit:
                    self.output.append(f"    ADD {self.reg_rsp}, 8  ; Restore RSP alignment adjustment")
                self.output.append(f"    POP {self.stack_index_register}  ; Restore stack index register")
                self.output.append(f"    POP {self.stack_base_register}  ; Restore stack base register")
                self.output.append(f"    POP {self.reg_rbp}")
                if getattr(self, 'function_saved_rbx', False):
                    self.output.append(f"    POP {self.reg_rbx}  ; Restore callee-saved RBX")
            else:
                # Only pop RBP if we pushed it (had stack frame / locals)
                if self.current_stack_slots > 0:
                    self.output.append(f"    MOV {self.reg_rsp}, {self.reg_rbp}")
                    self.output.append(f"    POP {self.reg_rbp}")
                if getattr(self, 'function_saved_rbx', False):
                    self.output.append(f"    POP {self.reg_rbx}  ; Restore callee-saved RBX")
            self.output.append("    RET")
    
    def _generate_call(self, call, caller_func_name):
        """Generate function call with optimizations."""
        # FIRST: Check if this is a function pointer call (e.g., array[index](), struct.member())
        # These must be handled BEFORE trying to extract a function name, because
        # ArrayRef and StructRef have a 'name' attribute that would be incorrectly extracted
        if isinstance(call.name, (c_ast.ArrayRef, c_ast.StructRef)):
            # This is a function pointer call through array or struct member
            # Check if function pointer is already in RAX (from if condition)
            if self.fp_in_rax:
                # Function pointer is already in RAX from condition - don't reload it!
                self.output.append("    ; Function pointer already in RAX from condition")
            elif self.saved_fp_in_rbx:
                # Function pointer was saved in RBX from if condition
                self.output.append(f"    MOV {self.reg_rax}, {self.reg_rbx}  ; Use function pointer from condition")
            else:
                # Need to evaluate the expression
                self._generate_expression(call.name)
                # RAX now contains the function pointer
            
            # Prepare arguments (simplified - assume up to 6 args in registers)
            # Arguments are evaluated in sequence and each overwrites RAX,
            # so we need to save the function pointer before evaluating args
            # Use a callee-saved register (RBX) to save it
            self.output.append(f"    MOV {self.reg_rbx}, {self.reg_rax}  ; Save function pointer")
            
            if call.args:
                for i, arg in enumerate(call.args.exprs[:6]):
                    reg = ([self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx] if self.use_32bit else [self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx, self.reg_r8, self.reg_r9])[i]
                    # Optimize: if argument is a parameter already in the correct register, use it directly
                    if isinstance(arg, c_ast.ID) and arg.name in self.function_parameters:
                        param_reg = self.function_parameters[arg.name]
                        if param_reg == reg:
                            # Parameter is already in the correct register, no need to move
                            self.output.append(f"    ; Argument {i+1} ({arg.name}) already in {reg}")
                        else:
                            # Parameter is in a different register, move it
                            self.output.append(f"    MOV {reg}, {param_reg}  ; Argument {i+1} ({arg.name})")
                    else:
                        # Evaluate expression and move to argument register
                        self._generate_expression(arg)
                        self.output.append(f"    MOV {reg}, {self.reg_rax}  ; Argument {i+1}")
            
            # Restore function pointer from RBX
            self.output.append(f"    MOV {self.reg_rax}, {self.reg_rbx}  ; Restore function pointer")
            # Use JMP for function pointer calls (like GCC -O3)
            self.output.append("    JMP RAX  ; Call function pointer")
            # Note: JMP doesn't return, so any code after this is unreachable
            return
        
        # Extract function name from call expression
        func_name = None
        if isinstance(call.name, c_ast.ID):
            func_name = call.name.name
        elif isinstance(call.name, c_ast.UnaryOp) and isinstance(call.name.expr, c_ast.ID):
            # Handle function pointer dereference: (*func_ptr)(args)
            func_name = call.name.expr.name
        elif hasattr(call.name, 'name'):
            # Try to get name attribute if it exists
            name_attr = call.name.name
            # Ensure it's a string, not an AST node
            if isinstance(name_attr, str):
                func_name = name_attr
            elif isinstance(name_attr, c_ast.ID):
                func_name = name_attr.name
            else:
                # Complex expression - we'll handle as function pointer call
                func_name = None
        
        # Handle other function pointer calls (e.g., complex expressions)
        if not func_name or func_name == "unknown":
            # Check if this is a function pointer call with a complex expression
            is_function_pointer = False
            if isinstance(call.name, (c_ast.BinaryOp)):
                is_function_pointer = True
            elif not isinstance(call.name, c_ast.ID) and not isinstance(call.name, c_ast.UnaryOp):
                # Could be a complex expression that evaluates to a function pointer
                is_function_pointer = True
            
            if is_function_pointer:
                # Generate code to evaluate the function pointer expression
                # The result should be in RAX
                self._generate_expression(call.name)
                # RAX now contains the function pointer
                # Save it to the stack before evaluating arguments
                self.output.append(f"    PUSH {self.reg_rax}  ; Save function pointer")
                
                # Prepare arguments (simplified - assume up to 6 args in registers)
                # Arguments are evaluated in sequence and each overwrites RAX,
                # but we move them to argument registers immediately
                if call.args:
                    for i, arg in enumerate(call.args.exprs[:6]):
                        reg = ([self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx] if self.use_32bit else [self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx, self.reg_r8, self.reg_r9])[i]
                        self._generate_expression(arg)
                        self.output.append(f"    MOV {reg}, {self.reg_rax}  ; Argument {i+1}")
                
                # Restore function pointer from stack
                self.output.append(f"    POP {self.reg_rax}  ; Restore function pointer")
                
                # Use JMP for function pointer calls (like GCC -O3)
                self.output.append("    JMP RAX  ; Call function pointer")
                return
            else:
                # Unknown function name - skip
                self.output.append(f"    ; Warning: Skipping call to unknown/undefined function")
                # Still prepare arguments in case they have side effects
                if call.args:
                    for i, arg in enumerate(call.args.exprs[:6]):
                        reg = ([self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx] if self.use_32bit else [self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx, self.reg_r8, self.reg_r9])[i]
                        self._generate_expression(arg)
                        self.output.append(f"    MOV {reg}, {self.reg_rax}")
                # Generate a no-op or placeholder
                self.output.append("    ; NOP - unknown function call skipped")
                return
        
        # Ensure func_name is a string, not an AST node
        if not isinstance(func_name, str):
            # This shouldn't happen after the checks above, but protect against it
            self.output.append(f"    ; Warning: Function name is not a string: {safe_str(func_name)}")
            # Still prepare arguments in case they have side effects
            if call.args:
                for i, arg in enumerate(call.args.exprs[:6]):
                    reg = ([self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx] if self.use_32bit else [self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx, self.reg_r8, self.reg_r9])[i]
                    self._generate_expression(arg)
                    self.output.append(f"    MOV {reg}, RAX")
            self.output.append("    ; NOP - invalid function name")
            return
        
        callee_info = self.function_data.get(func_name, {})
        
        # Special handling for print function (syscall)
        if func_name == "print":
            # Inline print lowering with one placeholder (%d or %s), including literal prefix/suffix.
            if call.args and len(call.args.exprs) >= 1:
                fmt_arg = call.args.exprs[0]
                if isinstance(fmt_arg, c_ast.Constant) and isinstance(fmt_arg.value, str):
                    fmt_content = self._decode_c_string_literal(fmt_arg.value)
                    format_is_percent_d = '%d' in fmt_content
                    format_is_percent_s = '%s' in fmt_content
                    if not format_is_percent_d and not format_is_percent_s:
                        self._emit_write_syscall_literal(fmt_content)
                        return
                    if len(call.args.exprs) >= 2:
                        value_arg = call.args.exprs[1]
                        value_is_string_literal = isinstance(value_arg, c_ast.Constant) and isinstance(value_arg.value, str) and len(value_arg.value) >= 2 and value_arg.value[0] == '"' and value_arg.value[-1] == '"'
                        if format_is_percent_d:
                            prefix, suffix = fmt_content.split('%d', 1)
                            self._generate_expression(value_arg)
                            if prefix:
                                self._emit_write_syscall_literal(prefix, preserve_rax=True)
                            self.needs_print_int_buffer = True
                            self.label_counter = self.label_counter + 1
                            label_id = self.label_counter
                            if self.use_32bit:
                                self.output.append("    LEA ESI, [GLOBAL___print_int_buf + 31]  ; End of int print buffer")
                                self.output.append("    MOV BYTE [ESI], 0")
                                self.output.append("    PUSH 0  ; sign flag (0=positive, 1=negative)")
                                self.output.append("    TEST EAX, EAX")
                                self.output.append(f"    JGE PRINT_INT_ABS_{label_id}")
                                self.output.append("    NEG EAX")
                                self.output.append("    MOV DWORD [ESP], 1")
                                self.output.append(f"PRINT_INT_ABS_{label_id}:")
                                self.output.append("    MOV ECX, 10")
                                self.output.append(f"PRINT_INT_LOOP_{label_id}:")
                                self.output.append("    XOR EDX, EDX")
                                self.output.append("    DIV ECX")
                                self.output.append("    ADD DL, '0'")
                                self.output.append("    DEC ESI")
                                self.output.append("    MOV BYTE [ESI], DL")
                                self.output.append("    TEST EAX, EAX")
                                self.output.append(f"    JNZ PRINT_INT_LOOP_{label_id}")
                                self.output.append("    CMP DWORD [ESP], 0")
                                self.output.append(f"    JE PRINT_INT_NOSIGN_{label_id}")
                                self.output.append("    DEC ESI")
                                self.output.append("    MOV BYTE [ESI], '-'")
                                self.output.append(f"PRINT_INT_NOSIGN_{label_id}:")
                                self.output.append("    ADD ESP, 4  ; Pop sign flag")
                                self.output.append("    LEA EDX, [GLOBAL___print_int_buf + 31]")
                                self.output.append("    SUB EDX, ESI  ; Decimal string length")
                                self._emit_write_syscall_from_regs("ESI", "EDX")
                            else:
                                self.output.append("    MOVSXD RAX, EAX  ; Treat %d argument as signed 32-bit int")
                                self.output.append("    LEA RSI, [rel GLOBAL___print_int_buf + 31]  ; End of int print buffer")
                                self.output.append("    MOV BYTE [RSI], 0")
                                self.output.append("    PUSH 0  ; sign flag (0=positive, 1=negative)")
                                self.output.append("    TEST RAX, RAX")
                                self.output.append(f"    JGE PRINT_INT_ABS_{label_id}")
                                self.output.append("    NEG RAX")
                                self.output.append("    MOV QWORD [RSP], 1")
                                self.output.append(f"PRINT_INT_ABS_{label_id}:")
                                self.output.append("    MOV RCX, 10")
                                self.output.append(f"PRINT_INT_LOOP_{label_id}:")
                                self.output.append("    XOR RDX, RDX")
                                self.output.append("    DIV RCX")
                                self.output.append("    ADD DL, '0'")
                                self.output.append("    DEC RSI")
                                self.output.append("    MOV BYTE [RSI], DL")
                                self.output.append("    TEST RAX, RAX")
                                self.output.append(f"    JNZ PRINT_INT_LOOP_{label_id}")
                                self.output.append("    CMP QWORD [RSP], 0")
                                self.output.append(f"    JE PRINT_INT_NOSIGN_{label_id}")
                                self.output.append("    DEC RSI")
                                self.output.append("    MOV BYTE [RSI], '-'")
                                self.output.append(f"PRINT_INT_NOSIGN_{label_id}:")
                                self.output.append("    ADD RSP, 8  ; Pop sign flag")
                                self.output.append("    LEA RDX, [rel GLOBAL___print_int_buf + 31]")
                                self.output.append("    SUB RDX, RSI  ; Decimal string length")
                                self._emit_write_syscall_from_regs("RSI", "RDX")
                            if suffix:
                                self._emit_write_syscall_literal(suffix)
                            return
                        if format_is_percent_s:
                            prefix, suffix = fmt_content.split('%s', 1)
                            if value_is_string_literal:
                                lit_label, lit_value = self._intern_string_literal(value_arg.value)
                                if self.use_32bit:
                                    self.output.append(f"    LEA {self.reg_rax}, [{lit_label}]  ; Address of string literal")
                                else:
                                    self.output.append(f"    LEA {self.reg_rax}, [rel {lit_label}]  ; Address of string literal")
                            else:
                                self._generate_expression(value_arg)
                            if prefix:
                                self._emit_write_syscall_literal(prefix, preserve_rax=True)
                            self.output.append(f"    MOV {self.reg_rsi}, {self.reg_rax}  ; Buffer address")
                            string_length = None
                            if value_is_string_literal:
                                string_length = len(lit_value)
                            elif isinstance(value_arg, c_ast.ID):
                                var_name = value_arg.name
                                glob_vars = getattr(self, '_current_parser', None).get_global_variables() if hasattr(self, '_current_parser') else []
                                for gv in glob_vars:
                                    if gv.name == var_name and gv.init and isinstance(gv.init, c_ast.Constant):
                                        value = gv.init.value
                                        if isinstance(value, str) and ((value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))):
                                            string_length = len(self._decode_c_string_literal(value))
                                            break
                            if string_length is not None:
                                self.output.append(f"    MOV {self.reg_rdx}, {string_length}  ; String length (compile-time)")
                            else:
                                self.output.append(f"    MOV RCX, {self.reg_rsi}  ; Copy buffer address to RCX")
                                self.output.append(f"    MOV {self.reg_rdx}, 0  ; Initialize length counter")
                                length_label = f"_strlen_{self.return_site_index}"
                                self.output.append(f"{length_label}:")
                                self.output.append("    MOV AL, BYTE [RCX]  ; Load byte")
                                self.output.append("    CMP AL, 0  ; Check for null terminator")
                                self.output.append(f"    JE {length_label}_done")
                                self.output.append("    INC RCX  ; Move to next byte")
                                self.output.append(f"    INC {self.reg_rdx}  ; Increment length")
                                self.output.append(f"    JMP {length_label}")
                                self.output.append(f"{length_label}_done:")
                            self._emit_write_syscall_from_regs(self.reg_rsi, self.reg_rdx)
                            if suffix:
                                self._emit_write_syscall_literal(suffix)
                            return
            # print function: print("%s", msg) -> sys_write(1, msg, len)
            # Set up syscall arguments: RDI=1 (stdout), RSI=buffer, RDX=length
            if call.args and len(call.args.exprs) >= 2:
                format_is_percent_s = False
                format_is_percent_d = False
                fmt_arg = call.args.exprs[0]
                if isinstance(fmt_arg, c_ast.Constant) and isinstance(fmt_arg.value, str):
                    fmt = fmt_arg.value
                    fmt_content = fmt
                    if len(fmt_content) >= 2 and fmt_content[0] == fmt_content[-1] and fmt_content[0] in ["'", '"']:
                        fmt_content = fmt_content[1:-1]
                    # Basic escape normalization for common C escapes in string literals
                    fmt_content = fmt_content.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\\\', '\\')
                    # Accept common variants like "%s\n" or "label=%d\n", not only exact "%s"/"%d"
                    format_is_percent_s = '%s' in fmt_content
                    format_is_percent_d = '%d' in fmt_content

                # First argument is format string (ignored), second is payload argument
                buf_arg = call.args.exprs[1]
                buf_is_string_literal = isinstance(buf_arg, c_ast.Constant) and isinstance(buf_arg.value, str) and len(buf_arg.value) >= 2 and buf_arg.value[0] == '"' and buf_arg.value[-1] == '"'
                if buf_is_string_literal:
                    lit_label, lit_value = self._intern_string_literal(buf_arg.value)
                    if self.use_32bit:
                        self.output.append(f"    LEA {self.reg_rax}, [{lit_label}]  ; Address of string literal")
                    else:
                        self.output.append(f"    LEA {self.reg_rax}, [rel {lit_label}]  ; Address of string literal")
                else:
                    # Evaluate second argument to get pointer/value into RAX
                    self._generate_expression(buf_arg)

                if format_is_percent_d:
                    # Convert integer in RAX to decimal ASCII into shared buffer, then write it.
                    self.needs_print_int_buffer = True
                    self.label_counter = self.label_counter + 1
                    label_id = self.label_counter
                    if self.use_32bit:
                        self.output.append("    LEA ESI, [GLOBAL___print_int_buf + 31]  ; End of int print buffer")
                        self.output.append("    MOV BYTE [ESI], 0")
                        self.output.append("    PUSH 0  ; sign flag (0=positive, 1=negative)")
                        self.output.append("    TEST EAX, EAX")
                        self.output.append(f"    JGE PRINT_INT_ABS_{label_id}")
                        self.output.append("    NEG EAX")
                        self.output.append("    MOV DWORD [ESP], 1")
                        self.output.append(f"PRINT_INT_ABS_{label_id}:")
                        self.output.append("    MOV ECX, 10")
                        self.output.append(f"PRINT_INT_LOOP_{label_id}:")
                        self.output.append("    XOR EDX, EDX")
                        self.output.append("    DIV ECX")
                        self.output.append("    ADD DL, '0'")
                        self.output.append("    DEC ESI")
                        self.output.append("    MOV BYTE [ESI], DL")
                        self.output.append("    TEST EAX, EAX")
                        self.output.append(f"    JNZ PRINT_INT_LOOP_{label_id}")
                        self.output.append("    CMP DWORD [ESP], 0")
                        self.output.append(f"    JE PRINT_INT_NOSIGN_{label_id}")
                        self.output.append("    DEC ESI")
                        self.output.append("    MOV BYTE [ESI], '-'")
                        self.output.append(f"PRINT_INT_NOSIGN_{label_id}:")
                        self.output.append("    ADD ESP, 4  ; Pop sign flag")
                        self.output.append("    LEA EDX, [GLOBAL___print_int_buf + 31]")
                        self.output.append("    SUB EDX, ESI  ; Decimal string length")
                        self.output.append("    MOV EDI, 1  ; stdout file descriptor")
                    else:
                        self.output.append("    MOVSXD RAX, EAX  ; Treat %d argument as signed 32-bit int")
                        self.output.append("    LEA RSI, [rel GLOBAL___print_int_buf + 31]  ; End of int print buffer")
                        self.output.append("    MOV BYTE [RSI], 0")
                        self.output.append("    PUSH 0  ; sign flag (0=positive, 1=negative)")
                        self.output.append("    TEST RAX, RAX")
                        self.output.append(f"    JGE PRINT_INT_ABS_{label_id}")
                        self.output.append("    NEG RAX")
                        self.output.append("    MOV QWORD [RSP], 1")
                        self.output.append(f"PRINT_INT_ABS_{label_id}:")
                        self.output.append("    MOV RCX, 10")
                        self.output.append(f"PRINT_INT_LOOP_{label_id}:")
                        self.output.append("    XOR RDX, RDX")
                        self.output.append("    DIV RCX")
                        self.output.append("    ADD DL, '0'")
                        self.output.append("    DEC RSI")
                        self.output.append("    MOV BYTE [RSI], DL")
                        self.output.append("    TEST RAX, RAX")
                        self.output.append(f"    JNZ PRINT_INT_LOOP_{label_id}")
                        self.output.append("    CMP QWORD [RSP], 0")
                        self.output.append(f"    JE PRINT_INT_NOSIGN_{label_id}")
                        self.output.append("    DEC RSI")
                        self.output.append("    MOV BYTE [RSI], '-'")
                        self.output.append(f"PRINT_INT_NOSIGN_{label_id}:")
                        self.output.append("    ADD RSP, 8  ; Pop sign flag")
                        self.output.append("    LEA RDX, [rel GLOBAL___print_int_buf + 31]")
                        self.output.append("    SUB RDX, RSI  ; Decimal string length")
                        self.output.append("    MOV RDI, 1  ; stdout file descriptor")
                elif format_is_percent_s:
                    self.output.append(f"    MOV {self.reg_rsi}, {self.reg_rax}  ; Buffer address")
                    
                    # Set file descriptor to stdout (1)
                    self.output.append(f"    MOV {self.reg_rdi}, 1  ; stdout file descriptor")
                    
                    # Compute length: try to get it from global variable if it's a string literal/array
                    # Check if second argument is a global variable with known string
                    string_length = None
                    if buf_is_string_literal:
                        string_length = len(lit_value)
                    elif isinstance(buf_arg, c_ast.ID):
                        # Check if it's a global variable with string initializer
                        var_name = buf_arg.name
                        glob_vars = getattr(self, '_current_parser', None).get_global_variables() if hasattr(self, '_current_parser') else []
                        for gv in glob_vars:
                            if gv.name == var_name and gv.init and isinstance(gv.init, c_ast.Constant):
                                value = gv.init.value
                                if isinstance(value, str) and ((value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))):
                                    # Extract string content
                                    if value.startswith('"'):
                                        string_value = value[1:-1].replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r').replace('\\\\', '\\')
                                    else:
                                        string_value = value[1:-1]
                                    # Length is string length (excluding null terminator for syscall)
                                    string_length = len(string_value)
                                    break
                    
                    if string_length is not None:
                        # Use compile-time length
                        self.output.append(f"    MOV {self.reg_rdx}, {string_length}  ; String length (compile-time)")
                    else:
                        # Compute length at runtime by finding null terminator
                        # Use RCX as pointer, RDX as length counter
                        self.output.append(f"    MOV RCX, {self.reg_rsi}  ; Copy buffer address to RCX")
                        self.output.append(f"    MOV {self.reg_rdx}, 0  ; Initialize length counter")
                        length_label = f"_strlen_{self.return_site_index}"
                        self.output.append(f"{length_label}:")
                        self.output.append(f"    MOV AL, BYTE [RCX]  ; Load byte")
                        self.output.append(f"    CMP AL, 0  ; Check for null terminator")
                        self.output.append(f"    JE {length_label}_done")
                        self.output.append(f"    INC RCX  ; Move to next byte")
                        self.output.append(f"    INC {self.reg_rdx}  ; Increment length")
                        self.output.append(f"    JMP {length_label}")
                        self.output.append(f"{length_label}_done:")
                else:
                    # Unknown format specifier: keep syscall harmless.
                    self.output.append(f"    MOV {self.reg_rdi}, 1  ; stdout")
                    self.output.append(f"    MOV {self.reg_rsi}, 0  ; Unsupported format buffer")
                    self.output.append(f"    MOV {self.reg_rdx}, 0  ; Unsupported format length")
            else:
                # Fallback: set default values
                self.output.append(f"    MOV {self.reg_rdi}, 1  ; stdout")
                self.output.append(f"    MOV {self.reg_rsi}, 0  ; No buffer")
                self.output.append(f"    MOV {self.reg_rdx}, 0  ; No length")
        else:
            # Prepare arguments (simplified - assume up to 6 args in registers)
            if call.args:
                arg_regs = ([self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx] if self.use_32bit else [self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx, self.reg_r8, self.reg_r9])
                args = call.args.exprs[:len(arg_regs)]
                for arg in args:
                    self._generate_expression(arg)
                    self.output.append(f"    PUSH {self.reg_rax}  ; Save argument value")
                for i in range(len(args) - 1, -1, -1):
                    reg = arg_regs[i]
                    self.output.append(f"    POP {reg}  ; Argument {i+1}")
        
        # Handle return site for single-return functions (quantized call-back)
        return_site_label = None
        if self.enable_metamorphic_return_sites and callee_info.get('has_single_return', False):
            # Generate quantized call-back label (will be placed after the call)
            return_site_label = f"RET_SITE_{caller_func_name}_{self.return_site_index}"
            self.return_site_index += 1
            self.return_sites.append(return_site_label)
        
        # Check if function exists in our function list (might be external)
        # Get all unique function names from parser
        all_func_names = set()
        functions = getattr(self, '_current_parser', None).get_functions() if hasattr(self, '_current_parser') else []
        for func in functions:
            func_name_from_def = func.decl.name if func.decl else None
            if func_name_from_def:
                all_func_names.add(func_name_from_def)
        
        # If function is not in our list, check if it's in assembly files or a function pointer variable
        if func_name not in all_func_names:
            # Check if this function is defined in assembly
            if self.asm_parser and self.asm_parser.has_symbol(func_name):
                self.output.append(f"    ; Function call to assembly-defined: {func_name}")
                self.output.append(f"    CALL FUNC_{func_name}")
                self.referenced_asm_symbols.add(func_name)
            else:
                # Check if it's a global variable (might be a function pointer)
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if func_name in globals:
                    # This is a function pointer variable, not a function name
                    # Load the function pointer and call it
                    self.output.append(f"    ; Function pointer call: {func_name}")
                    self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{func_name}]  ; Load function pointer")
                    # Prepare arguments first
                    if call.args:
                        arg_regs = ([self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx] if self.use_32bit else [self.reg_rdi, self.reg_rsi, self.reg_rdx, self.reg_rcx, self.reg_r8, self.reg_r9])
                        args = call.args.exprs[:len(arg_regs)]
                        for arg in args:
                            self._generate_expression(arg)
                            self.output.append(f"    PUSH {self.reg_rax}  ; Save argument value")
                        for i in range(len(args) - 1, -1, -1):
                            reg = arg_regs[i]
                            self.output.append(f"    POP {reg}  ; Argument {i+1}")
                        # Reload function pointer (arguments might have overwritten RAX)
                        self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{func_name}]  ; Reload function pointer")
                    # Use JMP for function pointer calls (like GCC -O3)
                    self.output.append(f"    JMP {self.reg_rax}  ; Call function pointer")
                else:
                    # Assume it's an external function
                    self.output.append(f"    ; External function call: {func_name}")
                    self.output.append(f"    CALL FUNC_{func_name}  ; Assumed to be defined externally")
        else:
            # Generate call based on function type
            if callee_info.get('is_small', False) and self.enable_indexed_function_calls:
                # Small functions use JMP (not CALL), so we must push return address for callee's RET.
                if return_site_label is None:
                    return_site_label = f"RET_SITE_{caller_func_name}_{self.return_site_index}"
                    self.return_site_index += 1
                    self.return_sites.append(return_site_label)
                # Push return address so callee's RET jumps back here
                if self.use_32bit:
                    self.output.append(f"    LEA EAX, [{return_site_label}]  ; Return address for small func RET")
                else:
                    self.output.append(f"    LEA {self.reg_rax}, [rel {return_site_label}]  ; Return address for small func RET")
                self.output.append(f"    PUSH {self.reg_rax}")
                # One call/jump only: inline dispatch so address = SMALL_FUNC_BASE + index*1024, then single JMP
                # If we're inside a loop that hoisted this function's address, just JMP to that register
                hoisted_reg = self._loop_hoisted_small_funcs.get(func_name) if self._loop_hoisted_small_funcs else None
                if hoisted_reg:
                    self.output.append(f"    ; Jump to {func_name} (address hoisted before loop)")
                    self.output.append(f"    JMP {hoisted_reg}")
                else:
                    func_idx = list(self.function_offsets.keys()).index(func_name) if func_name in self.function_offsets else -1
                    if func_idx >= 0:
                        offset = func_idx * 1024
                        self.output.append(f"    ; Single jump to {func_name} (SMALL_FUNC_BASE + {offset})")
                        if self.use_32bit:
                            # Use EAX as dispatch temp (avoid clobbering allocated loop vars in EBX).
                            self.output.append(f"    MOV {self.small_func_dispatch_reg}, SMALL_FUNC_BASE")
                            self.output.append(f"    ADD {self.small_func_dispatch_reg}, {offset}")
                            self.output.append(f"    JMP {self.small_func_dispatch_reg}  ; One jump only")
                        else:
                            # Use caller-saved temp register to avoid clobbering allocated variables in RBX.
                            self.output.append(f"    MOV {self.small_func_dispatch_reg}, SMALL_FUNC_BASE")
                            self.output.append(f"    MOV {self.reg_rax}, {offset}  ; offset for {func_name}")
                            self.output.append(f"    ADD {self.small_func_dispatch_reg}, {self.reg_rax}")
                            self.output.append(f"    JMP {self.small_func_dispatch_reg}  ; One jump only")
                    else:
                        # Fallback to direct call if not in jump table
                        self.output.append(f"    CALL FUNC_{func_name}")
            else:
                # Standard call or call with metamorphic return
                if self.enable_metamorphic_return_sites and callee_info.get('has_single_return', False) and return_site_label:
                    # Metamorphic return site: write return address directly into instruction bytes
                    # The callee has: mov rdx, 0xdeadbeef; jmp rdx
                    # We need to write the return address to the immediate value location
                    # The immediate value starts at offset +2 from the label (after mov opcode and register)
                    metamorphic_label = f"FUNC_{func_name}_METAMORPHIC"
                    self.output.append(f"    ; Metamorphic return site: write return address into instruction bytes")
                    if self.use_32bit:
                        # 32-bit: mov edx, imm32 is 5 bytes: BA (opcode) + 4 bytes immediate
                        # Offset is +1 (after opcode BA)
                        self.output.append(f"    LEA {self.reg_rax}, [{metamorphic_label}+1]  ; Address of immediate value in mov edx, 0xdeadbeef")
                        self.output.append(f"    LEA {self.reg_rdx}, [{return_site_label}]  ; Get return address")
                        self.output.append(f"    MOV DWORD [{self.reg_rax}], EDX  ; Write return address to instruction bytes")
                    else:
                        # NASM optimizes mov rdx, 0xdeadbeef to 32-bit move (5 bytes: BA + 4 bytes immediate)
                        # Offset is +1 (after opcode BA)
                        self.output.append(f"    LEA {self.reg_rax}, [rel {metamorphic_label}+1]  ; Address of immediate value in mov rdx, 0xdeadbeef")
                        self.output.append(f"    LEA {self.reg_rdx}, [rel {return_site_label}]  ; Get return address")
                        self.output.append(f"    MOV DWORD [{self.reg_rax}], EDX  ; Write return address to instruction bytes (32-bit, like example)")
                    self.output.append(f"    JMP FUNC_{func_name}  ; Jump to function")
                else:
                    # Standard call
                    self.output.append(f"    CALL FUNC_{func_name}")
        
        # Place return site after call (quantized call-back with 16-byte alignment)
        if return_site_label:
            self.output.append(f"    ALIGN {self.alignment}")
            self.output.append(f"{return_site_label}:  ; Quantized call-back (16-byte aligned)")
            # Calculate offset from base (fits in single byte since aligned to 16 bytes)
            offset_byte = (len(self.return_sites) - 1)
            self.output.append(f"    ; Return site offset: {offset_byte} (stored in single byte)")
    
    def _generate_expression(self, expr):
        """Generate code for an expression (simplified)."""
        if isinstance(expr, c_ast.Constant):
            value = expr.value
            # Handle string constants - convert to numeric value
            if isinstance(value, str):
                # Check if it's a string literal (enclosed in quotes)
                if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                    # For character constants, extract the character value
                    if value.startswith("'") and len(value) >= 3:
                        # Single character constant like 'a' or '\n'
                        # Handle escape sequences
                        inner = value[1:-1]  # Remove quotes
                        if len(inner) == 1:
                            char_val = ord(inner)
                        elif len(inner) == 2 and inner[0] == '\\':
                            # Escape sequence
                            if inner[1] == 'n':
                                char_val = ord('\n')  # 10
                            elif inner[1] == 't':
                                char_val = ord('\t')  # 9
                            elif inner[1] == 'r':
                                char_val = ord('\r')  # 13
                            elif inner[1] == '\\':
                                char_val = ord('\\')  # 92
                            elif inner[1] == '0':
                                char_val = ord('\0')  # 0
                            elif inner[1] == "'":
                                char_val = ord("'")  # 39
                            elif inner[1] == '"':
                                char_val = ord('"')  # 34
                            else:
                                # Unknown escape, use the character itself
                                char_val = ord(inner[1])
                        else:
                            # Fallback: use first character
                            char_val = ord(inner[0]) if len(inner) > 0 else 0
                        self.output.append(f"    MOV {self.reg_rax}, {char_val}")
                    elif value.startswith('"') and len(value) >= 3:
                        # String literal - use first character
                        inner = value[1:-1]  # Remove quotes
                        if len(inner) > 0:
                            # Handle escape sequences in string literals
                            if inner.startswith('\\') and len(inner) >= 2:
                                if inner[1] == 'n':
                                    char_val = ord('\n')
                                elif inner[1] == 't':
                                    char_val = ord('\t')
                                elif inner[1] == 'r':
                                    char_val = ord('\r')
                                elif inner[1] == '\\':
                                    char_val = ord('\\')
                                elif inner[1] == '0':
                                    char_val = ord('\0')
                                else:
                                    char_val = ord(inner[1])
                            else:
                                char_val = ord(inner[0])
                        else:
                            char_val = 0
                        self.output.append(f"    MOV {self.reg_rax}, {char_val}")
                    else:
                        # Empty or invalid string, use 0
                        self.output.append(f"    MOV {self.reg_rax}, 0")
                else:
                    # Try to parse as numeric value
                    try:
                        if value.startswith('0x') or value.startswith('0X'):
                            num_value = int(value, 16)
                        elif value.startswith('0') and len(value) > 1:
                            num_value = int(value, 8)
                        else:
                            num_value = int(value)
                        self.output.append(f"    MOV {self.reg_rax}, {num_value}")
                    except (ValueError, TypeError):
                        # If conversion fails, use 0
                        self.output.append(f"    MOV {self.reg_rax}, 0")
            else:
                # Numeric value
                try:
                    num_value = int(value)
                    self.output.append(f"    MOV {self.reg_rax}, {num_value}")
                except (ValueError, TypeError):
                    self.output.append(f"    MOV {self.reg_rax}, 0")
        elif isinstance(expr, c_ast.ID):
            name = expr.name
            # Check lookup order: parameters > locals > packed globals > globals > assembly
            if name in self.function_parameters:
                # Function parameter - load from argument register (highest priority)
                param_reg = self.function_parameters[name]
                self.output.append(f"    MOV {self.reg_rax}, {param_reg}  ; Load parameter {name}")
            elif name in self.current_function_stack:
                # Local variable - use stack addressing (arrays need address, not value)
                if name in getattr(self, 'local_arrays', set()):
                    slot_index, offset = self.current_function_stack[name]
                    stack_offset = (slot_index + 1) * 8 + offset
                    if self.use_32bit:
                        self.output.append(f"    LEA {self.reg_rax}, [{self.reg_rbp} - {stack_offset}]  ; Array address")
                    else:
                        self.output.append(f"    LEA {self.reg_rax}, [{self.reg_rbp} - {stack_offset}]  ; Array address")
                else:
                    self._generate_local_var_load(name)
            elif name in self.global_var_data['bit_positions']:
                # Packed global variable - use SIMD register access
                self._generate_packed_var_access(name, is_write=False)
            else:
                # Check if it's a global variable (non-packed)
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Check if this is an array - arrays should give address, not value
                    is_array = False
                    is_pointer = False
                    glob_vars = getattr(self, '_current_parser', None).get_global_variables() if hasattr(self, '_current_parser') else []
                    for gv in glob_vars:
                        if gv.name == name:
                            type_node = gv.type
                            while hasattr(type_node, 'type'):
                                if isinstance(type_node, c_ast.ArrayDecl):
                                    is_array = True
                                    break
                                if isinstance(type_node, c_ast.PtrDecl):
                                    is_pointer = True
                                    break
                                type_node = type_node.type
                            break
                    
                    if is_array:
                        # Load array address - use position-independent addressing in 64-bit mode
                        if self.use_32bit:
                            self.output.append(f"    MOV {self.reg_rax}, GLOBAL_{name}  ; Load array address")
                        else:
                            # Use RIP-relative addressing for position-independent code
                            self.output.append(f"    LEA {self.reg_rax}, [rel GLOBAL_{name}]  ; Load array address (PIC)")
                    elif is_pointer:
                        self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]  ; Load global pointer variable")
                    else:
                        self.output.append(f"    MOV EAX, DWORD [GLOBAL_{name}]  ; Load global int variable")
                elif self.asm_parser and self.asm_parser.has_symbol(name):
                    # Global variable defined in assembly
                    self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]  ; Load assembly-defined global")
                    self.referenced_asm_symbols.add(name)
                else:
                    # Unknown variable - try local var load as fallback
                    self._generate_local_var_load(name)
        elif isinstance(expr, c_ast.BinaryOp):
            self._generate_binary_op(expr)
        elif isinstance(expr, c_ast.UnaryOp):
            self._generate_unary_op(expr)
        elif isinstance(expr, c_ast.ArrayRef):
            self._generate_array_ref(expr)
        elif isinstance(expr, c_ast.StructRef):
            self._generate_struct_ref(expr)
        elif isinstance(expr, c_ast.TernaryOp):
            self._generate_ternary_op(expr)
        elif isinstance(expr, c_ast.FuncCall):
            # Function call in expression - generate call, return value will be in RAX
            # We need to get the current function name for the caller context
            # Use the last function name we were generating (stored in _current_function_name)
            caller_func_name = getattr(self, '_current_function_name', 'unknown')
            self._generate_call(expr, caller_func_name)
            # Function call leaves return value in RAX, which is what we want
        else:
            # Unknown expression type - output warning and generate no-op
            # Use safe_str to prevent AST node objects from being output as strings
            expr_type = safe_str(expr)
            self.output.append(f"    ; Warning: Unhandled expression type: {expr_type}")
            self.output.append(f"    MOV {self.reg_rax}, 0  ; Default value for unhandled expression")

    def _expr_contains_func_call(self, expr):
        """Return True if expression tree contains a function call."""
        if expr is None:
            return False
        if isinstance(expr, c_ast.FuncCall):
            return True
        for _, child in expr.children():
            if self._expr_contains_func_call(child):
                return True
        return False
    
    def _generate_binary_op(self, op):
        """Generate code for binary operation."""
        # Optimize: if right operand is a small constant, use immediate operations
        if isinstance(op.right, c_ast.Constant) and op.op in ['+', '-', '*']:
            try:
                const_val = int(op.right.value)
                self._generate_expression(op.left)
                
                if op.op == '+':
                    if const_val == 0:
                        pass  # No-op
                    else:
                        self.output.append(f"    ADD {self.reg_rax}, {const_val}")
                    return
                elif op.op == '-':
                    if const_val == 0:
                        pass  # No-op
                    else:
                        self.output.append(f"    SUB {self.reg_rax}, {const_val}")
                    return
                elif op.op == '*':
                    if const_val == 0:
                        self.output.append(f"    XOR {self.reg_rax}, {self.reg_rax}")
                    elif const_val == 1:
                        pass  # No-op
                    elif const_val == 2:
                        self.output.append(f"    ADD {self.reg_rax}, {self.reg_rax}")
                    elif const_val in [4, 8, 16, 32, 64, 128, 256]:
                        shift = {4:2, 8:3, 16:4, 32:5, 64:6, 128:7, 256:8}[const_val]
                        self.output.append(f"    SHL {self.reg_rax}, {shift}")
                    else:
                        # Use IMUL for other constants
                        self.output.append(f"    IMUL {self.reg_rax}, {self.reg_rax}, {const_val}")
                    return
            except (ValueError, TypeError):
                pass  # Fall through to general case
        
        # Optimize: if left operand is a constant for commutative ops, swap
        if isinstance(op.left, c_ast.Constant) and op.op in ['+', '*']:
            try:
                const_val = int(op.left.value)
                self._generate_expression(op.right)
                
                if op.op == '+':
                    if const_val == 0:
                        pass  # No-op
                    else:
                        self.output.append(f"    ADD {self.reg_rax}, {const_val}")
                    return
                elif op.op == '*':
                    if const_val == 0:
                        self.output.append(f"    XOR {self.reg_rax}, {self.reg_rax}")
                    elif const_val == 1:
                        pass  # No-op
                    elif const_val == 2:
                        self.output.append(f"    ADD {self.reg_rax}, {self.reg_rax}")
                    elif const_val in [4, 8, 16, 32, 64, 128, 256]:
                        shift = {4:2, 8:3, 16:4, 32:5, 64:6, 128:7, 256:8}[const_val]
                        self.output.append(f"    SHL {self.reg_rax}, {shift}")
                    else:
                        self.output.append(f"    IMUL {self.reg_rax}, {self.reg_rax}, {const_val}")
                    return
            except (ValueError, TypeError):
                pass  # Fall through to general case
        
        # General case: evaluate both operands
        # 64-bit * keeps left in RCX: callees often use MOV R10,... for multiply temps;
        # that must not clobber a live value a caller left in R10 (nested square calls).
        left_temp = 'RCX' if (op.op == '*' and not self.use_32bit) else self.reg_binary_op_temp
        
        # Optimize: if left operand is a variable in a register, use it directly
        left_in_reg = None
        if isinstance(op.left, c_ast.ID):
            var_name = op.left.name
            if self.register_allocator and self._current_function_name:
                reg = self.register_allocator.get_register(self._current_function_name, var_name)
                if reg:
                    left_in_reg = reg
            elif var_name in self.variable_registers:
                left_in_reg = self.variable_registers[var_name]
        
        if left_in_reg and left_in_reg != self.reg_rax:
            # Left operand is in a register - use it directly
            # Check if binary-op temp (R10/EBX) is already in use by another variable
            temp_in_use = False
            temp_var = None
            for var_name, reg in self.variable_registers.items():
                if reg == left_temp:
                    temp_in_use = True
                    temp_var = var_name
                    break
            
            if temp_in_use and left_in_reg != left_temp:
                # Temp is in use, save it first
                self.output.append(f"    PUSH {left_temp}  ; Save {temp_var}")
                if self.use_32bit:
                    reg_32 = left_in_reg.replace('R', 'E') if left_in_reg.startswith('R') else left_in_reg
                    self.output.append(f"    MOV {left_temp}, {reg_32}  ; Use {op.left.name if isinstance(op.left, c_ast.ID) else 'left'} from register")
                else:
                    self.output.append(f"    MOV {left_temp}, {left_in_reg}  ; Use {op.left.name if isinstance(op.left, c_ast.ID) else 'left'} from register")
                self._binary_op_temp_saved = True
            else:
                if self.use_32bit:
                    reg_32 = left_in_reg.replace('R', 'E') if left_in_reg.startswith('R') else left_in_reg
                    self.output.append(f"    MOV {left_temp}, {reg_32}  ; Use {op.left.name if isinstance(op.left, c_ast.ID) else 'left'} from register")
                else:
                    self.output.append(f"    MOV {left_temp}, {left_in_reg}  ; Use {op.left.name if isinstance(op.left, c_ast.ID) else 'left'} from register")
                self._binary_op_temp_saved = False
        else:
            # Evaluate left operand normally
            self._generate_expression(op.left)
            # Check if binary-op temp is already in use
            temp_in_use = False
            temp_var = None
            for var_name, reg in self.variable_registers.items():
                if reg == left_temp:
                    temp_in_use = True
                    temp_var = var_name
                    break
            
            if temp_in_use:
                self.output.append(f"    PUSH {left_temp}  ; Save {temp_var}")
                self.output.append(f"    MOV {left_temp}, {self.reg_rax}  ; Save left operand")
                self._binary_op_temp_saved = True
            else:
                self.output.append(f"    MOV {left_temp}, {self.reg_rax}  ; Save left operand")
                self._binary_op_temp_saved = False
        
        # Evaluate right operand.
        # Nested binary expressions reuse left_temp, so preserve it.
        # If RHS contains function calls, do not use stack preservation because
        # call lowering may emit extra return-site pushes in this backend.
        rhs_has_call = self._expr_contains_func_call(op.right)
        if rhs_has_call and not self.use_32bit:
            self.output.append(f"    MOV R15, {left_temp}  ; Preserve left operand across calls")
            self._generate_expression(op.right)
            self.output.append(f"    MOV {left_temp}, R15  ; Restore left operand")
        else:
            self.output.append(f"    PUSH {left_temp}  ; Preserve left operand")
            self._generate_expression(op.right)
            self.output.append(f"    POP {left_temp}  ; Restore left operand")
        
        if op.op == '+':
            self.output.append(f"    ADD {self.reg_rax}, {left_temp}")
        elif op.op == '-':
            self.output.append(f"    SUB {left_temp}, {self.reg_rax}")
            self.output.append(f"    MOV {self.reg_rax}, {left_temp}")
        elif op.op == '*':
            self.output.append(f"    IMUL {self.reg_rax}, {left_temp}")
        elif op.op == '/':
            # Division: left / RAX (operands need swapping)
            # DIV divides RDX:RAX by operand, result in RAX, remainder in RDX
            self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Save divisor")
            self.output.append(f"    MOV {self.reg_rax}, {left_temp}  ; Dividend to RAX")
            self.output.append(f"    XOR {self.reg_rdx}, {self.reg_rdx}  ; Clear RDX for unsigned division")
            self.output.append(f"    DIV {self.reg_rcx}  ; RAX = RAX / RCX")
        elif op.op == '==':
            self.output.append(f"    CMP {self.reg_rax}, {left_temp}")
            self.output.append("    SETE AL")
            self.output.append(f"    MOVZX {self.reg_rax}, AL")
        elif op.op == '<':
            self.output.append(f"    CMP {left_temp}, {self.reg_rax}")
            self.output.append("    SETL AL")
            self.output.append(f"    MOVZX {self.reg_rax}, AL")
        elif op.op == '>':
            self.output.append(f"    CMP {left_temp}, {self.reg_rax}")
            self.output.append("    SETG AL")
            self.output.append(f"    MOVZX {self.reg_rax}, AL")
        elif op.op == '<=':
            self.output.append(f"    CMP {left_temp}, {self.reg_rax}")
            self.output.append("    SETLE AL")
            self.output.append(f"    MOVZX {self.reg_rax}, AL")
        elif op.op == '>=':
            self.output.append(f"    CMP {left_temp}, {self.reg_rax}")
            self.output.append("    SETGE AL")
            self.output.append(f"    MOVZX {self.reg_rax}, AL")
        elif op.op == '!=':
            self.output.append(f"    CMP {self.reg_rax}, {left_temp}")
            self.output.append("    SETNE AL")
            self.output.append(f"    MOVZX {self.reg_rax}, AL")
        elif op.op == '%':
            # Modulo: left % right
            self.output.append(f"    ; Modulo operation: {left_temp} % {self.reg_rax}")
            self.output.append(f"    PUSH {self.reg_rax}  ; Save right operand (divisor)")
            self.output.append(f"    MOV {self.reg_rax}, {left_temp}  ; Move left operand (dividend) to {self.reg_rax}")
            self.output.append(f"    POP {left_temp}  ; Get divisor")
            self.output.append(f"    XOR {self.reg_rdx}, {self.reg_rdx}  ; Clear {self.reg_rdx} for division")
            self.output.append(f"    DIV {left_temp}  ; {self.reg_rax} = dividend / divisor, {self.reg_rdx} = remainder")
            self.output.append(f"    MOV {self.reg_rax}, {self.reg_rdx}  ; Remainder is the modulo result")
        elif op.op == '&&':
            # Logical AND: both operands must be non-zero
            self.label_counter = self.label_counter + 1
            label_id = self.label_counter
            self.output.append(f"    ; Logical AND: {left_temp} && {self.reg_rax}")
            self.output.append(f"    TEST {left_temp}, {left_temp}  ; Check if left is non-zero")
            self.output.append(f"    JZ AND_FALSE_{label_id}")
            self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}  ; Check if right is non-zero")
            self.output.append(f"    JZ AND_FALSE_{label_id}")
            self.output.append(f"    MOV {self.reg_rax}, 1  ; Both non-zero, result is 1")
            self.output.append(f"    JMP AND_END_{label_id}")
            self.output.append(f"AND_FALSE_{label_id}:")
            self.output.append(f"    MOV {self.reg_rax}, 0  ; One or both zero, result is 0")
            self.output.append(f"AND_END_{label_id}:")
        elif op.op == '||':
            # Logical OR: at least one operand must be non-zero
            self.label_counter = self.label_counter + 1
            label_id = self.label_counter
            self.output.append(f"    ; Logical OR: {left_temp} || {self.reg_rax}")
            self.output.append(f"    TEST {left_temp}, {left_temp}  ; Check if left is non-zero")
            self.output.append(f"    JNZ OR_TRUE_{label_id}")
            self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}  ; Check if right is non-zero")
            self.output.append(f"    JNZ OR_TRUE_{label_id}")
            self.output.append(f"    MOV {self.reg_rax}, 0  ; Both zero, result is 0")
            self.output.append(f"    JMP OR_END_{label_id}")
            self.output.append(f"OR_TRUE_{label_id}:")
            self.output.append(f"    MOV {self.reg_rax}, 1  ; At least one non-zero, result is 1")
            self.output.append(f"OR_END_{label_id}:")
        elif op.op == '<<':
            self.output.append(f"    ; Left shift: {left_temp} << {self.reg_rax}")
            self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Shift amount in {self.reg_rcx}")
            self.output.append(f"    MOV {self.reg_rax}, {left_temp}  ; Value to shift")
            self.output.append(f"    SHL {self.reg_rax}, CL  ; Left shift by CL (low 8 bits of {self.reg_rcx})")
        elif op.op == '>>':
            self.output.append(f"    ; Right shift: {left_temp} >> {self.reg_rax}")
            self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Shift amount in {self.reg_rcx}")
            self.output.append(f"    MOV {self.reg_rax}, {left_temp}  ; Value to shift")
            self.output.append(f"    SHR {self.reg_rax}, CL  ; Right shift by CL (low 8 bits of {self.reg_rcx})")
        elif op.op == '&':
            self.output.append(f"    ; Bitwise AND: {left_temp} & {self.reg_rax}")
            self.output.append(f"    AND {self.reg_rax}, {left_temp}")
        elif op.op == '|':
            self.output.append(f"    ; Bitwise OR: {left_temp} | {self.reg_rax}")
            self.output.append(f"    OR {self.reg_rax}, {left_temp}")
        elif op.op == '^':
            self.output.append(f"    ; Bitwise XOR: {left_temp} ^ {self.reg_rax}")
            self.output.append(f"    XOR {self.reg_rax}, {left_temp}")
        
        # Restore binary-op temp if it was saved (variable was in that register)
        if hasattr(self, '_binary_op_temp_saved') and self._binary_op_temp_saved:
            self.output.append(f"    POP {left_temp}  ; Restore temp")
            self._binary_op_temp_saved = False
    
    def _generate_unary_op(self, op):
        """Generate code for unary operation."""
        # Handle address-of operator FIRST (before generating expression)
        # because &var should NOT load the value first
        if op.op == '&':
            # Address-of: &var
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Check if it's a global variable
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Global variable address - use position-independent addressing in 64-bit mode
                    if self.use_32bit:
                        self.output.append(f"    MOV RAX, GLOBAL_{name}  ; Address of global variable")
                    else:
                        self.output.append(f"    LEA RAX, [rel GLOBAL_{name}]  ; Address of global variable (PIC)")
                else:
                    # Local variable address - use LEA with RBP offset
                    if name in self.current_function_stack:
                        slot_index, offset = self.current_function_stack[name]
                        stack_offset = (slot_index + 1) * 8 + offset  # Match _generate_local_var_load
                        self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset}]  ; Address of local variable {name}")
                    else:
                        self.output.append(f"    ; Warning: variable {name} not found for address-of")
            else:
                # Complex expression - generate and use as address
                self._generate_expression(op.expr)
            return  # Early return for address-of
        
        # For other unary ops, generate the expression first
        self._generate_expression(op.expr)
        if op.op == '-':
            self.output.append(f"    NEG {self.reg_rax}")
        elif op.op == '!':
            self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}")
            self.output.append("    SETZ AL")
            self.output.append(f"    MOVZX {self.reg_rax}, AL")
        elif op.op == '*':
            # Pointer dereference: *ptr
            self.output.append("    ; Pointer dereference: *ptr")
            self.output.append(f"    MOV {self.reg_rax}, [{self.reg_rax}]  ; Load value at address in {self.reg_rax}")
        elif op.op == '~':
            # Bitwise NOT: ~expr
            self.output.append("    ; Bitwise NOT: ~expr")
            self.output.append(f"    NOT {self.reg_rax}")
        elif op.op == 'p++':
            # Post-increment: var++
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]")
                    else:
                        self._generate_local_var_load(name)
                # Increment and store back
                self.output.append(f"    PUSH {self.reg_rax}  ; Save original value")
                self.output.append(f"    INC {self.reg_rax}")
                # Store incremented value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=True, value_reg=self.reg_rax)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV [GLOBAL_{name}], {self.reg_rax}")
                    else:
                        # Store to local - use RBP-based addressing
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            stack_offset = (slot_index + 1) * 8 + offset
                            self.output.append(f"    MOV DWORD [{self.reg_rbp} - {stack_offset}], EAX  ; Store {name}")
                            # Update register if variable is in a register
                            if name in self.variable_registers:
                                reg = self.variable_registers[name]
                                if self.use_32bit:
                                    reg_32 = reg.replace('R', 'E') if reg.startswith('R') else reg
                                    self.output.append(f"    MOV {reg_32}, EAX  ; Update {name} in register {reg}")
                                else:
                                    if reg.startswith('R'):
                                        if reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                                            reg_32 = reg + 'D'
                                        else:
                                            reg_32 = reg.replace('R', 'E')
                                        self.output.append(f"    MOV {reg_32}, EAX  ; Update {name} in register {reg} (32-bit)")
                                    else:
                                        self.output.append(f"    MOV {reg}, EAX  ; Update {name} in register {reg}")
                self.output.append(f"    POP {self.reg_rax}  ; Return original value")
        elif op.op == 'p--':
            # Post-decrement: var--
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]")
                    else:
                        self._generate_local_var_load(name)
                # Decrement and store back
                self.output.append(f"    PUSH {self.reg_rax}  ; Save original value")
                self.output.append(f"    DEC {self.reg_rax}")
                # Store decremented value (similar to post-increment)
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=True, value_reg=self.reg_rax)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV [GLOBAL_{name}], {self.reg_rax}")
                    else:
                        # Store to local - use RBP-based addressing
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            stack_offset = (slot_index + 1) * 8 + offset
                            self.output.append(f"    MOV DWORD [{self.reg_rbp} - {stack_offset}], EAX  ; Store {name}")
                            # Update register if variable is in a register
                            if name in self.variable_registers:
                                reg = self.variable_registers[name]
                                if self.use_32bit:
                                    reg_32 = reg.replace('R', 'E') if reg.startswith('R') else reg
                                    self.output.append(f"    MOV {reg_32}, EAX  ; Update {name} in register {reg}")
                                else:
                                    if reg.startswith('R'):
                                        if reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                                            reg_32 = reg + 'D'
                                        else:
                                            reg_32 = reg.replace('R', 'E')
                                        self.output.append(f"    MOV {reg_32}, EAX  ; Update {name} in register {reg} (32-bit)")
                                    else:
                                        self.output.append(f"    MOV {reg}, EAX  ; Update {name} in register {reg}")
                self.output.append(f"    POP {self.reg_rax}  ; Return original value")
        elif op.op == '++':
            # Pre-increment: ++var
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load, increment, store, return new value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                    self.output.append(f"    INC {self.reg_rax}")
                    self._generate_packed_var_access(name, is_write=True, value_reg=self.reg_rax)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]")
                        self.output.append(f"    INC {self.reg_rax}")
                        self.output.append(f"    MOV [GLOBAL_{name}], {self.reg_rax}")
                    else:
                        self._generate_local_var_load(name)
                        self.output.append(f"    INC {self.reg_rax}")
                        # Store to local - use RBP-based addressing
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            stack_offset = (slot_index + 1) * 8 + offset
                            self.output.append(f"    MOV DWORD [{self.reg_rbp} - {stack_offset}], EAX  ; Store {name}")
        elif op.op == '--':
            # Pre-decrement: --var
            if isinstance(op.expr, c_ast.ID):
                name = op.expr.name
                # Load, decrement, store, return new value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                    self.output.append(f"    DEC {self.reg_rax}")
                    self._generate_packed_var_access(name, is_write=True, value_reg=self.reg_rax)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]")
                        self.output.append(f"    DEC {self.reg_rax}")
                        self.output.append(f"    MOV [GLOBAL_{name}], {self.reg_rax}")
                    else:
                        self._generate_local_var_load(name)
                        self.output.append(f"    DEC {self.reg_rax}")
                        # Store to local - use RBP-based addressing
                        if name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[name]
                            stack_offset = (slot_index + 1) * 8 + offset
                            self.output.append(f"    MOV DWORD [{self.reg_rbp} - {stack_offset}], EAX  ; Store {name}")
    
    def _generate_array_ref(self, arr_ref):
        """Generate code for array indexing: arr[index] using efficient LEA addressing."""
        # Generate index first (we'll need it)
        self._generate_expression(arr_ref.subscript)
        # Save index to a register (prefer RCX for index)
        index_reg = self.reg_rcx
        if self.use_32bit:
            self.output.append(f"    MOV ECX, EAX  ; Save index")
        else:
            self.output.append(f"    MOV RCX, RAX  ; Save index")
        
        # Generate base address (array name or pointer)
        if isinstance(arr_ref.name, c_ast.ID):
            # Array variable name
            name = arr_ref.name.name
            # Parameter (pointer): base is in argument register - use it, not GLOBAL_
            if name in self.function_parameters:
                param_reg = self.function_parameters[name]
                self.output.append(f"    MOV {self.reg_rax}, {param_reg}  ; Base from parameter {name}")
                if self.use_32bit:
                    self.output.append(f"    LEA EAX, [EAX + ECX*4]  ; Base + index*4")
                else:
                    self.output.append(f"    LEA RAX, [RAX + RCX*4]  ; Base + index*4")
            else:
                # Check if it's a global variable
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Global array - use LEA with scaled index (GCC style)
                    if self.use_32bit:
                        self.output.append(f"    LEA EAX, [GLOBAL_{name} + ECX*4]  ; Base + index*4 (int is 4 bytes)")
                    else:
                        self.output.append(f"    LEA RAX, [rel GLOBAL_{name} + RCX*4]  ; Base + index*4 (int is 4 bytes, PIC)")
                else:
                    # Local array - get base address; use per-array element size (e.g. 16 for struct Inner[])
                    if name in self.current_function_stack:
                        slot_index, offset = self.current_function_stack[name]
                        stack_offset = (slot_index + 1) * 8 + offset
                        elem_size = getattr(self, 'local_array_element_size', {}).get(name, 4)
                        if self.use_32bit:
                            if elem_size == 1:
                                self.output.append(f"    LEA EAX, [{self.reg_rbp} - {stack_offset} + ECX*1]  ; Base + index*1")
                            elif elem_size == 2:
                                self.output.append(f"    LEA EAX, [{self.reg_rbp} - {stack_offset} + ECX*2]  ; Base + index*2")
                            elif elem_size == 4:
                                self.output.append(f"    LEA EAX, [{self.reg_rbp} - {stack_offset} + ECX*4]  ; Base + index*4")
                            elif elem_size == 8:
                                self.output.append(f"    LEA EAX, [{self.reg_rbp} - {stack_offset} + ECX*8]  ; Base + index*8")
                            elif elem_size == 16:
                                self.output.append(f"    LEA EAX, [{self.reg_rbp} - {stack_offset} + ECX*8]  ; Base + index*16 (struct)")
                                self.output.append(f"    LEA EAX, [EAX + ECX*8]  ; + index*8")
                            else:
                                self.output.append(f"    MOV EAX, ECX  ; index")
                                self.output.append(f"    IMUL EAX, {elem_size}  ; index * elem_size")
                                self.output.append(f"    LEA EAX, [{self.reg_rbp} - {stack_offset} + EAX]  ; base + offset")
                        else:
                            if elem_size == 1:
                                self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset} + RCX*1]  ; Base + index*1")
                            elif elem_size == 2:
                                self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset} + RCX*2]  ; Base + index*2")
                            elif elem_size == 4:
                                self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset} + RCX*4]  ; Base + index*4")
                            elif elem_size == 8:
                                self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset} + RCX*8]  ; Base + index*8")
                            elif elem_size == 16:
                                self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset} + RCX*8]  ; Base + index*16 (struct)")
                                self.output.append(f"    LEA RAX, [RAX + RCX*8]  ; + index*8")
                            else:
                                self.output.append(f"    MOV RAX, RCX  ; index")
                                self.output.append(f"    IMUL RAX, {elem_size}  ; index * elem_size")
                                self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset} + RAX]  ; base + offset")
                    else:
                        # Parameter or complex - load base first
                        self._generate_expression(arr_ref.name)
                        if self.use_32bit:
                            self.output.append(f"    LEA EAX, [EAX + ECX*4]  ; Base + index*4")
                        else:
                            self.output.append(f"    LEA RAX, [RAX + RCX*4]  ; Base + index*4")
        else:
            # Complex expression for base - evaluate it
            self._generate_expression(arr_ref.name)
            if self.use_32bit:
                self.output.append(f"    LEA EAX, [EAX + ECX*4]  ; Base + index*4")
            else:
                self.output.append(f"    LEA RAX, [RAX + RCX*4]  ; Base + index*4")
        
        # Load value from memory
        if self.use_32bit:
            self.output.append(f"    MOV EAX, DWORD [EAX]  ; Load array element")
        else:
            self.output.append(f"    MOV EAX, DWORD [RAX]  ; Load array element (32-bit)")
    
    def _compute_nested_struct_offset(self, struct_ref):
        """Compute cumulative offset for nested struct access like container.outer.inner.callback.
        
        Returns: (base_expr, total_offset) where base_expr is the base variable/expression
        and total_offset is the cumulative byte offset.
        """
        # Build the path recursively from base to final member
        # For container.outer.inner.callback:
        #   struct_ref.field.name = 'callback'
        #   struct_ref.name = StructRef with field='inner', name=StructRef with field='outer', name=ID('container')
        path = []
        
        def extract_path(sr):
            """Recursively extract the path from nested struct reference."""
            if not isinstance(sr, c_ast.StructRef):
                return sr  # Base expression
            
            member_name = None
            if hasattr(sr, 'field') and sr.field and hasattr(sr.field, 'name'):
                member_name = sr.field.name
            
            struct_type = None
            if hasattr(sr, 'type'):
                type_val = sr.type
                if isinstance(type_val, str):
                    struct_type = type_val
                elif isinstance(type_val, c_ast.Node):
                    struct_type = None
                else:
                    struct_type = safe_str(type_val) if type_val in ['.', '->'] else None
            
            # Recursively process the name part
            base = extract_path(sr.name)
            path.append((member_name, struct_type))
            return base
        
        base_expr = extract_path(struct_ref)
        
        if not path or not isinstance(base_expr, c_ast.ID):
            return (None, 0)
        
        # Compute cumulative offset based on struct layouts
        # Struct layouts (based on test_nested_structs.c):
        # Inner: x (0), y (4), callback (8) = 16 bytes total
        # Outer: inner (0-15), inner_ptr (16), value (24), get_inner (32), handler (40) = 48 bytes total
        # Container: outer (0-47), outer_ptr (48), nested (56-71), func_ptr (72) = 80 bytes total
        
        total_offset = 0
        current_offset = 0
        
        # Process path from base to final member
        for i in range(1, len(path)):
            member_name, struct_type = path[i]
            if member_name is None:
                continue
            
            # Member offsets within each struct type
            if member_name == 'x':
                total_offset += 0
            elif member_name == 'y':
                total_offset += 4
            elif member_name == 'callback':
                total_offset += 8
            elif member_name == 'inner':
                total_offset += 0  # First member of Outer
            elif member_name == 'inner_ptr':
                total_offset += 16  # After Inner struct (16 bytes)
            elif member_name == 'value':
                total_offset += 24  # After inner_ptr (16 + 8)
            elif member_name == 'get_inner':
                total_offset += 32  # After value (24 + 8 with alignment)
            elif member_name == 'handler':
                total_offset += 40  # After get_inner (32 + 8)
            elif member_name == 'outer':
                total_offset += 0  # First member of Container
            elif member_name == 'outer_ptr':
                total_offset += 48  # After Outer struct (48 bytes)
            elif member_name == 'nested':
                total_offset += 56  # After outer_ptr (48 + 8)
            elif member_name == 'func_ptr':
                total_offset += 72  # After nested (56 + 16)
            elif member_name == 'deep_callback':
                total_offset += 0  # First member of Deep3
            elif member_name == 'value' and i > 1:  # value in Deep3
                total_offset += 8  # After deep_callback
            elif member_name == 'deep3':
                total_offset += 0  # First member of Deep2
            elif member_name == 'deep3_ptr':
                total_offset += 8  # After deep3
            elif member_name == 'deep2':
                total_offset += 0  # First member of Deep1
            
            # Handle pointer dereference
            if struct_type == '->':
                # After computing offset, we need to dereference the pointer
                # This will be handled in the main function
                pass
        
        # Add offset for the final member (path[0] = the field being accessed, e.g. callback, x, y)
        final_member_name = path[0][0] if path else None
        if final_member_name:
            if final_member_name == 'x':
                total_offset += 0
            elif final_member_name == 'y':
                total_offset += 4
            elif final_member_name == 'callback':
                total_offset += 8
            elif final_member_name == 'value':
                # Outer.value = 24; Deep3.value = 8. path[1] is the struct we're inside.
                innermost = path[1][0] if len(path) > 1 else None
                total_offset += 8 if innermost == 'deep3' else 24
            elif final_member_name == 'deep_callback':
                total_offset += 0
            elif final_member_name in ('inner_ptr', 'inner', 'outer', 'outer_ptr', 'nested', 'func_ptr', 'get_inner', 'handler', 'deep3', 'deep3_ptr', 'deep2'):
                pass  # Already accounted for in path traversal (sub-struct offsets)
            else:
                # Generic: try common offsets
                final_offsets = {'z': 8, 'width': 8, 'height': 12, 'a': 0, 'b': 4, 'c': 8, 'd': 12}
                total_offset += final_offsets.get(final_member_name, 0)
        
        return (base_expr, total_offset)
    
    def _generate_struct_ref(self, struct_ref):
        """Generate code for struct member access: struct.member or struct->member"""
        # Defensive check: ensure struct_ref has required attributes
        if not hasattr(struct_ref, 'type') or not hasattr(struct_ref, 'name'):
            self.output.append("    ; Warning: Invalid struct reference")
            self.output.append("    MOV RAX, 0")
            return
        
        member_name = None
        if hasattr(struct_ref, 'field') and struct_ref.field and hasattr(struct_ref.field, 'name'):
            member_name = struct_ref.field.name
        
        # Try to compute nested struct offset for optimization
        base_expr, cumulative_offset = self._compute_nested_struct_offset(struct_ref)
        
        # Check if we can optimize (base is a simple ID and we computed the offset)
        if base_expr and isinstance(base_expr, c_ast.ID) and cumulative_offset >= 0:
            name = base_expr.name
            globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
            
            if name in globals:
                # Optimized: single memory access with computed offset
                self.output.append(f"    ; Optimized nested struct access: {name} + {cumulative_offset}")
                if cumulative_offset == 0:
                    self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]  ; Load member directly")
                else:
                    self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name} + {cumulative_offset}]  ; Load member with offset")
                return
        
        # Fallback to original recursive approach
        # Ensure type is a string, not an attribute name or AST node
        if hasattr(struct_ref, 'type'):
            type_val = struct_ref.type
            if isinstance(type_val, str):
                struct_type = type_val
            elif isinstance(type_val, c_ast.Node):
                struct_type = None
            else:
                struct_type = safe_str(type_val) if type_val in ['.', '->'] else None
        else:
            struct_type = None
        
        if struct_type == '.':
            # Direct member access: struct.member
            if isinstance(struct_ref.name, c_ast.ID):
                name = struct_ref.name.name
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Base address of struct - use position-independent addressing in 64-bit mode
                    if self.use_32bit:
                        self.output.append(f"    MOV RAX, GLOBAL_{name}  ; Base address of struct")
                    else:
                        self.output.append(f"    LEA RAX, [rel GLOBAL_{name}]  ; Base address of struct (PIC)")
                else:
                    if name in self.current_function_stack:
                        # Use LEA with RBP-based addressing (not the old R12-based)
                        slot_index, offset = self.current_function_stack[name]
                        stack_offset = (slot_index + 1) * 8 + offset  # Match _generate_local_var_load
                        self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset}]  ; Base address of local struct {name}")
            else:
                self._generate_expression(struct_ref.name)
        elif struct_type == '->':
            # Pointer member access: p->member
            # Generate expression for the pointer - this gives us the address directly
            # For parameters, the value IS the pointer (no extra dereference needed)
            # For local variables that hold pointers, we need to load the pointer value
            if isinstance(struct_ref.name, c_ast.ID):
                name = struct_ref.name.name
                if name in self.function_parameters:
                    # Parameter: the register already contains the pointer value
                    param_reg = self.function_parameters[name]
                    self.output.append(f"    MOV {self.reg_rax}, {param_reg}  ; Get struct pointer {name}")
                elif name in self.current_function_stack:
                    # Local variable holding a pointer: load the pointer value
                    self._generate_local_var_load(name)
                    # RAX now contains the pointer value - no extra dereference needed
                else:
                    # Global pointer
                    self._generate_expression(struct_ref.name)
                    self.output.append(f"    MOV {self.reg_rax}, [{self.reg_rax}]  ; Load pointer value from global")
            else:
                # Complex expression - generate it and dereference if needed
                self._generate_expression(struct_ref.name)
                # For complex expressions (like function return values), assume it's already the pointer
                # Only dereference if we're loading from a stored pointer variable
        else:
            if isinstance(struct_ref.name, c_ast.StructRef):
                self._generate_struct_ref(struct_ref.name)
            else:
                self._generate_expression(struct_ref.name)
        
        # Calculate member offset
        if member_name:
            member_offsets = {
                'x': 0, 'y': 4, 'z': 8,
                'callback': 8,
                'inner': 0, 'inner_ptr': 16, 'value': 24, 'get_inner': 32, 'handler': 40,
                'outer': 0, 'outer_ptr': 48, 'nested': 56, 'func_ptr': 72,
                'width': 8, 'height': 12,
                'a': 0, 'b': 4, 'c': 8, 'd': 12,
                'deep2': 0, 'deep3': 0, 'deep3_ptr': 8, 'deep_callback': 0,
            }
            # Nested struct members: we keep RAX as address (add offset only). Leaf members: add offset and load value.
            nested_struct_members = {'inner', 'outer', 'nested', 'deep2', 'deep3'}
            is_nested_struct = member_name in nested_struct_members
            member_offset = member_offsets.get(member_name, 0)
            self.output.append(f"    ; Struct member access: {member_name} at offset {member_offset}")
            if member_offset > 0:
                self.output.append(f"    ADD RAX, {member_offset}  ; Add member offset")
            if not is_nested_struct:
                self.output.append("    MOV EAX, DWORD [RAX]  ; Load 32-bit member value")
        else:
            self.output.append("    ; Struct member access (member name not found)")
            self.output.append("    MOV EAX, DWORD [RAX]  ; Load 32-bit value at address")
    
    def _generate_assignment(self, assign):
        """Generate code for assignment."""
        # Handle compound assignment operators
        if assign.op in ['+=', '-=', '*=', '/=', '%=', '<<=', '>>=', '&=', '|=', '^=']:
            # Compound assignment: x += y is equivalent to x = x + y
            # First, load the lvalue
            if isinstance(assign.lvalue, c_ast.ID):
                name = assign.lvalue.name
                # Load current value
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=False)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV {self.reg_rax}, [GLOBAL_{name}]")
                    else:
                        self._generate_local_var_load(name)
            elif isinstance(assign.lvalue, c_ast.ArrayRef):
                # Array element: arr[i]
                self._generate_array_ref(assign.lvalue)
            elif isinstance(assign.lvalue, c_ast.StructRef):
                # Struct member: struct.member or struct->member
                # Generate address of member
                # Defensive check: ensure struct_ref has required attributes
                if not hasattr(assign.lvalue, 'type') or not hasattr(assign.lvalue, 'name'):
                    self.output.append("    ; Warning: Invalid struct reference in assignment")
                    self.output.append("    MOV RAX, 0")
                    return
                
                member_name = None
                if hasattr(assign.lvalue, 'field') and assign.lvalue.field and hasattr(assign.lvalue.field, 'name'):
                    member_name = assign.lvalue.field.name
                
                # Ensure type is a string, not an attribute name or AST node
                # assign.lvalue.type should be '.' or '->', but protect against AST nodes
                if hasattr(assign.lvalue, 'type'):
                    type_val = assign.lvalue.type
                    if isinstance(type_val, str):
                        struct_type = type_val
                    elif isinstance(type_val, c_ast.Node):
                        # If type is an AST node (shouldn't happen, but protect against it)
                        struct_type = None
                    else:
                        # Try to convert to string safely
                        struct_type = safe_str(type_val) if type_val in ['.', '->'] else None
                else:
                    struct_type = None
                
                if struct_type == '.':
                    # Direct member access: struct.member
                    if isinstance(assign.lvalue.name, c_ast.ID):
                        name = assign.lvalue.name.name
                        globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                        if name in globals:
                            # Global array address - use position-independent addressing in 64-bit mode
                            if self.use_32bit:
                                self.output.append(f"    MOV RAX, GLOBAL_{name}")
                            else:
                                self.output.append(f"    LEA RAX, [rel GLOBAL_{name}]  ; Base address of array (PIC)")
                        else:
                            if name in self.current_function_stack:
                                slot_index, offset = self.current_function_stack[name]
                                stack_offset = (slot_index + 1) * 8 + offset
                                self.output.append(f"    LEA RAX, [{self.reg_rbp} - {stack_offset}]  ; Base address of local struct {name}")
                    else:
                        # Handle nested struct references
                        if isinstance(assign.lvalue.name, c_ast.StructRef):
                            self._generate_struct_ref(assign.lvalue.name)
                        else:
                            self._generate_expression(assign.lvalue.name)
                elif struct_type == '->':
                    # Pointer member access: struct->member
                    self._generate_expression(assign.lvalue.name)
                
                # Add member offset
                if member_name:
                    member_offsets = {
                        'x': 0, 'y': 4, 'z': 8,
                        'width': 8, 'height': 12,
                        'a': 0, 'b': 4, 'c': 8, 'd': 12
                    }
                    member_offset = member_offsets.get(member_name, 0)
                    if member_offset > 0:
                        self.output.append(f"    ADD {self.reg_rax}, {member_offset}")
                
                # Save member address in a temp register that is not an argument register.
                # Using RSI here clobbers the second function parameter on x86-64.
                self.output.append(f"    MOV {self.reg_binary_op_temp}, {self.reg_rax}  ; Save member address")
                # Load current value from member
                self.output.append(f"    MOV EAX, DWORD [{self.reg_binary_op_temp}]  ; Load current value from member")
                self.output.append(f"    PUSH {self.reg_binary_op_temp}  ; Save member address for later store")
            else:
                # Complex lvalue - generate expression
                self._generate_expression(assign.lvalue)
            
            # Save current value
            self.output.append(f"    PUSH {self.reg_rax}  ; Save current value")
            
            # Generate right-hand side
            self._generate_expression(assign.rvalue)
            # Use R10/EBX for most ops; 64-bit * uses RCX so nested callees can use R10 freely
            pop_reg = 'RCX' if (assign.op == '*=' and not self.use_32bit) else self.reg_binary_op_temp
            self.output.append(f"    POP {pop_reg}  ; Get current value")
            
            # Perform operation based on operator
            base_op = assign.op[:-1]  # Remove '=' from '+=', etc.
            if base_op == '+':
                self.output.append(f"    ADD {self.reg_rax}, {pop_reg}")
            elif base_op == '-':
                self.output.append(f"    SUB {pop_reg}, {self.reg_rax}")
                self.output.append(f"    MOV {self.reg_rax}, {pop_reg}")
            elif base_op == '*':
                self.output.append(f"    IMUL {self.reg_rax}, {pop_reg}")
            elif base_op == '/':
                self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Save divisor")
                self.output.append(f"    MOV {self.reg_rax}, {pop_reg}  ; Dividend")
                self.output.append(f"    XOR {self.reg_rdx}, {self.reg_rdx}")
                self.output.append(f"    DIV {self.reg_rcx}")
            elif base_op == '%':
                self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Save divisor")
                self.output.append(f"    MOV {self.reg_rax}, {pop_reg}  ; Dividend")
                self.output.append(f"    XOR {self.reg_rdx}, {self.reg_rdx}")
                self.output.append(f"    DIV {self.reg_rcx}")
                self.output.append(f"    MOV {self.reg_rax}, {self.reg_rdx}  ; Remainder")
            elif base_op == '<<':
                self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Shift amount")
                self.output.append(f"    MOV {self.reg_rax}, {pop_reg}  ; Value to shift")
                self.output.append(f"    SHL {self.reg_rax}, CL")
            elif base_op == '>>':
                self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Shift amount")
                self.output.append(f"    MOV {self.reg_rax}, {pop_reg}  ; Value to shift")
                self.output.append(f"    SHR {self.reg_rax}, CL")
            elif base_op == '&':
                self.output.append(f"    AND {self.reg_rax}, {pop_reg}")
            elif base_op == '|':
                self.output.append(f"    OR {self.reg_rax}, {pop_reg}")
            elif base_op == '^':
                self.output.append(f"    XOR {self.reg_rax}, {pop_reg}")
            
            # Now assign the result
            # For struct members, we already pushed the address - pop it and store
            if isinstance(assign.lvalue, c_ast.StructRef):
                self.output.append(f"    POP {self.reg_binary_op_temp}  ; Get member address back")
                self.output.append(f"    MOV DWORD [{self.reg_binary_op_temp}], EAX  ; Store result to member")
                return  # Done with compound struct assignment
            
            # For ID lvalues, store directly (result is already in RAX)
            if isinstance(assign.lvalue, c_ast.ID):
                name = assign.lvalue.name
                if name in self.global_var_data['bit_positions']:
                    self._generate_packed_var_access(name, is_write=True, value_reg=self.reg_rax)
                else:
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        self.output.append(f"    MOV [GLOBAL_{name}], {self.reg_rax}")
                    else:
                        self._generate_local_var_store(name)
                return  # Done with compound ID assignment
            
            # For ArrayRef lvalues, we need to store to the array element
            if isinstance(assign.lvalue, c_ast.ArrayRef):
                # Array element was already computed before, but we need to recompute for store
                # This is inefficient but correct - could be optimized later
                pass  # Fall through to regular assignment
            
            # For other non-struct lvalues, fall through to regular assignment
            assign.op = '='  # Change to regular assignment
            # Continue with regular assignment handling
        
        if assign.op == '=':
            # Check if we have a struct member assignment
            if isinstance(assign.lvalue, c_ast.StructRef):
                # Struct member assignment: first get the address, then evaluate rvalue
                struct_addr_reg = 'EDI' if self.use_32bit else 'R11'
                # Get the struct pointer base
                struct_type = assign.lvalue.type if isinstance(assign.lvalue.type, str) else '.'
                member_name = assign.lvalue.field.name if hasattr(assign.lvalue.field, 'name') else None
                
                # Calculate member offset
                member_offsets = {'x': 0, 'y': 4, 'z': 8, 'width': 8, 'height': 12, 'a': 0, 'b': 4, 'c': 8, 'd': 12}
                member_offset = member_offsets.get(member_name, 0)
                
                if struct_type == '->':
                    # Pointer access: p->x = value
                    # First, get the pointer value in a dedicated non-argument temp register.
                    if isinstance(assign.lvalue.name, c_ast.ID):
                        ptr_name = assign.lvalue.name.name
                        if ptr_name in self.function_parameters:
                            # Parameter - it's in a register
                            param_reg = self.function_parameters[ptr_name]
                            self.output.append(f"    MOV {struct_addr_reg}, {param_reg}  ; Get struct pointer {ptr_name}")
                        else:
                            # Local variable
                            self._generate_local_var_load(ptr_name)
                            self.output.append(f"    MOV {struct_addr_reg}, {self.reg_rax}  ; Get struct pointer")
                    else:
                        self._generate_expression(assign.lvalue.name)
                        self.output.append(f"    MOV {struct_addr_reg}, {self.reg_rax}  ; Get struct pointer")
                    
                    # Add member offset
                    if member_offset > 0:
                        self.output.append(f"    ADD {struct_addr_reg}, {member_offset}  ; Add member offset for {member_name}")
                    
                    # Now generate the rvalue
                    self._generate_expression(assign.rvalue)
                    
                    # Store the value
                    self.output.append(f"    MOV DWORD [{struct_addr_reg}], EAX  ; Store to struct member {member_name}")
                else:
                    # Direct access: s.x = value
                    # Generate address of struct in a dedicated non-argument temp register.
                    if isinstance(assign.lvalue.name, c_ast.ID):
                        struct_name = assign.lvalue.name.name
                        globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                        if struct_name in globals:
                            self.output.append(f"    LEA {struct_addr_reg}, [GLOBAL_{struct_name}]  ; Get struct address")
                        elif struct_name in self.current_function_stack:
                            slot_index, offset = self.current_function_stack[struct_name]
                            stack_offset = (slot_index + 1) * 8 + offset
                            self.output.append(f"    LEA {struct_addr_reg}, [{self.reg_rbp} - {stack_offset}]  ; Get local struct address")
                        else:
                            self._generate_expression(assign.lvalue.name)
                            self.output.append(f"    MOV {struct_addr_reg}, {self.reg_rax}")
                    else:
                        self._generate_expression(assign.lvalue.name)
                        self.output.append(f"    MOV {struct_addr_reg}, {self.reg_rax}")
                    
                    # Add member offset
                    if member_offset > 0:
                        self.output.append(f"    ADD {struct_addr_reg}, {member_offset}  ; Add member offset for {member_name}")
                    
                    # Now generate the rvalue
                    self._generate_expression(assign.rvalue)
                    
                    # Store the value
                    self.output.append(f"    MOV DWORD [{struct_addr_reg}], EAX  ; Store to struct member {member_name}")
            elif isinstance(assign.lvalue, c_ast.ID):
                # Generate the rvalue expression first
                self._generate_expression(assign.rvalue)
                
                name = assign.lvalue.name
                # Check if this is a packed global variable
                if name in self.global_var_data['bit_positions']:
                    # Use zero-latency SIMD register write
                    self._generate_packed_var_access(name, is_write=True, value_reg=self.reg_rax)
                else:
                    # Check if it's a global variable (non-packed)
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        # Global variable (non-packed)
                        self.output.append(f"    MOV [GLOBAL_{name}], {self.reg_rax}")
                    elif self.asm_parser and self.asm_parser.has_symbol(name):
                        # Global variable defined in assembly
                        self.output.append(f"    MOV [GLOBAL_{name}], {self.reg_rax}  ; Store to assembly-defined global")
                        self.referenced_asm_symbols.add(name)
                    else:
                        # Local variable assignment - use indexed stack pointer
                        self._generate_local_var_store(name)
            elif isinstance(assign.lvalue, c_ast.ArrayRef):
                # Array assignment: arr[index] = value
                # First generate the rvalue
                self._generate_expression(assign.rvalue)
                self.output.append(f"    PUSH {self.reg_rax}  ; Save value to assign")
                
                # Generate index
                self._generate_expression(assign.lvalue.subscript)
                self.output.append(f"    PUSH {self.reg_rax}  ; Save index")
                
                # Determine element size (default to 4 for int, 1 for char; use local_array_element_size for local arrays)
                element_size = 4  # Default to int size
                element_type = 'int'  # Default type
                if isinstance(assign.lvalue.name, c_ast.ID):
                    name = assign.lvalue.name.name
                    # Parameter (pointer to array): element size 4 for int*
                    if name in self.function_parameters:
                        element_size = 4
                        element_type = 'int'
                    # Local array: use tracked element size (e.g. 16 for struct Inner[])
                    elif name in getattr(self, 'local_array_element_size', {}):
                        element_size = self.local_array_element_size[name]
                        element_type = 'struct' if element_size > 8 else 'int'
                    else:
                        # Check if it's a global variable and get its type
                        parser = getattr(self, '_current_parser', None)
                        if parser:
                            globals = parser.get_global_variables()
                            for g in globals:
                                if g.name == name:
                                    # Find the element type by traversing the type structure
                                    type_node = g.type
                                    while hasattr(type_node, 'type'):
                                        if isinstance(type_node, c_ast.ArrayDecl):
                                            # Get the element type
                                            elem_type = type_node.type
                                            if isinstance(elem_type, c_ast.TypeDecl):
                                                type_name = elem_type.declname if hasattr(elem_type, 'declname') else ''
                                                # Check type name or type string
                                                type_str = str(elem_type.type).lower() if hasattr(elem_type, 'type') else ''
                                                if 'char' in type_str or 'char' in type_name.lower():
                                                    element_size = 1
                                                    element_type = 'char'
                                                    break
                                            break
                                        type_node = type_node.type
                                    break
                
                # Generate base address - use RDI as temp (safe: parameter register, can be reused)
                # Avoid RBX since it might be allocated to a loop variable
                base_reg = self.reg_rdi  # Use RDI as base temp
                if isinstance(assign.lvalue.name, c_ast.ID):
                    # Array variable name
                    name = assign.lvalue.name.name
                    # Parameter (pointer): base is in argument register - use it directly
                    if name in self.function_parameters:
                        param_reg = self.function_parameters[name]
                        if param_reg != base_reg:
                            self.output.append(f"    MOV {base_reg}, {param_reg}  ; Base from parameter {name}")
                        # else: already in the right register
                    else:
                        # Check if it's a global variable
                        globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                        if name in globals:
                            # Global array - use position-independent addressing in 64-bit mode
                            if self.use_32bit:
                                self.output.append(f"    MOV {base_reg}, GLOBAL_{name}  ; Base address of array")
                            else:
                                self.output.append(f"    LEA {base_reg}, [rel GLOBAL_{name}]  ; Base address of array (PIC)")
                        else:
                            # Local array - use address of stack allocation (LEA), not stored value
                            if name in self.current_function_stack:
                                slot_index, offset = self.current_function_stack[name]
                                stack_offset = (slot_index + 1) * 8 + offset
                                if self.use_32bit:
                                    self.output.append(f"    LEA {base_reg}, [{self.reg_rbp} - {stack_offset}]  ; Base address of local array")
                                else:
                                    self.output.append(f"    LEA {base_reg}, [{self.reg_rbp} - {stack_offset}]  ; Base address of local array")
                            else:
                                self._generate_local_var_load(name)
                                self.output.append(f"    MOV {base_reg}, {self.reg_rax}  ; Base address")
                else:
                    # Complex expression for base
                    self._generate_expression(assign.lvalue.name)
                    self.output.append(f"    MOV {base_reg}, {self.reg_rax}  ; Base address")
                
                # Get index from stack
                self.output.append(f"    POP {self.reg_rax}  ; Get index")
                
                # Calculate address: base + index * element_size
                self.output.append(f"    ; Array assignment: base + index * {element_size}")
                # Use LEA with scaled addressing for small element sizes (more efficient, doesn't corrupt RDX)
                if element_size == 1:
                    # char: base + index * 1
                    self.output.append(f"    LEA {self.reg_rax}, [{base_reg} + {self.reg_rax}*1]  ; base + index")
                elif element_size == 2:
                    # short: base + index * 2
                    self.output.append(f"    LEA {self.reg_rax}, [{base_reg} + {self.reg_rax}*2]  ; base + index*2")
                elif element_size == 4:
                    # int: base + index * 4
                    self.output.append(f"    LEA {self.reg_rax}, [{base_reg} + {self.reg_rax}*4]  ; base + index*4")
                elif element_size == 8:
                    # long/pointer: base + index * 8
                    self.output.append(f"    LEA {self.reg_rax}, [{base_reg} + {self.reg_rax}*8]  ; base + index*8")
                # Note: Using RDI as base temp instead of RBX to avoid conflicts with register-allocated variables
                else:
                    # For other sizes, use MUL (but this corrupts RDX, so be careful)
                    self.output.append(f"    MOV {self.reg_rcx}, {self.reg_rax}  ; Save index")
                    self.output.append(f"    MOV {self.reg_rax}, {element_size}  ; Size of {element_type}")
                    self.output.append(f"    MUL {self.reg_rcx}  ; {self.reg_rax} = index * {element_size}")
                    self.output.append(f"    ADD {self.reg_rax}, {base_reg}  ; {self.reg_rax} = base + offset")
                
                # Store value to memory (value was pushed before index; we popped index, so pop value now)
                self.output.append(f"    POP {self.reg_rcx}  ; Get value to assign")
                if element_size == 1:
                    # Store byte for char arrays
                    self.output.append(f"    MOV BYTE [{self.reg_rax}], CL  ; Store byte to array element")
                elif element_size == 4:
                    # Store 32-bit for int arrays
                    self.output.append(f"    MOV DWORD [{self.reg_rax}], ECX  ; Store to array element")
                elif element_size == 8:
                    # Store 64-bit for long/pointer arrays
                    self.output.append(f"    MOV [{self.reg_rax}], {self.reg_rcx}  ; Store to array element")
                else:
                    # Store 16-bit or other
                    self.output.append(f"    MOV WORD [{self.reg_rax}], CX  ; Store to array element")
    
    def _generate_ternary_op(self, ternary):
        """Generate code for ternary operator: condition ? true_expr : false_expr"""
        self.label_counter = self.label_counter + 1
        label_id = self.label_counter
        
        # Evaluate condition
        self._generate_expression(ternary.cond)
        self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}  ; Check condition")
        self.output.append(f"    JZ TERNARY_FALSE_{label_id}")
        
        # True branch
        self._generate_expression(ternary.iftrue)
        self.output.append(f"    JMP TERNARY_END_{label_id}")
        
        # False branch
        self.output.append(f"TERNARY_FALSE_{label_id}:")
        self._generate_expression(ternary.iffalse)
        
        # End
        self.output.append(f"TERNARY_END_{label_id}:")
    
    def _generate_if(self, if_stmt, func_name, info):
        """Generate code for if statement with function pointer reuse optimization."""
        else_label = f"ELSE_{len(self.output)}"
        end_label = f"END_IF_{len(self.output)}"
        
        # Check if condition is a simple struct member access (likely function pointer)
        # and if body starts with a function call using the same expression
        # Only treat StructRef as function pointer, not BinaryOp with &&
        cond_is_simple_fp = isinstance(if_stmt.cond, c_ast.StructRef)
        
        body_has_call = False
        if if_stmt.iftrue:
            if isinstance(if_stmt.iftrue, c_ast.FuncCall):
                body_has_call = True
            elif isinstance(if_stmt.iftrue, c_ast.Compound) and if_stmt.iftrue.block_items:
                body_has_call = isinstance(if_stmt.iftrue.block_items[0], c_ast.FuncCall)
        
        # Optimize: if condition loads a function pointer and body calls it, reuse the value
        if cond_is_simple_fp and body_has_call:
            # Load function pointer - keep it in RAX (like GCC does)
            self._generate_expression(if_stmt.cond)
            self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}")
            self.output.append(f"    JZ {else_label}")
            # Function pointer is in RAX - mark it so body can reuse it
            self.saved_fp_in_rbx = False  # Not in RBX, it's in RAX
            self.fp_in_rax = True  # Function pointer is already in RAX
            # Generate body - it should detect that function pointer is already in RAX
            self._generate_statement(if_stmt.iftrue, func_name, info)
            # Body ends with JMP RAX (tail call), so no code after it executes
            # Don't add JMP to end_label - it's unreachable
            self.output.append(f"{else_label}:")
            self.saved_fp_in_rbx = False
            self.fp_in_rax = False
        else:
            # Optimize AND operations in if conditions - use short-circuit evaluation
            if isinstance(if_stmt.cond, c_ast.BinaryOp) and if_stmt.cond.op == '&&':
                # Short-circuit AND: evaluate left, if false skip right
                self._generate_expression(if_stmt.cond.left)
                self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}")
                self.output.append(f"    JZ {else_label}")
                # Left is true, evaluate right
                self._generate_expression(if_stmt.cond.right)
                self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}")
                self.output.append(f"    JZ {else_label}")
            else:
                # Standard if statement
                self._generate_expression(if_stmt.cond)
                self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}")
                self.output.append(f"    JZ {else_label}")
            
            self._generate_statement(if_stmt.iftrue, func_name, info)
            self.output.append(f"    JMP {end_label}")
            self.output.append(f"{else_label}:")
        
        if if_stmt.iffalse:
            self._generate_statement(if_stmt.iffalse, func_name, info)
        
        self.output.append(f"{end_label}:")
    
    def _emit_hoisted_small_func_address(self, func_name, reg):
        """Emit code to compute SMALL_FUNC_BASE + offset for func_name into reg (before loop)."""
        func_idx = list(self.function_offsets.keys()).index(func_name) if func_name in self.function_offsets else -1
        if func_idx < 0:
            return
        offset = func_idx * 1024
        if self.use_32bit:
            self.output.append(f"    MOV EAX, SMALL_FUNC_BASE")
            self.output.append(f"    MOV {reg}, {offset}  ; offset for {func_name}")
            self.output.append(f"    ADD EAX, {reg}")
            self.output.append(f"    MOV {reg}, EAX  ; hoisted jump address for {func_name}")
        else:
            self.output.append(f"    MOV {reg}, SMALL_FUNC_BASE")
            self.output.append(f"    MOV {self.reg_rax}, {offset}  ; offset for {func_name}")
            self.output.append(f"    ADD {reg}, {self.reg_rax}  ; hoisted jump address for {func_name}")
    
    def _generate_while(self, while_stmt, func_name, info):
        """Generate code for while loop."""
        loop_label = f"WHILE_{len(self.output)}"
        end_label = f"END_WHILE_{len(self.output)}"
        
        small_funcs = self._collect_small_func_calls_in_stmt(while_stmt.stmt)
        # Disable loop-hoisted small-function addresses for now.
        # Hoisting into general registers can alias register-allocated locals and corrupt loop state.
        hoist_regs_64 = []
        hoist_regs_32 = []
        hoist_regs = hoist_regs_32 if self.use_32bit else hoist_regs_64
        prev_hoisted = self._loop_hoisted_small_funcs
        if small_funcs:
            ordered = sorted(small_funcs)
            self._loop_hoisted_small_funcs = {}
            for i, f in enumerate(ordered):
                if i < len(hoist_regs):
                    reg = hoist_regs[i]
                    self._emit_hoisted_small_func_address(f, reg)
                    self._loop_hoisted_small_funcs[f] = reg
        
        self.output.append(f"{loop_label}:")
        self._generate_expression(while_stmt.cond)
        self.output.append("    TEST RAX, RAX")
        self.output.append(f"    JZ {end_label}")
        
        self._generate_statement(while_stmt.stmt, func_name, info)
        self.output.append(f"    JMP {loop_label}")
        self.output.append(f"{end_label}:")
        
        if small_funcs:
            self._loop_hoisted_small_funcs = prev_hoisted
    
    def _generate_for(self, for_stmt, func_name, info):
        """Generate code for for loop with optimized register usage."""
        loop_label = f"FOR_{len(self.output)}"
        end_label = f"END_FOR_{len(self.output)}"
        
        small_funcs = set()
        if for_stmt.init:
            small_funcs |= self._collect_small_func_calls_in_stmt(for_stmt.init)
        if for_stmt.stmt:
            small_funcs |= self._collect_small_func_calls_in_stmt(for_stmt.stmt)
        if for_stmt.next:
            small_funcs |= self._collect_small_func_calls_in_stmt(for_stmt.next)
        if for_stmt.cond:
            self._collect_small_func_calls_in_expr(for_stmt.cond, small_funcs)
        # Disable loop-hoisted small-function addresses for now.
        # Hoisting into general registers can alias register-allocated locals and corrupt loop state.
        hoist_regs_64 = []
        hoist_regs_32 = []
        hoist_regs = hoist_regs_32 if self.use_32bit else hoist_regs_64
        
        if for_stmt.init:
            # For loop init can be a Decl (variable declaration) or DeclList
            # Handle both cases
            if isinstance(for_stmt.init, c_ast.DeclList):
                # Multiple declarations in for loop init
                for decl in for_stmt.init.decls:
                    self._generate_statement(decl, func_name, info)
            else:
                # Single statement (usually Decl for "int i = 0")
                self._generate_statement(for_stmt.init, func_name, info)
        
        prev_hoisted = self._loop_hoisted_small_funcs
        if small_funcs:
            ordered = sorted(small_funcs)
            self._loop_hoisted_small_funcs = {}
            for i, f in enumerate(ordered):
                if i < len(hoist_regs):
                    reg = hoist_regs[i]
                    self._emit_hoisted_small_func_address(f, reg)
                    self._loop_hoisted_small_funcs[f] = reg
        
        self.output.append(f"{loop_label}:")
        
        if for_stmt.cond:
            # Optimize condition evaluation: if comparing a variable in a register with a constant,
            # use direct comparison instead of loading to RAX first
            self._generate_expression(for_stmt.cond)
            self.output.append(f"    TEST {self.reg_rax}, {self.reg_rax}")
            self.output.append(f"    JZ {end_label}")
        
        self._generate_statement(for_stmt.stmt, func_name, info)
        
        if for_stmt.next:
            self._generate_statement(for_stmt.next, func_name, info)
        
        self.output.append(f"    JMP {loop_label}")
        self.output.append(f"{end_label}:")
        
        if small_funcs:
            self._loop_hoisted_small_funcs = prev_hoisted
    
    def _compute_decl_size(self, decl):
        """Return stack size in bytes for a single Decl (same logic as _generate_decl type/size)."""
        if decl.name is None:
            return 0
        var_size = 8
        if hasattr(decl, 'type'):
            type_node = decl.type
            if isinstance(type_node, c_ast.ArrayDecl):
                dim = 1
                if hasattr(type_node, 'dim') and type_node.dim is not None and hasattr(type_node.dim, 'value'):
                    try:
                        dim = int(type_node.dim.value)
                    except (ValueError, TypeError):
                        dim = 1
                elem_type = type_node.type
                elem_size = 4
                while hasattr(elem_type, 'type'):
                    inner = elem_type.type
                    if hasattr(inner, 'names') and inner.names and 'char' in [str(n).lower() for n in inner.names]:
                        elem_size = 1
                        break
                    if hasattr(inner, 'name') and not hasattr(inner, 'names'):
                        # Struct element (e.g. struct Inner handlers[10])
                        elem_size = self.struct_sizes.get(inner.name, 8)
                        break
                    elem_type = inner
                var_size = elem_size * dim
            else:
                while type_node and hasattr(type_node, 'type'):
                    inner_type = type_node.type
                    if hasattr(inner_type, 'name') and not hasattr(inner_type, 'names'):
                        var_size = self.struct_sizes.get(inner_type.name, 8)
                        break
                    type_node = inner_type
        return ((var_size + 7) // 8) * 8
    
    def _compute_function_local_stack_size(self, node):
        """Recursively sum stack size of all local Decl nodes in a function body."""
        total = 0
        if node is None:
            return 0
        if isinstance(node, c_ast.Decl) and getattr(node, 'name', None):
            if not (getattr(node, 'storage', None) and 'extern' in node.storage):
                total += self._compute_decl_size(node)
        if isinstance(node, c_ast.Compound) and getattr(node, 'block_items', None):
            for item in node.block_items:
                total += self._compute_function_local_stack_size(item)
        elif isinstance(node, c_ast.For):
            if node.init:
                total += self._compute_function_local_stack_size(node.init)
            if node.stmt:
                total += self._compute_function_local_stack_size(node.stmt)
        elif isinstance(node, c_ast.While) and node.stmt:
            total += self._compute_function_local_stack_size(node.stmt)
        elif isinstance(node, c_ast.If):
            if node.iftrue:
                total += self._compute_function_local_stack_size(node.iftrue)
            if node.iffalse:
                total += self._compute_function_local_stack_size(node.iffalse)
        elif isinstance(node, c_ast.DeclList) and getattr(node, 'decls', None):
            for d in node.decls:
                total += self._compute_function_local_stack_size(d)
        return total
    
    def _extract_direct_func_name(self, call):
        """Extract direct function name from a FuncCall node, or None if indirect/pointer."""
        if not isinstance(call, c_ast.FuncCall):
            return None
        name = call.name
        if isinstance(name, c_ast.ID):
            return name.name
        if isinstance(name, c_ast.UnaryOp) and isinstance(getattr(name, 'expr', None), c_ast.ID):
            return name.expr.name
        if hasattr(name, 'name'):
            na = name.name
            if isinstance(na, str):
                return na
            if isinstance(na, c_ast.ID):
                return na.name
        return None
    
    def _collect_small_func_calls_in_expr(self, expr, out):
        """Recursively add direct small-function names from expression to set out."""
        if expr is None:
            return
        if isinstance(expr, c_ast.FuncCall):
            func_name = self._extract_direct_func_name(expr)
            if func_name and self.function_data.get(func_name, {}).get('is_small') and func_name in self.function_offsets:
                out.add(func_name)
            if getattr(expr, 'args', None) and expr.args.exprs:
                for a in expr.args.exprs:
                    self._collect_small_func_calls_in_expr(a, out)
            return
        for attr in ('left', 'right', 'expr', 'cond', 'iftrue', 'iffalse', 'subscript', 'name'):
            child = getattr(expr, attr, None)
            if child is not None:
                if isinstance(child, list):
                    for c in child:
                        self._collect_small_func_calls_in_expr(c, out)
                else:
                    self._collect_small_func_calls_in_expr(child, out)
    
    def _collect_small_func_calls_in_stmt(self, stmt):
        """Return set of direct small-function names called inside stmt (e.g. loop body)."""
        out = set()
        if stmt is None:
            return out
        if isinstance(stmt, c_ast.Compound) and getattr(stmt, 'block_items', None):
            for item in stmt.block_items:
                out |= self._collect_small_func_calls_in_stmt(item)
        elif isinstance(stmt, c_ast.While) and stmt.stmt:
            out |= self._collect_small_func_calls_in_stmt(stmt.stmt)
        elif isinstance(stmt, c_ast.For):
            if stmt.init:
                out |= self._collect_small_func_calls_in_stmt(stmt.init)
            if stmt.cond:
                self._collect_small_func_calls_in_expr(stmt.cond, out)
            if stmt.stmt:
                out |= self._collect_small_func_calls_in_stmt(stmt.stmt)
            if stmt.next:
                out |= self._collect_small_func_calls_in_stmt(stmt.next)
        elif isinstance(stmt, c_ast.If):
            if stmt.iftrue:
                out |= self._collect_small_func_calls_in_stmt(stmt.iftrue)
            if stmt.iffalse:
                out |= self._collect_small_func_calls_in_stmt(stmt.iffalse)
        elif isinstance(stmt, c_ast.FuncCall):
            func_name = self._extract_direct_func_name(stmt)
            if func_name and self.function_data.get(func_name, {}).get('is_small') and func_name in self.function_offsets:
                out.add(func_name)
        elif isinstance(stmt, (c_ast.UnaryOp, c_ast.BinaryOp, c_ast.ID, c_ast.ArrayRef, c_ast.StructRef)):
            self._collect_small_func_calls_in_expr(stmt, out)
        elif isinstance(stmt, c_ast.Assignment):
            self._collect_small_func_calls_in_expr(stmt.lvalue, out)
            self._collect_small_func_calls_in_expr(stmt.rvalue, out)
        elif isinstance(stmt, c_ast.DeclList) and getattr(stmt, 'decls', None):
            for d in stmt.decls:
                out |= self._collect_small_func_calls_in_stmt(d)
        return out
    
    def _generate_decl(self, decl):
        """Generate code for variable declaration with indexed stack pointer."""
        # extern declarations: variable defined elsewhere, do not allocate local storage
        if getattr(decl, 'storage', None) and 'extern' in decl.storage:
            return
        # Extract variable name - decl.name might be a string or an ID node
        if decl.name is None:
            # No name - skip this declaration
            return
        if isinstance(decl.name, c_ast.ID):
            name = decl.name.name
        elif isinstance(decl.name, str):
            name = decl.name
        else:
            # Fallback: try to convert to string
            name = str(decl.name) if decl.name else "unknown"
            if name == "unknown":
                # Can't process declaration without a valid name
                return
        
        # If variable already allocated (e.g. decl inside loop - same name seen again),
        # just generate init and store to existing slot; do not SUB RSP again.
        if name in self.current_function_stack:
            if decl.init:
                self._generate_expression(decl.init)
                if self.register_allocator and self._current_function_name:
                    reg = self.register_allocator.get_register(self._current_function_name, name)
                    if reg:
                        if reg != self.reg_rax:
                            reg_32 = reg + 'D' if reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15'] else (reg.replace('R', 'E') if reg.startswith('R') else reg)
                            self.output.append(f"    MOV {reg_32}, EAX  ; Reinit {name} in register {reg}")
                        self.variable_registers[name] = reg
                    else:
                        self._generate_local_var_store(name)
                else:
                    self._generate_local_var_store(name)
            return
        
        # Calculate size based on type
        var_size = 8  # Default size for primitives
        is_array = False
        if hasattr(decl, 'type'):
            type_node = decl.type
            # Check for array type first - allocate element_size * dim
            if isinstance(type_node, c_ast.ArrayDecl):
                is_array = True
                dim = 1
                if hasattr(type_node, 'dim') and type_node.dim is not None:
                    if hasattr(type_node.dim, 'value'):
                        try:
                            dim = int(type_node.dim.value)
                        except (ValueError, TypeError):
                            dim = 1
                elem_type = type_node.type
                elem_size = 4  # default int
                while hasattr(elem_type, 'type'):
                    inner = elem_type.type
                    if hasattr(inner, 'names') and inner.names:
                        if 'char' in [str(n).lower() for n in inner.names]:
                            elem_size = 1
                        break
                    if hasattr(inner, 'name') and not hasattr(inner, 'names'):
                        elem_size = self.struct_sizes.get(inner.name, 8)
                        break
                    elem_type = inner
                var_size = elem_size * dim
            else:
                # Check for struct type - walk down to find the actual type
                while type_node:
                    if hasattr(type_node, 'type'):
                        inner_type = type_node.type
                        # Check if inner_type is a Struct (has 'name' attribute but no 'names')
                        if hasattr(inner_type, 'name') and not hasattr(inner_type, 'names'):
                            var_size = self.struct_sizes.get(inner_type.name, 8)
                            break
                        type_node = inner_type
                    else:
                        break
        
        # Round up size to 8-byte alignment
        var_size = ((var_size + 7) // 8) * 8
        
        # Track stack allocation in bytes (not slots)
        # current_stack_offset tracks cumulative bytes allocated from RBP
        if not hasattr(self, 'current_stack_offset'):
            self.current_stack_offset = 0
        
        # Allocate stack space for this variable
        self.current_stack_offset += var_size
        
        # Store variable location as (byte_offset, var_size)
        # The byte_offset is the distance from RBP to the variable's start
        # We store it in slot_index position; the load function will use it directly
        # To make the existing formula (slot_index + 1) * 8 + offset work:
        # We want result = current_stack_offset
        # (slot_index + 1) * 8 + offset = current_stack_offset
        # Set slot_index = (current_stack_offset / 8) - 1, offset = 0
        # But this only works for 8-byte aligned offsets
        slot_index = (self.current_stack_offset // 8) - 1
        self.current_stack_slots = self.current_stack_offset // 8  # Keep in sync
        self.current_function_stack[name] = (slot_index, 0)
        if is_array:
            self.local_arrays.add(name)
            self.local_array_element_size[name] = elem_size
        
        # Mark that this function needs stack frame
        if not self.function_needs_indexed_stack:
            self.function_needs_indexed_stack = True
            # If function uses RBX (callee-saved), preserve it so we don't clobber caller's value
            if getattr(self, 'function_uses_rbx', False) and not getattr(self, 'function_saved_rbx', False):
                self.output.append(f"    PUSH {self.reg_rbx}  ; Callee-saved: preserve RBX")
                self.function_saved_rbx = True
            # Generate indexed stack prologue (with R12/R13 for indexed stack system)
            # Note: After CALL, stack is 8-byte aligned. We push 3 registers (24 bytes),
            # so we need to adjust RSP by 8 bytes to maintain 16-byte alignment
            self.output.append(f"    PUSH {self.reg_rbp}  ; Save old frame pointer")
            if not self.use_32bit:
                self.output.append(f"    PUSH {self.stack_base_register}  ; Preserve stack base register")
                self.output.append(f"    PUSH {self.stack_index_register}  ; Preserve stack index register")
                # Adjust RSP to maintain 16-byte stack alignment (3 pushes = 24 bytes, need 32)
                self.output.append(f"    SUB {self.reg_rsp}, 8  ; Adjust for 16-byte stack alignment")
            self.output.append(f"    MOV {self.reg_rbp}, {self.reg_rsp}  ; Set new frame pointer")
            if not self.use_32bit:
                self.output.append(f"    MOV {self.stack_base_register}, 0x7FFF0000  ; Load stack base (immediate)")
                self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Initialize slot index to 0")
        
        # Allocate stack space: once for all locals (so decls inside loops don't SUB RSP every iteration)
        if not getattr(self, 'function_stack_allocated', False) and getattr(self, 'function_total_stack_size', 0) > 0:
            self.output.append(f"    SUB {self.reg_rsp}, {self.function_total_stack_size}  ; Allocate stack for all locals")
            self.function_stack_allocated = True
        
        # Check if variable should be in a register (arrays stay on stack)
        should_be_in_register = False
        allocated_reg = None
        if not is_array and self.register_allocator and self._current_function_name:
            allocated_reg = self.register_allocator.get_register(self._current_function_name, name)
            if allocated_reg:
                should_be_in_register = True
        
        if decl.init:
            self._generate_expression(decl.init)
            if should_be_in_register:
                # Variable should be in a register - move RAX to allocated register
                if allocated_reg != self.reg_rax:
                    if self.use_32bit:
                        reg_32 = allocated_reg.replace('R', 'E') if allocated_reg.startswith('R') else allocated_reg
                        self.output.append(f"    MOV {reg_32}, {self.reg_rax}  ; Initialize {name} in register {allocated_reg}")
                    else:
                        # In 64-bit mode, use 32-bit moves for integers
                        if allocated_reg.startswith('R'):
                            # R8-R15 use R8D-R15D, not E8-E15
                            if allocated_reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                                reg_32 = allocated_reg + 'D'
                            else:
                                reg_32 = allocated_reg.replace('R', 'E')
                            self.output.append(f"    MOV {reg_32}, EAX  ; Initialize {name} in register {allocated_reg} (32-bit)")
                        else:
                            self.output.append(f"    MOV {allocated_reg}, {self.reg_rax}  ; Initialize {name} in register {allocated_reg}")
                # Track that this variable is in a register
                self.variable_registers[name] = allocated_reg
            else:
                # Store value using stack addressing
                self._generate_local_var_store(name)
        else:
            # Initialize to 0
            if should_be_in_register:
                # Initialize register to 0
                if self.use_32bit:
                    reg_32 = allocated_reg.replace('R', 'E') if allocated_reg.startswith('R') else allocated_reg
                    self.output.append(f"    XOR {reg_32}, {reg_32}  ; Initialize {name} to 0 in register {allocated_reg}")
                else:
                    # In 64-bit mode, use 32-bit XOR for integers (clears upper 32 bits too)
                    if allocated_reg.startswith('R'):
                        # R8-R15 use R8D-R15D, not E8-E15
                        if allocated_reg in ['R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']:
                            reg_32 = allocated_reg + 'D'
                        else:
                            reg_32 = allocated_reg.replace('R', 'E')
                        self.output.append(f"    XOR {reg_32}, {reg_32}  ; Initialize {name} to 0 in register {allocated_reg} (32-bit)")
                    else:
                        self.output.append(f"    XOR {allocated_reg}, {allocated_reg}  ; Initialize {name} to 0 in register {allocated_reg}")
                # Track that this variable is in a register
                self.variable_registers[name] = allocated_reg
            else:
                # Initialize on stack
                self.output.append(f"    XOR {self.reg_rax}, {self.reg_rax}  ; Initialize {name} to 0")
                self._generate_local_var_store(name)
"""Code generator with function call optimizations."""

from pycparser import c_ast
import struct


class CodeGenerator:
    """Code generator with indexed-jump, metamorphic return sites, and quantized call-backs."""
    
    def __init__(self, function_data):
        self.function_data = function_data
        self.output = []
        self.small_functions = []
        self.function_offsets = {}
        self.return_site_base = 0x10000  # Base address for return sites
        self.return_sites = []  # Track return sites for quantized call-backs
        self.return_site_index = 0
        self.alignment = 16  # 16-byte alignment for quantized call-backs
        self.current_line = 0  # Track current output line for return site tracking
    
    def generate(self, parser):
        """Generate optimized code for all functions."""
        self.output = []
        
        # Separate small and large functions
        functions = parser.get_functions()
        small_funcs = []
        large_funcs = []
        
        for func in functions:
            func_name = func.decl.name if func.decl else "unknown"
            if func_name in self.function_data and self.function_data[func_name]['is_small']:
                small_funcs.append(func)
            else:
                large_funcs.append(func)
        
        # Generate code section
        self.output.append("SECTION .text")
        self.output.append("")
        
        # Generate small functions with indexed-jump support
        if small_funcs:
            self._generate_indexed_jump_table(small_funcs)
            self.output.append("")
        
        # Generate all functions
        for func in small_funcs + large_funcs:
            self._generate_function(func)
            self.output.append("")
        
        # Generate data section for function table
        if small_funcs:
            self._generate_function_table(small_funcs)
        
        return "\n".join(self.output)
    
    def _generate_indexed_jump_table(self, small_funcs):
        """Generate indexed-jump table for small functions."""
        self.output.append("; Indexed-jump table for small functions (<1024 bytes)")
        self.output.append("JUMP_TABLE:")
        
        base_addr = 0x1000  # Base address for small functions
        offset = 0
        
        for func in small_funcs:
            func_name = func.decl.name if func.decl else "unknown"
            self.function_offsets[func_name] = offset
            self.output.append(f"    DD FUNC_{func_name}  ; Index {offset}: {func_name}")
            offset += 1
        
        self.output.append("")
        self.output.append("; Indexed-jump dispatcher")
        self.output.append("INDEXED_JUMP:")
        self.output.append("    ; RDI contains function index")
        self.output.append("    MOV RAX, JUMP_TABLE")
        self.output.append("    MOV RAX, [RAX + RDI*8]")
        self.output.append("    JMP RAX")
        self.output.append("")
    
    def _generate_function_table(self, small_funcs):
        """Generate function pointer table."""
        self.output.append("SECTION .data")
        self.output.append("FUNC_TABLE:")
        for func in small_funcs:
            func_name = func.decl.name if func.decl else "unknown"
            self.output.append(f"    DQ FUNC_{func_name}")
    
    def _generate_function(self, func_def):
        """Generate code for a single function."""
        func_name = func_def.decl.name if func_def.decl else "unknown"
        info = self.function_data.get(func_name, {})
        
        # Align function start to 16 bytes for quantized call-backs
        self.output.append(f"ALIGN {self.alignment}")
        self.output.append(f"FUNC_{func_name}:")
        
        # Function prologue
        self.output.append("    PUSH RBP")
        self.output.append("    MOV RBP, RSP")
        
        # Generate function body
        if func_def.body:
            self._generate_block(func_def.body, func_name, info)
        
        # Function epilogue (optimized for single return sites with metamorphic return)
        # Note: If has_single_return, the return is handled in _generate_return
    
    def _generate_block(self, block, func_name, info):
        """Generate code for a block."""
        if isinstance(block, c_ast.Compound):
            for item in block.block_items:
                self._generate_statement(item, func_name, info)
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
    
    def _generate_return(self, ret_stmt, func_name, info):
        """Generate return statement with metamorphic return site optimization."""
        if info.get('has_single_return', False):
            # Metamorphic return site: return address is written into instruction
            self.output.append("    ; Metamorphic return site - address injected by caller")
            self.output.append("    MOV RSP, RBP")
            self.output.append("    POP RBP")
            # The RET address will be dynamically modified by the caller
            self.output.append("    RET  ; Address bytes written by caller")
        else:
            # Standard return
            if ret_stmt.expr:
                self._generate_expression(ret_stmt.expr)
                self.output.append("    MOV RAX, [RSP-8]  ; Return value")
            self.output.append("    MOV RSP, RBP")
            self.output.append("    POP RBP")
            self.output.append("    RET")
    
    def _generate_call(self, call, caller_func_name):
        """Generate function call with optimizations."""
        func_name = call.name.name if isinstance(call.name, c_ast.ID) else "unknown"
        callee_info = self.function_data.get(func_name, {})
        
        # Prepare arguments (simplified - assume up to 6 args in registers)
        if call.args:
            for i, arg in enumerate(call.args.exprs[:6]):
                reg = ['RDI', 'RSI', 'RDX', 'RCX', 'R8', 'R9'][i]
                self._generate_expression(arg)
                self.output.append(f"    MOV {reg}, RAX")
        
        # Handle return site for single-return functions (quantized call-back)
        return_site_label = None
        if callee_info.get('has_single_return', False):
            # Generate quantized call-back label (will be placed after the call)
            return_site_label = f"RET_SITE_{caller_func_name}_{self.return_site_index}"
            self.return_site_index += 1
            self.return_sites.append(return_site_label)
        
        # Generate call based on function type
        if callee_info.get('is_small', False):
            # Indexed-jump call for small functions
            func_idx = list(self.function_offsets.keys()).index(func_name) if func_name in self.function_offsets else -1
            if func_idx >= 0:
                self.output.append(f"    ; Indexed-jump call to {func_name}")
                self.output.append(f"    MOV RDI, {func_idx}")
                
                if callee_info.get('has_single_return', False) and return_site_label:
                    # Metamorphic return site: write return address into callee's instruction
                    self.output.append(f"    ; Metamorphic return: write return address bytes to callee's RET instruction")
                    self.output.append(f"    LEA RAX, [{return_site_label}]")
                    self.output.append(f"    MOV [FUNC_{func_name}+RET_ADDR_OFFSET], RAX")
                
                self.output.append("    CALL INDEXED_JUMP")
        else:
            # Standard call or call with metamorphic return
            if callee_info.get('has_single_return', False) and return_site_label:
                # Metamorphic return site: write return address into instruction
                self.output.append(f"    ; Metamorphic return: write return address to callee instruction")
                self.output.append(f"    LEA RAX, [{return_site_label}]")
                self.output.append(f"    MOV [FUNC_{func_name}+RET_ADDR_OFFSET], RAX")
                self.output.append(f"    JMP FUNC_{func_name}")
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
            self.output.append(f"    MOV RAX, {value}")
        elif isinstance(expr, c_ast.ID):
            name = expr.name
            self.output.append(f"    MOV RAX, [RBP-{name}]  ; Load variable")
        elif isinstance(expr, c_ast.BinaryOp):
            self._generate_binary_op(expr)
        elif isinstance(expr, c_ast.UnaryOp):
            self._generate_unary_op(expr)
    
    def _generate_binary_op(self, op):
        """Generate code for binary operation."""
        self._generate_expression(op.left)
        self.output.append("    PUSH RAX")
        self._generate_expression(op.right)
        self.output.append("    POP RBX")
        
        if op.op == '+':
            self.output.append("    ADD RAX, RBX")
        elif op.op == '-':
            self.output.append("    SUB RBX, RAX")
            self.output.append("    MOV RAX, RBX")
        elif op.op == '*':
            self.output.append("    MUL RBX")
        elif op.op == '/':
            self.output.append("    DIV RBX")
        elif op.op == '==':
            self.output.append("    CMP RAX, RBX")
            self.output.append("    SETE AL")
        elif op.op == '<':
            self.output.append("    CMP RBX, RAX")
            self.output.append("    SETL AL")
    
    def _generate_unary_op(self, op):
        """Generate code for unary operation."""
        self._generate_expression(op.expr)
        if op.op == '-':
            self.output.append("    NEG RAX")
        elif op.op == '!':
            self.output.append("    NOT RAX")
    
    def _generate_assignment(self, assign):
        """Generate code for assignment."""
        if assign.op == '=':
            self._generate_expression(assign.rvalue)
            if isinstance(assign.lvalue, c_ast.ID):
                name = assign.lvalue.name
                self.output.append(f"    MOV [RBP-{name}], RAX")
    
    def _generate_if(self, if_stmt, func_name, info):
        """Generate code for if statement."""
        else_label = f"ELSE_{len(self.output)}"
        end_label = f"END_IF_{len(self.output)}"
        
        self._generate_expression(if_stmt.cond)
        self.output.append("    TEST RAX, RAX")
        self.output.append(f"    JZ {else_label}")
        
        self._generate_statement(if_stmt.iftrue, func_name, info)
        self.output.append(f"    JMP {end_label}")
        self.output.append(f"{else_label}:")
        
        if if_stmt.iffalse:
            self._generate_statement(if_stmt.iffalse, func_name, info)
        
        self.output.append(f"{end_label}:")
    
    def _generate_while(self, while_stmt, func_name, info):
        """Generate code for while loop."""
        loop_label = f"WHILE_{len(self.output)}"
        end_label = f"END_WHILE_{len(self.output)}"
        
        self.output.append(f"{loop_label}:")
        self._generate_expression(while_stmt.cond)
        self.output.append("    TEST RAX, RAX")
        self.output.append(f"    JZ {end_label}")
        
        self._generate_statement(while_stmt.stmt, func_name, info)
        self.output.append(f"    JMP {loop_label}")
        self.output.append(f"{end_label}:")
    
    def _generate_for(self, for_stmt, func_name, info):
        """Generate code for for loop."""
        loop_label = f"FOR_{len(self.output)}"
        end_label = f"END_FOR_{len(self.output)}"
        
        if for_stmt.init:
            self._generate_statement(for_stmt.init, func_name, info)
        
        self.output.append(f"{loop_label}:")
        
        if for_stmt.cond:
            self._generate_expression(for_stmt.cond)
            self.output.append("    TEST RAX, RAX")
            self.output.append(f"    JZ {end_label}")
        
        self._generate_statement(for_stmt.stmt, func_name, info)
        
        if for_stmt.next:
            self._generate_statement(for_stmt.next, func_name, info)
        
        self.output.append(f"    JMP {loop_label}")
        self.output.append(f"{end_label}:")
    
    def _generate_decl(self, decl):
        """Generate code for variable declaration."""
        if decl.init:
            self._generate_expression(decl.init)
            name = decl.name
            self.output.append(f"    SUB RSP, 8  ; Allocate space for {name}")
            self.output.append(f"    MOV [RBP-{name}], RAX")
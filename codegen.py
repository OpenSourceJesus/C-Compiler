"""Code generator with function call optimizations."""

from pycparser import c_ast
import struct


class CodeGenerator:
    """Code generator with indexed-jump, metamorphic return sites, quantized call-backs, and SIMD bit-packing."""
    
    def __init__(self, function_data, global_var_data=None):
        self.function_data = function_data
        self.global_var_data = global_var_data or {'packed_vars': [], 'bit_positions': {}, 'total_bits_used': 0}
        self.output = []
        self.small_functions = []
        self.function_offsets = {}
        self.return_site_base = 0x10000  # Base address for return sites
        self.return_sites = []  # Track return sites for quantized call-backs
        self.return_site_index = 0
        self.alignment = 16  # 16-byte alignment for quantized call-backs
        self.current_line = 0  # Track current output line for return site tracking
        self.simd_register = 'xmm15'  # Last SIMD register for bit-packing
        
        # Indexed stack pointer system (16-byte intervals)
        self.stack_slot_size = 16  # 16-byte intervals
        self.stack_base_register = 'R12'  # Base address register for stack
        self.stack_index_register = 'R13'  # Index register (stores slot index, fits in 32 bits)
        self.current_function_stack = {}  # Track local variables: {name: (slot_index, offset)}
        self.current_stack_slots = 0  # Number of 16-byte slots allocated in current function
        self.stack_base_address = 'STACK_BASE'  # Symbol for stack base address
    
    def generate(self, parser):
        """Generate optimized code for all functions."""
        self.output = []
        self._current_parser = parser  # Store parser reference for variable lookup
        
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
        
        # Generate initialization code for SIMD bit-packing
        if self.global_var_data['packed_vars']:
            self._generate_simd_packing_init()
            self.output.append("")
        
        # Generate code section
        self.output.append("SECTION .text")
        self.output.append("")
        
        # Generate main entry point that calls initialization
        if self.global_var_data['packed_vars']:
            self.output.append("; Program entry point")
            self.output.append("_start:")
            self.output.append("    CALL _init_simd_packing  ; Initialize SIMD bit-packing")
            self.output.append("")
        
        # Generate small functions with indexed-jump support
        if small_funcs:
            self._generate_indexed_jump_table(small_funcs)
            self.output.append("")
        
        # Generate all functions
        for func in small_funcs + large_funcs:
            self._generate_function(func)
            self.output.append("")
        
        # Generate data section for function table and global variables
        self._generate_data_section(parser)
        
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
    
    def _generate_data_section(self, parser):
        """Generate data section for global variables."""
        globals = parser.get_global_variables()
        if not globals:
            return
        
        self.output.append("SECTION .data")
        self.output.append("")
        
        packed_var_names = {var['name'] for var in self.global_var_data['packed_vars']}
        
        for var in globals:
            var_name = var.name if var.name else None
            if not var_name:
                continue
            
            # Only generate data for non-packed variables
            # Packed variables are stored in SIMD register
            if var_name not in packed_var_names:
                # Regular global variable
                self.output.append(f"GLOBAL_{var_name}:")
                if var.init:
                    # Has initializer
                    if isinstance(var.init, c_ast.Constant):
                        value = var.init.value
                        self.output.append(f"    DD {value}  ; {var_name}")
                    else:
                        self.output.append(f"    DD 0  ; {var_name} (initialized at runtime)")
                else:
                    self.output.append(f"    DD 0  ; {var_name}")
            else:
                # Packed variable - still need a storage location for initialization
                # but it will be packed into SIMD register
                self.output.append(f"GLOBAL_{var_name}:")
                if var.init:
                    if isinstance(var.init, c_ast.Constant):
                        value = var.init.value
                        self.output.append(f"    DB {value}  ; {var_name} (packed into SIMD register)")
                    else:
                        self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
                else:
                    self.output.append(f"    DB 0  ; {var_name} (packed into SIMD register)")
        
        self.output.append("")
    
    def _generate_simd_packing_init(self):
        """Generate initialization code to pack global variables into SIMD register."""
        self.output.append("; SIMD Bit-Packing: Pack global variables (1-7 bits) into last SIMD register")
        self.output.append("; This register (xmm15) is typically ignored by standard compilers")
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
            self.output.append(f"    MOVZX RAX, BYTE [GLOBAL_{var_name}]  ; Load {var_name}")
            self.output.append(f"    ; Extract and mask to {bits} bits")
            self.output.append(f"    AND RAX, {(1 << bits) - 1}  ; Mask to {bits} bits")
            
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
        """Generate inline assembly to access a packed variable from SIMD register.
        
        Uses direct SIMD register access for zero-latency operations, avoiding
        memory reads that could stall the pipeline during interrupt callbacks.
        """
        if var_name not in self.global_var_data['bit_positions']:
            return None  # Not a packed variable
        
        start_bit, bits = self.global_var_data['bit_positions'][var_name]
        mask = (1 << bits) - 1
        
        if is_write:
            # Write: extract value, modify, pack back
            # Zero-latency: all operations on registers, no memory access
            self.output.append(f"    ; Zero-latency write to packed variable {var_name} (bits {start_bit}-{start_bit+bits-1})")
            self.output.append(f"    ; Direct SIMD register access - no memory stall")
            # Save the value to write (it's in value_reg, typically RAX)
            self.output.append(f"    PUSH {value_reg}  ; Save value to write")
            self.output.append(f"    MOVQ RAX, {self.simd_register}  ; Load packed register (register-to-register)")
            self.output.append(f"    ; Clear old value bits")
            mask_shifted = mask << start_bit
            self.output.append(f"    MOV RBX, {mask_shifted}")
            self.output.append(f"    NOT RBX  ; Invert mask")
            self.output.append(f"    AND RAX, RBX  ; Clear bits for {var_name}")
            self.output.append(f"    ; Insert new value")
            self.output.append(f"    POP RBX  ; Restore value to write")
            self.output.append(f"    AND RBX, {mask}  ; Mask to {bits} bits")
            self.output.append(f"    SHL RBX, {start_bit}  ; Shift to position")
            self.output.append(f"    OR RAX, RBX  ; Insert new value")
            self.output.append(f"    MOVQ {self.simd_register}, RAX  ; Store back to SIMD register (register-to-register)")
            self.output.append(f"    ; Zero-latency: all operations in registers, no pipeline stall")
        else:
            # Read: extract value from register
            # Zero-latency: direct register access, no memory read
            self.output.append(f"    ; Zero-latency read from packed variable {var_name} (bits {start_bit}-{start_bit+bits-1})")
            self.output.append(f"    ; Direct SIMD register access - eliminates memory read stall")
            self.output.append(f"    MOVQ RAX, {self.simd_register}  ; Load packed register (register-to-register)")
            if start_bit > 0:
                self.output.append(f"    SHR RAX, {start_bit}  ; Shift to extract {var_name}")
            self.output.append(f"    AND RAX, {mask}  ; Mask to {bits} bits")
            self.output.append(f"    ; Value now in RAX (zero-latency, no memory access, no pipeline stall)")
        
        return True
    
    def _is_interrupt_callback(self, func_name):
        """Check if function is an interrupt callback."""
        from analyzer import is_interrupt_callback
        return is_interrupt_callback(func_name)
    
    def _generate_local_var_load(self, var_name):
        """Generate code to load a local variable using indexed stack pointer.
        
        Stack address = [R12 + slot_index*16 + offset]
        Where R12 = stack base, slot_index fits in 32 bits (enables pointer compression)
        """
        if var_name not in self.current_function_stack:
            # Variable not found in current function - might be a parameter or error
            # For now, assume it's a parameter passed in register or use fallback
            self.output.append(f"    ; Warning: {var_name} not found in stack, assuming parameter")
            return
        
        slot_index, offset = self.current_function_stack[var_name]
        
        # Calculate address: [R12 + slot_index*16 + offset]
        # Use indexed addressing: R12 (base) + slot_index*16 (displacement)
        self.output.append(f"    ; Load local variable {var_name} from slot {slot_index}, offset {offset}")
        self.output.append(f"    ; Indexed stack: address = [R12 + {slot_index}*16 + {offset}]")
        self.output.append(f"    ; Slot index {slot_index} fits in 32 bits for pointer compression")
        
        # Calculate effective address: R12 + slot_index*16 + offset
        displacement = slot_index * self.stack_slot_size + offset
        if displacement == 0:
            # Direct access to slot 0
            self.output.append(f"    MOV RAX, [{self.stack_base_register}]  ; Load from slot 0")
        else:
            # Use displacement addressing
            self.output.append(f"    MOV RAX, [{self.stack_base_register} + {displacement}]  ; Load from slot {slot_index}")
    
    def _generate_local_var_store(self, var_name):
        """Generate code to store a local variable using indexed stack pointer.
        
        Stack address = [R12 + slot_index*16 + offset]
        Where R12 = stack base, slot_index fits in 32 bits (enables pointer compression)
        """
        if var_name not in self.current_function_stack:
            # Variable not found - allocate it now
            slot_index = self.current_stack_slots
            offset = 0
            self.current_stack_slots += 1
            self.current_function_stack[var_name] = (slot_index, offset)
            self.output.append(f"    ; Allocating slot {slot_index} for {var_name}")
            self.output.append(f"    INC {self.stack_index_register}  ; Increment slot index")
        else:
            slot_index, offset = self.current_function_stack[var_name]
        
        # Store value using indexed addressing
        self.output.append(f"    ; Store to local variable {var_name} at slot {slot_index}, offset {offset}")
        self.output.append(f"    ; Indexed stack: address = [R12 + {slot_index}*16 + {offset}]")
        self.output.append(f"    ; Slot index {slot_index} fits in 32 bits for pointer compression")
        
        displacement = slot_index * self.stack_slot_size + offset
        if displacement == 0:
            self.output.append(f"    MOV [{self.stack_base_register}], RAX  ; Store to slot 0")
        else:
            self.output.append(f"    MOV [{self.stack_base_register} + {displacement}], RAX  ; Store to slot {slot_index}")
    
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
    
    def _generate_function(self, func_def):
        """Generate code for a single function."""
        func_name = func_def.decl.name if func_def.decl else "unknown"
        info = self.function_data.get(func_name, {})
        is_interrupt = self._is_interrupt_callback(func_name)
        
        # Reset stack tracking for this function
        self.current_function_stack = {}
        self.current_stack_slots = 0
        
        # Align function start to 16 bytes for quantized call-backs
        self.output.append(f"ALIGN {self.alignment}")
        self.output.append(f"FUNC_{func_name}:")
        
        if is_interrupt:
            self.output.append(f"    ; Interrupt callback: using zero-latency SIMD register access")
            # For interrupt callbacks, ensure SIMD register is preserved/accessible
            self.output.append(f"    ; {self.simd_register} contains packed kernel flags (no memory reads)")
        
        # Function prologue with indexed stack pointer
        self.output.append("    ; Indexed stack pointer prologue (16-byte intervals)")
        self.output.append("    PUSH RBP")
        self.output.append("    PUSH R12  ; Preserve stack base register")
        self.output.append("    PUSH R13  ; Preserve stack index register")
        self.output.append("    MOV RBP, RSP  ; Save old RSP")
        
        # Initialize indexed stack pointer system
        # R12 = stack base address, R13 = current slot index (0-based)
        self.output.append(f"    MOV {self.stack_base_register}, {self.stack_base_address}  ; Load stack base")
        self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Initialize slot index to 0")
        self.output.append("    ; Stack address = [R12 + R13*16] for indexed access")
        self.output.append("    ; Pointer compression: R13 fits in 32 bits, allowing two indices in one 64-bit register")
        
        # For interrupt callbacks, preserve SIMD register if needed
        if is_interrupt:
            # Allocate one slot (16 bytes) for SIMD register preservation
            self.current_stack_slots = 1
            self.output.append(f"    INC {self.stack_index_register}  ; Allocate slot 0 for SIMD register")
            # Note: xmm15 is typically preserved across calls, but we ensure it's accessible
        
        # Generate function body
        if func_def.body:
            self._generate_block(func_def.body, func_name, info)
        
        # Function epilogue (optimized for single return sites with metamorphic return)
        # Note: If has_single_return, the return is handled in _generate_return
        if is_interrupt and self.current_stack_slots > 0:
            self.output.append(f"    DEC {self.stack_index_register}  ; Deallocate SIMD register slot")
        
        # Restore registers
        self.output.append("    POP R13  ; Restore stack index register")
        self.output.append("    POP R12  ; Restore stack base register")
    
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
    
    def _generate_return(self, ret_stmt, func_name, info):
        """Generate return statement with metamorphic return site optimization."""
        if info.get('has_single_return', False):
            # Metamorphic return site: return address is written into instruction
            self.output.append("    ; Metamorphic return site - address injected by caller")
            # Restore stack index to 0 (all slots deallocated)
            if self.current_stack_slots > 0:
                self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
            self.output.append("    MOV RSP, RBP")
            self.output.append("    POP RBP")
            # The RET address will be dynamically modified by the caller
            self.output.append("    RET  ; Address bytes written by caller")
        else:
            # Standard return
            if ret_stmt.expr:
                self._generate_expression(ret_stmt.expr)
                # Return value is already in RAX from expression evaluation
            # Restore stack index to 0 (all slots deallocated)
            if self.current_stack_slots > 0:
                self.output.append(f"    XOR {self.stack_index_register}, {self.stack_index_register}  ; Reset stack index")
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
            # Check if this is a packed global variable
            if name in self.global_var_data['bit_positions']:
                # Use zero-latency SIMD register access
                self._generate_packed_var_access(name, is_write=False)
            else:
                # Check if it's a global variable (non-packed)
                globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                if name in globals:
                    # Global variable (non-packed)
                    self.output.append(f"    MOV RAX, [GLOBAL_{name}]  ; Load global variable")
                else:
                    # Local variable - use indexed stack pointer
                    self._generate_local_var_load(name)
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
                # Check if this is a packed global variable
                if name in self.global_var_data['bit_positions']:
                    # Use zero-latency SIMD register write
                    self._generate_packed_var_access(name, is_write=True, value_reg='RAX')
                else:
                    # Check if it's a global variable (non-packed)
                    globals = [g.name for g in getattr(self, '_current_parser', None).get_global_variables() if g.name] if hasattr(self, '_current_parser') else []
                    if name in globals:
                        # Global variable (non-packed)
                        self.output.append(f"    MOV [GLOBAL_{name}], RAX")
                    else:
                        # Local variable assignment - use indexed stack pointer
                        self._generate_local_var_store(name)
    
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
        """Generate code for variable declaration with indexed stack pointer."""
        name = decl.name
        # Allocate a 16-byte slot for the variable (indexed stack)
        slot_index = self.current_stack_slots
        self.current_stack_slots += 1
        
        # Store variable location: (slot_index, offset_within_slot)
        # For simplicity, we'll use offset 0 within each slot
        # Multiple small variables could share a slot, but for now one per slot
        self.current_function_stack[name] = (slot_index, 0)
        
        # Increment stack index register to allocate new slot
        self.output.append(f"    ; Allocate slot {slot_index} (16 bytes) for {name}")
        self.output.append(f"    INC {self.stack_index_register}  ; Increment slot index")
        
        if decl.init:
            self._generate_expression(decl.init)
            # Store value using indexed addressing
            self._generate_local_var_store(name)
        else:
            # Initialize to 0
            self.output.append(f"    XOR RAX, RAX  ; Initialize {name} to 0")
            self._generate_local_var_store(name)
"""GDB debug-run support, register assertions, and memory dumps."""

import os
import re
import shutil
import subprocess
import sys
import tempfile

REGISTER_ASSERT_PATTERN = re.compile(
    r'//.*?\b(RAX|EAX|RBX|EBX|RCX|ECX|RDX|EDX|RSI|ESI|RDI|EDI|RSP|ESP|RBP|EBP|R8|R9|R10|R11|R12|R13|R14|R15)\s*=\s*(0[xX][0-9a-fA-F]+|\d+)\b',
    re.IGNORECASE,
)

REGISTER_ASSERT_IN_TEXT = re.compile(
    r'\b(RAX|EAX|RBX|EBX|RCX|ECX|RDX|EDX|RSI|ESI|RDI|EDI|RSP|ESP|RBP|EBP|R8|R9|R10|R11|R12|R13|R14|R15)\s*=\s*(0[xX][0-9a-fA-F]+|\d+)\b',
    re.IGNORECASE,
)

MEMDUMP_IN_TEXT = re.compile(r'\bMEMDUMP\b(.*)$', re.IGNORECASE)

MEMDUMP_PATTERN = re.compile(r'//.*?\bMEMDUMP\b(.*)$', re.IGNORECASE)

DBG_ASSERT_ASM_PATTERN = re.compile(
    r';\s*DBG_ASSERT\s+([^:]+):(\d+)\s+(\w+)=(0[xX][0-9a-fA-F]+|\d+)',
)

DBG_MEMDUMP_ASM_PATTERN = re.compile(
    r';\s*DBG_MEMDUMP\s+([^:]+):(\d+)\s+(\S+)\s+(\d+)',
)

KNOWN_REGS = frozenset({
    'RAX', 'EAX', 'RBX', 'EBX', 'RCX', 'ECX', 'RDX', 'EDX',
    'RSI', 'ESI', 'RDI', 'EDI', 'RSP', 'ESP', 'RBP', 'EBP',
    'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15',
})

REG64_TO_32 = {
    'RAX': 'EAX', 'RBX': 'EBX', 'RCX': 'ECX', 'RDX': 'EDX',
    'RSI': 'ESI', 'RDI': 'EDI', 'RSP': 'ESP', 'RBP': 'EBP',
}

REG32_TO_64 = {value: key for key, value in REG64_TO_32.items()}


def parse_register_value(value_str):
    value_str = value_str.strip()
    if value_str.lower().startswith('0x'):
        return int(value_str, 16)
    return int(value_str, 10)


def normalize_register_for_mode(register, use_32bit):
    register = register.upper()
    if use_32bit:
        return REG64_TO_32.get(register, register)
    return REG32_TO_64.get(register, register)


def parse_memdump_payload(payload):
    """Parse MEMDUMP comment payload into base address/register and byte count."""
    payload = payload.strip()
    if not payload:
        return {'base': 'RSP', 'size': 64}

    parts = [part for part in re.split(r'[\s,]+', payload) if part]
    if len(parts) == 1:
        token = parts[0]
        upper = token.upper()
        if upper in KNOWN_REGS:
            return {'base': upper, 'size': 64}
        if token.lower().startswith('0x') or token.isdigit():
            return {'base': parse_register_value(token), 'size': 64}
        raise ValueError(f'invalid MEMDUMP payload: {payload!r}')

    base_token, size_token = parts[0], parts[1]
    upper = base_token.upper()
    base = upper if upper in KNOWN_REGS else parse_register_value(base_token)
    return {'base': base, 'size': parse_register_value(size_token)}


def parse_memdump_in_line(line):
    match = MEMDUMP_PATTERN.search(line)
    if not match:
        return None
    return parse_memdump_payload(match.group(1))


def _register_assert_from_match(match):
    return {
        'register': match.group(1).upper(),
        'expected': parse_register_value(match.group(2)),
        'expected_str': match.group(2),
    }


def _memdump_payload_excluding_register_assertions(payload):
    """Remove register assertion substrings from a MEMDUMP payload."""
    return REGISTER_ASSERT_IN_TEXT.sub('', payload).strip()


def _register_assertions_in_comment(comment):
    """Return all register assertions in a comment, in left-to-right order."""
    return [_register_assert_from_match(match) for match in REGISTER_ASSERT_IN_TEXT.finditer(comment)]


def parse_debug_hooks_in_line(line):
    """Parse // debug comments into ordered register assert / memdump hooks.

    Supports combined comments such as:
      // MEMDUMP RAX = 0x0              (memdump, then register check)
      // RAX = 0x0 MEMDUMP              (register check, then memdump)
      // RAX = 0x0 RAX = 0x1            (consecutive register checks)
      // MEMDUMP RAX = 0x0 RAX = 0x1    (memdump, then consecutive checks)
    """
    if '//' not in line:
        return line.rstrip(), []

    comment_idx = line.index('//')
    code_before = line[:comment_idx].rstrip()
    comment = line[comment_idx + 2:]

    reg_matches = list(REGISTER_ASSERT_IN_TEXT.finditer(comment))
    mem_match = MEMDUMP_IN_TEXT.search(comment)
    if not reg_matches and not mem_match:
        return code_before, []

    ordered = []
    if mem_match:
        payload = _memdump_payload_excluding_register_assertions(mem_match.group(1))
        memdump = parse_memdump_payload(payload) if payload else {'base': 'RSP', 'size': 64}
        ordered.append((mem_match.start(), {'kind': 'memdump', **memdump}))
    for reg_match in reg_matches:
        ordered.append((reg_match.start(), {'kind': 'assert', **_register_assert_from_match(reg_match)}))

    ordered.sort(key=lambda item: item[0])
    return code_before, [hook for _, hook in ordered]


def _debug_hook_entry(hook, source_file, line, sequence):
    entry = {
        'file': source_file,
        'line': line,
        'sequence': sequence,
        'placement': 'after',
    }
    if hook['kind'] == 'assert':
        entry.update({
            'register': hook['register'],
            'expected': hook['expected'],
            'expected_str': hook['expected_str'],
        })
    else:
        entry.update({
            'base': hook['base'],
            'size': hook['size'],
        })
    return entry


def _target_line(stripped_lines, code_before):
    if code_before:
        stripped_lines.append(code_before)
        return len(stripped_lines)
    return None


def prepare_source_and_debug_comments(content, source_file, extract_debug=False):
    """Strip debug comments and extract register assertions / memdumps when enabled."""
    if not extract_debug:
        return content, [], []

    stripped_lines = []
    register_assertions = []
    memdumps = []
    pending = []
    abs_source_file = os.path.abspath(source_file)

    def _flush_pending(target_line):
        for sequence, hook in enumerate(pending):
            entry = _debug_hook_entry(hook, abs_source_file, target_line, sequence)
            if hook['kind'] == 'assert':
                register_assertions.append(entry)
            else:
                memdumps.append(entry)
        pending.clear()

    for line in content.splitlines():
        code_before, hooks = parse_debug_hooks_in_line(line)

        if not hooks:
            stripped_lines.append(line)
            if pending:
                _flush_pending(len(stripped_lines))
            continue

        if code_before:
            target_line = _target_line(stripped_lines, code_before)
            if target_line is None:
                continue
            for sequence, hook in enumerate(hooks):
                entry = _debug_hook_entry(hook, abs_source_file, target_line, sequence)
                if hook['kind'] == 'assert':
                    register_assertions.append(entry)
                else:
                    memdumps.append(entry)
            continue

        pending.extend(hooks)

    stripped_content = '\n'.join(stripped_lines)
    if content.endswith('\n') and stripped_content and not stripped_content.endswith('\n'):
        stripped_content += '\n'
    return stripped_content, register_assertions, memdumps


def _skip_stripped_debug_line(line):
    """True for blank lines and comments that cpp removes from preprocessed output."""
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith('//'):
        return True
    if stripped.startswith('/*') or stripped.startswith('*') or stripped.endswith('*/'):
        return True
    return False


def map_stripped_lines_to_preprocessed(stripped_content, preprocessed_content):
    mapping = {}
    stripped_lines = stripped_content.splitlines()
    preprocessed_lines = preprocessed_content.splitlines()
    stripped_index = 0

    for preprocessed_line_num, preprocessed_line in enumerate(preprocessed_lines, start=1):
        while stripped_index < len(stripped_lines) and _skip_stripped_debug_line(stripped_lines[stripped_index]):
            stripped_index += 1
        if stripped_index >= len(stripped_lines):
            break
        if stripped_lines[stripped_index].strip() == preprocessed_line.strip():
            mapping[stripped_index + 1] = preprocessed_line_num
            stripped_index += 1

    return mapping


def remap_debug_line_numbers(entries, line_mapping):
    remapped = []
    for entry in entries:
        item = dict(entry)
        item['line'] = line_mapping.get(entry['line'], entry['line'])
        remapped.append(item)
    return remapped


def format_memdump_base(base):
    if isinstance(base, int):
        return hex(base)
    return str(base).upper()


def parse_debug_metadata_from_asm(asm_path):
    assertions = []
    memdumps = []
    with open(asm_path, 'r') as f:
        for line in f:
            match = DBG_ASSERT_ASM_PATTERN.search(line)
            if match:
                assertions.append({
                    'file': match.group(1),
                    'line': int(match.group(2)),
                    'register': match.group(3).upper(),
                    'expected': parse_register_value(match.group(4)),
                    'expected_str': match.group(4),
                    'label': f'__dbg_assert_{len(assertions)}',
                })
                continue
            match = DBG_MEMDUMP_ASM_PATTERN.search(line)
            if match:
                base_text = match.group(3)
                base = parse_register_value(base_text) if base_text.lower().startswith('0x') else base_text.upper()
                memdumps.append({
                    'file': match.group(1),
                    'line': int(match.group(2)),
                    'base': base,
                    'size': int(match.group(4)),
                    'label': f'__dbg_memdump_{len(memdumps)}',
                })
    return assertions, memdumps


def _gdb_memdump_commands(entry, use_32bit):
    base = entry['base']
    size = entry['size']
    location = f"{entry['file']}:{entry['line']}"
    lines = [
        f'printf "MEMDUMP at {location}\\n"',
    ]
    if isinstance(base, int):
        lines.append(f'set $addr = {hex(base)}')
    else:
        reg = normalize_register_for_mode(str(base), use_32bit).lower()
        lines.append(f'set $addr = ${reg}')
    lines.append(f'x/{size}bx $addr')
    return lines


def build_gdb_script(executable, assertions, memdumps, use_32bit=False):
    lines = [
        'set pagination off',
        'set confirm off',
        'set debuginfod enabled off',
        f'file {executable}',
    ]

    checkpoints = []
    for idx, assertion in enumerate(assertions):
        checkpoints.append((
            assertion.get('label', f'__dbg_assert_{idx}'),
            'assert',
            assertion,
        ))
    for idx, memdump in enumerate(memdumps):
        checkpoints.append((
            memdump.get('label', f'__dbg_memdump_{idx}'),
            'memdump',
            memdump,
        ))

    for label, kind, entry in checkpoints:
        lines.append(f'break {label}')
        lines.append('commands')
        lines.append('silent')
        if kind == 'assert':
            register = normalize_register_for_mode(entry['register'], use_32bit)
            gdb_reg = register.lower()
            expected = entry['expected']
            location = f"{entry['file']}:{entry['line']}"
            lines.append(f'if ${gdb_reg} != {expected}')
            lines.append(
                f'  printf "Assertion failed: {register} != {entry.get("expected_str", hex(expected))} '
                f'(actual=%#x) at {location}\\n", ${gdb_reg}'
            )
            lines.append('  quit 1')
            lines.append('end')
        else:
            lines.extend(_gdb_memdump_commands(entry, use_32bit))
        lines.append('continue')
        lines.append('end')

    lines.append('run')
    lines.append('if $_siginfo')
    lines.append('  quit 1')
    lines.append('end')
    lines.append('quit 0')
    return '\n'.join(lines) + '\n'


def run_gdb(executable, assertions=None, memdumps=None, verbose=False, use_32bit=False):
    if not shutil.which('gdb'):
        print("Error: gdb not found. Install it with:", file=sys.stderr)
        print("  sudo apt-get install gdb    # Debian/Ubuntu", file=sys.stderr)
        return False

    executable = os.path.abspath(executable)
    if not os.path.isfile(executable):
        print(f"Error: executable not found: {executable}", file=sys.stderr)
        return False

    assertions = assertions or []
    memdumps = memdumps or []
    script_content = build_gdb_script(executable, assertions, memdumps, use_32bit=use_32bit)

    print(f"Running {executable} under gdb...", file=sys.stderr)
    if verbose:
        if assertions:
            print(f"  {len(assertions)} register assertion(s) enabled", file=sys.stderr)
        if memdumps:
            print(f"  {len(memdumps)} memdump checkpoint(s) enabled", file=sys.stderr)

    script_file = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.gdb', delete=False) as script:
            script.write(script_content)
            script_file = script.name

        result = subprocess.run(
            ['gdb', '-batch', '-x', script_file, executable],
            text=True,
        )

        if result.returncode != 0:
            print("Error: GDB debug run failed", file=sys.stderr)
            return False

        return True
    finally:
        if script_file:
            try:
                os.unlink(script_file)
            except OSError:
                pass

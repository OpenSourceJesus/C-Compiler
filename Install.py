#!/usr/bin/env python3
"""Install dependencies for the C compiler."""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"
MIN_PYTHON = (3, 8)

PYTHON_PACKAGES = [
    ("pycparser", "pycparser"),
    ("pycparser-fake-libc", "pycparser_fake_libc"),
    ("matplotlib", "matplotlib"),
]

SYSTEM_TOOLS = [
    {
        "name": "assembler",
        "commands": ("nasm", "yasm"),
        "required": True,
        "packages": {
            "apt": ("nasm",),
            "dnf": ("nasm",),
            "yum": ("nasm",),
            "pacman": ("nasm",),
        },
    },
    {
        "name": "linker",
        "commands": ("ld.gold", "ld"),
        "required": True,
        "packages": {
            "apt": ("binutils",),
            "dnf": ("binutils",),
            "yum": ("binutils",),
            "pacman": ("binutils",),
        },
    },
    {
        "name": "qemu user mode",
        "commands": ("qemu-x86_64",),
        "required": False,
        "packages": {
            "apt": ("qemu-user",),
            "dnf": ("qemu-user",),
            "yum": ("qemu-user",),
            "pacman": ("qemu-user",),
        },
    },
    {
        "name": "qemu system mode",
        "commands": ("qemu-system-x86_64",),
        "required": False,
        "packages": {
            "apt": ("qemu-system-x86",),
            "dnf": ("qemu-system-x86",),
            "yum": ("qemu-system-x86",),
            "pacman": ("qemu-system-x86",),
        },
    },
]


def check_python_version():
    if sys.version_info < MIN_PYTHON:
        version = ".".join(str(part) for part in MIN_PYTHON)
        print(f"Error: Python {version}+ is required (found {sys.version.split()[0]})", file=sys.stderr)
        return False
    return True


def command_available(command):
    return shutil.which(command) is not None


def detect_package_manager():
    for manager, command in (
        ("pacman", "pacman"),
        ("apt", "apt-get"),
        ("dnf", "dnf"),
        ("yum", "yum"),
    ):
        if command_available(command):
            return manager
    return None


def run_command(command, check=True):
    print(f"$ {' '.join(command)}")
    return subprocess.run(command, check=check)


def install_python_packages(break_system_packages=False):
    if not REQUIREMENTS.exists():
        print(f"Error: requirements file not found: {REQUIREMENTS}", file=sys.stderr)
        return False

    print("Installing Python dependencies...")
    pip_command = [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    if break_system_packages:
        pip_command.append("--break-system-packages")
    try:
        run_command(pip_command)
    except subprocess.CalledProcessError:
        print("Error: failed to install Python dependencies", file=sys.stderr)
        return False

    missing = []
    for package_name, import_name in PYTHON_PACKAGES:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(package_name)

    if missing:
        print(f"Error: missing Python packages after install: {', '.join(missing)}", file=sys.stderr)
        return False

    print("Python dependencies installed.")
    return True


def tool_status(tool):
    for command in tool["commands"]:
        if command_available(command):
            return True, command
    return False, None


def check_system_tools():
    missing_required = []
    missing_optional = []

    print("Checking system tools...")
    for tool in SYSTEM_TOOLS:
        ok, command = tool_status(tool)
        label = tool["name"]
        if ok:
            print(f"  ✓ {label}: {command}")
            continue

        print(f"  ✗ {label}: not found")
        if tool["required"]:
            missing_required.append(tool)
        else:
            missing_optional.append(tool)

    return missing_required, missing_optional


def install_system_packages(tools, package_manager):
    packages = []
    for tool in tools:
        tool_packages = tool["packages"].get(package_manager, ())
        packages.extend(tool_packages)

    if not packages:
        return False

    unique_packages = []
    seen = set()
    for package in packages:
        if package not in seen:
            seen.add(package)
            unique_packages.append(package)

    if package_manager == "apt":
        command = ["sudo", "apt-get", "install", "-y", *unique_packages]
    elif package_manager == "pacman":
        command = ["sudo", "pacman", "-S", "--needed", "--noconfirm", *unique_packages]
    else:
        command = ["sudo", package_manager, "install", "-y", *unique_packages]

    try:
        run_command(command)
    except subprocess.CalledProcessError:
        print("Error: failed to install system packages", file=sys.stderr)
        return False

    return True


def print_manual_system_instructions(tools, package_manager):
    if not tools:
        return

    print("\nInstall missing system tools manually:")
    for tool in tools:
        packages = tool["packages"].get(package_manager or "apt", ())
        package_list = " ".join(packages)
        commands = " or ".join(tool["commands"])
        print(f"  {tool['name']} ({commands})")
        if package_manager == "apt":
            print(f"    sudo apt-get install {package_list}")
        elif package_manager == "pacman":
            print(f"    sudo pacman -S --needed {package_list}")
        elif package_manager in ("dnf", "yum"):
            print(f"    sudo {package_manager} install {package_list}")
        else:
            print(f"    install packages: {package_list}")


def parse_args():
    parser = argparse.ArgumentParser(description="Install dependencies for the C compiler")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check dependencies without installing anything",
    )
    parser.add_argument(
        "--system-deps",
        action="store_true",
        help="Attempt to install missing system tools with the detected package manager",
    )
    parser.add_argument(
        "--skip-python",
        action="store_true",
        help="Skip installing Python packages",
    )
    parser.add_argument(
        "--break-system-packages",
        action="store_true",
        help="Pass --break-system-packages to pip (for externally-managed Python environments)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not check_python_version():
        return 1

    os.chdir(ROOT)

    if not args.check_only and not args.skip_python:
        if not install_python_packages(break_system_packages=args.break_system_packages):
            return 1
    elif not args.skip_python:
        missing = []
        for package_name, import_name in PYTHON_PACKAGES:
            try:
                __import__(import_name)
            except ImportError:
                missing.append(package_name)
        if missing:
            print(f"Missing Python packages: {', '.join(missing)}")
            return 1
        print("Python dependencies OK.")

    missing_required, missing_optional = check_system_tools()
    package_manager = detect_package_manager()

    if args.system_deps and (missing_required or missing_optional):
        if package_manager is None:
            print("Error: no supported package manager found (pacman, apt-get, dnf, or yum)", file=sys.stderr)
            print_manual_system_instructions(missing_required + missing_optional, None)
            return 1

        print(f"\nInstalling system packages via {package_manager}...")
        if not install_system_packages(missing_required + missing_optional, package_manager):
            return 1

        missing_required, missing_optional = check_system_tools()

    if missing_required:
        print("\nRequired system tools are still missing.", file=sys.stderr)
        print_manual_system_instructions(missing_required, package_manager)
        return 1

    if missing_optional:
        print("\nOptional tools not installed (needed only for QEMU testing).")
        print_manual_system_instructions(missing_optional, package_manager)

    print("\nInstallation complete.")
    print("Compile C code with:")
    print("  python3 compiler.py input.c -o output.asm")
    return 0


if __name__ == "__main__":
    sys.exit(main())

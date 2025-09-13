"""Utility functions and classes for the CLI tool"""

import os
import shutil

class CLIColors:
    """ANSI color codes for CLI output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_terminal_width():
    """Get the terminal width."""
    return shutil.get_terminal_size().columns

def center_text(text, width=None):
    """Center align text."""
    if width is None:
        width = get_terminal_width()
    
    # Handle ANSI color codes when calculating text length
    visible_length = len(''.join(text.split('\033[')[0::2]))
    padding = (width - visible_length) // 2
    return ' ' * padding + text

def print_centered(text, width=None):
    """Print centered text."""
    print(center_text(text, width))

def create_separator(width=None, style="─"):
    """Create a separator line."""
    if width is None:
        width = get_terminal_width()
    return style * width

def print_banner():
    """Print the application banner"""
    width = min(get_terminal_width(), 80)  # Cap width at 80 characters
    box_width = 60  # Fixed width for the box
    
    # Create the banner box
    top = "╔" + "═" * (box_width - 2) + "╗"
    title = "║" + "🚀 ENHANCED CLI TOOLKIT 🚀".center(box_width - 2) + "║"
    subtitle = "║" + "Your All-in-One Command Line Assistant".center(box_width - 2) + "║"
    bottom = "╚" + "═" * (box_width - 2) + "╝"
    
    # Print banner
    print("\n")
    print_centered(top, width)
    print_centered(title, width)
    print_centered(subtitle, width)
    print_centered(bottom, width)
    print("\n")
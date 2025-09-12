"""
Utility functions and classes for the CLI tool
"""

class CLIColors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_banner():
    """Display the main CLI banner"""
    banner = f"""
{CLIColors.CYAN}{CLIColors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                    🚀 ENHANCED CLI TOOLKIT 🚀                ║
║              Your All-in-One Command Line Assistant          ║
╚══════════════════════════════════════════════════════════════╝
{CLIColors.END}
    """
    print(banner)
"""
This is our main menu for the System Information tool!
It helps us choose what we want to know about our computer.
"""

import os
from modules.utils import CLIColors
from modules.system_monitor import SystemMonitor

def get_terminal_width():
    """Get how wide our terminal window is"""
    try:
        return os.get_terminal_size().columns
    except:
        return 80

def print_centered(text, width=None):
    """Print text in the middle of the screen"""
    if width is None:
        width = get_terminal_width()
    print(text.center(width))

def system_info_menu():
    """
    This is our main menu where we can choose what we want to check about our computer!
    Like a control panel with different buttons to press.
    """
    # Create our system monitor helper
    monitor = SystemMonitor()
    
    while True:
        # Make our menu look pretty
        print("\n" + "=" * get_terminal_width())
        print(f"{CLIColors.CYAN}🔧 System Information & Monitoring 🔧{CLIColors.END}")
        print("=" * get_terminal_width() + "\n")
        
        # Show all the things we can do
        options = {
            "1": "📊 Show All System Information",
            "2": "💻 Basic System Information",
            "3": "🔍 CPU Information",
            "4": "📝 Memory Status",
            "5": "💾 Disk Information",
            "6": "🌐 Network Status",
            "7": "⏰ System Uptime",
            "8": "↩️  Back to Main Menu"
        }
        
        # Print our menu options
        print("What would you like to check?\n")
        for key, value in options.items():
            print(f"  {key}. {value}")
            
        # Ask what the user wants to do
        choice = input(f"\n{CLIColors.BOLD}Choose an option (1-8): {CLIColors.END}").strip()
        
        if choice == "1":
            # Show everything!
            monitor.display_system_info()
            
        elif choice == "2":
            # Show basic system info
            print(f"\n{CLIColors.CYAN}💻 Basic System Information:{CLIColors.END}")
            print("=" * 50)
            for key, value in monitor.get_basic_system_info().items():
                print(f"  • {key}: {value}")
                
        elif choice == "3":
            # Show CPU info
            print(f"\n{CLIColors.CYAN}🔍 CPU Information:{CLIColors.END}")
            print("=" * 50)
            cpu_info = monitor.get_cpu_info()
            for key, value in cpu_info.items():
                if key == "Usage Per Core":
                    print(f"\n  • Core Usage:")
                    for core, usage in value.items():
                        print(f"    - {core}: {usage}")
                else:
                    print(f"  • {key}: {value}")
                    
        elif choice == "4":
            # Show memory info
            print(f"\n{CLIColors.CYAN}📝 Memory Status:{CLIColors.END}")
            print("=" * 50)
            for key, value in monitor.get_memory_info().items():
                print(f"  • {key}: {value}")
                
        elif choice == "5":
            # Show disk info
            print(f"\n{CLIColors.CYAN}💾 Disk Information:{CLIColors.END}")
            print("=" * 50)
            for disk in monitor.get_disk_info():
                print(f"\n  Drive: {disk['Drive']}")
                for key, value in disk.items():
                    if key != 'Drive':
                        print(f"    • {key}: {value}")
                        
        elif choice == "6":
            # Show network info
            print(f"\n{CLIColors.CYAN}🌐 Network Status:{CLIColors.END}")
            print("=" * 50)
            for nic, info in monitor.get_network_info().items():
                print(f"\n  Interface: {nic}")
                for key, value in info.items():
                    print(f"    • {key}: {value}")
                    
        elif choice == "7":
            # Show uptime
            print(f"\n{CLIColors.CYAN}⏰ System Uptime:{CLIColors.END}")
            print("=" * 50)
            print(f"  • Your computer has been running for: {monitor.format_uptime()}")
            
        elif choice == "8":
            # Go back to main menu
            return
            
        else:
            print(f"\n{CLIColors.RED}❌ Please choose a valid option (1-8){CLIColors.END}")
            
        # Wait for user to read the information
        input(f"\n{CLIColors.BOLD}Press Enter to continue...{CLIColors.END}")

if __name__ == "__main__":
    system_info_menu()
#!/usr/bin/env python3
"""
Enhanced CLI Tool - Multi-purpose command line interface
"""

import os
from dotenv import load_dotenv
from modules.utils import CLIColors, print_banner
from modules.youtube_manager import youtube_menu
from modules.weather_manager import weather_menu
from modules.chrome_manager import chrome_menu

# Load environment variables from .env file
load_dotenv()

def main_menu():
    """Display main menu and get user choice"""
    print_banner()
    
    options = {
        "1": "🎵 YouTube Playlist Generator",
        "2": "🌐 Chrome Utilities", 
        "3": "🌤️  Weather Forecast",
        "4": "📁 File Manager",
        "5": "🔧 System Information",
        "6": "📊 Network Tools",
        "7": "⚙️  Settings & Configuration",
        "8": "❓ Help & About",
        "9": "🚪 Exit"
    }
    
    print(f"{CLIColors.YELLOW}Available Tools:{CLIColors.END}")
    print("=" * 60)
    
    for key, value in options.items():
        print(f"  {CLIColors.GREEN}{key}{CLIColors.END}. {value}")
        
    print("=" * 60)
    return input(f"\n{CLIColors.BOLD}Choose an option (1-9): {CLIColors.END}").strip()

# Stub functions for other menus
def file_manager_menu():
    print(f"\n{CLIColors.CYAN}📁 File Manager{CLIColors.END}")
    print(f"{CLIColors.YELLOW}⚠️ Feature coming soon!{CLIColors.END}")

def system_info_menu():
    print(f"\n{CLIColors.CYAN}🔧 System Information{CLIColors.END}")
    print(f"{CLIColors.YELLOW}⚠️ Feature coming soon!{CLIColors.END}")

def network_tools_menu():
    print(f"\n{CLIColors.CYAN}📊 Network Tools{CLIColors.END}")
    print(f"{CLIColors.YELLOW}⚠️ Feature coming soon!{CLIColors.END}")

def settings_menu():
    print(f"\n{CLIColors.CYAN}⚙️ Settings & Configuration{CLIColors.END}")
    print(f"{CLIColors.YELLOW}⚠️ Feature coming soon!{CLIColors.END}")

def help_menu():
    print(f"\n{CLIColors.CYAN}❓ Help & About{CLIColors.END}")
    print("=" * 50)
    print(f"""
{CLIColors.GREEN}Enhanced CLI Toolkit{CLIColors.END}
A comprehensive command-line interface with multiple utilities.

{CLIColors.YELLOW}Setup Instructions:{CLIColors.END}
1. Create a .env file with your API keys:
   - YOUTUBE_API_KEY=your_youtube_api_key
   - OPENWEATHER_API_KEY=your_openweather_api_key

2. Install required dependencies:
   pip install -r requirements.txt
""")

def main():
    """Main application loop"""
    while True:
        try:
            choice = main_menu()
            
            if choice == "1":
                youtube_menu()
            elif choice == "2":
                chrome_menu()
            elif choice == "3":
                weather_menu()
            elif choice == "4":
                file_manager_menu()
            elif choice == "5":
                system_info_menu()
            elif choice == "6":
                network_tools_menu()
            elif choice == "7":
                settings_menu()
            elif choice == "8":
                help_menu()
            elif choice == "9":
                print(f"\n{CLIColors.GREEN}👋 Thanks for using Enhanced CLI Toolkit!{CLIColors.END}")
                break
            else:
                print(f"\n{CLIColors.RED}❌ Invalid option. Please choose 1-9.{CLIColors.END}")
                
            # Pause before returning to main menu
            if choice != "9":
                input(f"\n{CLIColors.BLUE}Press Enter to continue...{CLIColors.END}")
                
        except KeyboardInterrupt:
            print(f"\n\n{CLIColors.YELLOW}👋 Goodbye!{CLIColors.END}")
            break
        except Exception as e:
            print(f"\n{CLIColors.RED}❌ An error occurred: {str(e)}{CLIColors.END}")
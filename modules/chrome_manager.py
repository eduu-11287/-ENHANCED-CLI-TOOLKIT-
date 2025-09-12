"""
Chrome Utilities Module
"""

import subprocess
from modules.utils import CLIColors

def chrome_menu():
    """Chrome utilities menu"""
    print(f"\n{CLIColors.CYAN}🌐 Chrome Utilities{CLIColors.END}")
    print("=" * 50)
    
    options = {
        "1": "Open Multiple URLs",
        "2": "Clear Browser Data",
        "3": "Launch Incognito Mode",
        "4": "Browser Bookmarks Manager",
        "5": "Back to Main Menu"
    }
    
    for key, value in options.items():
        print(f"  {key}. {value}")
    
    choice = input(f"\n{CLIColors.BOLD}Choose option (1-5): {CLIColors.END}").strip()
    
    if choice == "1":
        urls_input = input(f"{CLIColors.YELLOW}Enter URLs (comma-separated): {CLIColors.END}").strip()
        if urls_input:
            urls = [url.strip() for url in urls_input.split(",")]
            try:
                for url in urls:
                    if not url.startswith(('http://', 'https://')):
                        url = 'https://' + url
                    subprocess.run(['xdg-open', url], check=False)
                print(f"{CLIColors.GREEN}✅ Opened {len(urls)} URLs in browser{CLIColors.END}")
            except Exception as e:
                print(f"{CLIColors.RED}❌ Error opening URLs: {str(e)}{CLIColors.END}")
        else:
            print(f"{CLIColors.RED}❌ Please enter valid URLs{CLIColors.END}")
    
    elif choice == "3":
        try:
            subprocess.run(['google-chrome', '--incognito'], check=False)
            print(f"{CLIColors.GREEN}✅ Chrome incognito mode launched{CLIColors.END}")
        except Exception as e:
            print(f"{CLIColors.RED}❌ Could not launch Chrome: {str(e)}{CLIColors.END}")
    
    elif choice == "5":
        return
    else:
        print(f"{CLIColors.YELLOW}⚠️ Feature coming soon!{CLIColors.END}")
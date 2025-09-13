"""
This is our system monitor! It helps us understand what's happening in our computer,
like checking how hard it's working or if it's getting too hot.
"""

import psutil  # This is like a helper that can talk to our computer
import platform  # This helps us know what kind of computer we have
import cpuinfo  # This tells us about our computer's brain (CPU)
from datetime import datetime
import os
from typing import Dict, List, Tuple

from modules.utils import CLIColors  # This helps us make pretty colored text

class SystemMonitor:
    """
    Think of this as a doctor for your computer! It can check:
    - How hard your computer is working (CPU usage)
    - How much memory (RAM) it's using
    - How much space is left on your hard drive
    - If your computer is getting too hot
    """
    
    def __init__(self):
        """
        This is like setting up our doctor's office with all the tools we need
        """
        # Check what kind of computer we're using
        self.system = platform.system()  # Windows, Linux, or Mac
        self.is_windows = self.system == "Windows"
        self.is_linux = self.system == "Linux"
        
        # Get information about the computer's brain (CPU)
        self.cpu_info = cpuinfo.get_cpu_info()
        
        # Remember when we started checking things
        self.start_time = datetime.now()

    def get_basic_system_info(self) -> Dict[str, str]:
        """
        This is like asking your computer to introduce itself!
        It tells us its name, what kind of computer it is, and other fun facts.
        """
        return {
            "System": platform.system(),  # What kind of computer (Windows, Linux, Mac)
            "Computer Name": platform.node(),  # The name of the computer
            "CPU": self.cpu_info['brand_raw'],  # What kind of brain (CPU) it has
            "Total Memory": f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",  # How much memory it has
            "Python Version": platform.python_version(),  # Which version of Python we're using
            "Operating System": f"{platform.system()} {platform.release()}"  # More details about the computer type
        }

    def get_cpu_info(self) -> Dict[str, str]:
        """
        This checks how hard the computer's brain (CPU) is working!
        Like checking if your computer is thinking really hard or just relaxing.
        """
        # Get how hard each part of the CPU is working
        cpu_percents = psutil.cpu_percent(interval=1, percpu=True)
        
        # Get the temperature (if we can)
        temp = self._get_cpu_temperature()
        
        return {
            "CPU Name": self.cpu_info['brand_raw'],
            "Architecture": self.cpu_info['arch'],
            "Cores": f"{psutil.cpu_count()} ({psutil.cpu_count(logical=False)} physical)",
            "Current Speed": f"{self.cpu_info['hz_actual'][0]/1000000:.2f} MHz",
            "Base Speed": f"{self.cpu_info['hz_advertised'][0]/1000000:.2f} MHz",
            "Temperature": f"{temp}°C" if temp else "Not available",
            "Usage Per Core": {f"Core {i+1}": f"{percent}%" for i, percent in enumerate(cpu_percents)},
            "Total CPU Usage": f"{psutil.cpu_percent()}%"
        }

    def _get_cpu_temperature(self) -> float:
        """
        This checks if the computer is getting too hot!
        Like using a thermometer for your computer.
        """
        try:
            if self.is_linux:
                # On Linux, we look in a special folder for temperature info
                temp = psutil.sensors_temperatures()
                if 'coretemp' in temp:
                    return temp['coretemp'][0].current
                return None
            elif self.is_windows:
                # On Windows, we need special tools to check temperature
                # We'll add this feature later
                return None
            return None
        except:
            return None

    def get_memory_info(self) -> Dict[str, str]:
        """
        This checks how much memory (RAM) your computer is using!
        Like checking how many things your computer can remember at once.
        """
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Convert bytes to more readable format (GB)
        total_gb = memory.total / (1024**3)
        used_gb = memory.used / (1024**3)
        free_gb = memory.available / (1024**3)
        
        return {
            "Total Memory": f"{total_gb:.2f} GB",
            "Used Memory": f"{used_gb:.2f} GB",
            "Free Memory": f"{free_gb:.2f} GB",
            "Memory Usage": f"{memory.percent}%",
            "Swap Total": f"{swap.total / (1024**3):.2f} GB",
            "Swap Used": f"{swap.used / (1024**3):.2f} GB",
            "Swap Free": f"{swap.free / (1024**3):.2f} GB"
        }

    def get_disk_info(self) -> List[Dict[str, str]]:
        """
        This checks your computer's storage!
        Like checking how full your toy box is and how much more you can fit.
        """
        disks = []
        
        # Look at all the storage spaces (hard drives) in your computer
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                # Convert bytes to GB for easier reading
                total_gb = usage.total / (1024**3)
                used_gb = usage.used / (1024**3)
                free_gb = usage.free / (1024**3)
                
                disks.append({
                    "Drive": partition.device,
                    "Mount Point": partition.mountpoint,
                    "File System": partition.fstype,
                    "Total Space": f"{total_gb:.2f} GB",
                    "Used Space": f"{used_gb:.2f} GB",
                    "Free Space": f"{free_gb:.2f} GB",
                    "Usage": f"{usage.percent}%"
                })
            except:
                # Skip any drives we can't read
                continue
                
        return disks

    def get_network_info(self) -> Dict[str, Dict[str, str]]:
        """
        This checks how your computer is talking to the internet!
        Like checking how many messages your computer is sending and receiving.
        """
        network_info = {}
        
        # Look at all the ways your computer can connect to the internet
        for name, stats in psutil.net_io_counters(pernic=True).items():
            # Convert bytes to megabytes for easier reading
            bytes_sent_mb = stats.bytes_sent / (1024**2)
            bytes_recv_mb = stats.bytes_recv / (1024**2)
            
            network_info[name] = {
                "Sent": f"{bytes_sent_mb:.2f} MB",
                "Received": f"{bytes_recv_mb:.2f} MB",
                "Packets Sent": str(stats.packets_sent),
                "Packets Received": str(stats.packets_recv),
                "Errors In": str(stats.errin),
                "Errors Out": str(stats.errout)
            }
            
        return network_info

    def format_uptime(self) -> str:
        """
        This tells us how long your computer has been awake!
        Like a stopwatch that started when you turned on your computer.
        """
        # Get how many seconds the computer has been running
        uptime = psutil.boot_time()
        boot_time = datetime.fromtimestamp(uptime)
        now = datetime.now()
        
        # Calculate the difference
        uptime_duration = now - boot_time
        
        # Make it easy to read
        days = uptime_duration.days
        hours = uptime_duration.seconds // 3600
        minutes = (uptime_duration.seconds % 3600) // 60
        seconds = uptime_duration.seconds % 60
        
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"
        
    def display_system_info(self):
        """
        This shows all the information in a pretty way!
        Like making a nice report card for your computer.
        """
        # Get all our computer's information
        basic_info = self.get_basic_system_info()
        cpu_info = self.get_cpu_info()
        memory_info = self.get_memory_info()
        disk_info = self.get_disk_info()
        network_info = self.get_network_info()
        
        # Print everything in a nice way with colors!
        print(f"\n{CLIColors.CYAN}💻 System Information:{CLIColors.END}")
        print("=" * 50)
        
        # Basic System Info
        print(f"\n{CLIColors.YELLOW}🖥️  Basic System Information:{CLIColors.END}")
        for key, value in basic_info.items():
            print(f"  • {key}: {value}")
            
        # CPU Information
        print(f"\n{CLIColors.YELLOW}🔍 CPU Information:{CLIColors.END}")
        for key, value in cpu_info.items():
            if key == "Usage Per Core":
                print(f"  • Core Usage:")
                for core, usage in value.items():
                    print(f"    - {core}: {usage}")
            else:
                print(f"  • {key}: {value}")
                
        # Memory Information
        print(f"\n{CLIColors.YELLOW}📊 Memory Information:{CLIColors.END}")
        for key, value in memory_info.items():
            print(f"  • {key}: {value}")
            
        # Disk Information
        print(f"\n{CLIColors.YELLOW}💾 Disk Information:{CLIColors.END}")
        for disk in disk_info:
            print(f"\n  Drive: {disk['Drive']}")
            for key, value in disk.items():
                if key != 'Drive':
                    print(f"    • {key}: {value}")
                    
        # Network Information
        print(f"\n{CLIColors.YELLOW}🌐 Network Information:{CLIColors.END}")
        for nic, info in network_info.items():
            print(f"\n  Interface: {nic}")
            for key, value in info.items():
                print(f"    • {key}: {value}")
                
        # Uptime
        print(f"\n{CLIColors.YELLOW}⏰ System Uptime:{CLIColors.END}")
        print(f"  • {self.format_uptime()}")
        
        print("\n" + "=" * 50)
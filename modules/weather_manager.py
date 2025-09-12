"""
Weather Forecast Module
"""

import os
import requests
from datetime import datetime
from typing import Dict

from modules.utils import CLIColors

class WeatherManager:
    def __init__(self):
        self.api_key = os.getenv("OPENWEATHER_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        
    def get_current_weather(self, city: str) -> Dict:
        """Get current weather for a city"""
        if not self.api_key:
            return {"error": "OpenWeather API key not found in .env file"}
            
        url = f"{self.base_url}/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
    
    def get_forecast(self, city: str, days: int = 5) -> Dict:
        """Get weather forecast for a city"""
        if not self.api_key:
            return {"error": "OpenWeather API key not found in .env file"}
            
        url = f"{self.base_url}/forecast"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
            "cnt": days * 8  # 8 forecasts per day (every 3 hours)
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"API request failed: {str(e)}"}
    
    def format_current_weather(self, data: Dict) -> str:
        """Format current weather data for display"""
        if "error" in data:
            return f"{CLIColors.RED}❌ {data['error']}{CLIColors.END}"
            
        try:
            city = data['name']
            country = data['sys']['country']
            temp = data['main']['temp']
            feels_like = data['main']['feels_like']
            humidity = data['main']['humidity']
            pressure = data['main']['pressure']
            description = data['weather'][0]['description'].title()
            wind_speed = data['wind']['speed']
            
            # Weather emoji mapping
            weather_emojis = {
                "clear": "☀️",
                "clouds": "☁️",
                "rain": "🌧️",
                "drizzle": "🌦️",
                "thunderstorm": "⛈️",
                "snow": "🌨️",
                "mist": "🌫️",
                "fog": "🌫️"
            }
            
            main_weather = data['weather'][0]['main'].lower()
            emoji = weather_emojis.get(main_weather, "🌤️")
            
            output = f"""
{CLIColors.CYAN}{CLIColors.BOLD}🌍 Current Weather for {city}, {country}{CLIColors.END}
{CLIColors.YELLOW}{'=' * 50}{CLIColors.END}

{emoji} {CLIColors.BOLD}Condition:{CLIColors.END} {description}
🌡️  {CLIColors.BOLD}Temperature:{CLIColors.END} {temp}°C (feels like {feels_like}°C)
💧 {CLIColors.BOLD}Humidity:{CLIColors.END} {humidity}%
📊 {CLIColors.BOLD}Pressure:{CLIColors.END} {pressure} hPa
💨 {CLIColors.BOLD}Wind Speed:{CLIColors.END} {wind_speed} m/s
            """
            
            return output
            
        except KeyError as e:
            return f"{CLIColors.RED}❌ Error parsing weather data: {str(e)}{CLIColors.END}"
    
    def format_forecast(self, data: Dict) -> str:
        """Format forecast data for display"""
        if "error" in data:
            return f"{CLIColors.RED}❌ {data['error']}{CLIColors.END}"
            
        try:
            city = data['city']['name']
            country = data['city']['country']
            
            output = f"""
{CLIColors.CYAN}{CLIColors.BOLD}📅 5-Day Forecast for {city}, {country}{CLIColors.END}
{CLIColors.YELLOW}{'=' * 60}{CLIColors.END}
"""
            
            # Group forecasts by day
            daily_forecasts = {}
            for item in data['list']:
                date = datetime.fromtimestamp(item['dt']).strftime('%Y-%m-%d')
                if date not in daily_forecasts:
                    daily_forecasts[date] = []
                daily_forecasts[date].append(item)
            
            # Display first 5 days
            for i, (date, forecasts) in enumerate(list(daily_forecasts.items())[:5]):
                day_name = datetime.strptime(date, '%Y-%m-%d').strftime('%A, %B %d')
                
                # Get daily min/max temps
                temps = [f['main']['temp'] for f in forecasts]
                min_temp = min(temps)
                max_temp = max(temps)
                
                # Get most common weather condition
                conditions = [f['weather'][0]['main'] for f in forecasts]
                main_condition = max(set(conditions), key=conditions.count)
                
                weather_emojis = {
                    "Clear": "☀️",
                    "Clouds": "☁️", 
                    "Rain": "🌧️",
                    "Drizzle": "🌦️",
                    "Thunderstorm": "⛈️",
                    "Snow": "🌨️",
                    "Mist": "🌫️",
                    "Fog": "🌫️"
                }
                
                emoji = weather_emojis.get(main_condition, "🌤️")
                
                output += f"""
{emoji} {CLIColors.BOLD}{day_name}{CLIColors.END}
   🌡️  {min_temp:.1f}°C - {max_temp:.1f}°C | 🌤️  {main_condition}
"""
            
            return output
            
        except KeyError as e:
            return f"{CLIColors.RED}❌ Error parsing forecast data: {str(e)}{CLIColors.END}"

def weather_menu():
    """Weather forecast menu"""
    print(f"\n{CLIColors.CYAN}🌤️ Weather Forecast{CLIColors.END}")
    print("=" * 50)
    
    weather = WeatherManager()
    
    options = {
        "1": "Current Weather",
        "2": "5-Day Forecast",
        "3": "Weather for Multiple Cities",
        "4": "Back to Main Menu"
    }
    
    for key, value in options.items():
        print(f"  {key}. {value}")
    
    choice = input(f"\n{CLIColors.BOLD}Choose option (1-4): {CLIColors.END}").strip()
    
    if choice == "1":
        city = input(f"{CLIColors.YELLOW}Enter city name: {CLIColors.END}").strip()
        if city:
            print(f"\n{CLIColors.BLUE}🔍 Fetching current weather for {city}...{CLIColors.END}")
            data = weather.get_current_weather(city)
            print(weather.format_current_weather(data))
        else:
            print(f"{CLIColors.RED}❌ Please enter a valid city name{CLIColors.END}")
    
    elif choice == "2":
        city = input(f"{CLIColors.YELLOW}Enter city name: {CLIColors.END}").strip()
        if city:
            print(f"\n{CLIColors.BLUE}🔍 Fetching 5-day forecast for {city}...{CLIColors.END}")
            data = weather.get_forecast(city)
            print(weather.format_forecast(data))
        else:
            print(f"{CLIColors.RED}❌ Please enter a valid city name{CLIColors.END}")
    
    elif choice == "3":
        cities_input = input(f"{CLIColors.YELLOW}Enter cities (comma-separated): {CLIColors.END}").strip()
        if cities_input:
            cities = [city.strip() for city in cities_input.split(",")]
            for city in cities:
                print(f"\n{CLIColors.BLUE}🔍 Fetching weather for {city}...{CLIColors.END}")
                data = weather.get_current_weather(city)
                print(weather.format_current_weather(data))
        else:
            print(f"{CLIColors.RED}❌ Please enter valid city names{CLIColors.END}")
    
    elif choice == "4":
        return
    else:
        print(f"{CLIColors.YELLOW}⚠️ Invalid option{CLIColors.END}")
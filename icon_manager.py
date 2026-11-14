import tkinter as tk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import os

class IconManager:
    _instance = None
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            cls._instance._init_font()
        return cls._instance

    def _init_font(self):
        try:
            # Try to load Windows 10/11 native icon font
            self.font_path = "segmdl2.ttf"
            # Just test if it can be loaded
            ImageFont.truetype(self.font_path, 20)
        except IOError:
            # Fallback to Segoe UI Symbol
            try:
                self.font_path = "seguisym.ttf"
                ImageFont.truetype(self.font_path, 20)
            except IOError:
                self.font_path = "arial.ttf" # Last resort fallback

    def get_icon(self, unicode_char, size=24, color="black"):
        """
        Generate a PhotoImage from a unicode character using Segoe MDL2 Assets.
        """
        cache_key = (unicode_char, size, color)
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            font = ImageFont.truetype(self.font_path, size)
            
            # Create a transparent image
            # The size should be slightly larger to accommodate the character
            img_size = int(size * 1.5)
            img = Image.new('RGBA', (img_size, img_size), (255, 255, 255, 0))
            draw = ImageDraw.Draw(img)
            
            # Calculate text size and position to center it
            left, top, right, bottom = font.getbbox(unicode_char)
            text_width = right - left
            text_height = bottom - top
            
            x = (img_size - text_width) / 2 - left
            y = (img_size - text_height) / 2 - top
            
            draw.text((x, y), unicode_char, font=font, fill=color)
            
            photo = ImageTk.PhotoImage(img)
            self._cache[cache_key] = photo
            return photo
        except Exception as e:
            print(f"Error generating icon: {e}")
            # Return an empty image as fallback
            img = Image.new('RGBA', (size, size), (255, 255, 255, 0))
            photo = ImageTk.PhotoImage(img)
            self._cache[cache_key] = photo
            return photo

# Common icons mapped to Segoe MDL2 Assets
ICONS = {
    'dashboard': '\uE9D9',
    'invoice': '\uE8A5',
    'accounts_rec': '\uE8C7',
    'accounts_pay': '\uE8CE',
    'employees': '\uE716',
    'transactions': '\uE8A3',
    'customers': '\uE716',
    'treasury': '\uE825',
    'reports': '\uE9F9',
    'settings': '\uE713',
    'search': '\uE721',
    'add': '\uE710',
    'money': '\uE825',
    'revenue': '\uE224',
    'expenses': '\uE225',
    'calendar': '\uE787',
    'rocket': '\uE80A'
}

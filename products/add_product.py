#!/usr/bin/env python3
"""
Interactive tool to add a product to the Wix products CSV.

Usage:
    python add_product.py <csv_file>

Example:
    python add_product.py wix_products.csv
"""

import csv
import sys
import uuid
import argparse
import requests
import itertools
import hashlib
import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote, urlparse
from PIL import Image
import io

try:
    from pick import pick
    PICK_AVAILABLE = True
except ImportError:
    PICK_AVAILABLE = False
    print("⚠️  להתקנת בחירה עם חיצים, הרץ: pip install pick --break-system-packages")
    print("   כרגע תוכל לבחור רק באמצעות מספרים\n")

# Memory file to store last choices
MEMORY_FILE = Path.home() / '.add_product_memory.json'


def load_memory() -> Dict:
    """Load previous choices from memory file"""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_memory(memory: Dict):
    """Save choices to memory file"""
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
            f.flush()  # Ensure data is written
    except Exception as e:
        # Debug: uncomment to see errors
        # print(f"Memory save error: {e}")
        pass


# GitHub base URL for images
GITHUB_BLOB_URL = "https://raw.github.com/hultzotKaduregel/2025-2026-products/refs/heads/main/images"

# Season options
SEASONS = ["2025/2026", "2026/2027", "2027/2028", "2028/2029", "2029/2030"]

# Categories
CATEGORIES = [
    "חולצות גברים",
    "חולצות גברים ארוכות",
    "חליפות ילדים",
    "חולצות נשים",
    "מכנסיים",
    "אימוניות",
    "ג'קטים ומעילים"
]

# Sub-categories
VERSION_OPTIONS = ["גרסת אוהד", "גרסת שחקן"]
JACKET_OPTIONS = ["ג'קט", "מעיל רוח"]
SHIRT_TYPES = ["בית", "חוץ", "השלישית", "הרביעית", "שוער"]

# Teams
CLUB_TEAMS = [
    "ליברפול", "מנצ'סטר יונייטד", "מנצ'סטר סיטי", "ארסנל", "צ'לסי", "טוטנהאם",
    "ברצלונה", "ריאל מדריד", "אתלטיקו מדריד",
    "יובנטוס", "מילאן", "אינטר מילאנו", "רומא", "נאפולי",
    "באיירן מינכן", "בורוסיה דורטמונד",
    "פריז סן ז'רמן",
    "אייאקס",
    "מועדונים אחרים"
]

NATIONAL_TEAMS = [
    "אוסטרליה", "אוסטריה", "אורוגוואי", "איטליה", "אלגיריה", "אנגליה", "ארגנטינה", "ארה\"ב",
    "בלגיה", "ברזיל", "גרמניה", "הולנד", "טוניסיה", "יפן", "ירדן", "מקסיקו",
    "מצרים", "מרוקו", "נורווגיה", "סקוטלנד", "ספרד", "ערב הסעודית", "פורטוגל",
    "צרפת", "קטאר", "קנדה", "שוויץ",
    "נבחרות אחרות"
]

OTHER_NATIONALS = [
    "אוסטרליה", "אוסטריה", "אורוגוואי", "אלגיריה", "ארה\"ב",
    "טוניסיה", "יפן", "ירדן", "מקסיקו", "מצרים", "מרוקו",
    "נורווגיה", "סקוטלנד", "ערב הסעודית", "קטאר", "קנדה", "שוויץ",
    "נבחרות אחרות"
]

# Size options
SIZE_OPTIONS_SMALL = "S;M;L;XL;2XL"
SIZE_OPTIONS_LARGE = "S;M;L;XL;2XL;3XL;4XL"
SIZE_OPTIONS_WOMEN = "S;M;L;XL"
SIZE_OPTIONS_KIDS = "16: 95-105 ס״מ;18: 105-115 ס״מ;20: 115-125 ס״מ;22: 125-135 ס״מ;24: 135-145 ס״מ;26: 145-155 ס״מ;28: 155-165 ס״מ"
SIZE_OPTIONS_PANTS = "S;M;L;XL;2XL"
SIZE_OPTIONS_KIDS_NUMBERS = "10;12;14;16;18"
SIZE_OPTIONS_TRACKSUIT_ALL = "10;12;14;16;18;S;M;L;XL;2XL"

# Tracksuit/Jacket age group options
AGE_GROUP_OPTIONS = ["ילדים", "מבוגרים"]

# Tracksuit size range options
TRACKSUIT_SIZE_OPTIONS = ["10-2XL", "10-18", "S-2XL"]

# Default prices per category
CATEGORY_PRICES = {
    "חולצות גברים": "250.0",
    "חולצות גברים ארוכות": "280.0",
    "חליפות ילדים": "260.0",
    "חולצות נשים": "250.0",
    "מכנסיים": "79.9",
    "אימוניות": "340.0",
    "ג'קטים ומעילים": "340.0",  # Default for adults
    "ג'קטים ומעילים למבוגרים": "340.0",
    "ג'קטים ומעילים לילדים": "370.0"
}

# Default discounts per category
CATEGORY_DISCOUNTS = {
    "חולצות גברים": "110.1",
    "חולצות גברים ארוכות": "130.1",
    "חליפות ילדים": "120.1",
    "חולצות נשים": "110.1",
    "מכנסיים": "0",
    "אימוניות": "100.1",
    "ג'קטים ומעילים": "140.1",  # Default for adults
    "ג'קטים ומעילים למבוגרים": "140.1",
    "ג'קטים ומעילים לילדים": "90.1"
}


def select_option(prompt: str, options: List[str], default_index: int = 0) -> str:
    """Display menu and get user selection"""
    
    # Ensure default_index is valid
    if default_index < 0 or default_index >= len(options):
        default_index = 0
    
    if PICK_AVAILABLE:
        # Use arrow-based selection with default
        selected, index = pick(options, prompt, indicator='=>', default_index=default_index)
        return selected
    else:
        # Fallback to number-based selection
        print(f"\n{prompt}")
        for i, option in enumerate(options, 1):
            marker = " (ברירת מחדל)" if (i - 1) == default_index else ""
            print(f"  {i}. {option}{marker}")
        
        while True:
            try:
                choice_input = input(f"\nבחר מספר (Enter = {default_index + 1}): ").strip()
                
                # If empty, use default
                if not choice_input:
                    return options[default_index]
                
                choice = int(choice_input)
                if 1 <= choice <= len(options):
                    return options[choice - 1]
                else:
                    print(f"❌ נא לבחור מספר בין 1 ל-{len(options)}")
            except ValueError:
                print("❌ נא להזין מספר תקין")


def yes_no_question(prompt: str) -> bool:
    """Ask yes/no question"""
    while True:
        answer = input(f"{prompt} (כן/לא): ").strip().lower()
        if answer in ["כן", "yes", "y", "1"]:
            return True
        elif answer in ["לא", "no", "n", "0"]:
            return False
        else:
            print("❌ נא להשיב 'כן' או 'לא'")


def download_image_as_jpg(url: str, output_path: Path) -> bool:
    """Download image and convert to JPG"""
    try:
        print(f"  מוריד: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Open image with PIL
        img = Image.open(io.BytesIO(response.content))
        
        # Convert to RGB if needed (for PNG with transparency, etc.)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Save as JPG
        img.save(output_path, 'JPEG', quality=95)
        print(f"  ✓ נשמר: {output_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ שגיאה בהורדת {url}: {e}")
        return False


def get_next_image_number(directory: Path) -> int:
    """Get next available image number in directory"""
    if not directory.exists():
        return 1
    
    existing_numbers = []
    for file in directory.glob("image*.jpg"):
        try:
            num = int(file.stem.replace("image", ""))
            existing_numbers.append(num)
        except ValueError:
            continue
    
    return max(existing_numbers, default=0) + 1


def download_images(urls: List[str], category: str, team: str, subdir: str) -> List[str]:
    """Download images and return GitHub URLs"""
    # Create directory structure
    base_dir = Path("./images")
    category_dir = base_dir / category / team / subdir
    category_dir.mkdir(parents=True, exist_ok=True)
    
    # Get starting image number
    start_num = get_next_image_number(category_dir)
    
    github_urls = []
    
    for i, url in enumerate(urls):
        image_num = start_num + i
        filename = f"image{image_num:03d}.jpg"
        output_path = category_dir / filename
        
        if download_image_as_jpg(url, output_path):
            # Create GitHub blob URL with proper encoding and ?raw=true
            relative_path = f"{category}/{team}/{subdir}/{filename}"
            encoded_path = quote(relative_path, safe='/')
            github_url = f"{GITHUB_BLOB_URL}/{encoded_path}"
            github_urls.append(github_url)
    
    return github_urls


def build_product_name(category: str, team: str, shirt_type: Optional[str], 
                       version: Optional[str], jacket_type: Optional[str], 
                       color: Optional[str], season: str, age_group: Optional[str] = None,
                       player_name: Optional[str] = None, player_number: Optional[str] = None) -> str:
    """Build product name based on selections"""
    
    season_short = season
    
    # חולצות גברים
    if category == "חולצות גברים":
        base_name = f"חולצת {team} {shirt_type} {season_short}"
        
        # Check if player-specific
        if player_name and player_number:
            return f"{base_name} ({player_name} #{player_number})"
        
        if version == "גרסת שחקן":
            return f"{base_name} - גרסת שחקן"
        return base_name
    
    # חולצות גברים ארוכות
    elif category == "חולצות גברים ארוכות":
        return f"חולצה ארוכה {team} {shirt_type} {season_short}"
    
    # חליפות ילדים
    elif category == "חליפות ילדים":
        return f"חליפת ילדים {team} {shirt_type} {season_short}"
    
    # חולצות נשים
    elif category == "חולצות נשים":
        return f"חולצת נשים {team} {shirt_type} {season_short}"
    
    # מכנסיים
    elif category == "מכנסיים":
        pants_type = shirt_type.replace("השלישית", "השלישי") if shirt_type else shirt_type
        return f"מכנס {team} {pants_type} {season_short}"
    
    # אימוניות
    elif category == "אימוניות":
        return f"אימונית {team} {color} {season_short}"
    
    # ג'קטים ומעילים
    elif category == "ג'קטים ומעילים":
        if age_group == "ילדים":
            return f"{jacket_type} ילדים {team} {color} {season_short}"
        else:
            return f"{jacket_type} {team} {color} {season_short}"
    
    return ""


def create_product_row(product_info: Dict) -> Dict:
    """Create a product row for the CSV"""
    
    handle_id = f"product_{uuid.uuid4()}"
    product_name = product_info['name']
    season_full = product_info['season']  # e.g., "2025/2026"
    year1 = season_full.split('/')[0][-2:]  # "25"
    year2 = season_full.split('/')[1][-2:]  # "26"
    season_yy = f"{year1}/{year2}" # "25/26"
    description_name = product_name.replace(f"{season_full.split('/')[1]}/{season_full.split('/')[0]}", season_yy)
    description = f"<p>{description_name}</p>"
    category = product_info['category']
    
    # Build collection - special handling for tracksuits and jackets
    collection_parts = []
    
    if category == "אימוניות":
        # For tracksuits, collection includes age-specific sub-categories
        tracksuit_range = product_info.get('tracksuit_range', 'S-2XL')
        if tracksuit_range == "10-2XL":
            collection_parts = [category, product_info['team'], "אימוניות לילדים", "אימוניות למבוגרים"]
        elif tracksuit_range == "10-18":
            collection_parts = [category, product_info['team'], "אימוניות לילדים"]
        else:  # S-2XL
            collection_parts = [category, product_info['team'], "אימוניות למבוגרים"]
    
    elif category == "ג'קטים ומעילים":
        # For jackets/coats, collection includes age group
        age_group = product_info.get('age_group', 'מבוגרים')
        if age_group == "ילדים":
            collection_parts = [category, f"{category} לילדים", product_info['team']]
        else:
            collection_parts = [category, f"{category} למבוגרים", product_info['team']]
    
    else:
        # Regular categories
        collection_parts = [category]
        
        team = product_info['team']
        collection_parts.append(team)
        if team in OTHER_NATIONALS:
            collection_parts.append("נבחרות אחרות")

    collection = ";".join(collection_parts)
    
    # Determine default sizes based on category and age group
    if category == "חליפות ילדים":
        default_sizes = SIZE_OPTIONS_KIDS
    elif category == "חולצות נשים":
        default_sizes = SIZE_OPTIONS_WOMEN
    elif category == "מכנסיים":
        default_sizes = SIZE_OPTIONS_PANTS
    elif category in ["חולצות גברים", "חולצות גברים ארוכות"]:
        default_sizes = SIZE_OPTIONS_LARGE  # Will be overridden for גרסת אוהד
    elif category == "אימוניות":
        tracksuit_range = product_info.get('tracksuit_range', 'S-2XL')
        if tracksuit_range == "10-2XL":
            default_sizes = SIZE_OPTIONS_TRACKSUIT_ALL
        elif tracksuit_range == "10-18":
            default_sizes = SIZE_OPTIONS_KIDS_NUMBERS
        else:  # S-2XL
            default_sizes = SIZE_OPTIONS_SMALL
    elif category == "ג'קטים ומעילים":
        age_group = product_info.get('age_group', 'מבוגרים')
        if age_group == "ילדים":
            default_sizes = SIZE_OPTIONS_KIDS_NUMBERS
        else:
            default_sizes = SIZE_OPTIONS_SMALL
    else:
        default_sizes = SIZE_OPTIONS_LARGE
    
    # Determine price and discount based on category and age group
    price_category = category
    if category == "ג'קטים ומעילים":
        age_group = product_info.get('age_group', 'מבוגרים')
        price_category = f"{category} ל{age_group}"
    
    # Base row with correct field order
    row = {
        'handleId': handle_id,
        'fieldType': 'Product',
        'name': product_name,
        'description': description,
        'productImageUrl': ';'.join(product_info['images']),
        'collection': collection,
        'sku': '',
        'ribbon': '',
        'price': CATEGORY_PRICES.get(price_category, '280.0'),
        'surcharge': '',
        'visible': 'true',
        'discountMode': 'AMOUNT',
        'discountValue': CATEGORY_DISCOUNTS.get(price_category, '130.1'),
        'inventory': 'InStock',
        'weight': '',
        'cost': ''
    }
    
    # Add options based on category
    option_num = 1
    
    # Size option (for most categories)
    if category in ["חולצות גברים", "חולצות גברים ארוכות", "חליפות ילדים", 
                    "חולצות נשים", "מכנסיים", "אימוניות", "ג'קטים ומעילים"]:
        row[f'productOptionName{option_num}'] = 'מידה'
        row[f'productOptionType{option_num}'] = 'DROP_DOWN'
        row[f'productOptionDescription{option_num}'] = product_info.get('sizes', default_sizes)
        option_num += 1
    
    # Patch option (for shirts and kids suits)
    if category in ['חולצות גברים', 'חולצות גברים ארוכות', 'חליפות ילדים']:
        row[f'productOptionName{option_num}'] = 'פאץ׳'
        row[f'productOptionType{option_num}'] = 'DROP_DOWN'
        # Check if team is a national team
        team = product_info['team']
        if team in NATIONAL_TEAMS:
            row[f'productOptionDescription{option_num}'] = 'ללא פאץ׳;גביע העולם 2026'
        else:
            row[f'productOptionDescription{option_num}'] = product_info.get('patch_options', 'ללא פאץ׳;ליגה;ליגת האלופות')
        option_num += 1
    
    # Complete set option (shorts/socks)
    if 'set_option' in product_info:
        if category in ['חליפות ילדים', 'מכנסיים']:
            # For kids suits and pants - name is "הוסף גרביים"
            row[f'productOptionName{option_num}'] = 'הוסף גרביים'
        elif category == "ג'קטים ומעילים":
            # For jackets (adults only) - name is "הוסף מכנסיים"
            row[f'productOptionName{option_num}'] = 'הוסף מכנסיים'
        else:
            # For shirts - name is "השלם לסט"
            row[f'productOptionName{option_num}'] = 'השלם לסט'
        
        row[f'productOptionType{option_num}'] = 'DROP_DOWN'
        row[f'productOptionDescription{option_num}'] = product_info['set_option']
        option_num += 1
    
    # Fill remaining option fields with empty strings
    for i in range(option_num, 7):
        row[f'productOptionName{i}'] = ''
        row[f'productOptionType{i}'] = ''
        row[f'productOptionDescription{i}'] = ''
    
    # Add additional info sections
    add_additional_info(row, category)
    
    # Custom text fields
    if category in ['חולצות גברים', 'חולצות גברים ארוכות', 'חליפות ילדים', 'חולצות נשים']:
        # For shirts - add "מספר" (number) field
        row['customTextField1'] = 'שם מאחור באנגלית'
        row['customTextCharLimit1'] = '20'
        row['customTextMandatory1'] = 'false'
        row['customTextField2'] = 'מספר מאחור'
        row['customTextCharLimit2'] = '2'
        row['customTextMandatory2'] = 'false'
    elif category == 'מכנסיים':
        # For pants - add "מספר" (number) field
        row['customTextField1'] = 'מספר'
        row['customTextCharLimit1'] = '2'
        row['customTextMandatory1'] = 'false'
        row['customTextField2'] = ''
        row['customTextCharLimit2'] = ''
        row['customTextMandatory2'] = ''
    else:
        row['customTextField1'] = ''
        row['customTextCharLimit1'] = ''
        row['customTextMandatory1'] = ''
        row['customTextField2'] = ''
        row['customTextCharLimit2'] = ''
        row['customTextMandatory2'] = ''
    
    # Brand at the end
    row['brand'] = ''
    
    return row


def create_variant_rows(product_row: Dict, product_info: Dict, fieldnames: List[str]) -> List[Dict]:
    """Create variant rows for all combinations of product options"""
    
    category = product_info['category']
    handle_id = product_row['handleId']
    
    # Collect all option values
    option_values_lists = []
    
    for i in range(1, 7):
        option_desc = product_row.get(f'productOptionDescription{i}', '')
        if option_desc:
            # Split by semicolon to get individual values
            values = [v.strip() for v in option_desc.split(';') if v.strip()]
            option_values_lists.append(values)
    
    # If no options, no variants needed
    if not option_values_lists:
        return []
    
    # Generate all combinations
    variants = []
    for combination in itertools.product(*option_values_lists):
        variant = {col: '' for col in fieldnames}
        
        variant['handleId'] = handle_id
        variant['fieldType'] = 'Variant'
        variant['visible'] = 'true'
        variant['inventory'] = 'InStock'
        
        # Set option values for this variant
        for i, value in enumerate(combination, 1):
            variant[f'productOptionDescription{i}'] = value
        
        # Calculate surcharge based on the selected options
        surcharge = 0.0
        for value in combination:
            if 'הוסף מכנס - 50.00 ₪' in value:
                surcharge += 50.0
            elif 'הוסף מכנס+גרביים - 80.00 ₪' in value:
                surcharge += 80.0
            elif 'כן - 30 ₪' in value:
                surcharge += 30.0
            elif 'כן - 99.90 ₪' in value:
                surcharge += 99.9
        
        if surcharge > 0:
            variant['surcharge'] = str(surcharge)
        
        variants.append(variant)
    
    return variants


def add_additional_info(row: Dict, category: str):
    """Add additional info sections to the row"""
    
    # Return policy (always first)
    row['additionalInfoTitle1'] = 'החזרת מוצר'
    row['additionalInfoDescription1'] = '''<ul dir="rtl">
\t<li>ההזמנות הינם הזמנות פרטיות של כל לקוח, החברה אינה מחזיקה מלאי ולכן לא ינתן החזר כספי או החלפה של מוצר.&nbsp;</li>
\t<li>החברה פועלת על פי טבלת מידות והמלצה של נציגי השירות ולא לוקחת אחריות על בחירת המידה של הלקוח, לכן לא יתאפשר החלפה של מידה.&nbsp;</li>
\t<li>החלפה / החזר כספי ינתן רק כאשר המוצר הגיע פגום או שונה ממה שהוזמן, החלפה או החזר כספי ינתנו עד 14 ימים מיום קבלת ההזמנה.&nbsp;</li>
\t<li>במידה והמוצר הגיע פגום / שונה ממה שהוזמן , ניתן לפנות אלינו דרך דף הפייסבוק בהודעה פרטית או דרך צור קשר באתר ולרשום במסודר את הבעיה בצירוף מספר הזמנה.&nbsp;</li>
\t<li>במידה והמוצר לא הגיע 60 ימים מיום ההזמנה, ינתן החזר כספי מלא.&nbsp;</li>
</ul>'''
    
    # Size table - different for each category
    if category in ['חולצות גברים', 'חולצות גברים ארוכות']:
        row['additionalInfoTitle2'] = 'טבלת מידות'
        row['additionalInfoDescription2'] = '''<div>
<table dir="rtl">
\t<tbody>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><strong>מידה</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong><span><span>גובה</span></span></strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong><span><span>אורך</span></span></strong></p>

\t\t\t<p><strong><span><span>חולצה</span></span></strong></p>

\t\t\t<p><span><span>(ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong><span><span>רוחב</span></span></strong></p>

\t\t\t<p><strong><span><span>חולצה</span></span></strong></p>

\t\t\t<p><span><span>(ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong><span><span>אורך</span></span></strong></p>

\t\t\t<p><strong><span><span>שרוול</span></span></strong></p>

\t\t\t<p><span><span>(ס״מ)</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>S</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>160-165</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>71</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>52</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>21</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>M</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>165-170</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>73</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>54</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>22</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>L</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>170-175</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>75</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>56</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>23</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>XL</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>175-180</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>77</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>58</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>24</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>2XL</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>180-185</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>79</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>60</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>25</span></span></p>
\t\t\t</td>
\t\t</tr>
\t</tbody>
</table>
</div>'''
    
    elif category == 'חליפות ילדים':
        row['additionalInfoTitle2'] = 'טבלת מידות ילדים'
        row['additionalInfoDescription2'] = '''<table dir="rtl">
\t<tbody>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>מידה</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>גובה (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>אורך חולצה (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>רוחב חזה (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>אורך מכנס (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>מותן (ס״מ)</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>16</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>95-105</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>43</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>32</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>32</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>20-37</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>18</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>105-115</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>47</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>34</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>34</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>21-39</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>20</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>115-125</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>50</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>36</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>36</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>22-41</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>22</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>125-135</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>53</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>38</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>38</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>23-42</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>24</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>135-145</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>56</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>40</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>39</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>24-44</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>26</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>145-155</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>58</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>42</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>40</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>25-47</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>28</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>155-165</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>61</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>44</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>43</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>26-50</span></span></p>
\t\t\t</td>
\t\t</tr>
\t</tbody>
</table>

<p>*עם סטיית תקן של 2-3 ס"מ</p>'''
    
    elif category == 'חולצות נשים':
        row['additionalInfoTitle2'] = 'טבלת מידות נשים'
        row['additionalInfoDescription2'] = '''<div>
<table dir="rtl">
\t<tbody>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>מידה</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>גובה (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>אורך חולצה (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>רוחב חזה (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>רוחב מותניים (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>אורך שרוול (ס״מ)</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>S</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>150-155</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>63</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>42</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>37</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>27.5</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>M</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>155-160</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>65</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>44</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>39</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>29</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>L</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>160-170</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>67</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>46</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>41</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>30.5</span></span></p>
\t\t\t</td>
\t\t</tr>
\t</tbody>
</table>
</div>'''
    
    elif category == 'אימוניות':
        row['additionalInfoTitle2'] = 'טבלת מידות'
        row['additionalInfoDescription2'] = '''<p><strong>מידות ילדים:</strong></p>

<table>
\t<tbody>
\t\t<tr>
\t\t\t<th>מידה</th>
\t\t\t<th>
\t\t\t<p>גובה</p>

\t\t\t<p>(ס״מ)</p>
\t\t\t</th>
\t\t\t<th>אורך ג׳קט (ס״מ)</th>
\t\t\t<th>רוחב חזה (ס״מ)</th>
\t\t\t<th>אורך שרוול (ס״מ)</th>
\t\t\t<th>אורך מכנס (ס״מ)</th>
\t\t</tr>
\t\t<tr>
\t\t\t<th>10</th>
\t\t\t<td>115-125</td>
\t\t\t<td>55</td>
\t\t\t<td>40</td>
\t\t\t<td>59.5</td>
\t\t\t<td>78</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>12</th>
\t\t\t<td>125-135</td>
\t\t\t<td>57.5</td>
\t\t\t<td>42</td>
\t\t\t<td>61</td>
\t\t\t<td>80</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>14</th>
\t\t\t<td>135-145</td>
\t\t\t<td>60</td>
\t\t\t<td>44</td>
\t\t\t<td>63.5</td>
\t\t\t<td>83</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>16</th>
\t\t\t<td>145-155</td>
\t\t\t<td>62.5</td>
\t\t\t<td>46</td>
\t\t\t<td>66</td>
\t\t\t<td>86</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>18</th>
\t\t\t<td>155-165</td>
\t\t\t<td>65</td>
\t\t\t<td>48</td>
\t\t\t<td>68.5</td>
\t\t\t<td>89</td>
\t\t</tr>
\t</tbody>
</table>

<p>&nbsp;</p>

<p><strong>מידות גברים:</strong></p>

<table>
\t<tbody>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><strong>מידה</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong>גובה</strong></p>

\t\t\t<p><strong>(ס״מ)</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong>אורך ג׳קט (ס״מ)</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong>היקף חזה (ס״מ)</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong>אורך שרוול (ס״מ)</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><strong>אורך מכנס (ס״מ)</strong></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><strong>S</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>155-170</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>66</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>98</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>58</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>98.5</p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><strong>M</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>165-175</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>68</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>104</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>59</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>101</p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><strong>L</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>170-185</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>70</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>110</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>60</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>103.5</p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><strong>XL</strong></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>180-195</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>72</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>116</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>61</p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p>106</p>
\t\t\t</td>
\t\t</tr>
\t</tbody>
</table>'''
    
    elif category == "ג'קטים ומעילים":
        # Check age group from product_info if available
        age_group = None
        # Try to extract from name or use default
        row['additionalInfoTitle2'] = 'טבלת מידות ג׳קטים'
        # For kids jackets - simplified table
        if 'ילדים' in row.get('name', ''):
            row['additionalInfoDescription2'] = '''<div>
<table dir="rtl">
\t<tbody>
\t\t<tr>
\t\t\t<th>מידה</th>
\t\t\t<th>
\t\t\t<p>גובה</p>

\t\t\t<p>(ס״מ)</p>
\t\t\t</th>
\t\t\t<th>אורך ג׳קט (ס״מ)</th>
\t\t\t<th>רוחב חזה (ס״מ)</th>
\t\t\t<th>אורך שרוול (ס״מ)</th>
\t\t\t<th>אורך מכנס (ס״מ)</th>
\t\t</tr>
\t\t<tr>
\t\t\t<th>10</th>
\t\t\t<td>115-125</td>
\t\t\t<td>55</td>
\t\t\t<td>40</td>
\t\t\t<td>59.5</td>
\t\t\t<td>78</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>12</th>
\t\t\t<td>125-135</td>
\t\t\t<td>57.5</td>
\t\t\t<td>42</td>
\t\t\t<td>61</td>
\t\t\t<td>80</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>14</th>
\t\t\t<td>135-145</td>
\t\t\t<td>60</td>
\t\t\t<td>44</td>
\t\t\t<td>63.5</td>
\t\t\t<td>83</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>16</th>
\t\t\t<td>145-155</td>
\t\t\t<td>62.5</td>
\t\t\t<td>46</td>
\t\t\t<td>66</td>
\t\t\t<td>86</td>
\t\t</tr>
\t\t<tr>
\t\t\t<th>18</th>
\t\t\t<td>155-165</td>
\t\t\t<td>65</td>
\t\t\t<td>48</td>
\t\t\t<td>68.5</td>
\t\t\t<td>89</td>
\t\t</tr>
\t</tbody>
</table>

<p dir="rtl">&nbsp;</p>

<p dir="rtl">&nbsp;</p>
</div>

<p dir="rtl">&nbsp;</p>'''
        else:
            # Adults jacket table
            row['additionalInfoDescription2'] = '''<div>
<table dir="rtl">
\t<tbody>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>מידה</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>גובה</span></span></p>

\t\t\t<p><span><span>(ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>אורך ג׳קט (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>רוחב חזה (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>אורך שרוול (ס״מ)</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>פתיחת שרוול (ס״מ)</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>S</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>165-170</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>66</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>51</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>84.5</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>13</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>M</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>170-175</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>69</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>53</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>87</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>13</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>L</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>175-180</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>72</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>55</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>89.5</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>14</span></span></p>
\t\t\t</td>
\t\t</tr>
\t\t<tr>
\t\t\t<td>
\t\t\t<p><span><span>XL</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>180-185</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>75</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>57</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>92</span></span></p>
\t\t\t</td>
\t\t\t<td>
\t\t\t<p><span><span>14</span></span></p>
\t\t\t</td>
\t\t</tr>
\t</tbody>
</table>
</div>

<p dir="rtl">&nbsp;</p>'''
    
    else:
        # Empty for other categories, but field must exist
        row['additionalInfoTitle2'] = ''
        row['additionalInfoDescription2'] = ''
    
    # Washing instructions (always third)
    row['additionalInfoTitle3'] = 'הוראות כביסה'
    row['additionalInfoDescription3'] = '''<ul dir="rtl">
\t<li>יש לכבס את המוצר בכביסה עדינה ובטמפרטורת 30 מעלות.</li>
\t<li>אין להשתמש במלבין או מרכך כביסה.</li>
\t<li>אין לגהץ את התחתית של הכתובת והמספרים על החולצה.</li>
</ul>'''
    
    # Shipping info (always fourth)
    row['additionalInfoTitle4'] = 'משלוח'
    row['additionalInfoDescription4'] = '''<ul dir="rtl">
\t<li>זמן האספקה הוא&nbsp;30-60 ימי עסקים&nbsp;מיום ביצוע ההזמנה.</li>
\t<li>המשלוח חינם.</li>
\t<li>המשלוח מגיע עד דלת הבית / לתא חכם בהתאם לבחירה בתהליך ההזמנה.</li>
</ul>'''
    
    # Empty fields 5 and 6
    row['additionalInfoTitle5'] = ''
    row['additionalInfoDescription5'] = ''
    row['additionalInfoTitle6'] = ''
    row['additionalInfoDescription6'] = ''


# Category order
CATEGORY_ORDER = {
    "חולצות גברים": 1,
    "חולצות גברים ארוכות": 2,
    "חליפות ילדים": 3,
    "חולצות נשים": 4,
    "מכנסיים": 5,
    "אימוניות": 6,
    "ג'קטים ומעילים": 7
}

# Team order (clubs then national teams alphabetically)
TEAM_ORDER = {}
for i, team in enumerate(CLUB_TEAMS):
    TEAM_ORDER[team] = i

# National teams in alphabetical order
national_sorted = sorted([t for t in NATIONAL_TEAMS if t != "נבחרות אחרות"])
national_sorted.append("נבחרות אחרות")
for i, team in enumerate(national_sorted):
    TEAM_ORDER[team] = len(CLUB_TEAMS) + i

# Shirt type order
SHIRT_TYPE_ORDER = {
    "בית": 1,
    "חוץ": 2,
    "השלישית": 3,
    "הרביעית": 4,
    "שוער": 5,
    "שוער 1": 5,
    "שוער 2": 6
}


def check_product_exists(csv_file: Path, product_info: Dict) -> Optional[str]:
    """
    Check if a product with the same year, category, team, and sub-category exists.
    Returns the existing product name if found, None otherwise.
    """
    if not csv_file.exists():
        return None
    
    # Build the expected product name pattern
    season_short = product_info['season']
    category = product_info['category']
    team = product_info['team']
    
    # Determine sub-category (shirt_type or color)
    if category in ["אימוניות", "ג'קטים ומעילים"]:
        sub_category = product_info.get('color', '')
    else:
        sub_category = product_info.get('shirt_type', '')
    
    # Read CSV and check for existing products
    with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if row['fieldType'] != 'Product':
                continue
            
            product_name = row.get('name', '')
            
            # Check if the product name contains all the key components
            # For חולצות גברים check both regular and גרסת אוהד versions
            if category == "חולצות גברים":
                # Check for base pattern with team, sub-category, and season
                # Also match numbered versions (e.g., "שוער", "שוער 1", "שוער 2")
                pattern = re.escape(f"{team} {sub_category}") + r'( \d+| [א-ת]+)? ' + re.escape(season_short)
                if re.search(pattern, product_name):
                    return product_name
            
            # For other categories, check exact pattern
            elif category == "חולצות גברים ארוכות":
                pattern = f"חולצה ארוכה {team} {sub_category} {season_short}"
                if pattern in product_name:
                    return product_name
            
            elif category == "חליפות ילדים":
                pattern = f"חליפת ילדים {team} {sub_category} {season_short}"
                if pattern in product_name:
                    return product_name
            
            elif category == "חולצות נשים":
                pattern = f"חולצת נשים {team} {sub_category} {season_short}"
                if pattern in product_name:
                    return product_name
            
            elif category == "מכנסיים":
                pants_type = sub_category.replace("השלישית", "השלישי") if sub_category else sub_category
                pattern = f"מכנס {team} {pants_type} {season_short}"
                if pattern in product_name:
                    return product_name
            
            elif category == "אימוניות":
                # Match color with optional number or text after it
                color_pattern = re.escape(sub_category) + r'( \d+| [א-ת]+)?'
                base_pattern = f"אימונית {team}"
                
                if base_pattern in product_name and re.search(color_pattern, product_name) and season_short in product_name:
                    return product_name
            
            elif category == "ג'קטים ומעילים":
                # Check if team, color (with optional number), and season are in the product name
                jacket_type = product_info.get('jacket_type', '')
                age_group = product_info.get('age_group', 'מבוגרים')
                
                # Build pattern to match color with optional number or text after it
                color_pattern = re.escape(sub_category) + r'( \d+| [א-ת]+)?'
                
                if team in product_name and re.search(color_pattern, product_name) and season_short in product_name:
                    if jacket_type in product_name and (age_group == "מבוגרים" or "ילדים" in product_name):
                        return product_name
    
    return None

def find_next_available_number(csv_file: Path, product_info: Dict, base_name: str) -> int:
    """Find the next available number suffix for a product"""
    if not csv_file.exists():
        return 1
    
    season_short = f"{product_info['season'].split('/')[1]}/{product_info['season'].split('/')[0]}"
    category = product_info['category']
    team = product_info['team']
    
    # Pattern to match numbered versions
    # e.g., "חולצת ברצלונה שוער 1 26/25", "חולצת ברצלונה שוער 2 26/25"
    existing_numbers = []
    
    with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if row['fieldType'] != 'Product':
                continue
            
            product_name = row.get('name', '')
            
            # Check if this product matches our base pattern
            # Extract base name without number (everything before the last space and year)
            parts = product_name.rsplit(' ', 1)
            if len(parts) == 2:
                name_without_year = parts[0]
                year_part = parts[1]
                
                # Check if year matches
                if year_part == season_short:
                    # Try to extract number from the end of name_without_year
                    # Pattern: base_name followed by optional space and digit
                    match = re.search(r'^(.+?)\s+(\d+)$', name_without_year)
                    if match:
                        name_base = match.group(1)
                        number = int(match.group(2))
                        
                        # Check if this matches our base (without number)
                        if base_name.strip() == name_base.strip():
                            existing_numbers.append(number)
                    else:
                        # No number suffix - this is the original (treat as 0)
                        if name_without_year.strip() == base_name.strip():
                            existing_numbers.append(0)
    
    # Find next available number
    if not existing_numbers:
        return 1
    
    # Find the first gap or return max + 1
    existing_numbers.sort()
    for i in range(1, max(existing_numbers) + 2):
        if i not in existing_numbers:
            return i
    
    return 1



def get_sort_key(row: Dict, product_info: Dict) -> tuple:
    """Generate sort key for a product row"""
    if row['fieldType'] != 'Product':
        # This shouldn't happen, but handle it
        return (999, 999, 999, "")
    
    # Extract info from the row
    name = row.get('name', '')
    collection = row.get('collection', '')
    
    # Parse collection to get category and team
    parts = collection.split(';')
    row_category = parts[0] if len(parts) > 0 else ''
    row_team = parts[1] if len(parts) > 1 else ''
    
    # Determine shirt_type_rank based on category
    shirt_type_rank = 0
    
    if row_category in ["אימוניות", "ג'קטים ומעילים"]:
        # For jackets/tracksuits: no shirt type sorting, use 0 for all
        # They will be sorted alphabetically by name (the 4th element in tuple)
        shirt_type_rank = 0
    else:
        # For shirts: extract shirt type from name
        row_shirt_type = None
        
        # Check for שוער 1 or שוער 2 first
        if " שוער 1 " in name:
            row_shirt_type = "שוער 1"
        elif " שוער 2 " in name:
            row_shirt_type = "שוער 2"
        else:
            # Check for regular shirt types
            for st in SHIRT_TYPES:
                if f" {st} " in name:
                    row_shirt_type = st
                    break
        
        shirt_type_rank = SHIRT_TYPE_ORDER.get(row_shirt_type, 0) if row_shirt_type else 0
    
    # Build sort key
    category_rank = CATEGORY_ORDER.get(row_category, 999)
    team_rank = TEAM_ORDER.get(row_team, 999)
    
    return (category_rank, team_rank, shirt_type_rank, name)


def get_product_sort_key(product_info: Dict) -> tuple:
    """Generate sort key for the new product"""
    category_rank = CATEGORY_ORDER.get(product_info['category'], 999)
    team_rank = TEAM_ORDER.get(product_info['team'], 999)
    shirt_type_rank = SHIRT_TYPE_ORDER.get(product_info.get('shirt_type'), 0) if product_info.get('shirt_type') else 0
    
    return (category_rank, team_rank, shirt_type_rank, product_info['name'])


def insert_product_in_order(csv_file: Path, product_row: Dict, product_info: Dict, fieldnames: List[str]):
    """Insert product in the correct sorted position or replace existing product"""
    
    # Generate variants for this product
    variant_rows = create_variant_rows(product_row, product_info, fieldnames)
    
    if not csv_file.exists():
        # File doesn't exist, create it with the product and variants
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(product_row)
            for variant in variant_rows:
                writer.writerow(variant)
        return
    
    # Read all existing rows
    rows = []
    with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    # Check if we're adding as goalkeeper 2
    if product_info.get('add_as_goalkeeper_2'):
        existing_name = product_info.get('existing_name')
        
        # Find and rename the existing product
        for i, row in enumerate(rows):
            if row['fieldType'] == 'Product' and row.get('name') == existing_name:
                # Check if custom suffix is provided
                if 'custom_suffix_existing' in product_info:
                    # Custom naming
                    parts = row['name'].rsplit(' ', 1)
                    new_name = f"{parts[0]} {product_info['custom_suffix_existing']} {parts[1]}"
                else:
                    # Default numbered naming
                    parts = row['name'].rsplit(' ', 1)
                    new_name = f"{parts[0]} 1 {parts[1]}"
                
                rows[i]['name'] = new_name
                update_product_in_merchant_feed(csv_file, existing_name, new_name)
                print(f"✓ המוצר הקיים שונה ל: {new_name}")
                break

        # Now insert the new goalkeeper 2 product in the correct position
        # (it should come right after goalkeeper 1)
        new_key = get_product_sort_key(product_info)
        insert_index = len(rows)
        
        for i, row in enumerate(rows):
            if row['fieldType'] == 'Product':
                row_key = get_sort_key(row, product_info)
                if new_key < row_key:
                    insert_index = i
                    break
        
        rows.insert(insert_index, product_row)
        # Insert variants right after the product
        for j, variant in enumerate(variant_rows):
            rows.insert(insert_index + 1 + j, variant)
        
        print(f"✓ המוצר החדש הוכנס במיקום {insert_index + 1}")
        
        # Write back all rows
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return
    
    # Check if we're replacing an existing product
    if product_info.get('replace_existing'):
        existing_name = product_info.get('existing_name')
        replaced = False
        
        # Find the existing product and its variants
        for i, row in enumerate(rows):
            if row['fieldType'] == 'Product' and row.get('name') == existing_name:
                # Found the product - now find all its variants
                product_index = i
                variant_count = 0
                
                # Count variants that follow this product
                j = i + 1
                while j < len(rows) and rows[j]['fieldType'] == 'Variant' and rows[j]['handleId'] == row['handleId']:
                    variant_count += 1
                    j += 1
                
                # Remove the old product and its variants
                for _ in range(variant_count + 1):
                    rows.pop(product_index)
                
                # Insert new product and variants at the same position
                rows.insert(product_index, product_row)
                for k, variant in enumerate(variant_rows):
                    rows.insert(product_index + 1 + k, variant)
                
                replaced = True
                print(f"✓ המוצר הוחלף במיקום {product_index + 1} (עם {len(variant_rows)} variants)")
                break
        
        if not replaced:
            print("⚠️  לא נמצא המוצר הקיים, מוסיף כמוצר חדש")
            # Fall through to insert as new product
        else:
            # Write back all rows
            with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            return
    
    # Not replacing - insert as new product in sorted position
    new_key = get_product_sort_key(product_info)
    insert_index = len(rows)  # Default to end
    
    for i, row in enumerate(rows):
        if row['fieldType'] == 'Product':
            row_key = get_sort_key(row, product_info)
            if new_key < row_key:
                insert_index = i
                break
    
    # Insert the product at the correct position
    rows.insert(insert_index, product_row)
    # Insert variants right after the product
    for j, variant in enumerate(variant_rows):
        rows.insert(insert_index + 1 + j, variant)
    
    # Write back all rows
    with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ המוצר הוכנס במיקום {insert_index + 1} (עם {len(variant_rows)} variants, סה\"כ {len(rows)} שורות)")


def interactive_add_product(csv_file: Path, append_to_merchant: bool = False):
    """Interactive process to add a product"""
    
    print("\n" + "="*70)
    print("הוספת מוצר חדש ל-CSV")
    print("="*70)
    
    # Load previous choices
    memory = load_memory()
    
    product_info = {}
    
    # 1. Season
    default_season_idx = 0
    if 'season' in memory and memory['season'] in SEASONS:
        default_season_idx = SEASONS.index(memory['season'])
    
    season = select_option("בחר עונה:", SEASONS, default_season_idx)
    product_info['season'] = season
    memory['season'] = season
    
    # 2. Category
    default_category_idx = 0
    if 'category' in memory and memory['category'] in CATEGORIES:
        default_category_idx = CATEGORIES.index(memory['category'])
    
    category = select_option("בחר קטגוריה:", CATEGORIES, default_category_idx)
    product_info['category'] = category
    memory['category'] = category
    
    # 3. Sub-category 1 (version/jacket type/age group)
    version = None
    jacket_type = None
    age_group = None
    tracksuit_range = None
    
    if category == "חולצות גברים":
        default_version_idx = 0
        if 'version' in memory and memory['version'] in VERSION_OPTIONS:
            default_version_idx = VERSION_OPTIONS.index(memory['version'])
        
        version = select_option("בחר גרסה:", VERSION_OPTIONS, default_version_idx)
        product_info['version'] = version
        memory['version'] = version

        # Ask if general or player-specific
        player_specific_options = ["כללית", "שחקן ספציפי"]
        default_player_idx = 0
        if 'player_specific' in memory and memory['player_specific'] in player_specific_options:
            default_player_idx = player_specific_options.index(memory['player_specific'])

        player_specific = select_option("בחר סוג חולצה:", player_specific_options, default_player_idx)
        product_info['player_specific'] = player_specific
        memory['player_specific'] = player_specific

        # If player-specific, ask for player name and number
        if player_specific == "שחקן ספציפי":
            player_name = input("\nהזן שם שחקן באנגלית: ").strip()
            if not player_name:
                print("❌ לא הוזן שם שחקן, אנא הרץ שוב")
                return
            
            product_info['player_name'] = player_name.upper()
            
            player_number = input("הזן מספר שחקן: ").strip()
            if not player_number:
                print("❌ לא הוזן מספר שחקן, אנא הרץ שוב")
                return
            
            product_info['player_number'] = player_number
    
    elif category == "אימוניות":
        # Ask for size range (which determines age groups in collection)
        default_range_idx = 0
        if 'tracksuit_range' in memory and memory['tracksuit_range'] in TRACKSUIT_SIZE_OPTIONS:
            default_range_idx = TRACKSUIT_SIZE_OPTIONS.index(memory['tracksuit_range'])
        
        tracksuit_range = select_option("בחר טווח מידות:", TRACKSUIT_SIZE_OPTIONS, default_range_idx)
        product_info['tracksuit_range'] = tracksuit_range
        memory['tracksuit_range'] = tracksuit_range
    
    elif category == "ג'קטים ומעילים":
        # First ask for jacket type
        default_jacket_idx = 0
        if 'jacket_type' in memory and memory['jacket_type'] in JACKET_OPTIONS:
            default_jacket_idx = JACKET_OPTIONS.index(memory['jacket_type'])
        
        jacket_type = select_option("בחר סוג:", JACKET_OPTIONS, default_jacket_idx)
        product_info['jacket_type'] = jacket_type
        memory['jacket_type'] = jacket_type
        
        # Then ask for age group
        default_age_idx = 0
        if 'age_group' in memory and memory['age_group'] in AGE_GROUP_OPTIONS:
            default_age_idx = AGE_GROUP_OPTIONS.index(memory['age_group'])
        
        age_group = select_option("בחר קבוצת גיל:", AGE_GROUP_OPTIONS, default_age_idx)
        product_info['age_group'] = age_group
        memory['age_group'] = age_group
    
    # 4. Sub-category 2 (shirt type or color)
    shirt_type = None
    color = None
    
    if category in ["אימוניות", "ג'קטים ומעילים"]:
        # Ask for color with default
        default_color = memory.get('color', '')
        color_input = input(f"\nהזן צבע (Enter = '{default_color}'): ").strip() if default_color else input("\nהזן צבע: ").strip()
        
        if not color_input and default_color:
            color = default_color
        else:
            color = color_input
        
        product_info['color'] = color
        memory['color'] = color
    else:
        # Ask for shirt type
        default_shirt_idx = 0
        if 'shirt_type' in memory and memory['shirt_type'] in SHIRT_TYPES:
            default_shirt_idx = SHIRT_TYPES.index(memory['shirt_type'])
        
        shirt_type = select_option("בחר סוג חולצה:", SHIRT_TYPES, default_shirt_idx)
        product_info['shirt_type'] = shirt_type
        memory['shirt_type'] = shirt_type
    
    # 5. Team
    all_teams = CLUB_TEAMS + NATIONAL_TEAMS
    
    default_team_idx = 0
    if 'team' in memory and memory['team'] in all_teams:
        default_team_idx = all_teams.index(memory['team'])
    
    if PICK_AVAILABLE:
        # Use arrow-based selection
        print("\n" + "="*70)
        team, index = pick(
            all_teams, 
            "בחר קבוצה (השתמש בחיצים ולחץ Enter):",
            indicator='=>',
            default_index=default_team_idx
        )
        
        # If "מועדונים אחרים" or "נבחרות אחרות", ask for custom name
        if team == "מועדונים אחרים":
            default_custom = memory.get('custom_club', '')
            custom_input = input(f"\nהזן שם מועדון (Enter = '{default_custom}'): ").strip() if default_custom else input("\nהזן שם מועדון: ").strip()
            
            if not custom_input and default_custom:
                custom_team_name = default_custom
            elif custom_input:
                custom_team_name = custom_input
                memory['custom_club'] = custom_input
            else:
                print("❌ לא הוזן שם, אנא הרץ שוב")
                return
            
            print(f"✓ נבחר: {custom_team_name}")
            product_info['custom_team_name'] = custom_team_name
        elif team == "נבחרות אחרות":
            default_custom = memory.get('custom_national', '')
            custom_input = input(f"\nהזן שם נבחרת (Enter = '{default_custom}'): ").strip() if default_custom else input("\nהזן שם נבחרת: ").strip()
            
            if not custom_input and default_custom:
                custom_team_name = default_custom
            elif custom_input:
                custom_team_name = custom_input
                memory['custom_national'] = custom_input
            else:
                print("❌ לא הוזן שם, אנא הרץ שוב")
                return
            
            print(f"✓ נבחר: {custom_team_name}")
            product_info['custom_team_name'] = custom_team_name
        
        product_info['team'] = team
        memory['team'] = team
        
        # Ask about additional patch options (for club teams only, not national teams)
        if category in ["חולצות גברים", "חולצות גברים ארוכות", "חליפות ילדים"] and shirt_type and team not in NATIONAL_TEAMS:
            print("\n" + "="*70)
            print("בחר פאצ׳ים נוספים להוסיף (מעבר ל'ללא פאץ׳' ו'ליגה'):")
            
            patch_extra_options = [
                "ליגת האלופות",
                "הליגה האירופית",
                "קונפרנס ליג",
                "ליגת האלופות והליגה האירופית",
                "ליגת האלופות וקונפרנס ליג"
            ]
            
            default_patch_idx = 0
            if 'patch_choice' in memory:
                try:
                    default_patch_idx = int(memory['patch_choice'])
                    if default_patch_idx < 0 or default_patch_idx >= len(patch_extra_options):
                        default_patch_idx = 0
                except:
                    default_patch_idx = 0
            
            selected_patch = select_option("בחר אופציה:", patch_extra_options, default_patch_idx)
            
            # Build patch options string
            if selected_patch == patch_extra_options[0]:
                # Default - Champions League only
                product_info['patch_options'] = 'ללא פאץ׳;ליגה;ליגת האלופות'
                memory['patch_choice'] = 0
            elif selected_patch == patch_extra_options[1]:
                # Europa League
                product_info['patch_options'] = 'ללא פאץ׳;ליגה;הליגה האירופית'
                memory['patch_choice'] = 1
            elif selected_patch == patch_extra_options[2]:
                # Conference League
                product_info['patch_options'] = 'ללא פאץ׳;ליגה;קונפרנס ליג'
                memory['patch_choice'] = 2
            elif selected_patch == patch_extra_options[3]:
                # Champions + Europa
                product_info['patch_options'] = 'ללא פאץ׳;ליגה;ליגת האלופות;הליגה האירופית'
                memory['patch_choice'] = 3
            elif selected_patch == patch_extra_options[4]:
                # Champions + Conference
                product_info['patch_options'] = 'ללא פאץ׳;ליגה;ליגת האלופות;קונפרנס ליג'
                memory['patch_choice'] = 4
    else:
            # Fallback to number-based selection
            print("\n" + "="*70)
            print("בחר קבוצה:")
            print("\nמועדוני כדורגל:")
            for i, team in enumerate(CLUB_TEAMS, 1):
                print(f"  {i}. {team}")
            
            offset = len(CLUB_TEAMS)
            print("\nנבחרות לאומיות:")
            for i, team in enumerate(NATIONAL_TEAMS, 1):
                print(f"  {i + offset}. {team}")
            
            while True:
                try:
                    choice = int(input("\nבחר מספר: "))
                    if 1 <= choice <= len(all_teams):
                        team = all_teams[choice - 1]
                        
                        # If "מועדונים אחרים" or "נבחרות אחרות", ask for custom name
                        if team == "מועדונים אחרים":
                            custom_input = input("\nהזן שם מועדון: ").strip()
                            if custom_input:
                                custom_team_name = custom_input
                                product_info['custom_team_name'] = custom_team_name
                                print(f"✓ נבחר: {custom_team_name}")
                            else:
                                print("❌ לא הוזן שם, נא לנסות שוב")
                                continue
                        elif team == "נבחרות אחרות":
                            custom_input = input("\nהזן שם נבחרת: ").strip()
                            if custom_input:
                                custom_team_name = custom_input
                                product_info['custom_team_name'] = custom_team_name
                                print(f"✓ נבחר: {custom_team_name}")
                            else:
                                print("❌ לא הוזן שם, נא לנסות שוב")
                                continue
                        
                        product_info['team'] = team
                        break
                    else:
                        print(f"❌ נא לבחור מספר בין 1 ל-{len(all_teams)}")
                except ValueError:
                    print("❌ נא להזין מספר תקין")
            
            # Ask about additional patch options (for club teams only, not national teams)
            if category in ["חולצות גברים", "חולצות גברים ארוכות", "חליפות ילדים"] and shirt_type and team not in NATIONAL_TEAMS:
                print("\n" + "="*70)
                print("בחר פאצ׳ים נוספים להוסיף (מעבר ל'ללא פאץ׳' ו'ליגה'):")
                
                patch_extra_options = [
                    "לא להוסיף פאצ׳ים נוספים (רק ליגת האלופות)",
                    "הליגה האירופית",
                    "קונפרנס ליג",
                    "ליגת האלופות והליגה האירופית",
                    "ליגת האלופות וקונפרנס ליג"
                ]
                
                default_patch_idx = 0
                if 'patch_choice' in memory:
                    try:
                        default_patch_idx = int(memory['patch_choice'])
                        if default_patch_idx < 0 or default_patch_idx >= len(patch_extra_options):
                            default_patch_idx = 0
                    except:
                        default_patch_idx = 0
                
                selected_patch = select_option("בחר אופציה:", patch_extra_options, default_patch_idx)
                
                # Build patch options string
                if selected_patch == patch_extra_options[0]:
                    product_info['patch_options'] = 'ללא פאץ׳;ליגה;ליגת האלופות'
                    memory['patch_choice'] = 0
                elif selected_patch == patch_extra_options[1]:
                    product_info['patch_options'] = 'ללא פאץ׳;ליגה;הליגה האירופית'
                    memory['patch_choice'] = 1
                elif selected_patch == patch_extra_options[2]:
                    product_info['patch_options'] = 'ללא פאץ׳;ליגה;קונפרנס ליג'
                    memory['patch_choice'] = 2
                elif selected_patch == patch_extra_options[3]:
                    product_info['patch_options'] = 'ללא פאץ׳;ליגה;ליגת האלופות;הליגה האירופית'
                    memory['patch_choice'] = 3
                elif selected_patch == patch_extra_options[4]:
                    product_info['patch_options'] = 'ללא פאץ׳;ליגה;ליגת האלופות;קונפרנס ליג'
                    memory['patch_choice'] = 4
    
    # Build product name
# Use custom team name if it exists, otherwise use team
    team_for_name = product_info.get('custom_team_name', team)
    product_name = build_product_name(category, team_for_name, shirt_type, version, jacket_type, color, season, age_group, product_info.get('player_name'), product_info.get('player_number'))
    product_info['name'] = product_name
    print(f"\n✓ שם המוצר: {product_name}")
    
    # Check if product already exists
    print("\nבודק אם המוצר כבר קיים...")
    existing_product = check_product_exists(csv_file, product_info)
    
    if existing_product:
        print("\n" + "="*70)
        print("⚠️  המוצר כבר קיים!")
        print(f"   שם המוצר הקיים: {existing_product}")
        print("="*70)
        
        # Special handling for goalkeeper (שוער) - allow adding as שוער 2
        # Special handling for goalkeeper, jackets, and tracksuits - allow adding numbered versions
        if shirt_type == "שוער" or category in ["ג'קטים ומעילים", "אימוניות"]:
            if PICK_AVAILABLE:
                # Use arrow-based selection
                options = [
                    "החלף את המוצר הקיים",
                    "הוסף כמוצר נוסף (המוצר הקיים יהפוך ל'1' והחדש ל'2')",
                    "הוסף כמוצר נוסף עם שמות מותאמים אישית",
                    "בטל"
                ]
                selected, index = pick(options, "\nמה תרצה לעשות?", indicator='=>')
                choice = index + 1
            else:
                # Fallback to number-based selection
                print("\nאפשרויות:")
                print("  1. החלף את המוצר הקיים")
                print("  2. הוסף כמוצר נוסף (המוצר הקיים יהפוך ל'1' והחדש ל'2')")
                print("  3. הוסף כמוצר נוסף עם שמות מותאמים אישית")
                print("  4. בטל")
                
                while True:
                    try:
                        choice = int(input("\nבחר אפשרות (1/2/3/4): "))
                        if choice in [1, 2, 3, 4]:
                            break
                        print("❌ נא לבחור 1, 2, 3 או 4")
                    except ValueError:
                        print("❌ נא להזין מספר תקין")
            
            if choice == 4:
                print("\n❌ פעולת ההוספה בוטלה.")
                return
            elif choice == 1:
                # Replace existing
                print("\n✓ המוצר הקיים יוחלף במוצר החדש")
                product_info['replace_existing'] = True
                product_info['existing_name'] = existing_product
            elif choice == 2:
                # Find next available number
                parts = product_name.rsplit(' ', 1)
                base_name = parts[0]
                next_number = find_next_available_number(csv_file, product_info, base_name)
                
                print(f"\n✓ המוצר החדש יתוסף כמספר {next_number}")
                product_info['add_as_goalkeeper_2'] = True
                product_info['existing_name'] = existing_product
                product_info['next_number'] = next_number
                
                # Update the new product name with next available number
                product_name = f"{parts[0]} {next_number} {parts[1]}"
                product_info['name'] = product_name
                print(f"   שם המוצר החדש: {product_name}")
            else:  # choice == 3
                # Custom naming
                print("\n✓ מצב התאמה אישית של שמות")
                print(f"   המוצר הקיים: {existing_product}")
                
                # Ask for custom suffix for existing product
                existing_suffix = input("\nהזן תוספת לשם המוצר הקיים (לדוגמה: 'אדום', 'כחול', 'ראשון'): ").strip()
                if not existing_suffix:
                    print("❌ לא הוזנה תוספת, פעולה בוטלה")
                    return
                
                # Ask for custom suffix for new product
                new_suffix = input("הזן תוספת לשם המוצר החדש (לדוגמה: 'שחור', 'לבן', 'שני'): ").strip()
                if not new_suffix:
                    print("❌ לא הוזנה תוספת, פעולה בוטלה")
                    return
                
                # Update product info with custom suffixes
                product_info['add_as_goalkeeper_2'] = True
                product_info['existing_name'] = existing_product
                product_info['custom_suffix_existing'] = existing_suffix
                product_info['custom_suffix_new'] = new_suffix
                
                # Update the new product name with custom suffix
                parts = product_name.rsplit(' ', 1)
                product_name = f"{parts[0]} {new_suffix} {parts[1]}"
                product_info['name'] = product_name
                
                print(f"\n   המוצר הקיים ישונה ל: {parts[0]} {existing_suffix} {parts[1]}")
                print(f"   שם המוצר החדש: {product_name}")
            
        else:
            # Regular product - ask if user wants to modify
            if PICK_AVAILABLE:
                options = ["כן, שנה את המוצר הקיים", "לא, בטל"]
                selected, index = pick(options, "\nהאם ברצונך לשנות את המוצר הקיים?", indicator='=>')
                modify = (index == 0)
            else:
                modify = yes_no_question("\nהאם ברצונך לשנות את המוצר הקיים?")
            
            if not modify:
                print("\n❌ פעולת ההוספה בוטלה.")
                return
            else:
                print("\n✓ המוצר הקיים יוחלף במוצר החדש")
                product_info['replace_existing'] = True
                product_info['existing_name'] = existing_product
    
    # 6. Images
    print("\n" + "="*70)
    print("הזן קישורים לתמונות (מופרדים ברווח):")
    image_urls_input = input().strip()
    image_urls = [url.strip() for url in image_urls_input.split() if url.strip()]
    
    if not image_urls:
        print("❌ לא הוזנו תמונות!")
        return
    
    print(f"\nמוריד {len(image_urls)} תמונות...")
    # Determine subdirectory name
    if category in ["אימוניות", "ג'קטים ומעילים"]:
        subdir = color  # Use color as-is for these categories
    else:
        subdir = shirt_type
    
    github_urls = download_images(image_urls, category, team, subdir)
    
    if not github_urls:
        print("❌ לא הצלחתי להוריד תמונות!")
        return
    
    product_info['images'] = github_urls
    print(f"✓ הורדו {len(github_urls)} תמונות בהצלחה")
    
    # 7. Sizes (only for גרסת אוהד in חולצות גברים)
    if category == "חולצות גברים" and version == "גרסת אוהד":
        size_range_options = ["S-2XL", "S-4XL"]
        default_size_idx = 0
        if 'size_range' in memory and memory['size_range'] in size_range_options:
            default_size_idx = size_range_options.index(memory['size_range'])
        
        size_range = select_option("בחר טווח מידות:", size_range_options, default_size_idx)
        product_info['sizes'] = SIZE_OPTIONS_SMALL if size_range == "S-2XL" else SIZE_OPTIONS_LARGE
        memory['size_range'] = size_range
    
    # 8. Set options (shorts/socks/pants)
    if category in ["חולצות גברים", "חולצות גברים ארוכות", "חולצות נשים"]:
        set_options = [
            "ללא אופציות נוספות",
            "הוסף אופציה של מכנס בלבד",
            "הוסף אופציה של מכנס ומכנס+גרביים"
        ]
        
        default_set_idx = 0
        if 'set_option_choice' in memory:
            try:
                default_set_idx = int(memory['set_option_choice'])
                if default_set_idx < 0 or default_set_idx >= len(set_options):
                    default_set_idx = 0
            except:
                default_set_idx = 0
        
        selected_option = select_option("בחר אופציות השלמה לסט:", set_options, default_set_idx)
        
        if selected_option == set_options[1]:
            # Only shorts
            product_info['set_option'] = "לא;הוסף מכנס - 50.00 ₪"
            memory['set_option_choice'] = 1
        elif selected_option == set_options[2]:
            # Shorts and shorts+socks
            product_info['set_option'] = "לא;הוסף מכנס - 50.00 ₪;הוסף מכנס+גרביים - 80.00 ₪"
            memory['set_option_choice'] = 2
        else:
            memory['set_option_choice'] = 0
        # If first option (no additions), don't add set_option
    
    elif category == "ג'קטים ומעילים" and age_group == "מבוגרים":
        # Add shorts option only for adult jackets
        shorts_options = [
            "ללא אופציות נוספות",
            "הוסף אופציה של מכנסיים"
        ]
        
        default_jacket_shorts_idx = 0
        if 'jacket_shorts_option' in memory:
            try:
                default_jacket_shorts_idx = int(memory['jacket_shorts_option'])
                if default_jacket_shorts_idx < 0 or default_jacket_shorts_idx >= len(shorts_options):
                    default_jacket_shorts_idx = 0
            except:
                default_jacket_shorts_idx = 0
        
        selected_option = select_option("בחר אופציות נוספות:", shorts_options, default_jacket_shorts_idx)
        
        if selected_option == shorts_options[1]:
            product_info['set_option'] = "לא;כן - 99.90 ₪"
            memory['jacket_shorts_option'] = 1
        else:
            memory['jacket_shorts_option'] = 0
    
    elif category in ["מכנסיים", "חליפות ילדים"]:
        socks_options = [
            "ללא אופציות נוספות",
            "הוסף אופציה של גרביים"
        ]
        
        default_socks_idx = 0
        if 'socks_option_choice' in memory:
            try:
                default_socks_idx = int(memory['socks_option_choice'])
                if default_socks_idx < 0 or default_socks_idx >= len(socks_options):
                    default_socks_idx = 0
            except:
                default_socks_idx = 0
        
        selected_option = select_option("בחר אופציות נוספות:", socks_options, default_socks_idx)
        
        if selected_option == socks_options[1]:
            product_info['set_option'] = "לא;כן - 30 ₪"
            memory['socks_option_choice'] = 1
        else:
            memory['socks_option_choice'] = 0
    
    # Create product row
    print("\nיוצר שורת מוצר...")
    product_row = create_product_row(product_info)
    
    # Read existing fieldnames if file exists
    csv_exists = csv_file.exists()
    if csv_exists:
        with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
    else:
        # Use all possible fieldnames
        fieldnames = list(product_row.keys())
    
    # Insert product in the correct sorted position
    print("\nמכניס מוצר במיקום הנכון...")
    insert_product_in_order(csv_file, product_row, product_info, fieldnames)

    # Append to Google Merchant feed
    if append_to_merchant:
        price_category = product_info['category']
        if product_info['category'] == "ג'קטים ומעילים":
            age_group = product_info.get('age_group', 'מבוגרים')
            price_category = f"{product_info['category']} ל{age_group}"

        base_price = float(CATEGORY_PRICES.get(price_category, '280.0'))
        discount = float(CATEGORY_DISCOUNTS.get(price_category, '130.1'))
        final_price = base_price - discount

        append_single_product_to_merchant_feed(csv_file, product_info['name'], product_info['images'], final_price)

    # Save memory for next time
    save_memory(memory)
    
    print("\n" + "="*70)
    if product_info.get('replace_existing'):
        print(f"✓ המוצר עודכן בהצלחה ב-{csv_file}!")
    else:
        print(f"✓ המוצר נוסף בהצלחה ל-{csv_file}!")
    print("="*70)


def sanitize_url_text(text: str) -> str:
    """Convert text to URL format by replacing spaces, slashes, and apostrophes with hyphens"""
    return text.replace(' ', '-').replace('/', '-').replace("'", '-')


def generate_product_id(product_name: str) -> str:
    """Generate a unique product ID based on the product name"""
    hash_object = hashlib.md5(product_name.encode('utf-8'))
    return f"prod_{hash_object.hexdigest()[:12]}"


def clean_description(description_html: str) -> str:
    """Extract text from HTML description"""
    if not description_html or description_html.strip() == '':
        return ''
    # Simple HTML tag removal
    clean = re.sub('<.*?>', '', description_html)
    clean = clean.replace('&nbsp;', ' ').strip()
    return clean

def append_single_product_to_merchant_feed(csv_file: Path, product_name: str, product_images: List[str], final_price: float):
    """Append a single product to Google Merchant feed"""
    output_file = csv_file.parent / f"{csv_file.stem}_googlemerchant.txt"
    
    # Clean product name for title/description
    title = re.sub(r'(\d{4})/(\d{4})', lambda m: f"{m.group(1)[-2:]}/{m.group(2)[-2:]}", product_name)
    description = title
    
    # Generate product URL
    product_url_slug = sanitize_url_text(product_name)
    product_link = f"https://www.xn--6dbbfabi4agf8g0au.com/product-page/{product_url_slug}"
    
    # Generate unique product ID
    product_id = generate_product_id(product_name)
    
    product_data = {
        'id': product_id,
        'title': title,
        'description': description,
        'link': product_link,
        'image_link': product_images[0] if product_images else '',
        'additional_image_link': ','.join(product_images[1:11]) if len(product_images) > 1 else '',
        'price': f"{final_price:.2f} ILS",
        'availability': 'in_stock',
        'condition': 'new'
    }
    
    # Check if file exists
    file_exists = output_file.exists()
    
    # Append to file
    with open(output_file, 'a', encoding='utf-8', newline='') as f:
        fieldnames = ['id', 'title', 'description', 'link', 'image_link', 
                     'additional_image_link', 'price', 'availability', 'condition']
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', extrasaction='ignore', lineterminator='\n')
        
        # Write header only if file is new
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(product_data)

def update_product_in_merchant_feed(csv_file: Path, old_product_name: str, new_product_name: str):
    """Update a product name in the Google Merchant feed"""
    output_file = csv_file.parent / f"{csv_file.stem}_googlemerchant.txt"
    
    if not output_file.exists():
        return  # Nothing to update
    
    # Read all rows
    rows = []
    with open(output_file, 'r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        fieldnames = reader.fieldnames
        rows = list(reader)
    
    # Find and update the matching product
    updated = False
    for row in rows:
        # Generate the old product ID
        old_product_id = generate_product_id(old_product_name)
        
        if row['id'] == old_product_id:
            # Update with new name
            new_title = re.sub(r'(\d{4})/(\d{4})', lambda m: f"{m.group(1)[-2:]}/{m.group(2)[-2:]}", new_product_name)
            new_product_url_slug = sanitize_url_text(new_product_name)
            new_product_link = f"https://www.xn--6dbbfabi4agf8g0au.com/product-page/{new_product_url_slug}"
            new_product_id = generate_product_id(new_product_name)
            
            row['id'] = new_product_id
            row['title'] = new_title
            row['description'] = new_title
            row['link'] = new_product_link
            updated = True
            break
    
    if updated:
        # Write back all rows
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser(
        description="כלי אינטראקטיבי להוספת או עדכון מוצרים ב-CSV של Wix",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
תיאור הכלי:
============
כלי זה מאפשר להוסיף מוצרים חדשים לקובץ CSV של Wix או לעדכן מוצרים קיימים.
הכלי פועל בצורה אינטראקטיבית ומנחה אותך שלב אחר שלב.

תהליך העבודה:
==============
1. בחירת עונה (2025/2026 עד 2029/2030)
2. בחירת קטגוריה:
   - חולצות גברים
   - חולצות גברים ארוכות
   - חליפות ילדים
   - חולצות נשים
   - מכנסיים
   - אימוניות
   - ג'קטים ומעילים

3. תת-קטגוריה 1 (תלוי בקטגוריה):
   - חולצות גברים: בחירה בין גרסת אוהד לגרסת שחקן
   - ג'קטים ומעילים: בחירה בין ג'קט למעיל רוח
   - קטגוריות אחרות: מדלג על שלב זה

4. תת-קטגוריה 2 (תלוי בקטגוריה):
   - חולצות, חליפות, מכנסיים: בחירת סוג (בית/חוץ/השלישית/שוער)
   - אימוניות וג'קטים: הזנת צבע ידנית

5. בחירת קבוצה:
   - מועדוני כדורגל (18 קבוצות + "מועדונים אחרים")
   - נבחרות לאומיות (25 נבחרות + "נבחרות אחרות")

6. הורדת תמונות:
   - הזנת קישורים לתמונות (מופרדים ברווח)
   - הכלי מוריד את התמונות וממיר אותן ל-JPG
   - התמונות נשמרות בתיקייה המתאימה
   - נוצרים קישורי GitHub אוטומטית

7. הגדרות נוספות (תלוי בקטגוריה):
   - חולצות גברים (גרסת אוהד): בחירת טווח מידות (S-2XL או S-4XL)
   - חולצות/חולצות נשים: אופציה להוסיף מכנס ו/או גרביים
   - מכנסיים/חליפות ילדים: אופציה להוסיף גרביים

8. בדיקת קיום מוצר:
   - אם המוצר כבר קיים, הכלי מציע לעדכן אותו
   - אפשר לבחור להחליף את המוצר הקיים או לבטל

מבנה תיקיות התמונות:
====================
התמונות נשמרות במבנה הבא:
  ./images/<קטגוריה>/<קבוצה>/<תת-קטגוריה>/image001.jpg

דוגמאות:
  ./images/חולצות גברים/ברצלונה/first/image001.jpg
  ./images/אימוניות/ליברפול/שחור/image001.jpg
  ./images/ג'קטים ומעילים/ריאל מדריד/כחול/image001.jpg

קישורי GitHub:
==============
הכלי יוצר קישורים בפורמט:
  https://github.com/hultzotKaduregel/2025-2026-products/blob/main/images/...

סדר המוצרים ב-CSV:
==================
המוצרים מסודרים לפי:
1. קטגוריה (חולצות גברים → חולצות גברים ארוכות → ... → ג'קטים ומעילים)
2. קבוצה (מועדונים לפי סדר קבוע, נבחרות לפי א"ב)
3. תת-קטגוריה (בית → חוץ → השלישית → שוער)
4. שם המוצר (אלפביתית)

דוגמאות שימוש:
===============
# הוספת מוצר לקובץ קיים:
python add_product.py wix_products.csv

# יצירת קובץ חדש:
python add_product.py new_products.csv

# יצירת קובץ + קובץ Google Merchant:
python add_product.py wix_products.csv --google-merchant

# הצגת עזרה:
python add_product.py -h

דרישות מערכת:
=============
יש להתקין את החבילות הבאות:
  pip install pillow requests --break-system-packages

אופציונלי (לבחירה עם חיצים):
  pip install pick --break-system-packages

בלי pick - תוכל לבחור רק באמצעות מספרים
עם pick - תוכל לבחור באמצעות חיצים ↑↓ ו-Enter (מומלץ!)

טיפים:
======
- ניתן לבטל את התהליך בכל שלב באמצעות Ctrl+C
- התמונות מומרות אוטומטית ל-JPG גם אם המקור בפורמט אחר
- כאשר מעדכנים מוצר קיים, התמונות הישנות מוחלפות בחדשות
- שמות התיקיות חייבים להתאים בדיוק לשמות הקבוצות

"""
    )
    
    parser.add_argument('csv_file', nargs='?', default='catalog_products.csv', type=str, 
                   help='CSV file path (Default: catalog_products.csv)')
    parser.add_argument('--google-merchant', '-g', action='store_true', 
                       help='Create Google Merchant file upon completion')
    
    args = parser.parse_args()
    csv_path = Path(args.csv_file)
    
    try:
        interactive_add_product(csv_path, append_to_merchant=args.google_merchant)
                    
    except KeyboardInterrupt:
        print("\n\n❌ בוטל על ידי המשתמש")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ שגיאה: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
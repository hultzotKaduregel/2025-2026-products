#!/usr/bin/env python3
"""
Check for missing products in catalog CSV.

Usage:
    python check_missing_products.py [options]

Examples:
    python check_missing_products.py
    python check_missing_products.py --season 26/27
    python check_missing_products.py --season 2026/2027
    python check_missing_products.py --season 2026
    python check_missing_products.py --csv my_catalog.csv
    python check_missing_products.py --exclude-fourth
    python check_missing_products.py --team ליברפול
    python check_missing_products.py --team Liverpool
    python check_missing_products.py --team פיורנטינה
    python check_missing_products.py --team club
    python check_missing_products.py --team national_team
    python check_missing_products.py --category men_jerseys
    python check_missing_products.py --category חולצות גברים
"""

import csv
import sys
import argparse
from pathlib import Path
from typing import List, Set

# Default clubs to check
DEFAULT_CLUBS = [
    "ליברפול", "מנצ'סטר יונייטד", "מנצ'סטר סיטי", "ארסנל", "צ'לסי", "טוטנהאם",
    "ברצלונה", "ריאל מדריד", "אתלטיקו מדריד",
    "יובנטוס", "מילאן", "אינטר מילאנו", "רומא", "נאפולי",
    "באיירן מינכן", "בורוסיה דורטמונד",
    "פריז סן ז'רמן",
    "אייאקס"
]

# National teams
NATIONAL_TEAMS = [
    "אוסטרליה", "אוסטריה", "אורוגוואי", "איטליה", "אלגיריה", "אנגליה", "ארגנטינה", "ארה\"ב",
    "בלגיה", "ברזיל", "גרמניה", "הולנד", "טוניסיה", "יפן", "ירדן", "מקסיקו",
    "מצרים", "מרוקו", "נורווגיה", "סקוטלנד", "ספרד", "ערב הסעודית", "פורטוגל",
    "צרפת", "קטאר", "קנדה", "שוויץ"
]

# All teams combined
ALL_TEAMS = DEFAULT_CLUBS + NATIONAL_TEAMS

# Categories to check
CATEGORIES = {
    'חולצות גברים': 'men_jerseys',
    'חולצות גברים ארוכות': 'long_jerseys',
    'חליפות ילדים': 'kids_kits',
    'חולצות נשים': 'women_jerseys'
}

# Shirt types
SHIRT_TYPES = ["בית", "חוץ", "השלישית", "הרביעית"]

# Team name translations (Hebrew to English)
TEAM_TRANSLATIONS = {
    # Clubs
    "ליברפול": "Liverpool",
    "מנצ'סטר יונייטד": "Manchester United",
    "מנצ'סטר סיטי": "Manchester City",
    "ארסנל": "Arsenal",
    "צ'לסי": "Chelsea",
    "טוטנהאם": "Tottenham",
    "ברצלונה": "Barcelona",
    "ריאל מדריד": "Real Madrid",
    "אתלטיקו מדריד": "Atletico Madrid",
    "יובנטוס": "Juventus",
    "מילאן": "Milan",
    "אינטר מילאנו": "Inter Milan",
    "רומא": "Roma",
    "נאפולי": "Napoli",
    "באיירן מינכן": "Bayern Munich",
    "בורוסיה דורטמונד": "Borussia Dortmund",
    "פריז סן ז'רמן": "PSG",
    "אייאקס": "Ajax",
    # National teams
    "אוסטרליה": "Australia",
    "אוסטריה": "Austria",
    "אורוגוואי": "Uruguay",
    "איטליה": "Italy",
    "אלגיריה": "Algeria",
    "אנגליה": "England",
    "ארגנטינה": "Argentina",
    "ארה\"ב": "USA",
    "בלגיה": "Belgium",
    "ברזיל": "Brazil",
    "גרמניה": "Germany",
    "הולנד": "Netherlands",
    "טוניסיה": "Tunisia",
    "יפן": "Japan",
    "ירדן": "Jordan",
    "מקסיקו": "Mexico",
    "מצרים": "Egypt",
    "מרוקו": "Morocco",
    "נורווגיה": "Norway",
    "סקוטלנד": "Scotland",
    "ספרד": "Spain",
    "ערב הסעודית": "Saudi Arabia",
    "פורטוגל": "Portugal",
    "צרפת": "France",
    "קטאר": "Qatar",
    "קנדה": "Canada",
    "שוויץ": "Switzerland"
}

# Reverse mapping (English to Hebrew)
TEAM_TRANSLATIONS_REVERSE = {v.lower(): k for k, v in TEAM_TRANSLATIONS.items()}

# Category translations (English to Hebrew)
CATEGORY_TRANSLATIONS = {
    'men_jerseys': 'חולצות גברים',
    'long_jerseys': 'חולצות גברים ארוכות',
    'kids_kits': 'חליפות ילדים',
    'women_jerseys': 'חולצות נשים'
}


def normalize_season(season_str: str, is_national_team: bool = False) -> str:
    """
    Normalize season string to appropriate format.
    For clubs: YYYY/YYYY format (e.g., "2025/2026")
    For national teams: Single year (e.g., "2026")
    
    Args:
        season_str: Season in format "25/26", "2025/2026", "26", or "2026"
        is_national_team: True if checking national teams
    
    Returns:
        Season in format "2025/2026" for clubs or "2026" for national teams
    """
    # Check if it's a single year format
    if '/' not in season_str:
        year = season_str.strip()
        
        # Convert 2-digit to 4-digit
        if len(year) == 2:
            year = f"20{year}"
        
        if len(year) != 4:
            raise ValueError(f"Invalid season format: {season_str}")
        
        if is_national_team:
            return year
        else:
            # For clubs, convert single year to YYYY/YYYY format
            # E.g., "2026" becomes "2025/2026"
            year_int = int(year)
            return f"{year_int - 1}/{year}"
    
    # It has a slash, so it's YYYY/YYYY format
    parts = season_str.split('/')
    if len(parts) != 2:
        raise ValueError(f"Invalid season format: {season_str}")
    
    year1, year2 = parts[0].strip(), parts[1].strip()
    
    # If 2-digit format, convert to 4-digit
    if len(year1) == 2:
        year1 = f"20{year1}"
    if len(year2) == 2:
        year2 = f"20{year2}"
    
    # Validate
    if len(year1) != 4 or len(year2) != 4:
        raise ValueError(f"Invalid season format: {season_str}")
    
    if is_national_team:
        # For national teams, return just the second year
        return year2
    else:
        return f"{year1}/{year2}"


def translate_team_to_hebrew(team_name: str) -> str:
    """
    Translate team name to Hebrew if it's in English.
    
    Args:
        team_name: Team name in Hebrew or English
    
    Returns:
        Team name in Hebrew
    """
    # Check if already Hebrew (contains Hebrew characters)
    if any('\u0590' <= c <= '\u05FF' for c in team_name):
        return team_name
    
    # Normalize: remove underscores/hyphens, convert to lowercase, remove extra spaces
    normalized = team_name.replace('_', ' ').replace('-', ' ').lower().strip()
    normalized = ' '.join(normalized.split())  # Remove extra spaces
    
    # Try to translate from English
    if normalized in TEAM_TRANSLATIONS_REVERSE:
        return TEAM_TRANSLATIONS_REVERSE[normalized]    
    return team_name


def translate_category_to_hebrew(category_name: str) -> str:
    """
    Translate category name to Hebrew if it's in English.
    
    Args:
        category_name: Category name in Hebrew or English
    
    Returns:
        Category name in Hebrew
    """
    # Check if already Hebrew (contains Hebrew characters)
    if any('\u0590' <= c <= '\u05FF' for c in category_name):
        return category_name
    
    # Try to translate from English
    category_lower = category_name.lower()
    if category_lower in CATEGORY_TRANSLATIONS:
        return CATEGORY_TRANSLATIONS[category_lower]
    
    raise ValueError(f"Invalid category: {category_name}")

def resolve_team_from_prefix(prefix: str, all_teams: List[str]) -> str:
    """
    Find team matching the prefix. If multiple matches, prompt user to select.
    
    Args:
        prefix: Team name prefix (can be in Hebrew or English)
        all_teams: List of all available teams
    
    Returns:
        Selected team name (Hebrew)
    """
    # Normalize prefix
    prefix_normalized = prefix.replace('_', ' ').replace('-', ' ').lower().strip()
    
    # Find matching teams
    matching_teams = []
    
    for team in all_teams:
        # Check Hebrew name
        if team.lower().startswith(prefix_normalized):
            matching_teams.append(team)
            continue
        
        # Check English name
        team_english = TEAM_TRANSLATIONS.get(team, '').lower()
        if team_english.startswith(prefix_normalized):
            matching_teams.append(team)
    
    # Handle results
    if len(matching_teams) == 0:
        # No matches - return prefix as custom team
        return prefix
    elif len(matching_teams) == 1:
        # Exact one match
        return matching_teams[0]
    else:
        # Multiple matches - prompt user
        print(f"\nMultiple teams found matching '{prefix}':")
        for i, team in enumerate(matching_teams, 1):
            english_name = TEAM_TRANSLATIONS.get(team, '')
            if english_name:
                print(f"  {i}. {team} ({english_name})")
            else:
                print(f"  {i}. {team}")
        
        while True:
            try:
                choice = input(f"\nSelect team (1-{len(matching_teams)}): ").strip()
                choice_num = int(choice)
                if 1 <= choice_num <= len(matching_teams):
                    return matching_teams[choice_num - 1]
                else:
                    print(f"Please enter a number between 1 and {len(matching_teams)}")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\n\nCancelled by user")
                sys.exit(1)

def load_existing_products(csv_file: Path) -> Set[str]:
    """
    Load existing products from CSV file.
    
    Args:
        csv_file: Path to CSV file
    
    Returns:
        Set of product names (normalized)
    """
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file}")
    
    products = set()
    
    with open(csv_file, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('fieldType') == 'Product':
                product_name = row.get('name', '').strip()
                if product_name:
                    products.add(product_name)
    
    return products


def generate_expected_product_name(category: str, team: str, shirt_type: str, season: str) -> str:
    """
    Generate expected product name based on category, team, shirt type, and season.
    
    Args:
        category: Category name (Hebrew)
        team: Team name (Hebrew)
        shirt_type: Shirt type (Hebrew)
        season: Season in format "2025/2026" (clubs) or "2026" (national teams)
    
    Returns:
        Expected product name
    """
    if category == "חולצות גברים":
        return f"חולצת {team} {shirt_type} {season}"
    elif category == "חולצות גברים ארוכות":
        return f"חולצה ארוכה {team} {shirt_type} {season}"
    elif category == "חליפות ילדים":
        return f"חליפת ילדים {team} {shirt_type} {season}"
    elif category == "חולצות נשים":
        return f"חולצת נשים {team} {shirt_type} {season}"
    
    return ""


def check_missing_products(csv_file: Path, season: str, teams: List[str], 
                          categories: List[str], shirt_types: List[str]) -> List[str]:
    """
    Check for missing products in catalog.
    
    Args:
        csv_file: Path to CSV file
        season: Season in format "2025/2026" or "2026" depending on team type
        teams: List of team names (Hebrew)
        categories: List of category names (Hebrew)
        shirt_types: List of shirt types (Hebrew)
    
    Returns:
        List of missing product names
    """
    # Load existing products
    existing_products = load_existing_products(csv_file)
    
    # Generate expected products
    missing_products = []
    
    for team in teams:
        for category in categories:
            for shirt_type in shirt_types:
                expected_name = generate_expected_product_name(category, team, shirt_type, season)
                
                if expected_name and expected_name not in existing_products:
                    missing_products.append(expected_name)
    
    return missing_products

def sort_products(products: List[str]) -> List[str]:
    """
    Sort products by custom order:
    1. Club/National team (clubs first)
    2. Team name (alphabetically)
    3. Category (men, long, kids, women)
    4. Shirt type (בית, חוץ, השלישית, הרביעית)
    
    Args:
        products: List of product names
    
    Returns:
        Sorted list of product names
    """
    def sort_key(product_name):
        # Determine team type (club=0, national=1)
        team_type = 1  # Default to national
        for club in DEFAULT_CLUBS:
            if club in product_name:
                team_type = 0
                break
        
        # Extract team name
        team_name = ""
        for team in ALL_TEAMS:
            if team in product_name:
                team_name = team
                break
        
        # Determine category order
        category_order = 3  # Default
        if "חולצת נשים" in product_name:
            category_order = 3
        elif "חליפת ילדים" in product_name:
            category_order = 2
        elif "חולצה ארוכה" in product_name:
            category_order = 1
        elif "חולצת" in product_name:
            category_order = 0
        
        # Determine shirt type order
        shirt_order = 3  # Default
        if "בית" in product_name:
            shirt_order = 0
        elif "חוץ" in product_name:
            shirt_order = 1
        elif "השלישית" in product_name:
            shirt_order = 2
        elif "הרביעית" in product_name:
            shirt_order = 3
        
        return (team_type, team_name, category_order, shirt_order)
    
    return sorted(products, key=sort_key)

def main():
    parser = argparse.ArgumentParser(
        description='Check for missing products in catalog CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python check_missing_products.py
    python check_missing_products.py --season 26/27
    python check_missing_products.py --season 2026/2027
    python check_missing_products.py --season 2026
    python check_missing_products.py --csv my_catalog.csv
    python check_missing_products.py --exclude-fourth
    python check_missing_products.py --team ליברפול
    python check_missing_products.py --team Liverpool
    python check_missing_products.py --team פיורנטינה
    python check_missing_products.py --team club
    python check_missing_products.py --team national_team
    python check_missing_products.py --category men_jerseys
    python check_missing_products.py --category חולצות גברים
        """
    )
    
    parser.add_argument('--season', type=str, default=None,
                       help='Season to check (format: 25/26, 2025/2026, or single year like 2026). Default: 2025/2026 for clubs, 2026 for national teams')
    parser.add_argument('--csv', type=str, default='catalog_products.csv',
                       help='CSV file to check (default: catalog_products.csv)')
    parser.add_argument('--exclude-fourth', action='store_true',
                       help='Exclude הרביעית from check')
    parser.add_argument('--team', type=str,
                       help='Check specific team only (Hebrew or English name, or "club"/"national_team" for all clubs/national teams)')
    parser.add_argument('--category', type=str,
                       help='Check specific category only (Hebrew or English name)')
    
    args = parser.parse_args()
    
    # Determine CSV file
    csv_file = Path(args.csv)
    
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_file}")
        sys.exit(1)
    
    # Determine teams to check
    if args.team:
        team_arg_lower = args.team.lower()
        
        # Check for special keywords
        if team_arg_lower in ['club', 'clubs']:
            teams = DEFAULT_CLUBS
            is_national_team = False
            print(f"Selected: All clubs ({len(teams)} teams)")
        elif team_arg_lower in ['national_team', 'national_teams', 'national', 'nationals']:
            teams = NATIONAL_TEAMS
            is_national_team = True
            print(f"Selected: All national teams ({len(teams)} teams)")
        else:
            # First try exact match
            team_hebrew = translate_team_to_hebrew(args.team)
            
            # If translation gave no match, try prefix matching
            if team_hebrew == args.team and not any('\u0590' <= c <= '\u05FF' for c in args.team):
                # Not Hebrew and not found in translations - try prefix match
                team_hebrew = resolve_team_from_prefix(args.team, ALL_TEAMS)
            
            teams = [team_hebrew]
            is_national_team = team_hebrew in NATIONAL_TEAMS
            if team_hebrew in ALL_TEAMS:
                print(f"Selected team: {team_hebrew}")
    else:
        # Default: check both clubs and national teams (we'll handle them separately)
        teams = None
        is_national_team = None
    
    # Determine default season based on team type
    if args.season:
        season_input = args.season
    else:
        # Default seasons
        season_input = None  # Will be determined per team type
    
    # Determine categories to check
    if args.category:
        try:
            category = translate_category_to_hebrew(args.category)
            categories = [category]
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        categories = list(CATEGORIES.keys())
    
    # Determine shirt types to check
    if args.exclude_fourth:
        shirt_types = ["בית", "חוץ", "השלישית"]
    else:
        shirt_types = SHIRT_TYPES
    
    # Handle case where we're checking all teams (both clubs and nationals)
    if teams is None:
        # Check clubs first
        try:
            club_season_input = season_input if season_input else "2025/2026"
            club_season = normalize_season(club_season_input, is_national_team=False)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        
        print(f"\n{'='*70}")
        print(f"Checking for missing products - CLUBS")
        print(f"{'='*70}")
        print(f"Season: {club_season}")
        print(f"CSV file: {csv_file}")
        print(f"Teams: {len(DEFAULT_CLUBS)} team(s)")
        print(f"Categories: {len(categories)} category(ies)")
        print(f"Shirt types: {', '.join(shirt_types)}")
        print(f"{'='*70}\n")
        
        club_missing = check_missing_products(csv_file, club_season, DEFAULT_CLUBS, categories, shirt_types)
        
        # Check national teams
        try:
            national_season_input = season_input if season_input else "2026"
            national_season = normalize_season(national_season_input, is_national_team=True)
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        
        print(f"\n{'='*70}")
        print(f"Checking for missing products - NATIONAL TEAMS")
        print(f"{'='*70}")
        print(f"Season: {national_season}")
        print(f"CSV file: {csv_file}")
        print(f"Teams: {len(NATIONAL_TEAMS)} team(s)")
        print(f"Categories: {len(categories)} category(ies)")
        print(f"Shirt types: {', '.join(shirt_types)}")
        print(f"{'='*70}\n")
        
        national_missing = check_missing_products(csv_file, national_season, NATIONAL_TEAMS, categories, shirt_types)
        
        # Combine results
        missing_products = club_missing + national_missing
    else:
        # Checking specific team(s)
        try:
            if season_input:
                season = normalize_season(season_input, is_national_team=is_national_team)
            else:
                # Use default based on team type
                if is_national_team:
                    season = "2026"
                else:
                    season = "2025/2026"
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
        
        print(f"\n{'='*70}")
        print(f"Checking for missing products")
        print(f"{'='*70}")
        print(f"Season: {season}")
        print(f"CSV file: {csv_file}")
        print(f"Teams: {len(teams)} team(s)")
        print(f"Categories: {len(categories)} category(ies)")
        print(f"Shirt types: {', '.join(shirt_types)}")
        print(f"{'='*70}\n")
        
        missing_products = check_missing_products(csv_file, season, teams, categories, shirt_types)
    
    if not missing_products:
        print("✓ No missing products found!")
    else:
        print(f"⚠ Found {len(missing_products)} missing product(s):\n")
        sorted_products = sort_products(missing_products)
        for product in sorted_products:
            print(f"  - {product}")
    
    print(f"\n{'='*70}")


if __name__ == '__main__':
    main()
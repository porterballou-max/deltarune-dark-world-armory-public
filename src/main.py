"""automation.py coordinates the primary systems automation workflow executed by setup.sh."""

from bs4 import BeautifulSoup
import requests
from enum import Enum
import re
import sys
import os

# PROGRAM OVERVIEW
#### Name: Dark World Armory: Deltarune Armor & Weapons Database
#### Description: An informational program that lets you read about each armor and weapon item
################# from the video game series DELTARUNE.
################# The program also allows you to get the equipment of best stats in each category.
################# (That is to say, highest DF score for armor, highest AT score for weapons)

## HELPER METHODS 
# Returns a list of all numbers found in a given string, including signage
def extract_signed_numbers_from_string(x):
    return re.findall(r'-?\d+', x)

# uses the above method to return either a "NaN" string or a number 
def safe_handle_num_extract(x):
    extract = extract_signed_numbers_from_string(x)
    if extract is None:
        return 0
    elif len(extract) == 0:
        return 0
    else:
        return int(extract[0])

## DATABASE 
# May be weapon or armor 
class DT_Item():
    def __init__(self, title, equippers, at, df, mag, other_effects):
        self.title = title
        self.equippers = equippers # who can equip this 
        self.attack = at
        self.defense = df
        self.magic = mag
        self.other_effects = other_effects

BASE_URL = "https://deltarune.wiki"
DT_CHAPTER_LATEST = 5
DTCharacters = []
DTEquipment = { "Weapons" : [], "Armors" : [] }

# Used to store weapons and armors to the DTEquipment dictionary. 
def extract_items(local_url, category, info_label):
    url = BASE_URL + local_url
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    items = []

    # Iterate over all entries, extract data from corresponding pages 
    entries = soup.find("div", id="mw-pages").find_all("li")
    entry_counter=0
    for x in entries:
        x_url = BASE_URL + x.find("a").get("href")
        
        x_response = requests.get(x_url)
        x_soup = BeautifulSoup(x_response.text, "html.parser")

        x_name = x_soup.find(attrs={"data-source":"name"}).text.strip()
        x_equip = x_soup.find(attrs={"data-source":"equip"})
        x_at = 0
        x_df = 0
        x_magic = 0
        x_effects = x_soup.find(attrs={"data-source":"effects"})

        # For items that can only be equipped by specific party members 
        if x_equip is not None:
            x_equip = x_equip.find_all("a")
            for i in range(0, len(x_equip)):
                x_equip[i] = x_equip[i].text

        # Look for effects on attack, defense, and magic. 
        if x_effects is not None:
            x_effects = x_effects.find("div").text.split(",")
            for eff in x_effects:
                if "AT" in eff:
                    x_at = safe_handle_num_extract(eff)
                    x_effects.remove(eff)
                elif "DF" in eff:
                    x_df = safe_handle_num_extract(eff)
                    x_effects.remove(eff)

                    # Special case for the Shadow Mantle since it has very unique game logic. 
                    if x_name == "Shadow Mantle":
                        x_df = DT_CHAPTER_LATEST

                elif "Magic" in eff:
                    x_magic = safe_handle_num_extract(eff)
                    x_effects.remove(eff)
                else:
                    eff = eff.strip() # Remove whitespace 

        # Generate an object and store it in the corresponding list. 
        DTEquipment[category].append( DT_Item(x_name, x_equip, x_at, x_df, x_magic, x_effects) )

        # Log progress 
        entries_total = len(entries)
        entry_counter += 1
        print( f"SAVED: {x_name} \t({info_label} {entry_counter}/{entries_total})" )

# Extracts all items usable by this character. 
def get_compatible_equipment_for_character(character_name):
    my_dict = { "Weapons" : [], "Armors" : [] }
    for key, value in DTEquipment.items():
        for entry in value:
            if entry.equippers is None:
                continue
            if character_name in entry.equippers:
                my_dict[key].append(entry)

    return my_dict

# Gets weapon/armor info from the deltarune wiki and stores it in custom classes for easy access 
def load_database():
    # Part 1. Load party members. We do this so the user can choose which character to
    #         build a loadout for. 
    # 1.1: Load "main characters" page.
    print("Loading party members...")
    party_members_url = BASE_URL + "/w/Category:Main_characters"
    response = requests.get(party_members_url)
    # 1.2: Load HTML data for each party member. 
    soup = BeautifulSoup(response.text, "html.parser")
    characters_container = soup.find("div", class_="mw-content-ltr mw-parser-output")
    characters_gallery = characters_container.find("ul")
    characters_each = characters_gallery.find_all("li")
    # 1.3: Generate a custom Python object for each party member
    for character in characters_each:
        char_name = character.find("div", class_="gallerytext").text
        DTCharacters.append( char_name.strip().split(" ")[0] ) # Extract only first names 
        print("SAVED: " + char_name)

    # 2. Extract weapons. 
    extract_items("/w/Category:Swords", "Weapons", "Sword")
    extract_items("/w/Category:Axes", "Weapons", "Axe")
    extract_items("/w/Category:Scarves", "Weapons", "Scarf")
    extract_items("/w/Category:Rings", "Weapons", "Ring")

    # 3. Extract armors. 
    extract_items("/w/Category:Armor", "Armors", "Armor")

## INPUT 
def select_option(options):
    for i in range(0, len(options)):
        print(f"{i+1}. {options[i]}")

    while 1==1:
        usr = input()
        usr = usr.strip()
        try:
            usr = int(usr)
            if usr < 1 or usr > len(options):
                print("Out of range answer.")
            else:
                return usr
        except Exception as e:
            print("Unknown error occurred. Try again.")


## LOADOUT BUILDER
def loadout_builder():
    # 1. Prompt the user on what they want to prioritize.
    print("~ LOADOUT BUILDER ~")
    print("First, select a loadout type. This will dictate what stat is prioritized.")
    usr_input = select_option(["Attack", "Defense", "Magic"])
    if usr_input == 1:
        loadout_stat = "attack"
    elif usr_input == 2:
        loadout_stat = "defense"
    elif usr_input == 3:
        loadout_stat = "magic"

    # 2. Prompt the user for which character they are building a loadout for. 
    print("Second, select the character for whom you are building a loadout.")
    usr_input = select_option(DTCharacters)
    usr_char_name = DTCharacters[usr_input-1]

    # 3. Get all equipment that this character can equip. 
    compatible_equipment = get_compatible_equipment_for_character(usr_char_name)

    # 4. Sort  weapons and armor by the desired stat. 
    compatible_equipment["Weapons"].sort(key=lambda x: x.__dict__[loadout_stat], reverse=True)
    compatible_equipment["Armors"].sort(key=lambda x: x.__dict__[loadout_stat], reverse=True)

    # 5. Get highest quality equipment as is available  
    dummyItem = DT_Item("None", None, 0, 0, 0, None)
    # Safely load weapon 
    if len(compatible_equipment["Weapons"]) > 0:
        loadoutWeapon = compatible_equipment["Weapons"][0]
    else:
        loadoutWeapon = dummyItem

        # Safely load armors 
    lenArmors = len(compatible_equipment["Armors"])
    if lenArmors == 0:
        loadoutArmor0 = dummyItem
        loadoutArmor1 = dummyItem
    elif lenArmors == 1:
        loadoutArmor0 = compatible_equipment["Armors"][0]
        loadoutArmor1 = dummyItem
    else:
        loadoutArmor0 = compatible_equipment["Armors"][0]
        loadoutArmor1 = compatible_equipment["Armors"][1]

    loadout_string = f"LOADOUT\nParty Member:\t{usr_char_name}\n"
    loadout_string += f"Priority Stat:\t{loadout_stat.capitalize()}\n"
    loadout_string += f"Weapon:\t{loadoutWeapon.title}\n"
    loadout_string += f"Armor #1:\t{loadoutArmor0.title}\n"
    loadout_string += f"Armor #2:\t{loadoutArmor1.title}"

    print(loadout_string)

    print("Would you like to save this loadout?")
    do_save = select_option(["Yes", "No"])

    if do_save == 1:
        new_file_name = f"Chapter_{DT_CHAPTER_LATEST}_{usr_char_name}_{loadout_stat.capitalize()}"
        with open(f"./output/{new_file_name}", "w") as f:
            f.write(loadout_string)

def main_menu():
    while 1==1:

        print("~ DELTARUNE DARK ARMORY ~")
        main_menu_opts = ["Loadout Builder", "What is this?", "Quit"]
        main_menu_selection = select_option(main_menu_opts)
        if main_menu_selection == 1:
            loadout_builder()
        elif main_menu_selection == 2:
            print("This is a fanmade tool for the game Deltarune.\nIt grabs info from the Deltarune wiki and helps you build\noptimized equipment loadouts for different player characters.")
            print("Press ENTER to return to main menu")
            input()
        elif main_menu_selection == 3:
            sys.exit(0)

        pass

    # Placeholder function showcasing where the automation task will live.
def main():
    """Run the main automation routine once the project requirements are defined."""

    # Retrieve data from the Deltarune Wiki and assemble data objects. 
    load_database()

    main_menu()

if __name__ == "__main__":
    main()
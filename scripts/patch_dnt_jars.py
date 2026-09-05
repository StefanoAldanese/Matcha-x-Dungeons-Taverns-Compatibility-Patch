import json
import os
import zipfile
import shutil
import tempfile

# Standard foods that point to dedicated Matcha loot tables
FOOD_REPLACEMENTS = {
    "minecraft:bread": "minecraft:food/bread",
    "minecraft:golden_apple": "minecraft:food/golden_apple",
    "minecraft:enchanted_golden_apple": "minecraft:food/enchanted_golden_apple",
    "minecraft:golden_carrot": "minecraft:food/golden_carrot",
    "minecraft:glow_berries": "minecraft:food/glow_berries",
    "minecraft:apple": "matcha:food/apple",
    "minecraft:carrot": "minecraft:food/carrot",
    "minecraft:sweet_berries": "minecraft:food/sweet_berries"
}

# Swap Stone tools for Copper tools
TOOL_REPLACEMENTS = {
    "minecraft:stone_pickaxe": "minecraft:copper_pickaxe",
    "stone_pickaxe": "minecraft:copper_pickaxe",
    "minecraft:stone_shovel": "minecraft:copper_shovel",
    "stone_shovel": "minecraft:copper_shovel",
    "minecraft:stone_axe": "minecraft:copper_axe",
    "stone_axe": "minecraft:copper_axe",
    "minecraft:stone_hoe": "minecraft:copper_hoe",
    "stone_hoe": "minecraft:copper_hoe",
    "minecraft:stone_sword": "minecraft:copper_sword",
    "stone_sword": "minecraft:copper_sword"
}

# Matcha's specific component injection for Baked Potatoes
BAKED_POTATO_COMPONENTS = {
    "minecraft:lore": [{"text": "❤❤❣", "color": "red", "italic": False}],
    "minecraft:consumable": {
        "consume_seconds": 1.6,
        "has_consume_particles": True,
        "on_consume_effects": [
            {"type": "minecraft:apply_effects", "effects": [{"id": "minecraft:regeneration", "amplifier": 2, "duration": 60, "show_particles": False, "show_icon": False}], "probability": 1.0}
        ]
    },
    "minecraft:food": {"nutrition": 0, "saturation": 0, "can_always_eat": True}
}

# Matcha's specific component injection for Cooked Meats
MEAT_COMPONENTS = {
    "minecraft:lore": [{"text": "❤❤", "color": "red", "italic": False}],
    "minecraft:consumable": {
        "on_consume_effects": [
            {"type": "minecraft:apply_effects", "effects": [{"id": "minecraft:regeneration", "amplifier": 2, "duration": 48, "show_particles": False, "show_icon": False}], "probability": 1.0}
        ]
    },
    "minecraft:food": {"nutrition": 0, "saturation": 0, "can_always_eat": True}
}

# Matcha's specific component injection for Tomatoes (Beetroots)
TOMATO_COMPONENTS = {
    "minecraft:item_name": "Tomatoes",
    "minecraft:lore": [{"text": "❤", "color": "red", "italic": False}],
    "minecraft:consumable": {
        "on_consume_effects": [
            {"type": "minecraft:apply_effects", "effects": [{"id": "minecraft:regeneration", "amplifier": 3, "duration": 15, "show_particles": False, "show_icon": False}]}
        ]
    }
}

COOKED_MEATS = {
    "minecraft:cooked_porkchop": "Cooked Porkchop",
    "minecraft:cooked_beef": "Cooked Beef",
    "minecraft:cooked_chicken": "Cooked Chicken",
    "minecraft:cooked_mutton": "Cooked Mutton"
}

# Exact mapping from your custom integration files
ARTIFACT_MAPPINGS = {
    "matcha:treasure/avesta": [
        "minecraft:chests/desert_pyramid",
        "nova_structures:chests/desert_pyramid",
        "nova_structures:chests/desert_temple/desert_temple_lesser"
    ],
    "matcha:treasure/crystal_heart": [
        "minecraft:chests/abandoned_mineshaft",
        "minecraft:chests/simple_dungeon",
        "nova_structures:chests/simple_dungeon",
        "nova_structures:chests/ancient_city"
    ],
    "matcha:treasure/divine_comedy": [
        "minecraft:chests/buried_treasure",
        "minecraft:chests/shipwreck_treasure",
        "nova_structures:chests/buried_treasure",
        "nova_structures:chests/fishing_buried_treasure",
        "nova_structures:chests/shipwreck_treasure"
    ],
    "minecraft:kleis_items/divine_fragment_poly": [
        "minecraft:chests/ancient_city",
        "nova_structures:chests/ancient_city"
    ],
    "matcha:treasure/enoch": [
        "minecraft:chests/abandoned_mineshaft",
        "minecraft:chests/simple_dungeon",
        "nova_structures:chests/simple_dungeon"
    ],
    "matcha:treasure/paradise_lost": [
        "minecraft:chests/buried_treasure",
        "minecraft:chests/shipwreck_treasure",
        "nova_structures:chests/buried_treasure",
        "nova_structures:chests/fishing_buried_treasure",
        "nova_structures:chests/shipwreck_treasure"
    ],
    "minecraft:kleis_items/ruby": [
        "minecraft:chests/bastion_bridge",
        "minecraft:chests/bastion_hoglin_stable",
        "minecraft:chests/bastion_other",
        "minecraft:chests/bastion_treasure",
        "nova_structures:chests/bastion_bridge",
        "nova_structures:chests/bastion_hoglin_stable",
        "nova_structures:chests/bastion_other",
        "nova_structures:chests/bastion_treasure"
    ],
    "minecraft:kleis_items/topaz": [
        "minecraft:chests/ancient_city",
        "nova_structures:chests/ancient_city",
        "nova_structures:chests/ancient_city_overhaul",
        "nova_structures:chests/ancient_city_center"
    ]
}

# Pre-compute targets to make the injection step efficient
TARGET_TO_ITEMS = {}
for artifact, targets in ARTIFACT_MAPPINGS.items():
    for target in targets:
        if target not in TARGET_TO_ITEMS:
            TARGET_TO_ITEMS[target] = []
        TARGET_TO_ITEMS[target].append(artifact)

def load_matcha_components(filepath):
    """Reads Matcha's recipe file to dynamically learn item components."""
    components_map = {}
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found. Dynamic components will be skipped.")
        return components_map
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        for recipe in data.values():
            if "result" in recipe and isinstance(recipe["result"], dict):
                item_id = recipe["result"].get("id", "")
                if ":" not in item_id:
                    item_id = f"minecraft:{item_id}"
                    
                if "components" in recipe["result"]:
                    components_map[item_id] = recipe["result"]["components"]
                    
    return components_map

def inject_components(entry, components, item_model=None, display_name=None):
    if "functions" not in entry or not isinstance(entry["functions"], list):
        entry["functions"] = []

    has_components = any(
        f.get("function") in ("minecraft:set_components", "set_components")
        for f in entry["functions"] if isinstance(f, dict)
    )

    if not has_components:
        comp_block = components.copy()
        if item_model:
            comp_block["minecraft:item_model"] = item_model
        if display_name:
            comp_block["minecraft:item_name"] = display_name

        entry["functions"].append({
            "function": "minecraft:set_components",
            "components": comp_block
        })

def patch_entry(entry, dynamic_components):
    if not isinstance(entry, dict):
        return

    entry_type = entry.get("type", "")

    if entry_type in ("item", "minecraft:item"):
        item_name = entry.get("name")

        if item_name in TOOL_REPLACEMENTS:
            entry["name"] = TOOL_REPLACEMENTS[item_name]

        elif item_name in FOOD_REPLACEMENTS:
            entry["type"] = "minecraft:loot_table"
            entry["value"] = FOOD_REPLACEMENTS[item_name]
            entry.pop("name", None)
            return

        elif item_name == "minecraft:beetroot":
            inject_components(entry, TOMATO_COMPONENTS)
            return

        elif item_name == "minecraft:baked_potato":
            inject_components(entry, BAKED_POTATO_COMPONENTS, "minecraft:baked_potato", "Baked Potato")
            return

        elif item_name in COOKED_MEATS:
            display_name = COOKED_MEATS[item_name]
            inject_components(entry, MEAT_COMPONENTS, item_name, display_name)
            return

        elif item_name in dynamic_components:
            inject_components(entry, dynamic_components[item_name])

    if "children" in entry and isinstance(entry["children"], list):
        for child in entry["children"]:
            patch_entry(child, dynamic_components)

def main():
    dnt_filename = "dnt mergend output.json"
    recipes_filename = "all recipes.json"
    
    if not os.path.exists(dnt_filename):
        print(f"Error: Could not find {dnt_filename}.")
        return

    dynamic_components = load_matcha_components(recipes_filename)

    with open(dnt_filename, "r", encoding="utf-8") as f:
        dnt_data = json.load(f)

    jar_updates = {}

    for filepath, table_data in dnt_data.items():
        if not isinstance(table_data, dict):
            continue

        # Extract the namespace and path string to match it against ARTIFACT_MAPPINGS
        parts = filepath.split("data/")
        target_name = ""
        if len(parts) > 1:
            local_path = parts[1]
            ns_parts = local_path.split("/")
            if len(ns_parts) >= 3:
                namespace = ns_parts[0]
                rest = "/".join(ns_parts[2:]).replace(".json", "")
                target_name = f"{namespace}:{rest}"

        jar_parts = filepath.split("/", 1)
        if len(jar_parts) < 2:
            continue

        jar_name = jar_parts[0] + ".jar"
        internal_path = jar_parts[1]

        if "pools" in table_data and isinstance(table_data["pools"], list):
            for pool in table_data["pools"]:
                if "entries" in pool and isinstance(pool["entries"], list):
                    for entry in pool["entries"]:
                        patch_entry(entry, dynamic_components)

            # Inject the custom mapped artifacts based on target_name
            if target_name in TARGET_TO_ITEMS:
                entries = []
                for item_id in TARGET_TO_ITEMS[target_name]:
                    entries.append({
                        "type": "minecraft:loot_table",
                        "value": item_id,
                        "weight": 1
                    })
                
                entries.append({"type": "minecraft:empty", "weight": 2})
                
                table_data["pools"].append({
                    "rolls": 1,
                    "entries": entries
                })

        table_data.pop("_source_file", None)

        if jar_name not in jar_updates:
            jar_updates[jar_name] = {}
        jar_updates[jar_name][internal_path] = table_data

    modified_jars = 0
    for jar_name, files_to_update in jar_updates.items():
        if not os.path.exists(jar_name):
            print(f"Skipping {jar_name} (File not found in folder)")
            continue

        print(f"Updating {jar_name}...")

        fd, temp_path = tempfile.mkstemp(suffix=".jar")
        os.close(fd)

        try:
            with zipfile.ZipFile(jar_name, 'r') as jar_read:
                with zipfile.ZipFile(temp_path, 'w', compression=zipfile.ZIP_DEFLATED) as jar_write:
                    for item in jar_read.infolist():
                        if item.filename not in files_to_update:
                            jar_write.writestr(item, jar_read.read(item.filename))

                    for internal_path, json_data in files_to_update.items():
                        json_str = json.dumps(json_data, indent=4)
                        jar_write.writestr(internal_path, json_str)

            shutil.move(temp_path, jar_name)
            modified_jars += 1
            print(f"Successfully updated {len(files_to_update)} files inside {jar_name}")

        except Exception as e:
            print(f"Failed to update {jar_name}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    print(f"\nDone! Modified {modified_jars} .jar files.")

if __name__ == "__main__":
    main()
import yaml
import json
import re
from collections import defaultdict
from pathlib import Path

DATA_FILE = Path("kana-data.yml")
API_DIR = Path("api/v1")
API_MIN_FILE = API_DIR / "kana.json"
API_PRETTY_FILE = API_DIR / "kana.pretty.json"
API_KV_FILE = API_DIR / "kana-kv.json"
API_KV_XSAMPA_FILE = API_DIR / "kana-kv-xsampa.json"
README_FILE = Path("README.md")
FULL_MD_FILE = Path("kana-table-full.md")
SIMPLE_MD_FILE = Path("kana-table-simple.md")

VOWELS = ["a", "i", "ɯ", "e", "o"]


def load_data():
    """Loads and returns the sound data from the YAML file."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def convert_ipa_to_xsampa(ipa_string):
    """Converts an IPA string to its X-SAMPA equivalent."""
    # Order is important: longer sequences first to avoid partial replacements.
    replacements = {
        "dʑ": "d_z\\",
        "tɕ": "t_s\\",
        "ɯ": "M",
        "ɕ": "s\\",
        "ç": "C",
        "ɸ": "p\\",
        "ɾ": "4",
        "ɡ": "g",
        "ɲ": "J",
        "ʲ": "_j",
    }
    for ipa, xsampa in replacements.items():
        ipa_string = ipa_string.replace(ipa, xsampa)
    return ipa_string


def generate_table(sounds, consonant_order, vowel_order, vowel_header_map=None):
    """Generates a Markdown table from a list of sounds."""
    if vowel_header_map is None:
        vowel_header_map = {v: v for v in vowel_order}

    table_data = defaultdict(dict)
    present_consonants = set()

    for sound in sounds:
        ipa_c = sound["ipa_c"]
        vowel = sound["vowel"]
        if vowel in vowel_order:
            table_data[ipa_c][vowel] = f"{sound['kana']}[{sound['ipa']}]"
            present_consonants.add(ipa_c)

    # Build Markdown string
    header = (
        "| IPA 子音 | "
        + " | ".join(vowel_header_map[v] for v in vowel_order)
        + " |"
    )
    separator = "|---|" + "---|" * len(vowel_order)

    lines = [header, separator]

    # Sort consonants based on the master order
    sorted_consonants = [c for c in consonant_order if c in present_consonants]

    for c in sorted_consonants:
        row = f"| {c} |"
        for v in vowel_order:
            cell_content = table_data[c].get(v, "")
            row += f" {cell_content} |"
        lines.append(row)

    return "\n".join(lines)


def generate_simple_table(md_table):
    """Generates a simple version of a Markdown table by removing IPA notations."""
    simple_md = re.sub(r"\[.*?\]", "", md_table)
    return simple_md


def build_readme(data):
    """Builds the main README.md file with a unified phonetic table."""
    print("Building README.md...")
    sounds = data["sounds"]
    c_order = data["consonant_order"]

    # --- README Header ---
    content = "# kana-table\n\n"
    content += "> Japanese syllabary table based on phonetics\n"
    content += "> 発音に基づいた五十音表\n\n"
    content += "This table groups kana by their consonant sound in IPA, providing a more phonetically consistent view than the standard Gojuon table.\n\n"
    content += "For more details and other formats, see the [API directory](./api/v1/).\n\n"

    # --- Generate Unified Tables ---
    all_sounds_table = generate_table(sounds, c_order, VOWELS)
    simple_table = generate_simple_table(all_sounds_table)

    content += "## Phonetic Kana Table (with IPA)\n\n"
    content += all_sounds_table + "\n\n"
    content += "## Phonetic Kana Table (Simple)\n\n"
    content += simple_table + "\n"

    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully created {README_FILE}")


def build_table_mds(data):
    """Builds separate Markdown files for the full and simple tables."""
    print("Building full and simple Markdown tables...")
    sounds = data["sounds"]
    c_order = data["consonant_order"]

    # Generate the base table with IPA
    full_table_content = generate_table(sounds, c_order, VOWELS)

    # Write the full table file
    with open(FULL_MD_FILE, "w", encoding="utf-8") as f:
        f.write("### Full Table\n\n")
        f.write(full_table_content + "\n")
    print(f"Successfully created {FULL_MD_FILE}")

    # Generate and write the simple table file
    simple_table_content = generate_simple_table(full_table_content)
    with open(SIMPLE_MD_FILE, "w", encoding="utf-8") as f:
        f.write("### Simple Table\n\n")
        f.write(simple_table_content + "\n")
    print(f"Successfully created {SIMPLE_MD_FILE}")


def build_json_api(data):
    """Builds the static JSON API files."""
    print("Building JSON API files...")
    API_DIR.mkdir(parents=True, exist_ok=True)

    # Add X-SAMPA attribute to each sound
    sounds_list = []
    for sound in data["sounds"]:
        sound_copy = sound.copy()
        sound_copy["x_sampa"] = convert_ipa_to_xsampa(sound_copy["ipa"])
        sounds_list.append(sound_copy)

    # 1. kana.json (minified list)
    with open(API_MIN_FILE, "w", encoding="utf-8") as f:
        json.dump(sounds_list, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Successfully created {API_MIN_FILE} (minified)")

    # 2. kana.pretty.json (pretty-printed list, one object per line)
    with open(API_PRETTY_FILE, "w", encoding="utf-8") as f:
        f.write("[\n")
        for i, sound in enumerate(sounds_list):
            line = json.dumps(sound, ensure_ascii=False, separators=(",", ":"))
            f.write(f"  {line}")
            if i < len(sounds_list) - 1:
                f.write(",")
            f.write("\n")
        f.write("]\n")
    print(
        f"Successfully created {API_PRETTY_FILE} (pretty, one object per line)"
    )

    # 3. kana-kv.json (key-value store with 'ipa' as key)
    kv_data_ipa = defaultdict(list)
    for sound in sounds_list:
        sound_copy = sound.copy()
        key = sound_copy.pop("ipa")
        kv_data_ipa[key].append(sound_copy)

    with open(API_KV_FILE, "w", encoding="utf-8") as f:
        json.dump(kv_data_ipa, f, ensure_ascii=False, indent=2)
    print(f"Successfully created {API_KV_FILE} (key-value by IPA)")

    # 4. kana-kv-xsampa.json (key-value store with 'x_sampa' as key)
    kv_data_xsampa = defaultdict(list)
    for sound in sounds_list:
        sound_copy = sound.copy()
        key = sound_copy.pop("x_sampa")
        kv_data_xsampa[key].append(sound_copy)

    with open(API_KV_XSAMPA_FILE, "w", encoding="utf-8") as f:
        json.dump(kv_data_xsampa, f, ensure_ascii=False, indent=2)
    print(f"Successfully created {API_KV_XSAMPA_FILE} (key-value by X-SAMPA)")


def main():
    """Main build function."""
    try:
        data = load_data()
        build_readme(data)
        build_table_mds(data)
        build_json_api(data)
        print("\nBuild process finished.")
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found. Please create it first.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()

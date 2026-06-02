import os
import sys
from pathlib import Path
import tomllib
import rich.box

BOX_MAP = {
    "MINIMAL": rich.box.MINIMAL,
    "ROUNDED": rich.box.ROUNDED,
    "SIMPLE": rich.box.SIMPLE,
    "HEAVY": rich.box.HEAVY,
    "NONE": None
}

APP_NAME = "ceyal"

#certain things are a mess. define later what can be configured, what shouldnt be.
# make it really precise in definition, though its for my personal use only...
# perplexing indeed.
# perhaps i should leave it at this. idk. add some comments atleast mayhaps

def get_user_config_path() -> Path:
    if sys.platform.startswith("linux"):
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    elif sys.platform == "darwin":
        config_home = Path.home() / "Library" / "Preferences"
    elif sys.platform.startswith("win"):
        config_home = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        config_home = Path.home() / ".config"
    return config_home / APP_NAME / "theme.toml"

def get_default_config_path() -> Path:
    # target is src/config/theme.toml , default.
    return Path(__file__).parent.parent / "config" / "theme.toml"

def _deep_update(default_dict, user_dict):
    # just appending that default with user config, and overwrite same keys., you get it.

    for key, value in user_dict.items():
        if isinstance(value, dict) and isinstance(default_dict.get(key), dict):
            default_dict[key] = _deep_update(default_dict.get(key, {}), value)
        else:
            default_dict[key] = value
    return default_dict

def load_theme() -> dict:
    default_path = get_default_config_path()
    user_path = get_user_config_path()
    theme_data = {}

    if default_path.exists():
        with open(default_path, "rb") as f:
            theme_data = tomllib.load(f)
    else:
        print(f"Warning: Default theme not found at {default_path}", file=sys.stderr)

    if user_path.exists():
        try:
            with open(user_path, "rb") as f:
                user_theme = tomllib.load(f)
                theme_data = _deep_update(theme_data, user_theme)
        except Exception as e:
            print(f"Warning: Failed to load user theme at {user_path}: {e}", file=sys.stderr)

    return theme_data

_THEME = load_theme()

# dont forget add to these as the theme.toml grows , etc.,


def get_color(urgency_name: str) -> str:
    return _THEME.get("colors", {}).get(urgency_name.lower(), "white")

def get_icon(icon_name: str) -> str:
    return _THEME.get("icons", {}).get(icon_name, "?")

def get_warning(urgency_name: str) -> str:
    return _THEME.get("warnings", {}).get(urgency_name.lower(), "")


def is_blinking() -> bool:
    return _THEME.get("animations", {}).get("blink_ongoing", True)

def get_table_kwargs() -> dict:
    tbl_config = _THEME.get("table", {})
    
    padding_val = tbl_config.get("padding", [0, 1])
    box_str = tbl_config.get("box_style", "MINIMAL").upper()
    
    return {
        "border_style": tbl_config.get("border_style", "dim"),
        "padding": tuple(padding_val), # Rich expects a tuple for padding
        "box": BOX_MAP.get(box_str, rich.box.MINIMAL),
        "expand": tbl_config.get("expand", False)
    }

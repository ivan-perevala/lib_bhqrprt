import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

project = "bhqrprt"
copyright = "2023-2024, BlenderHQ"
author = "Ivan Perevala (ivpe)"
version = "1.0.0"

extensions = [
    "sphinx.ext.coverage",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
]
source_suffix = {'.rst': 'restructuredtext'}
master_doc = 'index'

autodoc_member_order = "bysource"
autodoc_mock_imports = ["bpy", "gpu", "rna_keymap_ui", "bl_ui", "blf", "mathutils", "numpy", "gpu_extras"]

autodoc_typehints_format = 'short'
autodoc_typehints = 'none'

napoleon_google_docstring = False
napoleon_use_param = False
napoleon_use_ivar = True

language = "en"
locale_dirs = ['locale/']
gettext_compact = True
gettext_location = True

html_theme = "furo"
html_static_path = ["_static"]
html_templates_path = ["_templates"]
html_favicon = "_static/favicon.ico"
html_logo = "_static/logo.svg"
html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "black",
    },

    "dark_css_variables": {
        "color-brand-primary": "white",
    },
}

import sys
import shutil
from pyshortcuts import make_shortcut


def create_shortcuts():
    """Create application shortcuts"""
    # The command name from your entry_points
    command_name = 'spice'

    try:
        # Try to find it in PATH first
        script_path = shutil.which(command_name)

        if script_path is None:
            print(f"Error: '{command_name}' not found in PATH.")
            print(f"Make sure the package is installed and try again.")
            print(f"Try running: pip install --force-reinstall your-package")
            sys.exit(1)

        print(f"Found script at: {script_path}")

        make_shortcut(
            script=script_path,
            name='Spice',
            description='The Spice Editor - A Python IDE for Students',
            icon='path/to/icon.png',
            terminal=False,
            startmenu=True,
        )
        print("✓ Shortcuts created successfully!")
    except Exception as e:
        print(f"Failed to create shortcuts: {e}")
        sys.exit(1)


if __name__ == '__main__':
    create_shortcuts()
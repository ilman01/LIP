import xml.etree.ElementTree as ET
import copy
import json
import os
import urllib.request

class CircuitTransfer:
    def __init__(self, src_path: str, dst_path: str):
        if src_path:
            self._import_source_file(src_path)
        self._import_destination_file(dst_path)

    def _import_source_file(self, src_path: str):
        self.src_path = self._sanitize_path(src_path)
        self.src_tree = ET.parse(self.src_path)
        self.src_root = self.src_tree.getroot()   # <project> of file1

    def _import_destination_file(self, dst_path: str):
        self.dst_path = self._sanitize_path(dst_path)
        self.dst_tree = ET.parse(self.dst_path)
        self.dst_root = self.dst_tree.getroot()   # <project> of file2

    def _sanitize_path(self, path: str) -> str:
        if not isinstance(path, str):
            raise TypeError("Path must be a string. Seriously.")

        cleaned = path.strip().strip("'").strip("\"")

        # absolute path resolution to avoid "../" shenanigans
        cleaned = os.path.abspath(cleaned)

        if not os.path.exists(cleaned):
            raise FileNotFoundError(f"Path does not exist: {cleaned}")

        if not os.path.isfile(cleaned):
            raise ValueError(f"Path is not a file: {cleaned}")

        return cleaned
    
    def load_source_from_string(self, xml_string: str):
        """Replace the current source XML with one loaded from a string."""
        root = ET.fromstring(xml_string)
        self.src_tree = ET.ElementTree(root)
        self.src_root = root

    def get_src_circuit(self, name: str):
        """Get <circuit name='...'> from source file."""
        return self.src_root.find(f"./circuit[@name='{name}']")

    def get_dst_circuit(self, name: str):
        """Get <circuit name='...'> from destination file."""
        return self.dst_root.find(f"./circuit[@name='{name}']")

    def copy_to_dst(self, name: str, new_name: str = None):
        """
        Copy <circuit> from src → dst.
        If circuit with same name exists in dst, replace it.
        """
        src_circuit = self.get_src_circuit(name)
        if src_circuit is None:
            raise ValueError(f"Circuit '{name}' not found in source")

        # Clone it
        clone = copy.deepcopy(src_circuit)

        # Rename if needed
        if new_name is not None:
            clone.set("name", new_name)
            final_name = new_name
        else:
            final_name = name

        # If a circuit with the same name exists in destination, remove it
        dst_existing = self.get_dst_circuit(final_name)
        if dst_existing is not None:
            self.dst_root.remove(dst_existing)

        # Append the cloned circuit into destination <project>
        self.dst_root.append(clone)

    def save(self, out_path=None):
        out_path = self._sanitize_path(out_path)
        path = out_path
        if path is None:
            raise ValueError("Must specify output path for destination file")
        self.dst_tree.write(path, encoding="utf-8", xml_declaration=True)

class JSONMenu:
    def __init__(self, menu_json: dict):
        self.menu = menu_json

    @classmethod
    def from_file(cls, path: str):
        with open(path, "r") as f:
            data = json.load(f)
        return cls(data)
    
    @classmethod
    def from_string(cls, text: str):
        """Load menu structure from a JSON string."""
        data = json.loads(text)
        return cls(data)

    def run(self):
        history = []        # stack of dicts
        key_history = []    # stack of parent keys
        current = self.menu
        parent_key = None

        while True:
            # final leaf? exit and return the value
            if not isinstance(current, dict):
                print(f"\nImported: {current}")
                return current

            # Header
            if parent_key:
                print(f"\n=== {parent_key} ===")
            else:
                print("\n=== Logisim Importer Project (by Ilman) ===")

            keys = list(current.keys())

            # Print choices
            for i, key in enumerate(keys, start=1):
                print(f"{i}. {key}")

            # Add Back option only if not at root
            if history:
                print(f"{len(keys) + 1}. Back")

            choice = input("\nPick a number: ")

            # Validate numeric input
            if not choice.isdigit():
                print("Invalid choice, try again.")
                continue

            choice = int(choice)

            # Handle Back
            if history and choice == len(keys) + 1:
                current = history.pop()
                parent_key = key_history.pop() if key_history else None
                continue

            # Normal pick
            if 1 <= choice <= len(keys):
                picked_key = keys[choice - 1]

                # push current state to history
                history.append(current)
                key_history.append(parent_key)

                # move deeper
                parent_key = picked_key
                current = current[picked_key]
            else:
                print("Invalid choice, try again.")

def main():
    destination_file = input("Please enter the .circ file path that you want to insert to (destination): ")

    if os.path.exists("select_options.json"):
        menu = JSONMenu.from_file("select_options.json")
    else:
        with urllib.request.urlopen("https://raw.githubusercontent.com/ilman01/LIP/refs/heads/main/select_options.json") as response:
            remote_select_options = response.read().decode('utf-8')
        menu = JSONMenu.from_string(remote_select_options)
    
    picked = menu.run()

    if picked == "copy_circ":
        source_file = input("Source .circ: ")
        circ_name = input("Circuit Name: ")
        transfer = CircuitTransfer(source_file, destination_file)
        transfer.copy_to_dst(circ_name)
        transfer.save(destination_file)
        return

    if os.path.exists("master.circ"):
        transfer = CircuitTransfer("master.circ", destination_file)
    else:
        with urllib.request.urlopen("https://raw.githubusercontent.com/ilman01/LIP/refs/heads/main/master.circ") as response:
            remote_master_circ = response.read().decode('utf-8')
        transfer = CircuitTransfer("", destination_file)
        transfer.load_source_from_string(remote_master_circ)

    for circ_name in picked:
        transfer.copy_to_dst(circ_name)

    transfer.save(destination_file)

if __name__ == "__main__":
    main()

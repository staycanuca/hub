import os
import hashlib
import shutil
import xml.etree.ElementTree as ET
import zipfile
import urllib.parse

class RepoGenerator:
    """
    Generates a Kodi repository from addon sources.
    - Respects existing repository addon.xml if found.
    - Translates GitHub URL to the correct raw content URL.
    - Creates/updates the repository addon with a specific version.
    - Zips each addon folder with version in the filename (e.g., addon-1.2.3.zip).
    - Places zips in their own subdirectories for Kodi compatibility.
    - Creates addons.xml and addons.xml.md5.
    """

    # --- CONFIGURATION ---
    GITHUB_URL = "https://github.com/staycanuca/hub"
    DEFAULT_BRANCH = "main"

    REPO_ID = "repository.hub"
    REPO_NAME = "Hub Repository"
    REPO_VERSION = "1.0.3"  # Fallback version if repo addon.xml doesn't exist
    PROVIDER_NAME = "1X & Geamanu"
    # --- END CONFIGURATION ---

    def __init__(self):
        self.root_dir = os.path.abspath(os.path.dirname(__file__))
        self.raw_github_url = self._translate_github_url(self.GITHUB_URL)
        self._generate()

    def _translate_github_url(self, url):
        """Translates a standard GitHub URL to its raw content URL for a specific branch."""
        parsed = urllib.parse.urlparse(url)
        if parsed.netloc.lower() != 'github.com':
            print(f"URL is not a standard GitHub URL. Using it as is: {url}")
            return url.strip('/') + '/'
        
        path_parts = [part for part in parsed.path.split('/') if part]
        if len(path_parts) < 2:
            print(f"URL path '{parsed.path}' is not a valid user/repo format. Using URL as is.")
            return url.strip('/') + '/'

        user = path_parts[0]
        repo = path_parts[1].replace('.git', '')
        
        raw_url = f"https://github.com/{user}/{repo}/raw/refs/heads/{self.DEFAULT_BRANCH}/"
        print(f"Translated GitHub URL to raw content URL: {raw_url}")
        return raw_url

    def _generate(self):
        """Main generation logic."""
        print("\nStarting Kodi repository generation...")
        self._prepare_repository_addon()
        addons = self._find_addons()
        if not addons:
            print("No addons found. Exiting.")
            return

        self._process_addons(addons)
        print("\nRepository generation complete!")
        print(f"URL base configured: {self.raw_github_url}")
        print("The following files were created/updated:")
        print("- addons.xml & addons.xml.md5")
        print("- Versioned .zip files placed in subdirectories for each addon.")
        print("\nYou can now commit and push these files to your GitHub repository.")

    def _prepare_repository_addon(self):
        """Ensures the repository addon exists, generating it if necessary."""
        repo_dir = os.path.join(self.root_dir, self.REPO_ID)
        addon_xml_path = os.path.join(repo_dir, 'addon.xml')

        if os.path.exists(addon_xml_path):
            print(f"Found existing addon.xml for '{self.REPO_ID}'. Using it.")
            tree = ET.parse(addon_xml_path)
            self.REPO_VERSION = tree.getroot().get('version', self.REPO_VERSION)
            print(f"  -> Using version {self.REPO_VERSION} from existing file.")
        else:
            print(f"No addon.xml for '{self.REPO_ID}' found. Generating a new one...")
            os.makedirs(repo_dir, exist_ok=True)
            root = ET.Element('addon', id=self.REPO_ID, name=self.REPO_NAME, version=self.REPO_VERSION, provider_name=self.PROVIDER_NAME.replace('&', '&amp;'))
            ext_repo = ET.SubElement(root, 'extension', point='xbmc.addon.repository', name=self.REPO_NAME)
            dir_element = ET.SubElement(ext_repo, 'dir')
            ET.SubElement(dir_element, 'info', compressed="false").text = f"{self.raw_github_url}addons.xml"
            ET.SubElement(dir_element, 'checksum').text = f"{self.raw_github_url}addons.xml.md5"
            ET.SubElement(dir_element, 'datadir', zip="true").text = f"{self.raw_github_url}zip/"
            
            ext_meta = ET.SubElement(root, 'extension', point='xbmc.addon.metadata')
            ET.SubElement(ext_meta, 'summary').text = f"The official repository for {self.REPO_NAME}."
            ET.SubElement(ext_meta, 'description').text = f"Install this to get the latest updates from {self.REPO_NAME}."
            ET.SubElement(ext_meta, 'platform').text = "all"
            assets = ET.SubElement(ext_meta, 'assets')
            ET.SubElement(assets, 'icon').text = "icon.png"

            tree = ET.ElementTree(root)
            try: ET.indent(tree, space="    ", level=0)
            except AttributeError: pass
            tree.write(addon_xml_path, encoding='utf-8', xml_declaration=True)
            print(f"  -> Generated addon.xml for '{self.REPO_ID}' version {self.REPO_VERSION}")

        if not os.path.exists(os.path.join(repo_dir, 'icon.png')):
            print(f"WARNING: No icon.png found in '{self.REPO_ID}'.")

    def _find_addons(self):
        """Finds addon directories."""
        found = []
        print("\nScanning for addons:")
        for item in os.listdir(self.root_dir):
            addon_dir = os.path.join(self.root_dir, item)
            if os.path.isdir(addon_dir) and os.path.exists(os.path.join(addon_dir, 'addon.xml')) and not item.startswith('.'):
                print(f"  - Found: {item}")
                found.append(addon_dir)
        return found

    def _process_addons(self, addons):
        """Zips addons and generates the main addons.xml."""
        addons_xml_root = ET.Element('addons')

        for addon_dir in addons:
            addon_folder_name = os.path.basename(addon_dir)
            try:
                addon_xml_path = os.path.join(addon_dir, 'addon.xml')
                tree = ET.parse(addon_xml_path)
                addon_node = tree.getroot()
                addon_id = addon_node.get('id')
                addon_version = addon_node.get('version')

                if not addon_id or not addon_version:
                    print(f"\nWARNING: Skipping {addon_folder_name}. Missing id or version in addon.xml.")
                    continue
                
                print(f"\nProcessing: {addon_id} v{addon_version}")

                if addon_id == self.REPO_ID:
                    zip_version = self.REPO_VERSION
                else:
                    zip_version = addon_version
                    addons_xml_root.append(addon_node)

                # Create versioned zip file inside a subdirectory within 'zip'
                packages_dir = os.path.join(self.root_dir, 'zip')
                os.makedirs(packages_dir, exist_ok=True)
                zip_dir = os.path.join(packages_dir, addon_id)
                os.makedirs(zip_dir, exist_ok=True)
                zip_filename = f"{addon_id}-{zip_version}.zip"
                zip_filepath = os.path.join(zip_dir, zip_filename)
                
                print(f"  -> Creating archive: {zip_filename}")
                with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for root, _, files in os.walk(addon_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join(addon_folder_name, os.path.relpath(file_path, addon_dir))
                            zf.write(file_path, arcname)
                print(f"  -> Archive {zip_filename} created successfully.")

            except Exception as e:
                print(f"ERROR: Failed to process {addon_folder_name}: {e}")
        
        self._write_xml_files(addons_xml_root)

    def _write_xml_files(self, root_element):
        """Writes the final addons.xml and its md5 hash."""
        try:
            try: ET.indent(root_element, space="    ", level=0)
            except AttributeError: pass
            
            tree = ET.ElementTree(root_element)
            xml_path = os.path.join(self.root_dir, 'addons.xml')
            tree.write(xml_path, encoding='utf-8', xml_declaration=True)
            print("\nGenerated addons.xml")

            with open(xml_path, 'rb') as f:
                md5_hash = hashlib.md5(f.read()).hexdigest()
            
            md5_path = os.path.join(self.root_dir, 'addons.xml.md5')
            with open(md5_path, 'w') as f:
                f.write(md5_hash)
            print("Generated addons.xml.md5")

        except Exception as e:
            print(f"ERROR: Failed to write XML or MD5 file: {e}")

if __name__ == '__main__':
    RepoGenerator()

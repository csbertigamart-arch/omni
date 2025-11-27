import os
import json
import datetime
from pathlib import Path


class FileManager:
    def __init__(self):
        self.current_dir = os.getcwd()
        self.config_file = "excluded_files.json"
        self.excluded_files = []
        self.excluded_folders = []
        self.load_config()

    def load_config(self):
        """Load configuration from JSON file, create default if doesn't exist"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.excluded_files = config.get('excluded_files', [])
                    self.excluded_folders = config.get('excluded_folders', [])
                print(f"✓ Konfigurasi berhasil dimuat dari {self.config_file}")
            else:
                self.create_default_config()
        except Exception as e:
            print(f"✗ Error loading config: {str(e)}")
            self.create_default_config()

    def create_default_config(self):
        """Create default configuration file"""
        print("📝 Membuat file konfigurasi default...")
        # Default configuration
        self.excluded_files = ['allcode-',
                               'excluded_files.json', 'file_manager.py']
        self.excluded_folders = ['__pycache__', '.git', 'node_modules']
        self.save_config()
        print(
            f"✓ File {self.config_file} berhasil dibuat dengan konfigurasi default")

    def save_config(self):
        """Save configuration to JSON file"""
        try:
            config = {
                'excluded_files': self.excluded_files,
                'excluded_folders': self.excluded_folders,
                'last_updated': datetime.datetime.now().isoformat()
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"✓ Konfigurasi berhasil disimpan ke {self.config_file}")
        except Exception as e:
            print(f"✗ Error saving config: {str(e)}")

    def is_excluded(self, filepath):
        """Check if file or folder should be excluded"""
        filename = os.path.basename(filepath)

        # Check excluded files
        for excluded in self.excluded_files:
            if excluded in filename:
                return True

        # Check excluded folders
        for folder in self.excluded_folders:
            if folder in filepath.split(os.sep):
                return True

        return False

    def scan_all_files_tree(self, directory=None, prefix="", file_list=None, level=0):
        """Scan all files and folders in tree structure"""
        if directory is None:
            directory = self.current_dir
        if file_list is None:
            file_list = []

        try:
            items = sorted(os.listdir(directory))
            for i, item in enumerate(items):
                path = os.path.join(directory, item)
                is_last = i == len(items) - 1

                # Determine icon and style
                if os.path.isdir(path):
                    icon = "📁"
                    relative_path = os.path.relpath(path, self.current_dir)
                    is_excluded = self.is_excluded(relative_path)

                    # Add to file_list with proper prefix
                    current_prefix = prefix + ("└── " if is_last else "├── ")
                    file_list.append({
                        'path': relative_path,
                        'name': item,
                        'type': 'folder',
                        'display': f"{current_prefix}{icon} {item}/",
                        'excluded': is_excluded,
                        'level': level
                    })

                    # Only scan subdirectories if folder is not excluded
                    if not is_excluded:
                        new_prefix = prefix + ("    " if is_last else "│   ")
                        self.scan_all_files_tree(
                            path, new_prefix, file_list, level + 1)
                    else:
                        # Add indication that folder content is excluded
                        excluded_prefix = prefix + \
                            ("    " if is_last else "│   ")
                        file_list.append({
                            'path': f"{relative_path}/[CONTENT_EXCLUDED]",
                            'name': '[CONTENT_EXCLUDED]',
                            'type': 'info',
                            'display': f"{excluded_prefix}└── 📝 [Konten folder ini dikecualikan]",
                            'excluded': True,
                            'level': level + 1
                        })
                else:
                    icon = "📄"
                    relative_path = os.path.relpath(path, self.current_dir)
                    is_excluded = self.is_excluded(relative_path)

                    # Only add files that are not in excluded folders
                    parent_excluded = False
                    for folder in self.excluded_folders:
                        if folder in relative_path.split(os.sep):
                            parent_excluded = True
                            break

                    if not parent_excluded:
                        current_prefix = prefix + \
                            ("└── " if is_last else "├── ")
                        file_list.append({
                            'path': relative_path,
                            'name': item,
                            'type': 'file',
                            'display': f"{current_prefix}{icon} {item}",
                            'excluded': is_excluded,
                            'level': level
                        })
        except PermissionError:
            # Skip directories we don't have permission to access
            pass

        return file_list

    def read_file_content(self, filepath):
        """Read file content with appropriate encoding"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                return f"[Error reading file: {str(e)}]"
        except Exception as e:
            return f"[Error reading file: {str(e)}]"


class CodeCollector(FileManager):
    def __init__(self):
        super().__init__()
        self.output_filename = self.generate_output_filename()
        self.processed_files = []
        self.all_files = []

    def generate_output_filename(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"allcode-{timestamp}.txt"

    def collect_files(self):
        """Collect all non-excluded files"""
        files = []
        all_items = self.scan_all_files_tree()
        for item in all_items:
            if item['type'] == 'file' and not item['excluded']:
                files.append(item['path'])
        return files

    def generate_report(self):
        """Generate report in desired format"""
        files = self.collect_files()
        report_content = ""

        for file in files:
            content = self.read_file_content(file)
            report_content += f"{file} =\n{content}\n\n{'-'*50}\n\n"
            self.processed_files.append(file)

        return report_content

    def save_report(self):
        """Save report to file"""
        report = self.generate_report()
        try:
            with open(self.output_filename, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"✓ File {self.output_filename} berhasil dibuat!")

            # Display processed files
            self.print_processed_files()

        except Exception as e:
            print(f"✗ Error saat menyimpan file: {str(e)}")

    def print_processed_files(self):
        """Display list of processed files"""
        if self.processed_files:
            print("\nFile-file yang telah dimasukkan ke dalam txt:")
            print("-" * 50)
            for i, filename in enumerate(self.processed_files, 1):
                print(f"{i}. {filename}")
            print(f"\nTotal: {len(self.processed_files)} file")
        else:
            print("\nTidak ada file yang diproses.")


class ExclusionManager(FileManager):
    def __init__(self):
        super().__init__()
        self.file_tree = []

    def scan_separated_items(self):
        """Scan and separate folders and files"""
        all_items = self.scan_all_files_tree()

        folders = []
        files = []

        for item in all_items:
            if item['type'] == 'folder':
                folders.append(item)
            elif item['type'] == 'file':
                files.append(item)
            # Skip info items for this view

        return folders, files

    def display_separated_lists(self):
        """Display folders and files in separate numbered lists"""
        print("\n" + "="*80)
        print("📂 DAFTAR FOLDER DAN FILE TERPISAH")
        print("="*80)

        folders, files = self.scan_separated_items()

        excluded_folder_count = 0
        included_folder_count = 0
        excluded_file_count = 0
        included_file_count = 0

        # Display folders
        print("\n📁 DAFTAR FOLDER:")
        print("-" * 40)
        if folders:
            for i, folder in enumerate(folders, 1):
                if folder['excluded']:
                    print(f"\033[91m{i:3d}. {folder['display']} ✗\033[0m")
                    excluded_folder_count += 1
                else:
                    print(f"\033[97m{i:3d}. {folder['display']}\033[0m")
                    included_folder_count += 1
        else:
            print("   Tidak ada folder")

        # Display files
        print("\n📄 DAFTAR FILE:")
        print("-" * 40)
        if files:
            # Use letters for files
            for i, file_item in enumerate(files, 1):
                letter = chr(96 + i)  # a, b, c, ...
                if file_item['excluded']:
                    print(
                        f"\033[91m{letter:>3s}. {file_item['display']} ✗\033[0m")
                    excluded_file_count += 1
                else:
                    print(
                        f"\033[97m{letter:>3s}. {file_item['display']}\033[0m")
                    included_file_count += 1
        else:
            print("   Tidak ada file")

        print("\n" + "="*80)
        print("📊 STATISTIK:")
        print(
            f"Folder: {len(folders)} total ({included_folder_count} disertakan, {excluded_folder_count} dikecualikan)")
        print(
            f"File: {len(files)} total ({included_file_count} disertakan, {excluded_file_count} dikecualikan)")
        print("="*80)

        return folders, files

    def display_tree_with_colors(self):
        """Display file tree with colors (red for excluded, white for included)"""
        print("\n" + "="*80)
        print("🌳 STRUKTUR FILE & FOLDER (Merah: Dikecualikan, Putih: Disertakan)")
        print("="*80)

        self.file_tree = self.scan_all_files_tree()

        excluded_count = 0
        included_count = 0

        print(f"📁 {os.path.basename(self.current_dir)}/")
        for i, item in enumerate(self.file_tree, 1):
            if item['excluded']:
                # Red color for excluded items
                print(f"\033[91m{i:3d}. {item['display']} ✗\033[0m")
                excluded_count += 1
            else:
                # White color for included items
                print(f"\033[97m{i:3d}. {item['display']}\033[0m")
                included_count += 1

        print("-" * 80)
        print(f"Total: {len(self.file_tree)} item")
        print(f"Disertakan: {included_count} item")
        print(f"Dikecualikan: {excluded_count} item")
        print("="*80)

        return self.file_tree

    def add_exclusion(self, item_type, item_index, items_list):
        """Add file/folder to exclusion list"""
        if 1 <= item_index <= len(items_list):
            item = items_list[item_index - 1]
            item_name = item['name']
            item_path = item['path']

            print(f"\n📝 Menambah pengecualian:")
            print(f"   Nama: {item_name}")
            print(f"   Path: {item_path}")
            print(f"   Tipe: {'Folder' if item_type == 'folder' else 'File'}")

            confirm = input("\nApakah Anda yakin? (y/n): ").strip().lower()

            if confirm == 'y':
                if item_type == 'folder':
                    if item_name not in self.excluded_folders:
                        self.excluded_folders.append(item_name)
                        self.save_config()
                        print(
                            f"✓ Folder '{item_name}' telah ditambahkan ke daftar pengecualian")
                    else:
                        print(
                            f"ℹ Folder '{item_name}' sudah ada dalam daftar pengecualian")
                else:
                    if item_name not in self.excluded_files:
                        self.excluded_files.append(item_name)
                        self.save_config()
                        print(
                            f"✓ File '{item_name}' telah ditambahkan ke daftar pengecualian")
                    else:
                        print(
                            f"ℹ File '{item_name}' sudah ada dalam daftar pengecualian")
            else:
                print("✗ Penambahan pengecualian dibatalkan")
        else:
            print("✗ Nomor item tidak valid")

    def remove_exclusion(self, item_type, item_index, items_list):
        """Remove file/folder from exclusion list"""
        if 1 <= item_index <= len(items_list):
            item = items_list[item_index - 1]
            item_name = item['name']
            item_path = item['path']

            print(f"\n🗑️  Menghapus pengecualian:")
            print(f"   Nama: {item_name}")
            print(f"   Path: {item_path}")
            print(f"   Tipe: {'Folder' if item_type == 'folder' else 'File'}")

            confirm = input("\nApakah Anda yakin? (y/n): ").strip().lower()

            if confirm == 'y':
                if item_type == 'folder':
                    if item_name in self.excluded_folders:
                        self.excluded_folders.remove(item_name)
                        self.save_config()
                        print(
                            f"✓ Folder '{item_name}' telah dihapus dari daftar pengecualian")
                    else:
                        print(
                            f"ℹ Folder '{item_name}' tidak ada dalam daftar pengecualian")
                else:
                    if item_name in self.excluded_files:
                        self.excluded_files.remove(item_name)
                        self.save_config()
                        print(
                            f"✓ File '{item_name}' telah dihapus dari daftar pengecualian")
                    else:
                        print(
                            f"ℹ File '{item_name}' tidak ada dalam daftar pengecualian")
            else:
                print("✗ Penghapusan pengecualian dibatalkan")
        else:
            print("✗ Nomor item tidak valid")

    def manage_exclusions(self):
        """Main menu for managing exclusions"""
        while True:
            print("\n🎯 Opsi Tampilan:")
            print("1. Tampilan Tree (struktur asli)")
            print("2. Tampilan Terpisah (folder dan file terpisah)")
            print("3. Kembali ke menu utama")

            view_choice = input("\nPilih tampilan (1-3): ").strip()

            if view_choice == '1':
                self.manage_exclusions_tree_view()
            elif view_choice == '2':
                self.manage_exclusions_separated_view()
            elif view_choice == '3':
                break
            else:
                print("✗ Pilihan tidak valid")

    def manage_exclusions_tree_view(self):
        """Manage exclusions using tree view"""
        while True:
            file_tree = self.display_tree_with_colors()

            print("\n🎯 Opsi Pengelolaan Pengecualian:")
            print("1. Tambah item ke daftar pengecualian")
            print("2. Hapus item dari daftar pengecualian")
            print("3. Lihat daftar pengecualian saat ini")
            print("4. Refresh tampilan")
            print("5. Reset ke konfigurasi default")
            print("6. Kembali ke menu tampilan")

            choice = input("\nPilih opsi (1-6): ").strip()

            if choice == '1':
                try:
                    item_num = int(
                        input("Masukkan nomor item yang akan DIKECUALIKAN: "))
                    self.add_exclusion_single_list(item_num, file_tree)
                except ValueError:
                    print("✗ Masukkan nomor yang valid")

            elif choice == '2':
                try:
                    item_num = int(
                        input("Masukkan nomor item yang akan DISERTAKAN: "))
                    self.remove_exclusion_single_list(item_num, file_tree)
                except ValueError:
                    print("✗ Masukkan nomor yang valid")

            elif choice == '3':
                self.show_current_exclusions()

            elif choice == '4':
                print("🔄 Memuat ulang struktur file...")
                continue

            elif choice == '5':
                self.reset_to_default()

            elif choice == '6':
                break

            else:
                print("✗ Pilihan tidak valid")

    def manage_exclusions_separated_view(self):
        """Manage exclusions using separated view"""
        while True:
            folders, files = self.display_separated_lists()

            print("\n🎯 Opsi Pengelolaan Pengecualian:")
            print("1. Tambah folder ke daftar pengecualian")
            print("2. Hapus folder dari daftar pengecualian")
            print("3. Tambah file ke daftar pengecualian")
            print("4. Hapus file dari daftar pengecualian")
            print("5. Lihat daftar pengecualian saat ini")
            print("6. Refresh tampilan")
            print("7. Reset ke konfigurasi default")
            print("8. Kembali ke menu tampilan")

            choice = input("\nPilih opsi (1-8): ").strip()

            if choice == '1':
                try:
                    item_num = int(
                        input("Masukkan nomor folder yang akan DIKECUALIKAN: "))
                    self.add_exclusion('folder', item_num, folders)
                except ValueError:
                    print("✗ Masukkan nomor yang valid")

            elif choice == '2':
                try:
                    item_num = int(
                        input("Masukkan nomor folder yang akan DISERTAKAN: "))
                    self.remove_exclusion('folder', item_num, folders)
                except ValueError:
                    print("✗ Masukkan nomor yang valid")

            elif choice == '3':
                try:
                    item_input = input(
                        "Masukkan huruf file yang akan DIKECUALIKAN: ").strip().lower()
                    if len(item_input) == 1 and item_input.isalpha():
                        item_num = ord(item_input) - ord('a') + 1
                        if 1 <= item_num <= len(files):
                            self.add_exclusion('file', item_num, files)
                        else:
                            print("✗ Huruf file tidak valid")
                    else:
                        print("✗ Masukkan huruf yang valid (a, b, c, ...)")
                except Exception as e:
                    print(f"✗ Error: {str(e)}")

            elif choice == '4':
                try:
                    item_input = input(
                        "Masukkan huruf file yang akan DISERTAKAN: ").strip().lower()
                    if len(item_input) == 1 and item_input.isalpha():
                        item_num = ord(item_input) - ord('a') + 1
                        if 1 <= item_num <= len(files):
                            self.remove_exclusion('file', item_num, files)
                        else:
                            print("✗ Huruf file tidak valid")
                    else:
                        print("✗ Masukkan huruf yang valid (a, b, c, ...)")
                except Exception as e:
                    print(f"✗ Error: {str(e)}")

            elif choice == '5':
                self.show_current_exclusions()

            elif choice == '6':
                print("🔄 Memuat ulang struktur file...")
                continue

            elif choice == '7':
                self.reset_to_default()

            elif choice == '8':
                break

            else:
                print("✗ Pilihan tidak valid")

    def add_exclusion_single_list(self, item_index, file_tree):
        """Add exclusion for single list view"""
        if 1 <= item_index <= len(file_tree):
            item = file_tree[item_index - 1]
            item_name = item['name']

            # Skip if it's an info item
            if item_name == '[CONTENT_EXCLUDED]':
                print("✗ Tidak dapat mengecualikan item informasi")
                return

            item_type = 'folder' if item['type'] == 'folder' else 'file'

            print(f"\n📝 Menambah pengecualian:")
            print(f"   Nama: {item_name}")
            print(f"   Tipe: {'Folder' if item_type == 'folder' else 'File'}")

            confirm = input("\nApakah Anda yakin? (y/n): ").strip().lower()

            if confirm == 'y':
                if item_type == 'folder':
                    if item_name not in self.excluded_folders:
                        self.excluded_folders.append(item_name)
                        self.save_config()
                        print(
                            f"✓ Folder '{item_name}' telah ditambahkan ke daftar pengecualian")
                    else:
                        print(
                            f"ℹ Folder '{item_name}' sudah ada dalam daftar pengecualian")
                else:
                    if item_name not in self.excluded_files:
                        self.excluded_files.append(item_name)
                        self.save_config()
                        print(
                            f"✓ File '{item_name}' telah ditambahkan ke daftar pengecualian")
                    else:
                        print(
                            f"ℹ File '{item_name}' sudah ada dalam daftar pengecualian")
            else:
                print("✗ Penambahan pengecualian dibatalkan")
        else:
            print("✗ Nomor item tidak valid")

    def remove_exclusion_single_list(self, item_index, file_tree):
        """Remove exclusion for single list view"""
        if 1 <= item_index <= len(file_tree):
            item = file_tree[item_index - 1]
            item_name = item['name']

            # Skip if it's an info item
            if item_name == '[CONTENT_EXCLUDED]':
                print("✗ Tidak dapat menghapus pengecualian item informasi")
                return

            item_type = 'folder' if item['type'] == 'folder' else 'file'

            print(f"\n🗑️  Menghapus pengecualian:")
            print(f"   Nama: {item_name}")
            print(f"   Tipe: {'Folder' if item_type == 'folder' else 'File'}")

            confirm = input("\nApakah Anda yakin? (y/n): ").strip().lower()

            if confirm == 'y':
                if item_type == 'folder':
                    if item_name in self.excluded_folders:
                        self.excluded_folders.remove(item_name)
                        self.save_config()
                        print(
                            f"✓ Folder '{item_name}' telah dihapus dari daftar pengecualian")
                    else:
                        print(
                            f"ℹ Folder '{item_name}' tidak ada dalam daftar pengecualian")
                else:
                    if item_name in self.excluded_files:
                        self.excluded_files.remove(item_name)
                        self.save_config()
                        print(
                            f"✓ File '{item_name}' telah dihapus dari daftar pengecualian")
                    else:
                        print(
                            f"ℹ File '{item_name}' tidak ada dalam daftar pengecualian")
            else:
                print("✗ Penghapusan pengecualian dibatalkan")
        else:
            print("✗ Nomor item tidak valid")

    def reset_to_default(self):
        """Reset configuration to default with confirmation"""
        print("\n⚠️  PERINGATAN: Reset ke Konfigurasi Default")
        print("Konfigurasi saat ini akan diganti dengan:")
        print(
            f"File dikecualikan: {['allcode-',  'excluded_files.json', 'file_manager.py']}")
        print(
            f"Folder dikecualikan: {['__pycache__', '.git', 'node_modules']}")

        confirm = input(
            "\nApakah Anda yakin ingin reset ke konfigurasi default? (y/n): ").strip().lower()
        if confirm == 'y':
            self.create_default_config()
            print("✓ Konfigurasi telah direset ke default")
        else:
            print("✗ Reset dibatalkan")

    def show_current_exclusions(self):
        """Show current exclusion list"""
        print("\n" + "="*50)
        print("DAFTAR PENGECUALIAN SAAT INI")
        print("="*50)

        print("\n📄 FILE yang dikecualikan:")
        if self.excluded_files:
            for i, pattern in enumerate(self.excluded_files, 1):
                print(f"   {i:2d}. {pattern}")
        else:
            print("   Tidak ada file yang dikecualikan")

        print("\n📁 FOLDER yang dikecualikan:")
        if self.excluded_folders:
            for i, folder in enumerate(self.excluded_folders, 1):
                print(f"   {i:2d}. {folder}")
        else:
            print("   Tidak ada folder yang dikecualikan")

        input("\nTekan Enter untuk kembali...")


def main():
    """Main menu"""
    collector = CodeCollector()
    exclusion_manager = ExclusionManager()

    while True:
        print("\n" + "="*50)
        print("🌳 FILE MANAGER & CODE COLLECTOR")
        print("="*50)
        print("1. Proses - Kumpulkan kode dan simpan ke file TXT")
        print("2. Kelola File yang Dikecualikan")
        print("3. Lihat Konfigurasi Saat Ini")
        print("4. Keluar")

        choice = input("\nPilih menu (1-4): ").strip()

        if choice == '1':
            print("\nMemulai proses pengumpulan kode...")
            collector.save_report()

        elif choice == '2':
            exclusion_manager.manage_exclusions()

        elif choice == '3':
            print("\nKonfigurasi Saat Ini:")
            print(f"Directory: {exclusion_manager.current_dir}")
            print(f"File dikecualikan: {exclusion_manager.excluded_files}")
            print(f"Folder dikecualikan: {exclusion_manager.excluded_folders}")
            input("\nTekan Enter untuk kembali...")

        elif choice == '4':
            print("Terima kasih! Program selesai.")
            break

        else:
            print("✗ Pilihan tidak valid")


if __name__ == "__main__":
    main()

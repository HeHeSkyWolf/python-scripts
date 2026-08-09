"""
Image Metadata Renamer - Windows/WSL Enhanced
Handles Windows paths and file operations from WSL
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image
from PIL.ExifTags import TAGS


def is_wsl_path(path):
    """Check if path is a WSL mount path"""
    path_str = str(path)
    return path_str.startswith('/mnt/') or path_str.startswith('//wsl/')


def get_windows_path(wsl_path):
    """Convert WSL path to Windows path (for display purposes)"""
    wsl_path = str(wsl_path)
    if wsl_path.startswith('/mnt/'):
        # /mnt/c/Users -> C:\Users
        drive = wsl_path[5:6].upper()  # c -> C
        rest = wsl_path[6:]
        return f"{drive}:{rest.replace('/', '\\')}"
    return wsl_path


def safe_rename(src, dst):
    """Safe rename function that handles cross-device moves"""
    try:
        os.rename(src, dst)
        return True
    except OSError as e:
        print(f"  Rename failed: {e}")
        return False


def get_image_date(file_path, use_exif=True):
    """Extract date from image metadata"""
    # Implementation same as before...
    if use_exif:
        try:
            img = Image.open(file_path)
            exifdata = img.getexif()
            if exifdata:
                date_tags = {0x9003: 'DateTimeOriginal', 0x9004: 'DateTimeDigitized', 0x0132: 'DateTime'}
                for tag_id, tag_name in date_tags.items():
                    if tag_id in exifdata:
                        date_str = exifdata.get(tag_id)
                        if date_str:
                            for fmt in ['%Y:%m:%d %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                                try:
                                    return datetime.strptime(date_str, fmt)
                                except ValueError:
                                    continue
        except Exception:
            pass
    
    # Fallback to file modification date
    try:
        return datetime.fromtimestamp(os.path.getmtime(file_path))
    except Exception:
        return None


def process_directory(directory, recursive=False, use_exif=True, 
                     prefix="", suffix="", dry_run=False,
                     image_extensions=None):
    """Process images with Windows-specific improvements"""
    
    if image_extensions is None:
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', 
                           '.tiff', '.tif', '.webp', '.heic', '.heif'}
    
    directory = Path(directory)
    if not directory.exists():
        print(f"❌ Directory '{directory}' does not exist")
        return
    
    # Show Windows path for clarity
    if is_wsl_path(directory):
        win_path = get_windows_path(directory)
        print(f"📁 Processing: {directory}")
        print(f"   (Windows path: {win_path})")
    else:
        print(f"📁 Processing: {directory}")
    
    # Check if directory is readable
    if not os.access(directory, os.R_OK):
        print(f"❌ Cannot read directory: {directory}")
        print("   Try running with: sudo python script.py ...")
        return
    
    # Collect files
    image_files = []
    pattern = '*'
    if recursive:
        for ext in image_extensions:
            image_files.extend(directory.rglob(f'*{ext}'))
            image_files.extend(directory.rglob(f'*{ext.upper()}'))
    else:
        for ext in image_extensions:
            image_files.extend(directory.glob(f'*{ext}'))
            image_files.extend(directory.glob(f'*{ext.upper()}'))
    
    if not image_files:
        print(f"⚠️  No image files found in '{directory}'")
        return
    
    print(f"✅ Found {len(image_files)} image files")
    
    # Group by date
    date_groups = {}
    no_date_files = []
    
    print("\n📸 Reading metadata...")
    for file_path in image_files:
        date_obj = get_image_date(file_path, use_exif)
        if date_obj:
            date_key = date_obj.strftime("%Y%m%d_%H%M%S")
            date_groups.setdefault(date_key, []).append((file_path, date_obj))
        else:
            no_date_files.append(file_path)
            print(f"  ⚠️  No date: {file_path.name}")
    
    # Rename files
    renamed = skipped = errors = 0
    
    print("\n🔄 Renaming files...")
    for date_key, file_list in date_groups.items():
        file_list.sort(key=lambda x: x[0].name)
        
        for idx, (file_path, date_obj) in enumerate(file_list, 1):
            # Generate new name
            date_str = date_obj.strftime("%Y%m%d_%H%M%S")
            ext = file_path.suffix.lower()
            
            if len(file_list) > 1:
                new_name = f"{prefix}{date_str}_{idx:02d}{suffix}{ext}"
            else:
                new_name = f"{prefix}{date_str}{suffix}{ext}"
            
            # Sanitize for Windows
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                new_name = new_name.replace(char, '_')
            new_name = new_name.strip(' .')
            
            new_path = file_path.parent / new_name
            
            # Skip if unchanged
            if file_path.name == new_name:
                print(f"  ⏭️  Skip: {file_path.name} (already correct)")
                skipped += 1
                continue
            
            # Handle duplicates
            counter = 2
            while new_path.exists() and new_path != file_path:
                base = new_path.stem
                ext = new_path.suffix
                new_name = f"{base}_{counter}{ext}"
                new_path = file_path.parent / new_name
                counter += 1
            
            if dry_run:
                print(f"  🔄 Would rename: {file_path.name} -> {new_name}")
                renamed += 1
            else:
                try:
                    if safe_rename(file_path, new_path):
                        print(f"  ✅ Renamed: {file_path.name} -> {new_name}")
                        renamed += 1
                    else:
                        errors += 1
                except Exception as e:
                    print(f"  ❌ Error: {file_path.name} -> {e}")
                    errors += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"  Total files: {len(image_files)}")
    print(f"  ✅ Renamed: {renamed}")
    print(f"  ⏭️  Skipped: {skipped}")
    print(f"  ❌ Errors: {errors}")
    if no_date_files:
        print(f"  ⚠️  No EXIF date: {len(no_date_files)} (used file date instead)")
    if dry_run:
        print(f"\n💡 This was a DRY RUN. Remove --dry-run to actually rename files.")


def main():
    parser = argparse.ArgumentParser(
        description="Rename images by date (works with WSL↔Windows)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # Process Windows Pictures folder
  python rename_images.py /mnt/c/Users/John/Pictures
  
  # Recursive with prefix
  python rename_images.py /mnt/c/Photos -r -p "vacation_"
  
  # Preview changes (dry run)
  python rename_images.py /mnt/c/Users/John/Pictures --dry-run
  
  # Process only specific formats
  python rename_images.py /mnt/c/Photos -r --extensions .jpg,.png
        """
    )
    
    parser.add_argument('directory', help='Directory with images to rename')
    parser.add_argument('-r', '--recursive', action='store_true', 
                       help='Process subdirectories')
    parser.add_argument('--no-exif', action='store_true',
                       help='Use file modification date instead of EXIF')
    parser.add_argument('-p', '--prefix', default='', help='Filename prefix')
    parser.add_argument('-s', '--suffix', default='', help='Filename suffix')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview renaming without changes')
    parser.add_argument('--extensions', help='Comma-separated extensions (e.g., .jpg,.png)')
    
    args = parser.parse_args()
    
    # Parse extensions
    extensions = None
    if args.extensions:
        extensions = {ext.strip().lower() for ext in args.extensions.split(',')}
        if not all(e.startswith('.') for e in extensions):
            print("❌ Extensions must start with '.' (e.g., .jpg,.png)")
            sys.exit(1)
    
    # Process
    process_directory(
        directory=args.directory,
        recursive=args.recursive,
        use_exif=not args.no_exif,
        prefix=args.prefix,
        suffix=args.suffix,
        dry_run=args.dry_run,
        image_extensions=extensions
    )


if __name__ == "__main__":
    main()
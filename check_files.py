#!/usr/bin/env python3
"""
Script to check for required files and report their locations.
"""
import os
import sys
import importlib

def main():
    print("Checking for required files...")
    
    # Check for local page_script.js
    if os.path.exists("page_script.js"):
        print(f"✅ Found local page_script.js: {os.path.abspath('page_script.js')}")
    else:
        print("❌ Local page_script.js not found")
    
    # Try to find it in the package
    try:
        import autogen_ext
        package_dir = os.path.dirname(autogen_ext.__file__)
        package_script = os.path.join(package_dir, "agents", "web_surfer", "page_script.js")
        
        if os.path.exists(package_script):
            print(f"✅ Found package page_script.js: {package_script}")
        else:
            print(f"❌ Package page_script.js not found at expected location: {package_script}")
    except ImportError:
        print("❌ Could not import autogen_ext")
    
    # Check Python path
    print("\nPython path:")
    for path in sys.path:
        print(f"  - {path}")
    
    # Check current working directory
    print(f"\nCurrent working directory: {os.getcwd()}")
    
    # List files in current directory
    print("\nFiles in current directory:")
    for item in os.listdir("."):
        print(f"  - {item}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
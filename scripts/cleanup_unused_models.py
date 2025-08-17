#!/usr/bin/env python3
"""
Cleanup Unused Models Utility for Internal Assistant

This script removes completely unused model directories after duplicate cleanup.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Set

def get_active_models() -> Set[str]:
    """Get list of actively used models from configuration."""
    try:
        from internal_assistant.settings.settings import settings
        
        current_settings = settings()
        
        active_models = set()
        
        # Add LLM model
        if current_settings.llm.mode == "ollama":
            active_models.add("foundation-sec-q4km")
        elif current_settings.llm.mode == "llamacpp":
            model_file = current_settings.llamacpp.llm_hf_model_file
            if "foundation-sec" in model_file.lower():
                active_models.add("Foundation-Sec-8B")
        
        # Add embedding model
        if current_settings.embedding.mode == "huggingface":
            embed_model = current_settings.huggingface.embedding_hf_model_name
            if "nomic-embed-text" in embed_model:
                active_models.add("nomic-embed-text-v1.5")
            elif "bge-large" in embed_model:
                active_models.add("bge-large-en-v1.5")
            elif "all-MiniLM" in embed_model:
                active_models.add("all-MiniLM-L6-v2")
            elif "all-mpnet" in embed_model:
                active_models.add("all-mpnet-base-v2")
        
        return active_models
        
    except Exception as e:
        print(f"Error reading settings: {e}")
        return set()

def find_model_directories(models_dir: str = "models") -> List[Path]:
    """Find all model directories in the models folder."""
    models_path = Path(models_dir)
    
    if not models_path.exists():
        return []
    
    model_dirs = []
    
    # Look for HuggingFace cache directories
    cache_path = models_path / "cache"
    if cache_path.exists():
        for item in cache_path.iterdir():
            if item.is_dir() and item.name.startswith("models--"):
                model_dirs.append(item)
    
    # Look for direct model directories
    for item in models_path.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            if item.name not in ["cache", "embedding"]:
                model_dirs.append(item)
    
    return model_dirs

def analyze_unused_models(models_dir: str = "models") -> tuple[List[Path], List[Path]]:
    """Analyze which model directories are unused."""
    active_models = get_active_models()
    model_dirs = find_model_directories(models_dir)
    
    used_dirs = []
    unused_dirs = []
    
    print(f"🔍 Active models: {', '.join(active_models) if active_models else 'None'}")
    print("=" * 60)
    
    for model_dir in model_dirs:
        # Extract model name from directory
        dir_name = model_dir.name
        
        # Check if this directory contains an active model
        is_used = False
        for active_model in active_models:
            if active_model.lower() in dir_name.lower():
                is_used = True
                break
        
        # Check if directory has any files
        has_files = any(model_dir.rglob("*"))
        
        if is_used:
            used_dirs.append(model_dir)
            print(f"✅ {dir_name} - ACTIVE MODEL")
        elif has_files:
            unused_dirs.append(model_dir)
            print(f"❌ {dir_name} - UNUSED (has files)")
        else:
            print(f"⚠️  {dir_name} - EMPTY (already cleaned)")
    
    return used_dirs, unused_dirs

def cleanup_unused_models(models_dir: str = "models", dry_run: bool = True) -> None:
    """Remove unused model directories."""
    used_dirs, unused_dirs = analyze_unused_models(models_dir)
    
    if not unused_dirs:
        print("\n✅ No unused model directories found!")
        return
    
    if dry_run:
        print(f"\n🔍 DRY RUN - Would remove {len(unused_dirs)} unused directories:")
    else:
        print(f"\n🧹 REMOVING {len(unused_dirs)} unused directories:")
    
    print("=" * 60)
    
    total_size = 0
    removed_count = 0
    
    for model_dir in unused_dirs:
        # Calculate directory size
        dir_size = sum(f.stat().st_size for f in model_dir.rglob('*') if f.is_file())
        total_size += dir_size
        
        if dry_run:
            print(f"📁 Would remove: {model_dir.name} ({dir_size / (1024*1024):.2f} MB)")
        else:
            try:
                # Remove directory and all contents
                import shutil
                shutil.rmtree(model_dir)
                removed_count += 1
                print(f"✅ Removed: {model_dir.name} ({dir_size / (1024*1024):.2f} MB)")
            except Exception as e:
                print(f"❌ Failed to remove {model_dir.name}: {e}")
    
    if dry_run:
        print(f"\n📊 DRY RUN SUMMARY:")
        print(f"Directories that would be removed: {len(unused_dirs)}")
        print(f"Space that would be freed: {total_size / (1024*1024*1024):.2f} GB")
    else:
        print(f"\n✅ CLEANUP COMPLETE:")
        print(f"Directories removed: {removed_count}")
        print(f"Space freed: {total_size / (1024*1024*1024):.2f} GB")

def main():
    parser = argparse.ArgumentParser(description="Remove unused model directories")
    parser.add_argument('--models-dir', default='models', help='Models directory (default: models)')
    parser.add_argument('--cleanup', action='store_true', help='Actually remove unused directories')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without removing')
    
    args = parser.parse_args()
    
    # Analyze unused models
    used_dirs, unused_dirs = analyze_unused_models(args.models_dir)
    
    if not unused_dirs:
        print("\n✅ No unused model directories found!")
        return
    
    # Offer cleanup
    if args.cleanup or args.dry_run:
        cleanup_unused_models(args.models_dir, dry_run=args.dry_run)
    else:
        print(f"\n💡 To remove unused directories, run:")
        print(f"   python scripts/cleanup_unused_models.py --dry-run")
        print(f"   python scripts/cleanup_unused_models.py --cleanup")

if __name__ == "__main__":
    main()

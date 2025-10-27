#!/usr/bin/env python3
"""
Model Configuration Check Tool

Displays current LLM model configuration and validates model file existence.

Usage:
    poetry run python tools/system/check_model.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def check_current_model() -> bool:
    """Check current model configuration and return success status."""
    try:
        from internal_assistant.settings.settings import settings
        from internal_assistant.paths import models_path

        current_settings = settings()

        print("Current Model Configuration:")
        print("=" * 50)
        print(f"LLM Mode: {current_settings.llm.mode}")
        print(f"Prompt Style: {current_settings.llm.prompt_style}")
        print(f"Max Tokens: {current_settings.llm.max_new_tokens}")
        print(f"Context Window: {current_settings.llm.context_window}")
        print(f"Temperature: {current_settings.llm.temperature}")

        # Check model file based on mode
        if current_settings.llm.mode == "ollama":
            model_name = current_settings.ollama.llm_model
            print(f"\nOllama Model: {model_name}")
            print("(Managed by Ollama - use 'ollama list' to verify)")
            return True

        elif current_settings.llm.mode == "llamacpp":
            model_file = current_settings.llamacpp.llm_hf_model_file
            model_path = models_path / model_file
            print(f"\nModel File: {model_file}")

            if model_path.exists():
                size_gb = model_path.stat().st_size / (1024**3)
                print(f"Status: Found")
                print(f"Path: {model_path}")
                print(f"Size: {size_gb:.1f} GB")
                return True
            else:
                print(f"Status: Not Found")
                print(f"Expected Path: {model_path}")
                return False

        else:
            print(f"\nMode: {current_settings.llm.mode}")
            print("(External LLM service - no local model file)")
            return True

    except Exception as e:
        print(f"Error checking model: {e}")
        return False


def main():
    success = check_current_model()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

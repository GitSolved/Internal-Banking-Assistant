#!/usr/bin/env python3
"""
Simple script to check which model is currently being used.
"""

import sys
import os

# Add the project root to the path
sys.path.append(".")


def check_current_model():
    """Check which model is currently configured."""
    try:
        from internal_assistant.settings.settings import settings

        # Load settings using the proper function
        current_settings = settings()

        print("🔍 Current Model Configuration:")
        print("=" * 40)
        print(f"LLM Mode: {current_settings.llm.mode}")
        print(f"Model File: {current_settings.llamacpp.llm_hf_model_file}")
        print(f"Prompt Style: {current_settings.llm.prompt_style}")
        print(f"Max Tokens: {current_settings.llm.max_new_tokens}")
        print(f"Context Window: {current_settings.llm.context_window}")
        print(f"Temperature: {current_settings.llm.temperature}")

        # Check if model file exists
        from internal_assistant.paths import models_path

        model_path = models_path / current_settings.llamacpp.llm_hf_model_file

        if model_path.exists():
            size_gb = model_path.stat().st_size / (1024**3)
            print(f"✅ Model file found: {model_path}")
            print(f"   File size: {size_gb:.1f} GB")

            # Determine which model based on filename
            if "foundation-sec" in current_settings.llamacpp.llm_hf_model_file.lower():
                print("🎯 Model: Foundation-Sec-8B (Cybersecurity-focused)")
                print("   Specialization: Excellent for security analysis")
                print("   Parameters: 8B (optimized for security)")
                print("   Quantization: Q5 (high quality)")
            else:
                print(f"🎯 Model: {current_settings.llamacpp.llm_hf_model_file}")
                print(
                    "   Note: Consider upgrading to Foundation-Sec-8B for better security analysis"
                )
        else:
            print(f"❌ Model file not found: {model_path}")

        print("\n📊 Model Status:")
        print("=" * 40)
        if "foundation-sec" in current_settings.llamacpp.llm_hf_model_file.lower():
            print("✅ You're using Foundation-Sec-8B!")
            print("   - 8B parameters (optimized for security)")
            print("   - 5.6GB file size")
            print("   - Q5 quantization (high quality)")
            print("   - Cybersecurity specialized")
            print("   - Excellent for security analysis")
            print("   - Recommended for Internal Assistant")
        else:
            print(f"🎯 Model: {current_settings.llamacpp.llm_hf_model_file}")
            print("   - Consider upgrading to Foundation-Sec-8B")
            print("   - Better security analysis capabilities")
            print("   - Optimized for cybersecurity tasks")

    except Exception as e:
        print(f"❌ Error checking model: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    check_current_model()

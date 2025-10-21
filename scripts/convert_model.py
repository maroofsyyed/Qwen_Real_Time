#!/usr/bin/env python3
"""
Convert Qwen2.5-VL model to optimized format for vLLM
Optionally apply quantization for better performance
"""
import argparse
import os
import sys
from pathlib import Path

def check_dependencies():
    """Check if required libraries are installed"""
    try:
        import torch
        import transformers
        print(f"✓ PyTorch: {torch.__version__}")
        print(f"✓ Transformers: {transformers.__version__}")
        
        # Check for ROCm
        if torch.cuda.is_available():
            print(f"✓ GPU available: {torch.cuda.get_device_name(0)}")
            print(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            print("⚠ Warning: No GPU detected")
        
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        return False


def convert_to_safetensors(model_path: str, output_path: str):
    """Convert PyTorch checkpoint to safetensors format"""
    print("\n" + "="*60)
    print("Converting to SafeTensors format")
    print("="*60)
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        print(f"Loading model from: {model_path}")
        
        # Load model
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        
        # Save as safetensors
        os.makedirs(output_path, exist_ok=True)
        
        print(f"Saving to: {output_path}")
        model.save_pretrained(output_path, safe_serialization=True)
        tokenizer.save_pretrained(output_path)
        
        print("✓ Conversion complete!")
        print(f"  Output: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ Conversion failed: {e}")
        return False


def quantize_model(model_path: str, output_path: str, bits: int = 8):
    """
    Quantize model to reduce memory usage
    
    Args:
        model_path: Path to original model
        output_path: Path for quantized output
        bits: Quantization bits (4 or 8)
    """
    print("\n" + "="*60)
    print(f"Quantizing model to {bits}-bit")
    print("="*60)
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        # Try to import quantization library
        try:
            from auto_gptq import AutoGPTQForCausalLM, BaseQuantizeConfig
            use_gptq = True
        except ImportError:
            print("Note: auto-gptq not available, using bitsandbytes instead")
            use_gptq = False
        
        print(f"Loading model from: {model_path}")
        
        if use_gptq and bits == 4:
            # GPTQ quantization
            quantize_config = BaseQuantizeConfig(
                bits=bits,
                group_size=128,
                desc_act=False
            )
            
            model = AutoGPTQForCausalLM.from_pretrained(
                model_path,
                quantize_config=quantize_config,
                trust_remote_code=True
            )
            
            # Save quantized model
            model.save_quantized(output_path)
            
        else:
            # BitsAndBytes quantization (8-bit)
            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                load_in_8bit=(bits == 8),
                device_map="auto",
                trust_remote_code=True
            )
            
            # Save
            os.makedirs(output_path, exist_ok=True)
            model.save_pretrained(output_path)
        
        # Copy tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        tokenizer.save_pretrained(output_path)
        
        print("✓ Quantization complete!")
        print(f"  Output: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"✗ Quantization failed: {e}")
        print("\nNote: For full quantization support, install:")
        print("  pip install auto-gptq bitsandbytes")
        return False


def verify_model(model_path: str):
    """Verify model can be loaded"""
    print("\n" + "="*60)
    print("Verifying model")
    print("="*60)
    
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        
        print("Loading model...")
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            device_map="cpu",  # Load on CPU for verification
            low_cpu_mem_usage=True
        )
        
        print("✓ Model loaded successfully!")
        print(f"  Model type: {type(model).__name__}")
        print(f"  Vocab size: {len(tokenizer)}")
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters())
        print(f"  Parameters: {total_params / 1e9:.2f}B")
        
        return True
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Convert and optimize Qwen2.5-VL model for vLLM"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        required=True,
        help="Path to original model directory"
    )
    parser.add_argument(
        "--output-path",
        type=str,
        help="Path for converted model (default: {model_path}_converted)"
    )
    parser.add_argument(
        "--quantize",
        type=int,
        choices=[4, 8],
        help="Quantize to 4 or 8 bits"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify the model can be loaded"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install required dependencies:")
        print("  pip install torch transformers accelerate")
        sys.exit(1)
    
    # Set default output path
    if not args.output_path:
        if args.quantize:
            args.output_path = f"{args.model_path}_int{args.quantize}"
        else:
            args.output_path = f"{args.model_path}_converted"
    
    # Verify only
    if args.verify_only:
        success = verify_model(args.model_path)
        sys.exit(0 if success else 1)
    
    # Convert and/or quantize
    success = True
    
    if args.quantize:
        success = quantize_model(args.model_path, args.output_path, args.quantize)
    else:
        success = convert_to_safetensors(args.model_path, args.output_path)
    
    # Verify output
    if success:
        verify_model(args.output_path)
    
    print("\n" + "="*60)
    if success:
        print("✓ All operations completed successfully!")
        print(f"\nUpdate your .env file:")
        print(f"  MODEL_PATH={args.output_path}")
    else:
        print("✗ Some operations failed")
        sys.exit(1)


if __name__ == "__main__":
    main()


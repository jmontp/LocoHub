#!/usr/bin/env python3
"""
Generate Validation Images

Simple script to generate validation images with embedded configuration.
This creates all validation plots for documentation purposes.

Usage:
    python scripts/generate_validation_images.py
    python scripts/generate_validation_images.py --mode kinetic
    python scripts/generate_validation_images.py --tasks level_walking
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.validation.generate_validation_plots import ValidationPlotsGenerator
from lib.validation.image_generator_with_config import ValidationImageGenerator
from lib.validation.config_manager import ValidationConfigManager


def main():
    """Main function to generate validation images."""
    parser = argparse.ArgumentParser(
        description='Generate validation images with embedded configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_validation_images.py              # Generate all images
  python scripts/generate_validation_images.py --mode kinetic
  python scripts/generate_validation_images.py --tasks level_walking incline_walking
  python scripts/generate_validation_images.py --config-only  # Only config summaries
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['kinematic', 'kinetic', 'both'],
        default='both',
        help='Validation mode (default: both)'
    )
    
    parser.add_argument(
        '--tasks',
        nargs='*',
        help='Specific tasks to generate (default: all tasks)'
    )
    
    parser.add_argument(
        '--config-only',
        action='store_true',
        help='Generate only configuration summary images'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Custom output directory (default: docs/user_guide/docs/reference/datasets_documentation/validation_reports)'
    )
    
    args = parser.parse_args()
    
    # Determine modes to process
    if args.mode == 'both':
        modes = ['kinematic', 'kinetic']
    else:
        modes = [args.mode]
    
    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = project_root / "docs" / "user_guide" / "docs" / "reference" / "datasets_documentation" / "validation_reports"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎨 Generating validation images...")
    print(f"📁 Output directory: {output_dir}")
    
    try:
        # Initialize config manager
        config_mgr = ValidationConfigManager()
        
        # Generate config summary images if requested
        if args.config_only:
            print("\n📊 Generating configuration summary images...")
            img_generator = ValidationImageGenerator(config_mgr)
            
            for mode in modes:
                if config_mgr.config_exists(mode):
                    summary_path = img_generator.create_config_summary_image(mode, str(output_dir))
                    print(f"  ✅ Generated {mode} config summary: {Path(summary_path).name}")
            
            print("\n✅ Configuration summary generation complete!")
            return 0
        
        # Generate full validation plots
        total_generated = 0
        
        for mode in modes:
            print(f"\n📈 Processing {mode} validation...")
            
            if not config_mgr.config_exists(mode):
                print(f"  ⚠️  No {mode} config found, skipping...")
                continue
            
            # Initialize plot generator
            plot_generator = ValidationPlotsGenerator(mode=mode)
            
            # Generate plots
            if mode == 'kinematic':
                # Generate both forward kinematics and filters by phase
                results = plot_generator.generate_all_plots(args.tasks)
                total_generated += results['total_files']
            else:
                # For kinetic, only generate filters by phase
                files = plot_generator.generate_filters_by_phase_plots(args.tasks)
                total_generated += len(files)
            
            # Also generate config summary for this mode
            img_generator = ValidationImageGenerator(config_mgr)
            summary_path = img_generator.create_config_summary_image(mode, str(output_dir))
            print(f"  ✅ Generated {mode} config summary")
            total_generated += 1
        
        print(f"\n🎉 SUCCESS! Generated {total_generated} validation images")
        print(f"📁 All images saved to: {output_dir}")
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Orso Compressor CLI
# Command-line interface for compression without GUI
# For integration with Telegram bot

import argparse
import subprocess
import os
import sys
from pathlib import Path
import re

class OrsozoxCompressorCLI:
    """CLI wrapper for orso_compressor.py"""
    
    def __init__(self, input_file, output_dir):
        self.input_file = input_file
        self.output_dir = output_dir or os.path.dirname(input_file)
        self.video_path = input_file
        self.sub_path = None
        self.burn_subs = False
        self.quality = "Original (Same as Source)"
        self.codec = "H.264"
        self.crf = "25"
        self.preset = "medium"
        self.minrate = "1500k"
        self.maxrate = "3000k"
        self.bufsize = "4000k"
        self.scale = "scale=-2:1080"
        self.audio_bitrate = "192k"
        self.meta_title = "Powered By:- @inoshyi"
        self.meta_author = "@OrSoZoXch"
        self.enable_gpu = False
    
    def set_subtitle(self, subtitle_path):
        """Set subtitle file"""
        self.sub_path = subtitle_path
        self.burn_subs = True
    
    def set_quality(self, quality):
        """Set quality preset"""
        self.quality = quality
    
    def set_codec(self, codec):
        """Set codec (H.264 or H.265)"""
        self.codec = codec
    
    def set_scale(self, scale):
        """Set scale/resolution"""
        if scale.startswith('scale'):
            self.scale = scale
        else:
            self.scale = f"scale=-2:{scale}"
    
    def compress(self):
        """Execute compression"""
        if not os.path.exists(self.input_file):
            print(f"❌ Input file not found: {self.input_file}")
            return False
        
        # Get video info
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json',
                 '-show_streams', self.input_file],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                print("❌ FFprobe failed")
                return False
        except Exception as e:
            print(f"⚠️  FFprobe error: {e}")
        
        # Build FFmpeg command
        base_name = f"[Orsozox] {Path(self.input_file).stem} [{self.quality}]"
        output_file = os.path.join(self.output_dir, f"{base_name}.mp4")
        
        counter = 1
        while os.path.exists(output_file):
            output_file = os.path.join(self.output_dir, f"{base_name} ({counter}).mp4")
            counter += 1
        
        cmd = ['ffmpeg', '-y', '-i', self.input_file]
        
        # Codec
        if self.codec == "H.265":
            codec_name = 'libx265'
        else:
            codec_name = 'libx264'
        
        cmd.extend(['-c:v', codec_name, '-preset', self.preset, '-crf', self.crf,
                    '-minrate', self.minrate, '-maxrate', self.maxrate,
                    '-bufsize', self.bufsize])
        cmd.extend(['-pix_fmt', 'yuv420p', '-movflags', 'faststart'])
        
        # Filters
        filters = []
        if self.sub_path and self.burn_subs and os.path.exists(self.sub_path):
            sub_esc = self.sub_path.replace('\\\\', '/').replace(':', '\\\\:')
            filters.append(f"subtitles='{sub_esc}'")
        
        if self.scale:
            filters.append(self.scale)
        
        filters.append("drawtext=text='✠ Orsozox Movies ✠':x=w-tw-10:y=10:fontsize=20:fontcolor=white:shadowcolor=black:shadowx=5:shadowy=5")
        
        if filters:
            cmd.extend(['-vf', ','.join(filters)])
        
        # Audio
        cmd.extend(['-c:a', 'aac', '-b:a', self.audio_bitrate])
        
        # Metadata
        cmd.extend([
            '-metadata', f'title={self.meta_title}',
            '-metadata', f'author={self.meta_author}'
        ])
        
        cmd.append(output_file)
        
        print(f"🎬 Starting compression...")
        print(f"Input: {self.input_file}")
        print(f"Output: {output_file}")
        print(f"Codec: {self.codec} | Quality: {self.quality}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if result.returncode == 0:
                print(f"✅ Compression completed!")
                print(f"Output: {output_file}")
                return True
            else:
                print(f"❌ Compression failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print("❌ Compression timeout")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Orso Compressor CLI - Compress video with custom options'
    )
    parser.add_argument('--input', '-i', required=True, help='Input video file')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--subtitle', '-s', help='Subtitle file for burning')
    parser.add_argument('--burn-sub', action='store_true', help='Burn subtitle')
    parser.add_argument('--quality', '-q', default='Original (Same as Source)', 
                       help='Quality preset')
    parser.add_argument('--codec', '-c', default='H.264', help='Codec (H.264 or H.265)')
    parser.add_argument('--scale', help='Scale/resolution (e.g., 1080, 720, 480)')
    parser.add_argument('--compress', action='store_true', help='Enable compression')
    parser.add_argument('--gpu', action='store_true', help='Enable GPU encoding')
    
    args = parser.parse_args()
    
    compressor = OrsozoxCompressorCLI(args.input, args.output)
    
    if args.subtitle:
        compressor.set_subtitle(args.subtitle)
    
    if args.burn_sub:
        compressor.burn_subs = True
    
    if args.quality:
        compressor.set_quality(args.quality)
    
    if args.codec:
        compressor.set_codec(args.codec)
    
    if args.scale:
        compressor.set_scale(args.scale)
    
    if args.gpu:
        compressor.enable_gpu = True
    
    success = compressor.compress()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

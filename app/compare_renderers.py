#!/usr/bin/env python3
"""
On-device performance comparison script for Pi Zero W.
Logs timing metrics for both PIL and Pygame renderers.
"""

import os
import sys
import time
import logging
from pathlib import Path
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def run_renderer_test(renderer_name, script_name, duration=60):
    """Run a renderer for specified duration and collect timing logs."""
    import subprocess
    import signal
    
    logging.info(f"\n{'='*60}")
    logging.info(f"Testing {renderer_name} renderer for {duration} seconds...")
    logging.info(f"{'='*60}\n")
    
    # Start the clock process
    proc = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    render_times = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration:
            line = proc.stdout.readline()
            if line:
                print(line, end='')
                # Extract render timing
                if "Render timing:" in line and "total=" in line:
                    try:
                        # Parse: total=XXX.Xms
                        parts = line.split("total=")[1]
                        ms_val = float(parts.split("ms")[0])
                        render_times.append(ms_val)
                    except:
                        pass
            
            if proc.poll() is not None:
                break
    
    finally:
        # Clean shutdown
        proc.send_signal(signal.SIGTERM)
        time.sleep(1)
        if proc.poll() is None:
            proc.kill()
        proc.wait()
    
    return render_times

def main():
    """Run comparison test."""
    print("\n" + "="*60)
    print("Pi Zero W Clock Renderer Performance Comparison")
    print("="*60)
    
    # Load config
    config_path = Path("/app/config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    except:
        config = {}
    
    # Test duration
    test_duration = 60  # 1 minute each
    
    results = {}
    
    # Test PIL renderer (current)
    if os.path.exists("/app/framebuffer_clock.py"):
        pil_times = run_renderer_test("PIL Framebuffer", "/app/framebuffer_clock.py", test_duration)
        if pil_times:
            results['PIL'] = {
                'avg': sum(pil_times) / len(pil_times),
                'min': min(pil_times),
                'max': max(pil_times),
                'count': len(pil_times)
            }
    
    time.sleep(5)  # Brief pause between tests
    
    # Test Pygame renderer
    if os.path.exists("/app/pygame_clock.py"):
        pygame_times = run_renderer_test("Pygame Hardware", "/app/pygame_clock.py", test_duration)
        if pygame_times:
            results['Pygame'] = {
                'avg': sum(pygame_times) / len(pygame_times),
                'min': min(pygame_times),
                'max': max(pygame_times),
                'count': len(pygame_times)
            }
    
    # Print summary
    print("\n" + "="*60)
    print("PERFORMANCE COMPARISON SUMMARY")
    print("="*60)
    
    for renderer, stats in results.items():
        print(f"\n{renderer} Renderer:")
        print(f"  Average: {stats['avg']:.1f}ms")
        print(f"  Min:     {stats['min']:.1f}ms")
        print(f"  Max:     {stats['max']:.1f}ms")
        print(f"  Samples: {stats['count']}")
    
    if 'PIL' in results and 'Pygame' in results:
        speedup = results['PIL']['avg'] / results['Pygame']['avg']
        print(f"\nSpeedup: Pygame is {speedup:.1f}x faster than PIL")
        
        cpu_reduction = ((results['PIL']['avg'] - results['Pygame']['avg']) / results['PIL']['avg']) * 100
        print(f"CPU reduction: ~{cpu_reduction:.0f}% improvement")
        
        if results['Pygame']['avg'] < 50:
            print("\n✅ Pygame achieves <50ms - EXCELLENT for Pi Zero")
        elif results['Pygame']['avg'] < 100:
            print("\n✅ Pygame achieves <100ms - GOOD for Pi Zero")
        else:
            print("\n⚠️  Still slow, but better than PIL")
    
    print("\n" + "="*60)
    return 0

if __name__ == '__main__':
    sys.exit(main())

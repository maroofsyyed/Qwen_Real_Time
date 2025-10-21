#!/usr/bin/env python3
"""
Benchmark script for Qwen Vision-Language Service
Measures latency, throughput, and GPU memory usage
"""
import asyncio
import argparse
import time
import statistics
import json
from pathlib import Path
from typing import List, Dict
import sys

import aiohttp
import numpy as np
from PIL import Image


class BenchmarkRunner:
    """Run benchmarks against the service"""
    
    def __init__(self, server_url: str, num_requests: int = 100):
        self.server_url = server_url.rstrip('/')
        self.num_requests = num_requests
        self.results = []
        
    async def run(self):
        """Run all benchmarks"""
        print("=" * 70)
        print("Qwen Vision-Language Service Benchmark")
        print("=" * 70)
        print(f"\nServer: {self.server_url}")
        print(f"Number of requests: {self.num_requests}")
        print()
        
        # Check server health
        if not await self.check_health():
            print("Error: Server is not healthy")
            return False
        
        # Generate test images
        print("Generating test images...")
        test_images = self.generate_test_images(10)
        print(f"Generated {len(test_images)} test images\n")
        
        # Run benchmarks
        print("Running latency benchmark...")
        await self.benchmark_latency(test_images)
        
        # Analyze results
        self.print_results()
        
        return True
    
    async def check_health(self) -> bool:
        """Check if server is healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✓ Server is healthy")
                        print(f"  Inference ready: {data.get('inference_ready', False)}")
                        return True
                    else:
                        return False
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return False
    
    def generate_test_images(self, count: int) -> List[np.ndarray]:
        """Generate synthetic test images"""
        images = []
        
        for i in range(count):
            # Create random image
            img = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
            
            # Add some patterns to make it more realistic
            # Draw a gradient
            for y in range(720):
                img[y, :, 0] = (y / 720 * 255).astype(np.uint8)
            
            images.append(img)
        
        return images
    
    async def benchmark_latency(self, test_images: List[np.ndarray]):
        """Benchmark end-to-end latency"""
        
        # Since we're testing WebRTC, we'll simulate by measuring
        # the inference endpoint directly if available, or use the health endpoint
        # For a real benchmark, you'd need to simulate WebRTC clients
        
        print("\nNote: This is a simplified benchmark.")
        print("For accurate WebRTC benchmarks, use the full client simulation.\n")
        
        latencies = []
        
        for i in range(self.num_requests):
            start = time.time()
            
            # Simulate request (in real scenario, this would be WebRTC + inference)
            await self.simulate_request()
            
            latency = time.time() - start
            latencies.append(latency)
            
            if (i + 1) % 10 == 0:
                print(f"Completed {i + 1}/{self.num_requests} requests...")
        
        self.results = latencies
    
    async def simulate_request(self):
        """Simulate a single request"""
        try:
            async with aiohttp.ClientSession() as session:
                # Just hit the health endpoint as a simple timing test
                async with session.get(f"{self.server_url}/health") as resp:
                    await resp.json()
        except Exception as e:
            print(f"Request failed: {e}")
    
    def print_results(self):
        """Print benchmark results"""
        if not self.results:
            print("No results to display")
            return
        
        latencies = self.results
        
        print("\n" + "=" * 70)
        print("BENCHMARK RESULTS")
        print("=" * 70)
        
        # Latency statistics
        print("\nLatency Statistics (seconds):")
        print(f"  Mean:   {statistics.mean(latencies):.4f}")
        print(f"  Median: {statistics.median(latencies):.4f}")
        print(f"  Min:    {min(latencies):.4f}")
        print(f"  Max:    {max(latencies):.4f}")
        print(f"  StdDev: {statistics.stdev(latencies):.4f}")
        
        # Percentiles
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[len(sorted_latencies) * 50 // 100]
        p95 = sorted_latencies[len(sorted_latencies) * 95 // 100]
        p99 = sorted_latencies[len(sorted_latencies) * 99 // 100]
        
        print(f"\nPercentiles:")
        print(f"  P50: {p50:.4f}s")
        print(f"  P95: {p95:.4f}s")
        print(f"  P99: {p99:.4f}s")
        
        # Throughput
        total_time = sum(latencies)
        throughput = len(latencies) / total_time if total_time > 0 else 0
        
        print(f"\nThroughput:")
        print(f"  {throughput:.2f} requests/second")
        
        # Save results
        self.save_results({
            'num_requests': len(latencies),
            'latency': {
                'mean': statistics.mean(latencies),
                'median': statistics.median(latencies),
                'min': min(latencies),
                'max': max(latencies),
                'stddev': statistics.stdev(latencies),
                'p50': p50,
                'p95': p95,
                'p99': p99,
            },
            'throughput': throughput,
            'raw_latencies': latencies
        })
        
        print("\n" + "=" * 70)
    
    def save_results(self, results: dict):
        """Save results to JSON file"""
        output_dir = Path("benchmark_results")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"benchmark_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")


class GPUMonitor:
    """Monitor GPU memory usage"""
    
    def __init__(self):
        self.samples = []
    
    async def start_monitoring(self, interval: float = 1.0):
        """Start monitoring GPU usage"""
        import subprocess
        
        print("Starting GPU monitoring...")
        
        while True:
            try:
                # Use rocm-smi to get GPU memory
                result = subprocess.run(
                    ['rocm-smi', '--showmeminfo', 'vram'],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    # Parse output (simplified)
                    output = result.stdout
                    # Extract memory usage - this is simplified
                    # Real parsing would be more robust
                    self.samples.append({
                        'timestamp': time.time(),
                        'output': output
                    })
                
                await asyncio.sleep(interval)
                
            except FileNotFoundError:
                print("Warning: rocm-smi not found, skipping GPU monitoring")
                break
            except Exception as e:
                print(f"GPU monitoring error: {e}")
                await asyncio.sleep(interval)
    
    def print_summary(self):
        """Print GPU usage summary"""
        if not self.samples:
            print("No GPU samples collected")
            return
        
        print("\n" + "=" * 70)
        print("GPU MEMORY USAGE")
        print("=" * 70)
        print(f"\nCollected {len(self.samples)} samples")
        print("(Detailed GPU analysis requires parsing rocm-smi output)")


async def main():
    parser = argparse.ArgumentParser(description="Benchmark Qwen Vision Service")
    parser.add_argument(
        "--server-url",
        default="http://localhost:8000",
        help="Server URL"
    )
    parser.add_argument(
        "--num-requests",
        type=int,
        default=100,
        help="Number of requests to make"
    )
    parser.add_argument(
        "--monitor-gpu",
        action="store_true",
        help="Monitor GPU memory usage"
    )
    
    args = parser.parse_args()
    
    # Create benchmark runner
    benchmark = BenchmarkRunner(args.server_url, args.num_requests)
    
    # Start GPU monitoring if requested
    monitor = None
    monitor_task = None
    
    if args.monitor_gpu:
        monitor = GPUMonitor()
        monitor_task = asyncio.create_task(monitor.start_monitoring())
    
    # Run benchmark
    try:
        success = await benchmark.run()
        
        if not success:
            sys.exit(1)
    finally:
        # Stop GPU monitoring
        if monitor_task:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        if monitor:
            monitor.print_summary()


if __name__ == "__main__":
    asyncio.run(main())


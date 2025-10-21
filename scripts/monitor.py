#!/usr/bin/env python3
"""
Real-time monitoring tool for Qwen Vision-Language Service
Displays metrics, GPU usage, and session statistics
"""
import asyncio
import argparse
import subprocess
import time
from datetime import datetime
import aiohttp


class ServiceMonitor:
    """Monitor service health and performance"""
    
    def __init__(self, server_url: str, refresh_interval: float = 2.0):
        self.server_url = server_url.rstrip('/')
        self.refresh_interval = refresh_interval
        self.running = True
    
    async def run(self):
        """Run monitoring loop"""
        print("\033[2J\033[H")  # Clear screen
        print("=" * 80)
        print("Qwen Vision-Language Service Monitor")
        print("=" * 80)
        print("Press Ctrl+C to exit\n")
        
        try:
            while self.running:
                await self.update_display()
                await asyncio.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")
    
    async def update_display(self):
        """Update display with latest metrics"""
        # Move cursor to top
        print("\033[H")
        
        # Current time
        print(f"Last update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Server health
        health = await self.get_health()
        self.print_health(health)
        
        # GPU stats
        gpu_stats = await self.get_gpu_stats()
        self.print_gpu_stats(gpu_stats)
        
        # Service metrics
        metrics = await self.get_metrics()
        self.print_metrics(metrics)
    
    async def get_health(self) -> dict:
        """Get service health"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/health", timeout=5) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    else:
                        return {"status": "error", "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def get_gpu_stats(self) -> dict:
        """Get GPU statistics using rocm-smi"""
        try:
            result = subprocess.run(
                ['rocm-smi', '--showmeminfo', 'vram', '--showuse'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            if result.returncode == 0:
                # Parse output (simplified)
                return {
                    "available": True,
                    "output": result.stdout.split('\n')[:10]  # First 10 lines
                }
            else:
                return {"available": False, "error": "rocm-smi failed"}
        except FileNotFoundError:
            return {"available": False, "error": "rocm-smi not found"}
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    async def get_metrics(self) -> dict:
        """Get service metrics"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.server_url}/metrics", timeout=5) as resp:
                    if resp.status == 200:
                        # Parse Prometheus metrics (simple parsing)
                        text = await resp.text()
                        lines = text.split('\n')
                        metrics = {}
                        
                        for line in lines:
                            if line and not line.startswith('#'):
                                parts = line.split()
                                if len(parts) >= 2:
                                    metrics[parts[0]] = parts[1]
                        
                        return metrics
                    else:
                        return {}
        except Exception:
            return {}
    
    def print_health(self, health: dict):
        """Print health status"""
        print("─" * 80)
        print("SERVICE STATUS")
        print("─" * 80)
        
        if health.get("status") == "healthy":
            print("Status: ✓ HEALTHY")
            print(f"Inference Ready: {'✓' if health.get('inference_ready') else '✗'}")
            
            sessions = health.get('sessions', {})
            print(f"Total Sessions: {sessions.get('total_sessions', 0)}")
            print(f"Active Sessions: {sessions.get('active_sessions', 0)}")
            
            inference = health.get('inference', {})
            print(f"Total Requests: {inference.get('total_requests', 0)}")
            print(f"Successful: {inference.get('successful_requests', 0)}")
            print(f"Failed: {inference.get('failed_requests', 0)}")
            print(f"Dropped Frames: {inference.get('frames_dropped', 0)}")
            
            avg_time = inference.get('avg_inference_time', 0)
            if avg_time > 0:
                print(f"Avg Inference Time: {avg_time:.3f}s")
        else:
            print(f"Status: ✗ ERROR - {health.get('error', 'Unknown')}")
        
        print()
    
    def print_gpu_stats(self, stats: dict):
        """Print GPU statistics"""
        print("─" * 80)
        print("GPU STATUS")
        print("─" * 80)
        
        if stats.get("available"):
            output = stats.get("output", [])
            for line in output[:8]:  # Show first 8 lines
                print(line)
        else:
            print(f"GPU monitoring unavailable: {stats.get('error', 'Unknown')}")
        
        print()
    
    def print_metrics(self, metrics: dict):
        """Print service metrics"""
        if not metrics:
            return
        
        print("─" * 80)
        print("METRICS")
        print("─" * 80)
        
        for key, value in metrics.items():
            print(f"{key}: {value}")
        
        print()


async def main():
    parser = argparse.ArgumentParser(description="Monitor Qwen Vision Service")
    parser.add_argument(
        "--server-url",
        default="http://localhost:8000",
        help="Server URL"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Refresh interval in seconds"
    )
    
    args = parser.parse_args()
    
    monitor = ServiceMonitor(args.server_url, args.interval)
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())


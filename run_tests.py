#!/usr/bin/env python3
"""
Comprehensive test runner for LeKiwi base container
Tests container for StreamDeploy fleet deployment readiness
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict, Any

class TestRunner:
    """Main test runner for LeKiwi container validation"""
    
    def __init__(self, verbose: bool = False, quick: bool = False):
        self.verbose = verbose
        self.quick = quick
        self.project_root = Path(__file__).parent
        self.test_results: Dict[str, Any] = {}
        
    def run_command(self, cmd: List[str], description: str) -> bool:
        """Run a command and capture results"""
        if self.verbose:
            print(f"🔄 {description}")
            print(f"   Command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                cwd=self.project_root
            )
            
            success = result.returncode == 0
            
            if self.verbose or not success:
                if result.stdout:
                    print(f"   STDOUT: {result.stdout}")
                if result.stderr:
                    print(f"   STDERR: {result.stderr}")
            
            if success:
                print(f"✅ {description}")
            else:
                print(f"❌ {description}")
                
            return success
            
        except Exception as e:
            print(f"❌ {description} - Exception: {e}")
            return False
    
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are available"""
        print("🔍 Checking prerequisites...")
        
        prerequisites = [
            (["docker", "--version"], "Docker availability"),
            ([sys.executable, "--version"], "Python availability"),
            (["docker", "buildx", "version"], "Docker Buildx for multi-arch builds")
        ]
        
        all_good = True
        for cmd, desc in prerequisites:
            if not self.run_command(cmd, desc):
                all_good = False
        
        return all_good
    
    def install_test_dependencies(self) -> bool:
        """Install required Python test dependencies"""
        print("\n📦 Installing test dependencies...")
        
        dependencies = ["pytest", "pyzmq"]
        cmd = [sys.executable, "-m", "pip", "install"] + dependencies
        
        return self.run_command(cmd, "Installing test dependencies")
    
    def run_docker_build_tests(self) -> bool:
        """Run Docker container build tests"""
        print("\n🐳 Running Docker build tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/docker/test_build.py", 
            "-v" if self.verbose else "-q"
        ]
        
        success = self.run_command(cmd, "Docker build tests")
        self.test_results["docker_build"] = success
        return success
    
    def run_streamdeploy_integration_tests(self) -> bool:
        """Run StreamDeploy integration tests"""
        print("\n🚀 Running StreamDeploy integration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/integration/test_streamdeploy_integration.py", 
            "-v" if self.verbose else "-q"
        ]
        
        success = self.run_command(cmd, "StreamDeploy integration tests")
        self.test_results["streamdeploy_integration"] = success
        return success
    
    def run_production_config_tests(self) -> bool:
        """Run production configuration tests"""
        print("\n⚙️ Running production configuration tests...")
        
        cmd = [
            sys.executable, "-m", "pytest", 
            "tests/production/test_config_validation.py", 
            "-v" if self.verbose else "-q"
        ]
        
        success = self.run_command(cmd, "Production configuration tests")
        self.test_results["production_config"] = success
        return success
    
    def run_multi_arch_build_test(self) -> bool:
        """Test multi-architecture build for Raspberry Pi"""
        if self.quick:
            print("\n🏃 Skipping multi-arch build test (quick mode)")
            return True
            
        print("\n🏗️ Testing multi-architecture build...")
        
        # Test ARM64 build for Raspberry Pi
        cmd = [
            "docker", "buildx", "build",
            "--platform", "linux/arm64",
            "--tag", "lekiwi-base:test-arm64-final",
            "."
        ]
        
        success = self.run_command(cmd, "ARM64 build for Raspberry Pi")
        self.test_results["multi_arch_build"] = success
        return success
    
    def run_container_smoke_test(self) -> bool:
        """Run basic smoke test on built container"""
        print("\n💨 Running container smoke test...")
        
        # Build container
        build_cmd = ["docker", "build", "--tag", "lekiwi-base:smoke-test", "."]
        if not self.run_command(build_cmd, "Building container for smoke test"):
            return False
        
        # Run basic smoke test
        smoke_cmd = [
            "docker", "run", "--rm",
            "lekiwi-base:smoke-test",
            "python", "-c", 
            "import lerobot; from lerobot.robots.lekiwi.lekiwi_host import main; print('Smoke test passed')"
        ]
        
        success = self.run_command(smoke_cmd, "Container smoke test")
        self.test_results["smoke_test"] = success
        return success
    
    def cleanup_test_artifacts(self) -> bool:
        """Clean up test containers and images"""
        print("\n🧹 Cleaning up test artifacts...")
        
        # Get all test images
        list_cmd = ["docker", "images", "--filter", "reference=lekiwi-base:*test*", "-q"]
        try:
            result = subprocess.run(list_cmd, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                image_ids = result.stdout.strip().split('\n')
                
                # Remove test images
                cleanup_cmd = ["docker", "rmi", "-f"] + image_ids
                return self.run_command(cleanup_cmd, "Cleaning up test images")
        except Exception as e:
            print(f"⚠️ Cleanup warning: {e}")
        
        return True
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<30} {status}")
        
        print("-" * 60)
        print(f"Total: {total_tests} | Passed: {passed_tests} | Failed: {total_tests - passed_tests}")
        
        if passed_tests == total_tests:
            print("\n🎉 ALL TESTS PASSED! Container is ready for GHCR deployment.")
            print("🚀 Ready for StreamDeploy fleet management.")
            return True
        else:
            print(f"\n⚠️ {total_tests - passed_tests} test(s) failed. Please review and fix issues.")
            return False
    
    def run_all_tests(self) -> bool:
        """Run complete test suite"""
        print("🧪 Starting LeKiwi Base Container Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("❌ Prerequisites check failed. Please install required tools.")
            return False
        
        # Install dependencies
        if not self.install_test_dependencies():
            print("❌ Failed to install test dependencies.")
            return False
        
        # Run test suites
        test_suites = [
            self.run_docker_build_tests,
            self.run_streamdeploy_integration_tests,
            self.run_production_config_tests,
            self.run_container_smoke_test,
            self.run_multi_arch_build_test
        ]
        
        for test_suite in test_suites:
            try:
                test_suite()
            except KeyboardInterrupt:
                print("\n⚠️ Tests interrupted by user.")
                return False
            except Exception as e:
                print(f"❌ Test suite failed with exception: {e}")
                return False
        
        # Cleanup
        self.cleanup_test_artifacts()
        
        # Print summary
        end_time = time.time()
        duration = end_time - start_time
        print(f"\n⏱️ Total test duration: {duration:.2f} seconds")
        
        return self.print_summary()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Test LeKiwi base container for StreamDeploy fleet deployment"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true", 
        help="Enable verbose output"
    )
    parser.add_argument(
        "-q", "--quick", 
        action="store_true", 
        help="Skip time-consuming tests (multi-arch builds)"
    )
    parser.add_argument(
        "--test-suite", 
        choices=["docker", "integration", "production", "smoke", "all"],
        default="all",
        help="Run specific test suite"
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose, quick=args.quick)
    
    if args.test_suite == "all":
        success = runner.run_all_tests()
    elif args.test_suite == "docker":
        success = runner.run_docker_build_tests()
    elif args.test_suite == "integration":
        success = runner.run_streamdeploy_integration_tests()
    elif args.test_suite == "production":
        success = runner.run_production_config_tests()
    elif args.test_suite == "smoke":
        success = runner.run_container_smoke_test()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

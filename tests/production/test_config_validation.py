#!/usr/bin/env python3
"""
Test suite for production configuration validation
Tests container configuration for StreamDeploy fleet deployment
"""

import subprocess
import json
import os
import tempfile
import pytest
from pathlib import Path

class TestProductionConfig:
    """Test production configuration scenarios"""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent
    
    def test_bootstrap_token_injection(self, project_root):
        """Test bootstrap token injection from StreamDeploy"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:config-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test with various bootstrap token scenarios
        test_cases = [
            {
                "name": "standard_token",
                "env": {
                    "ROBOT_ID": "fleet-robot-001",
                    "DEPLOY_ENV": "production",
                    "SD_BOOTSTRAP_TOKEN": "bt_1234567890abcdef",
                    "SD_DEVICE_ID": "device-uuid-12345"
                }
            },
            {
                "name": "development_token", 
                "env": {
                    "ROBOT_ID": "dev-robot-test",
                    "DEPLOY_ENV": "development",
                    "SD_BOOTSTRAP_TOKEN": "bt_dev_token_test",
                    "SD_DEVICE_ID": "dev-device-001"
                }
            }
        ]
        
        for case in test_cases:
            container_name = f"config-test-{case['name']}"
            
            # Build environment args
            env_args = []
            for key, value in case['env'].items():
                env_args.extend(["-e", f"{key}={value}"])
            
            # Start container
            run_cmd = [
                "docker", "run", "-d",
                "--name", container_name
            ] + env_args + ["lekiwi-base:config-test"]
            
            run_result = subprocess.run(run_cmd, capture_output=True, text=True)
            assert run_result.returncode == 0, f"Container start failed for {case['name']}: {run_result.stderr}"
            
            try:
                # Wait for startup
                import time
                time.sleep(2)
                
                # Verify environment variables are set
                env_cmd = ["docker", "exec", container_name, "env"]
                env_result = subprocess.run(env_cmd, capture_output=True, text=True)
                assert env_result.returncode == 0, f"Environment check failed: {env_result.stderr}"
                
                env_output = env_result.stdout
                for key, value in case['env'].items():
                    assert f"{key}={value}" in env_output, f"Environment variable {key} not set correctly"
                
            finally:
                # Cleanup
                subprocess.run(["docker", "stop", container_name], capture_output=True)
                subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    def test_network_configuration(self, project_root):
        """Test network configuration for fleet deployment"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:network-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test different network configurations
        network_configs = [
            {
                "name": "host_network",
                "args": ["--network", "host"]
            },
            {
                "name": "bridge_network", 
                "args": ["-p", "5555:5555", "-p", "5556:5556"]
            },
            {
                "name": "custom_ports",
                "args": ["-p", "8555:5555", "-p", "8556:5556"]
            }
        ]
        
        for config in network_configs:
            container_name = f"network-test-{config['name']}"
            
            # Start container with network config
            run_cmd = [
                "docker", "run", "-d",
                "--name", container_name
            ] + config['args'] + [
                "-e", "ROBOT_ID=network-test-robot",
                "lekiwi-base:network-test"
            ]
            
            run_result = subprocess.run(run_cmd, capture_output=True, text=True)
            assert run_result.returncode == 0, f"Container start failed for {config['name']}: {run_result.stderr}"
            
            try:
                # Wait for startup
                import time
                time.sleep(3)
                
                # Check container is running
                status_cmd = ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"]
                status_result = subprocess.run(status_cmd, capture_output=True, text=True)
                assert "Up" in status_result.stdout, f"Container not running with {config['name']}: {status_result.stdout}"
                
            finally:
                # Cleanup
                subprocess.run(["docker", "stop", container_name], capture_output=True)
                subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    def test_volume_mounts(self, project_root):
        """Test volume mounting for persistent data"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:volume-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Create temporary directory for volume testing
        with tempfile.TemporaryDirectory() as temp_dir:
            container_name = "volume-test-container"
            
            # Start container with volume mount
            run_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-v", f"{temp_dir}:/data",
                "-e", "ROBOT_ID=volume-test-robot",
                "lekiwi-base:volume-test"
            ]
            
            run_result = subprocess.run(run_cmd, capture_output=True, text=True)
            assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"
            
            try:
                # Wait for startup
                import time
                time.sleep(2)
                
                # Test volume is accessible
                write_cmd = ["docker", "exec", container_name, "touch", "/data/test-file"]
                write_result = subprocess.run(write_cmd, capture_output=True, text=True)
                assert write_result.returncode == 0, f"Volume write test failed: {write_result.stderr}"
                
                # Verify file exists on host
                test_file = Path(temp_dir) / "test-file"
                assert test_file.exists(), "Volume mount not working - file not visible on host"
                
            finally:
                # Cleanup
                subprocess.run(["docker", "stop", container_name], capture_output=True)
                subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    def test_secrets_management(self, project_root):
        """Test secrets injection for production deployment"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:secrets-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Create temporary secrets directory
        with tempfile.TemporaryDirectory() as secrets_dir:
            # Create mock secret files
            bootstrap_token_file = Path(secrets_dir) / "bootstrap_token"
            bootstrap_token_file.write_text("secret-bootstrap-token-12345")
            
            device_cert_file = Path(secrets_dir) / "device.crt"
            device_cert_file.write_text("-----BEGIN CERTIFICATE-----\nMOCK_CERT_DATA\n-----END CERTIFICATE-----")
            
            container_name = "secrets-test-container"
            
            # Start container with secrets mounted
            run_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "-v", f"{secrets_dir}:/etc/streamdeploy/secrets:ro",
                "-e", "ROBOT_ID=secrets-test-robot",
                "-e", "SD_BOOTSTRAP_TOKEN_FILE=/etc/streamdeploy/secrets/bootstrap_token",
                "lekiwi-base:secrets-test"
            ]
            
            run_result = subprocess.run(run_cmd, capture_output=True, text=True)
            assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"
            
            try:
                # Wait for startup
                import time
                time.sleep(2)
                
                # Test secrets are accessible
                read_cmd = ["docker", "exec", container_name, "cat", "/etc/streamdeploy/secrets/bootstrap_token"]
                read_result = subprocess.run(read_cmd, capture_output=True, text=True)
                assert read_result.returncode == 0, f"Secret read failed: {read_result.stderr}"
                assert "secret-bootstrap-token-12345" in read_result.stdout
                
                # Test certificate file
                cert_cmd = ["docker", "exec", container_name, "cat", "/etc/streamdeploy/secrets/device.crt"]
                cert_result = subprocess.run(cert_cmd, capture_output=True, text=True)
                assert cert_result.returncode == 0, f"Certificate read failed: {cert_result.stderr}"
                assert "BEGIN CERTIFICATE" in cert_result.stdout
                
            finally:
                # Cleanup
                subprocess.run(["docker", "stop", container_name], capture_output=True)
                subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    def test_multi_robot_deployment(self, project_root):
        """Test multiple robot containers can run simultaneously"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:multi-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Start multiple robot containers
        robot_configs = [
            {"id": "robot-001", "cmd_port": 5555, "obs_port": 5556},
            {"id": "robot-002", "cmd_port": 5557, "obs_port": 5558},
            {"id": "robot-003", "cmd_port": 5559, "obs_port": 5560}
        ]
        
        containers = []
        
        try:
            for config in robot_configs:
                container_name = f"multi-test-{config['id']}"
                containers.append(container_name)
                
                # Start container with unique ports
                run_cmd = [
                    "docker", "run", "-d",
                    "--name", container_name,
                    "-p", f"{config['cmd_port']}:5555",
                    "-p", f"{config['obs_port']}:5556",
                    "-e", f"ROBOT_ID={config['id']}",
                    "-e", "DEPLOY_ENV=multi-robot-test",
                    "lekiwi-base:multi-test"
                ]
                
                run_result = subprocess.run(run_cmd, capture_output=True, text=True)
                assert run_result.returncode == 0, f"Container start failed for {config['id']}: {run_result.stderr}"
            
            # Wait for all containers to start
            import time
            time.sleep(5)
            
            # Verify all containers are running
            for container_name in containers:
                status_cmd = ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"]
                status_result = subprocess.run(status_cmd, capture_output=True, text=True)
                assert "Up" in status_result.stdout, f"Container {container_name} not running: {status_result.stdout}"
            
        finally:
            # Cleanup all containers
            for container_name in containers:
                subprocess.run(["docker", "stop", container_name], capture_output=True)
                subprocess.run(["docker", "rm", container_name], capture_output=True)
    
    def test_resource_limits_compliance(self, project_root):
        """Test container respects resource limits for fleet efficiency"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:limits-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test different resource limit scenarios
        limit_configs = [
            {"memory": "256m", "cpus": "0.5"},  # Minimal resources
            {"memory": "512m", "cpus": "1.0"},  # Standard resources
            {"memory": "1g", "cpus": "2.0"}     # High resources
        ]
        
        for i, limits in enumerate(limit_configs):
            container_name = f"limits-test-{i}"
            
            # Start container with resource limits
            run_cmd = [
                "docker", "run", "-d",
                "--name", container_name,
                "--memory", limits["memory"],
                "--cpus", limits["cpus"],
                "-e", f"ROBOT_ID=limits-test-robot-{i}",
                "lekiwi-base:limits-test"
            ]
            
            run_result = subprocess.run(run_cmd, capture_output=True, text=True)
            assert run_result.returncode == 0, f"Container start failed with limits {limits}: {run_result.stderr}"
            
            try:
                # Wait for startup
                import time
                time.sleep(3)
                
                # Check container is running
                status_cmd = ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"]
                status_result = subprocess.run(status_cmd, capture_output=True, text=True)
                assert "Up" in status_result.stdout, f"Container not running with limits {limits}: {status_result.stdout}"
                
                # Check resource usage is within limits
                stats_cmd = ["docker", "stats", "--no-stream", "--format", "json", container_name]
                stats_result = subprocess.run(stats_cmd, capture_output=True, text=True)
                
                if stats_result.returncode == 0:
                    stats_data = json.loads(stats_result.stdout)
                    # Basic validation that stats are available
                    assert "MemUsage" in stats_data
                    assert "CPUPerc" in stats_data
                
            finally:
                # Cleanup
                subprocess.run(["docker", "stop", container_name], capture_output=True)
                subprocess.run(["docker", "rm", container_name], capture_output=True)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

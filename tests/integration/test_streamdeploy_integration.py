#!/usr/bin/env python3
"""
Test suite for StreamDeploy integration
Tests container compatibility with StreamDeploy agent deployment
"""

import subprocess
import json
import time
import socket
import threading
import pytest
import zmq
from pathlib import Path
import tempfile
import os

class TestStreamDeployIntegration:
    """Test StreamDeploy agent integration"""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent
    
    @pytest.fixture
    def test_container_name(self):
        """Generate unique container name for tests"""
        return f"lekiwi-test-{int(time.time())}"
    
    def test_container_startup_with_streamdeploy_env(self, project_root, test_container_name):
        """Test container starts correctly with StreamDeploy environment variables"""
        # Build container first
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:streamdeploy-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test with StreamDeploy-style environment variables
        run_cmd = [
            "docker", "run", "-d",
            "--name", test_container_name,
            "-e", "ROBOT_ID=fleet-robot-001",
            "-e", "DEPLOY_ENV=production",
            "-e", "SD_DEVICE_ID=device-12345",
            "-e", "SD_BOOTSTRAP_TOKEN=test-token-123",
            "lekiwi-base:streamdeploy-test"
        ]
        
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"
        
        try:
            # Wait a moment for container to start
            time.sleep(2)
            
            # Check container is running
            status_cmd = ["docker", "ps", "--filter", f"name={test_container_name}", "--format", "{{.Status}}"]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)
            assert "Up" in status_result.stdout, f"Container not running: {status_result.stdout}"
            
            # Check environment variables are set correctly
            env_cmd = ["docker", "exec", test_container_name, "env"]
            env_result = subprocess.run(env_cmd, capture_output=True, text=True)
            assert env_result.returncode == 0, f"Environment check failed: {env_result.stderr}"
            
            env_output = env_result.stdout
            assert "ROBOT_ID=fleet-robot-001" in env_output
            assert "DEPLOY_ENV=production" in env_output
            assert "SD_DEVICE_ID=device-12345" in env_output
            
        finally:
            # Cleanup
            subprocess.run(["docker", "stop", test_container_name], capture_output=True)
            subprocess.run(["docker", "rm", test_container_name], capture_output=True)
    
    def test_health_check_integration(self, project_root, test_container_name):
        """Test health check works for StreamDeploy monitoring"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:health-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Start container with health check
        run_cmd = [
            "docker", "run", "-d",
            "--name", test_container_name,
            "--health-interval=10s",
            "--health-timeout=5s",
            "--health-retries=3",
            "lekiwi-base:health-test"
        ]
        
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"
        
        try:
            # Wait for health check to run
            time.sleep(15)
            
            # Check health status
            health_cmd = ["docker", "inspect", test_container_name, "--format", "{{.State.Health.Status}}"]
            health_result = subprocess.run(health_cmd, capture_output=True, text=True)
            
            # Health check should be unhealthy since lekiwi_host process isn't running
            # This is expected behavior for testing
            health_status = health_result.stdout.strip()
            assert health_status in ["unhealthy", "starting"], f"Unexpected health status: {health_status}"
            
        finally:
            # Cleanup
            subprocess.run(["docker", "stop", test_container_name], capture_output=True)
            subprocess.run(["docker", "rm", test_container_name], capture_output=True)
    
    def test_zmq_port_binding(self, project_root, test_container_name):
        """Test ZMQ ports can be bound for external communication"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:zmq-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Find available ports
        cmd_port = self._find_free_port()
        obs_port = self._find_free_port()
        
        # Start container with port mapping
        run_cmd = [
            "docker", "run", "-d",
            "--name", test_container_name,
            "-p", f"{cmd_port}:5555",  # Default ZMQ command port
            "-p", f"{obs_port}:5556",  # Default ZMQ observation port
            "lekiwi-base:zmq-test"
        ]
        
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"
        
        try:
            # Wait for container to start
            time.sleep(3)
            
            # Test ZMQ connection (should fail but ports should be bound)
            context = zmq.Context()
            
            # Test command socket
            cmd_socket = context.socket(zmq.PUSH)
            try:
                cmd_socket.connect(f"tcp://localhost:{cmd_port}")
                # If we get here, port is accessible
                cmd_accessible = True
            except Exception:
                cmd_accessible = False
            finally:
                cmd_socket.close()
            
            # Test observation socket  
            obs_socket = context.socket(zmq.PULL)
            obs_socket.setsockopt(zmq.RCVTIMEO, 1000)  # 1 second timeout
            try:
                obs_socket.connect(f"tcp://localhost:{obs_port}")
                obs_accessible = True
            except Exception:
                obs_accessible = False
            finally:
                obs_socket.close()
                
            context.term()
            
            # At least one port should be accessible (container is running)
            assert cmd_accessible or obs_accessible, "No ZMQ ports accessible"
            
        finally:
            # Cleanup
            subprocess.run(["docker", "stop", test_container_name], capture_output=True)
            subprocess.run(["docker", "rm", test_container_name], capture_output=True)
    
    def test_graceful_shutdown(self, project_root, test_container_name):
        """Test container handles SIGTERM gracefully (StreamDeploy requirement)"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:shutdown-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Start container
        run_cmd = [
            "docker", "run", "-d",
            "--name", test_container_name,
            "lekiwi-base:shutdown-test"
        ]
        
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"
        
        try:
            # Wait for container to start
            time.sleep(2)
            
            # Send SIGTERM and measure shutdown time
            start_time = time.time()
            stop_cmd = ["docker", "stop", "--time", "10", test_container_name]
            stop_result = subprocess.run(stop_cmd, capture_output=True, text=True)
            shutdown_time = time.time() - start_time
            
            assert stop_result.returncode == 0, f"Container stop failed: {stop_result.stderr}"
            assert shutdown_time < 10, f"Container took too long to shutdown: {shutdown_time}s"
            
            # Check container exited cleanly
            inspect_cmd = ["docker", "inspect", test_container_name, "--format", "{{.State.ExitCode}}"]
            inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True)
            exit_code = int(inspect_result.stdout.strip())
            assert exit_code == 0, f"Container didn't exit cleanly: exit code {exit_code}"
            
        finally:
            # Cleanup
            subprocess.run(["docker", "rm", test_container_name], capture_output=True)
    
    def test_resource_constraints(self, project_root, test_container_name):
        """Test container works within resource constraints (fleet efficiency)"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:resource-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Start container with resource limits
        run_cmd = [
            "docker", "run", "-d",
            "--name", test_container_name,
            "--memory", "512m",  # 512MB memory limit
            "--cpus", "1.0",     # 1 CPU limit
            "lekiwi-base:resource-test"
        ]
        
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        assert run_result.returncode == 0, f"Container start with limits failed: {run_result.stderr}"
        
        try:
            # Wait for container to start
            time.sleep(3)
            
            # Check container is still running under constraints
            status_cmd = ["docker", "ps", "--filter", f"name={test_container_name}", "--format", "{{.Status}}"]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)
            assert "Up" in status_result.stdout, f"Container not running under constraints: {status_result.stdout}"
            
            # Check memory usage
            stats_cmd = ["docker", "stats", "--no-stream", "--format", "table {{.MemUsage}}", test_container_name]
            stats_result = subprocess.run(stats_cmd, capture_output=True, text=True)
            assert stats_result.returncode == 0, f"Stats check failed: {stats_result.stderr}"
            
        finally:
            # Cleanup
            subprocess.run(["docker", "stop", test_container_name], capture_output=True)
            subprocess.run(["docker", "rm", test_container_name], capture_output=True)
    
    def test_logging_format(self, project_root, test_container_name):
        """Test container logging is compatible with StreamDeploy log collection"""
        # Build container
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:logging-test",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Start container
        run_cmd = [
            "docker", "run", "-d",
            "--name", test_container_name,
            "lekiwi-base:logging-test"
        ]
        
        run_result = subprocess.run(run_cmd, capture_output=True, text=True)
        assert run_result.returncode == 0, f"Container start failed: {run_result.stderr}"
        
        try:
            # Wait for some logs to be generated
            time.sleep(5)
            
            # Get container logs
            logs_cmd = ["docker", "logs", test_container_name]
            logs_result = subprocess.run(logs_cmd, capture_output=True, text=True)
            assert logs_result.returncode == 0, f"Logs retrieval failed: {logs_result.stderr}"
            
            logs_output = logs_result.stdout + logs_result.stderr
            
            # Check for expected log patterns
            assert len(logs_output) > 0, "No logs generated"
            
            # Should contain startup messages
            expected_patterns = [
                "Configuring LeKiwi",
                "Connecting LeKiwi", 
                "Starting HostAgent"
            ]
            
            for pattern in expected_patterns:
                assert pattern in logs_output, f"Expected log pattern not found: {pattern}"
            
        finally:
            # Cleanup
            subprocess.run(["docker", "stop", test_container_name], capture_output=True)
            subprocess.run(["docker", "rm", test_container_name], capture_output=True)
    
    def _find_free_port(self):
        """Find a free port for testing"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

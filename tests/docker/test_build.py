#!/usr/bin/env python3
"""
Test suite for Docker container build validation
Focuses on multi-architecture builds for StreamDeploy fleet deployment
"""

import subprocess
import json
import os
import tempfile
import pytest
from pathlib import Path

class TestDockerBuild:
    """Test Docker container build process"""
    
    @pytest.fixture
    def project_root(self):
        """Get project root directory"""
        return Path(__file__).parent.parent.parent
    
    def test_dockerfile_exists(self, project_root):
        """Verify Dockerfile exists and is readable"""
        dockerfile = project_root / "Dockerfile"
        assert dockerfile.exists(), "Dockerfile not found"
        assert dockerfile.is_file(), "Dockerfile is not a file"
        
        # Verify it's readable
        with open(dockerfile, 'r') as f:
            content = f.read()
            assert len(content) > 0, "Dockerfile is empty"
            assert "FROM python:" in content, "Dockerfile doesn't use Python base image"
    
    def test_build_amd64(self, project_root):
        """Test AMD64 container build"""
        cmd = [
            "docker", "build",
            "--platform", "linux/amd64",
            "--tag", "lekiwi-base:test-amd64",
            str(project_root)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 0, f"AMD64 build failed: {result.stderr}"
        assert "Successfully tagged lekiwi-base:test-amd64" in result.stdout
    
    def test_build_arm64(self, project_root):
        """Test ARM64 container build for Raspberry Pi"""
        # Check if buildx is available for multi-arch builds
        buildx_check = subprocess.run(
            ["docker", "buildx", "version"], 
            capture_output=True, text=True
        )
        
        if buildx_check.returncode != 0:
            pytest.skip("Docker buildx not available for multi-arch builds")
        
        cmd = [
            "docker", "buildx", "build",
            "--platform", "linux/arm64",
            "--tag", "lekiwi-base:test-arm64",
            "--load",  # Load into local docker daemon
            str(project_root)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
        
        assert result.returncode == 0, f"ARM64 build failed: {result.stderr}"
    
    def test_container_structure(self, project_root):
        """Test container internal structure and dependencies"""
        # Build container first
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:test-structure",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test Python dependencies are installed
        python_test_cmd = [
            "docker", "run", "--rm",
            "lekiwi-base:test-structure",
            "python", "-c", "import lerobot; import zmq; import cv2; print('Dependencies OK')"
        ]
        
        python_result = subprocess.run(python_test_cmd, capture_output=True, text=True)
        assert python_result.returncode == 0, f"Python dependencies test failed: {python_result.stderr}"
        assert "Dependencies OK" in python_result.stdout
        
        # Test lekiwi_host module is available
        lekiwi_test_cmd = [
            "docker", "run", "--rm",
            "lekiwi-base:test-structure",
            "python", "-c", "from lerobot.robots.lekiwi.lekiwi_host import main; print('LeKiwi host module OK')"
        ]
        
        lekiwi_result = subprocess.run(lekiwi_test_cmd, capture_output=True, text=True)
        assert lekiwi_result.returncode == 0, f"LeKiwi host module test failed: {lekiwi_result.stderr}"
        assert "LeKiwi host module OK" in lekiwi_result.stdout
    
    def test_container_user_security(self, project_root):
        """Test container runs as non-root user (StreamDeploy security requirement)"""
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:test-security",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test user is not root
        user_test_cmd = [
            "docker", "run", "--rm",
            "lekiwi-base:test-security",
            "whoami"
        ]
        
        user_result = subprocess.run(user_test_cmd, capture_output=True, text=True)
        assert user_result.returncode == 0, f"User test failed: {user_result.stderr}"
        assert user_result.stdout.strip() == "robot", f"Container should run as 'robot' user, got: {user_result.stdout.strip()}"
        
        # Test user has correct UID/GID
        id_test_cmd = [
            "docker", "run", "--rm",
            "lekiwi-base:test-security",
            "id"
        ]
        
        id_result = subprocess.run(id_test_cmd, capture_output=True, text=True)
        assert id_result.returncode == 0, f"ID test failed: {id_result.stderr}"
        assert "uid=1000(robot)" in id_result.stdout
        assert "gid=1000(robot)" in id_result.stdout
    
    def test_environment_variables(self, project_root):
        """Test default environment variables are set correctly"""
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:test-env",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test environment variables
        env_test_cmd = [
            "docker", "run", "--rm",
            "lekiwi-base:test-env",
            "env"
        ]
        
        env_result = subprocess.run(env_test_cmd, capture_output=True, text=True)
        assert env_result.returncode == 0, f"Environment test failed: {env_result.stderr}"
        
        env_output = env_result.stdout
        assert "ROBOT_ID=my-kiwi" in env_output
        assert "DEPLOY_ENV=production" in env_output
    
    def test_health_check_command(self, project_root):
        """Test health check command works"""
        build_cmd = [
            "docker", "build",
            "--tag", "lekiwi-base:test-health",
            str(project_root)
        ]
        
        build_result = subprocess.run(build_cmd, capture_output=True, text=True, cwd=project_root)
        assert build_result.returncode == 0, f"Build failed: {build_result.stderr}"
        
        # Test health check command directly
        health_test_cmd = [
            "docker", "run", "--rm",
            "lekiwi-base:test-health",
            "pgrep", "-f", "lerobot.robots.lekiwi.lekiwi_host"
        ]
        
        # This should fail since lekiwi_host is not running, but command should exist
        health_result = subprocess.run(health_test_cmd, capture_output=True, text=True)
        # pgrep returns 1 when no processes found, which is expected
        assert health_result.returncode == 1, "Health check command should return 1 when process not found"
    
    def cleanup_test_images(self):
        """Clean up test images"""
        test_tags = [
            "lekiwi-base:test-amd64",
            "lekiwi-base:test-arm64", 
            "lekiwi-base:test-structure",
            "lekiwi-base:test-security",
            "lekiwi-base:test-env",
            "lekiwi-base:test-health"
        ]
        
        for tag in test_tags:
            subprocess.run(["docker", "rmi", "-f", tag], capture_output=True)

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# LeKiwi Base Container Testing Guide

This document provides comprehensive testing instructions for the LeKiwi base container, specifically designed for StreamDeploy fleet deployment to GitHub Container Registry (GHCR).

## Overview

The testing framework validates:
- **Multi-architecture builds** (AMD64, ARM64 for Raspberry Pi)
- **StreamDeploy integration** (environment variables, health checks, networking)
- **Production configuration** (secrets, resource limits, multi-robot deployment)
- **GHCR publishing workflow** (automated CI/CD pipeline)

## Quick Start

### Prerequisites

Ensure you have the following installed:
- Docker (with buildx for multi-arch support)
- Python 3.10+
- Git

### Run All Tests

```bash
# Run complete test suite
python run_tests.py

# Run with verbose output
python run_tests.py --verbose

# Quick mode (skip time-consuming multi-arch builds)
python run_tests.py --quick
```

### Run Specific Test Suites

```bash
# Docker build tests only
python run_tests.py --test-suite docker

# StreamDeploy integration tests
python run_tests.py --test-suite integration

# Production configuration tests
python run_tests.py --test-suite production

# Basic smoke test
python run_tests.py --test-suite smoke
```

## Test Suites

### 1. Docker Build Tests (`tests/docker/test_build.py`)

Validates container build process and structure:

- **Dockerfile validation** - Ensures Dockerfile exists and is properly formatted
- **AMD64 build** - Tests standard x86_64 architecture build
- **ARM64 build** - Tests Raspberry Pi compatible build
- **Container structure** - Verifies Python dependencies and LeRobot installation
- **Security compliance** - Ensures non-root user execution
- **Environment variables** - Validates default configuration
- **Health check** - Tests health check command functionality

**Run manually:**
```bash
python -m pytest tests/docker/test_build.py -v
```

### 2. StreamDeploy Integration Tests (`tests/integration/test_streamdeploy_integration.py`)

Tests compatibility with StreamDeploy agent deployment:

- **Environment injection** - Tests bootstrap token and device ID injection
- **Health monitoring** - Validates health checks for fleet management
- **Network configuration** - Tests ZMQ port binding and accessibility
- **Graceful shutdown** - Ensures proper SIGTERM handling
- **Resource constraints** - Tests operation under memory/CPU limits
- **Logging format** - Validates log output for StreamDeploy collection

**Run manually:**
```bash
python -m pytest tests/integration/test_streamdeploy_integration.py -v
```

### 3. Production Configuration Tests (`tests/production/test_config_validation.py`)

Validates production deployment scenarios:

- **Bootstrap token injection** - Tests various token formats and environments
- **Network configurations** - Tests host, bridge, and custom port configurations
- **Volume mounting** - Validates persistent data storage
- **Secrets management** - Tests secure credential injection
- **Multi-robot deployment** - Ensures multiple containers can run simultaneously
- **Resource limits compliance** - Tests various resource constraint scenarios

**Run manually:**
```bash
python -m pytest tests/production/test_config_validation.py -v
```

## GitHub Actions Workflow

The automated CI/CD pipeline (`.github/workflows/build-and-publish.yml`) provides:

### Automated Testing
- Runs all test suites on every push/PR
- Multi-architecture build validation
- Security vulnerability scanning

### GHCR Publishing
- Automatic image publishing to GitHub Container Registry
- Multi-architecture support (AMD64, ARM64)
- Raspberry Pi specific tagging
- Semantic versioning support

### Deployment Validation
- Post-build deployment testing
- Container smoke tests
- ARM64 emulation testing

## Manual Testing Procedures

### Test Container Build

```bash
# Build for AMD64
docker build --platform linux/amd64 -t lekiwi-base:amd64 .

# Build for ARM64 (Raspberry Pi)
docker buildx build --platform linux/arm64 -t lekiwi-base:arm64 .
```

### Test StreamDeploy Integration

```bash
# Start container with StreamDeploy environment
docker run -d --name test-lekiwi \
  -e ROBOT_ID=test-robot-001 \
  -e DEPLOY_ENV=testing \
  -e SD_DEVICE_ID=device-12345 \
  -e SD_BOOTSTRAP_TOKEN=test-token \
  -p 5555:5555 -p 5556:5556 \
  lekiwi-base:latest

# Check logs
docker logs test-lekiwi

# Test health check
docker exec test-lekiwi pgrep -f lekiwi_host

# Cleanup
docker stop test-lekiwi && docker rm test-lekiwi
```

### Test Multi-Robot Deployment

```bash
# Start multiple robot containers
for i in {1..3}; do
  docker run -d --name robot-$i \
    -e ROBOT_ID=fleet-robot-00$i \
    -p $((5554 + i*2)):5555 \
    -p $((5555 + i*2)):5556 \
    lekiwi-base:latest
done

# Verify all running
docker ps --filter name=robot-

# Cleanup
docker stop robot-{1..3} && docker rm robot-{1..3}
```

## Troubleshooting

### Common Issues

**Docker buildx not available:**
```bash
# Install buildx
docker buildx install
docker buildx create --use
```

**Permission denied errors:**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Logout and login again
```

**Test failures due to port conflicts:**
```bash
# Check for conflicting processes
sudo netstat -tulpn | grep :555
# Kill conflicting processes or use different ports
```

**ARM64 build failures:**
```bash
# Enable QEMU emulation
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

### Debug Container Issues

```bash
# Run container interactively
docker run -it --entrypoint /bin/bash lekiwi-base:latest

# Check container logs
docker logs <container-name>

# Inspect container configuration
docker inspect <container-name>

# Check resource usage
docker stats <container-name>
```

## Performance Benchmarks

Expected performance characteristics:

- **Build time**: ~5-10 minutes (AMD64), ~10-20 minutes (ARM64)
- **Image size**: ~2-3 GB (includes Python, OpenCV, robotics libraries)
- **Memory usage**: ~200-500 MB at runtime
- **Startup time**: ~5-10 seconds
- **Health check interval**: 30 seconds

## Security Considerations

The container implements several security best practices:

- **Non-root execution** - Runs as `robot` user (UID 1000)
- **Minimal attack surface** - Only necessary packages installed
- **Secrets management** - Supports external secret injection
- **Network isolation** - Configurable network policies
- **Resource limits** - Supports CPU/memory constraints

## Fleet Deployment Checklist

Before deploying to production fleet:

- [ ] All tests pass (`python run_tests.py`)
- [ ] Multi-architecture builds successful
- [ ] Security scan clean (no critical vulnerabilities)
- [ ] Resource usage within acceptable limits
- [ ] Health checks responding correctly
- [ ] Logging format compatible with monitoring
- [ ] Network configuration tested
- [ ] Secrets injection working
- [ ] Graceful shutdown verified

## Support

For issues or questions:

1. Check this documentation
2. Review test output for specific error messages
3. Check GitHub Actions logs for CI/CD issues
4. Verify Docker and system prerequisites
5. Test with minimal configuration first

## Contributing

When adding new tests:

1. Follow existing test patterns
2. Add tests to appropriate suite (docker/integration/production)
3. Update this documentation
4. Ensure tests are idempotent and clean up after themselves
5. Test both success and failure scenarios

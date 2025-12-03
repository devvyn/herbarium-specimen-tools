#!/usr/bin/env bash
#
# Quick Start Script for Herbarium Specimen Tools (macOS/Linux)
#
# This script automates the complete setup process:
# - Installs uv if needed
# - Creates virtual environment
# - Installs dependencies
# - Generates sample images
# - Configures environment
# - Provides next steps
#

set -e  # Exit on error

echo "🚀 Herbarium Specimen Tools - Quick Start"
echo "=========================================="
echo ""

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "📦 uv not found. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for this session
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

    # Verify installation
    if ! command -v uv &> /dev/null; then
        echo "❌ uv installation failed"
        echo "   Please install manually: https://github.com/astral-sh/uv"
        exit 1
    fi

    echo "   ✅ uv installed successfully"
else
    echo "✅ uv is already installed"
fi

echo ""

# Create virtual environment
echo "📦 Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "   ⚠️  .venv already exists, skipping creation"
else
    uv venv
    echo "   ✅ Virtual environment created"
fi

echo ""

# Activate virtual environment
echo "📦 Activating virtual environment..."
if [[ "$OSTYPE" == "darwin"* ]] || [[ "$OSTYPE" == "linux-gnu"* ]]; then
    source .venv/bin/activate
    echo "   ✅ Virtual environment activated"
else
    echo "   ⚠️  Activate manually: source .venv/bin/activate"
fi

echo ""

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -e ".[dev]"
echo "   ✅ Dependencies installed"

echo ""

# Generate sample images
echo "🖼️  Generating sample specimen images..."
python scripts/generate_sample_images.py

echo ""

# Setup .env
echo "⚙️  Setting up environment configuration..."
echo "   (You can press Enter to accept defaults)"
echo ""
python scripts/setup_env.py

echo ""
echo "============================================"
echo "✅ Quick Start Complete!"
echo "============================================"
echo ""
echo "Your herbarium specimen tools are ready to use."
echo ""
echo "To start the server:"
echo "  python mobile/run_mobile_server.py --dev"
echo ""
echo "Then open your browser to:"
echo "  http://localhost:8000"
echo ""
echo "Development credentials:"
echo "  Username: testuser"
echo "  Password: testpass123"
echo ""

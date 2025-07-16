#!/bin/bash

echo "🖨️ Network Printer Model Detector"
echo "================================"
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt
echo ""
echo "Starting server..."
python3 printer_model_api.py 
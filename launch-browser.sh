#!/bin/bash

# launch-browser.sh - Start Brave or Chrome with CDP for substack2md
# Detects your browser, isolates a dedicated profile, and opens the
# remote debugging port on loopback so substack2md can drive the
# authenticated session.  macOS only.

set -e

PORT=9222
PROFILE_DIR=""

# Detect browser
if [ -d "/Applications/Brave Browser.app" ]; then
    BROWSER="Brave Browser"
    PROFILE_DIR="$HOME/.brave-cdp-profile"
    COMMAND="open -na \"Brave Browser\" --args"
elif [ -d "/Applications/Google Chrome.app" ]; then
    # Detect architecture
    if [ "$(uname -m)" = "arm64" ]; then
        BROWSER="Chrome (Apple Silicon)"
        COMMAND='arch -arm64 "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"'
    else
        BROWSER="Chrome (Intel)"
        COMMAND='"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"'
    fi
    PROFILE_DIR="$HOME/.chrome-cdp-profile"
else
    echo "ERROR: Could not find Brave or Chrome"
    echo "Please install one of these browsers first."
    exit 1
fi

echo "=== substack2md Browser Launcher ==="
echo "Browser: $BROWSER"
echo "Port: $PORT"
echo "Profile: $PROFILE_DIR"
echo ""

# Check if port is already in use
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "WARNING: Port $PORT is already in use"
    echo "If you have a browser already running with CDP, you can skip this step."
    echo ""
    read -p "Kill existing process and continue? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        kill $(lsof -t -i:$PORT) 2>/dev/null || true
        sleep 2
    else
        echo "Exiting. Use the existing browser or close it first."
        exit 0
    fi
fi

# Launch browser
echo "Launching browser..."
echo ""

if [ "$BROWSER" = "Brave Browser" ]; then
    open -na "Brave Browser" --args \
        --remote-debugging-port=$PORT \
        --remote-allow-origins=http://127.0.0.1:$PORT \
        --user-data-dir="$PROFILE_DIR"
else
    eval $COMMAND \
        --remote-debugging-port=$PORT \
        --remote-allow-origins=http://127.0.0.1:$PORT \
        --user-data-dir="$PROFILE_DIR" &
fi

# Wait for browser to start
echo "Waiting for browser to start..."
sleep 3

# Check if CDP is accessible
if curl -s http://127.0.0.1:$PORT/json > /dev/null; then
    echo "✓ Browser started successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Log into Substack in the browser window that just opened"
    echo "2. Run: substack2md <substack-post-url>"
    echo "   (or: python -m substack2md <substack-post-url>)"
    echo ""
    echo "Test CDP: curl http://127.0.0.1:$PORT/json"
else
    echo "✗ Browser started but CDP not accessible"
    echo "Please try closing all browser windows and running this script again"
    exit 1
fi

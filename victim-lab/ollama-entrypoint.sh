#!/bin/bash
# Start Ollama server in background
ollama serve &
OLLAMA_PID=$!

# Wait until Ollama API is ready
echo "[ollama-init] Waiting for Ollama to be ready..."
until ollama list > /dev/null 2>&1; do
    sleep 2
done
echo "[ollama-init] Ollama is up."

# Pull model only if not already present
MODEL="${OLLAMA_MODEL:-llama3}"
if ollama list | grep -q "^${MODEL}"; then
    echo "[ollama-init] Model '${MODEL}' already present, skipping pull."
else
    echo "[ollama-init] Pulling model '${MODEL}'..."
    ollama pull "${MODEL}"
    echo "[ollama-init] Model '${MODEL}' ready."
fi

# Hand off to Ollama server (foreground)
wait $OLLAMA_PID

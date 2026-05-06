import subprocess
result = subprocess.run(
    [
        '/home/jperez/llama.cpp/build/bin/llama-cli',
        '-m', '/home/jperez/models/qwen14b/qwen2.5-14b-instruct-q6_k-00001-of-00004.gguf',
        '-p', "Say just the word 'Hello'.",
        '-n', "10",
        '--log-disable',
        '--no-display-prompt'
    ],
    capture_output=True,
    text=True
)
print("STDOUT:")
print(repr(result.stdout))
print("STDERR:")
print(repr(result.stderr))

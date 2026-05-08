# Astra HUD

The Astra HUD is the desktop interface for Project Astra. It is implemented with
Tauri, React, and Vite, and is designed to act as a lightweight overlay for
sending user input to the Astra core runtime and displaying assistant responses.

## Responsibilities

- Capture user input from the desktop overlay.
- Send IPC requests to the Astra core runtime.
- Display assistant output, tool status, and runtime feedback.
- Keep the interface compact, keyboard-first, and suitable for repeated use.

## Development

Install dependencies:

```bash
npm install
```

Run the Vite development server:

```bash
npm run dev
```

Run the Tauri development shell:

```bash
npm run tauri dev
```

Build the frontend:

```bash
npm run build
```

Build the Tauri application:

```bash
npm run tauri build
```

## Project Structure

```text
src/          React application code
src-tauri/    Tauri shell, Rust entry points, permissions, and configuration
public/       Static frontend assets
```

## Notes

- The HUD is one layer of the system; the core runtime must be available for
  full assistant behavior.
- Build outputs and dependency folders are intentionally ignored by Git.

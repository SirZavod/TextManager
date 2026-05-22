# TextManager

A powerful, lightweight Tkinter-based desktop application designed for efficient text and dataset management. Ideal for bulk editing, cleaning, and preparing text captions for machine learning and generative AI training workflows.

---

## Technical Enhancements (v2)

The current version introduces architectural changes, interface unification, and modern display compatibility:

*   **HiDPI / 4K Monitor Support:** Native integration via OS-level DPI awareness (`ctypes` wrapper for Windows systems). Text, widgets, and canvas elements render crisply without system blurring or layout distortion.
*   **Unified Translation:** Complete overhaul of all dialogues, notifications, and error states into clean, context-accurate technical English.
*   **Optimized Memory Lifecycle:** Implements a strict two-tier data management system. Edits are handled in an isolated memory cache (`text_cache`) and matched against raw pristine disk snapshots (`disk_snapshots`) before any file write operations occur.
*   **Dynamic Data Contextualization:** Action states and warning modals adapt seamlessly to runtime choices, ensuring clear file tracking across modes.

---

## Dual-Mode Architecture

### 1. Batch Mode (Line-by-Line Editor)
Designed for mass modifications and global overviews of text-only files.

*   **Granular Interface:** Dynamically maps every `.txt` file in the directory to an isolated row widget with permanent filename tracking.
*   **Flexible Sorting Logic:** Instant indexing by strict alphanumeric filename patterns or reverse chronological order (by last modification date).
*   **Global Batch Replace Panel:** Allows execution of massive find-and-replace queries spanning across the entire memory cache simultaneously.
*   **Bulk Export Gate:** Features a dedicated export mechanism to deploy modified caches to target output paths safely without overlapping raw inputs.

### 2. Img+Txt Mode (Paired View)
Tailored specifically for dataset validation, pairing images directly with their corresponding text files or text descriptions.

*   **Asynchronous Scaling Canvas:** High-performance responsive image preview using PIL/Pillow with Lanczos resampling filters, adjusting on-the-fly to window scaling.
*   **Contextual Safety Modals:** Integrated protection warning loops that check current field modifications against disk snapshots when skipping files, preventing accidental data loss.
*   **Hotkeys & Navigation:** Full binding mapping support for quick switching (`F1` / `Left Arrow` for Previous, `F2` / `Right Arrow` for Next).

---

## Interface Previews

### Batch Mode View
![Batch Mode Overview](batch.png)

### Img+Txt Mode View
![Img+Txt Mode Overview](imgtxt.png)

---

## Legacy Limitations (v1 Retrospective)
Compared to the current version, the initial prototype (`v1`) had architectural gaps that limited production workflows:
*   **No HiDPI Awareness:** UI scaled poorly on high-resolution/4K screens, resulting in blurry fonts and layout clipping.
*   **Lack of Paired Validation:** Missing an interactive canvas view, making it impossible to evaluate text files directly alongside graphical inputs.
*   **No Multi-Format Fallbacks:** Lacked flexible codec mapping during directory parses, which frequently led to crash loops or data dropouts when reading non-UTF-8 character sets.
*   **No Contextual State Guardrails:** Lacked verification loops to catch volatile memory changes before interface navigation or directory updates.

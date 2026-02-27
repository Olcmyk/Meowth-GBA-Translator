"""Progress view component using CustomTkinter."""

import customtkinter as ctk


class ProgressView(ctk.CTkFrame):
    """Progress display: checkmarks for extract/build, progress bar for translate."""

    def __init__(self, master):
        """Initialize progress view."""
        super().__init__(master, corner_radius=10)

        ctk.CTkLabel(
            self, text="Progress", font=("", 13, "bold")
        ).pack(anchor="w", padx=14, pady=(12, 8))

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=(0, 12))

        # --- Step 1: Extract ---
        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))
        self.extract_icon = ctk.CTkLabel(row1, text="○", width=24, font=("", 14))
        self.extract_icon.pack(side="left")
        self.extract_label = ctk.CTkLabel(
            row1, text="Extract texts from ROM", text_color="gray", font=("", 12)
        )
        self.extract_label.pack(side="left", padx=(6, 0))

        # --- Step 2: Translate (with progress bar) ---
        row2 = ctk.CTkFrame(inner, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 2))
        self.translate_icon = ctk.CTkLabel(row2, text="○", width=24, font=("", 14))
        self.translate_icon.pack(side="left")
        self.translate_label = ctk.CTkLabel(
            row2, text="Translate texts", text_color="gray", font=("", 12)
        )
        self.translate_label.pack(side="left", padx=(6, 0))

        # Progress bar for translate step
        bar_row = ctk.CTkFrame(inner, fg_color="transparent")
        bar_row.pack(fill="x", pady=(2, 6), padx=(30, 0))

        self.progress_bar = ctk.CTkProgressBar(
            bar_row, height=8, corner_radius=4, progress_color="#2563eb",
        )
        self.progress_bar.pack(fill="x", side="left", expand=True, padx=(0, 10))
        self.progress_bar.set(0)

        self.batch_label = ctk.CTkLabel(
            bar_row, text="0/0", text_color="gray", font=("", 11), width=70,
        )
        self.batch_label.pack(side="right")

        # --- Step 3: Build ROM ---
        row3 = ctk.CTkFrame(inner, fg_color="transparent")
        row3.pack(fill="x", pady=(0, 0))
        self.build_icon = ctk.CTkLabel(row3, text="○", width=24, font=("", 14))
        self.build_icon.pack(side="left")
        self.build_label = ctk.CTkLabel(
            row3, text="Build ROM", text_color="gray", font=("", 12)
        )
        self.build_label.pack(side="left", padx=(6, 0))

    def update(self, stage: str, current: int, total: int, message: str):
        """Update translate progress bar and batch count."""
        if stage == "translate" and total > 0:
            self.progress_bar.set(current / total)
            self.batch_label.configure(text=f"{current}/{total}")

    def set_stage(self, stage: str, status: str):
        """Update stage status with checkmark icons."""
        icon_map = {
            "extract": (self.extract_icon, self.extract_label),
            "translate": (self.translate_icon, self.translate_label),
            "build": (self.build_icon, self.build_label),
        }
        pair = icon_map.get(stage)
        if not pair:
            return
        icon, label = pair

        if status == "started":
            icon.configure(text="◉", text_color="#2563eb")
            label.configure(text_color="#e5e7eb")
        elif status == "completed":
            icon.configure(text="✓", text_color="#16a34a")
            label.configure(text_color="#16a34a")
        elif status == "failed":
            icon.configure(text="✗", text_color="#dc2626")
            label.configure(text_color="#dc2626")
        else:
            icon.configure(text="○", text_color="gray")
            label.configure(text_color="gray")

    def reset(self):
        """Reset progress view."""
        self.progress_bar.set(0)
        self.batch_label.configure(text="0/0")
        for stage in ("extract", "translate", "build"):
            self.set_stage(stage, "pending")

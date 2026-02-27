"""Configuration form component using CustomTkinter."""

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from ...core import TranslationConfig
from ...translator import PROVIDER_PRESETS

# Language display name -> language code (must match languages.py)
LANGUAGES = {
    "English": "en",
    "Chinese": "zh-Hans",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
}

LANG_NAMES = list(LANGUAGES.keys())


class ConfigForm(ctk.CTkFrame):
    """Configuration form for translation settings."""

    def __init__(self, master):
        """Initialize configuration form."""
        super().__init__(master, corner_radius=10)

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        # --- Row 1: ROM File ---
        ctk.CTkLabel(inner, text="ROM File", font=("", 12, "bold")).pack(anchor="w")
        rom_row = ctk.CTkFrame(inner, fg_color="transparent")
        rom_row.pack(fill="x", pady=(2, 8))
        self.rom_entry = ctk.CTkEntry(
            rom_row, placeholder_text="Select a GBA ROM file...", height=30
        )
        self.rom_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            rom_row, text="Browse", width=80, height=30, command=self._browse_rom
        ).pack(side="right")

        # --- Row 2: Languages ---
        ctk.CTkLabel(inner, text="Languages", font=("", 12, "bold")).pack(anchor="w")
        lang_row = ctk.CTkFrame(inner, fg_color="transparent")
        lang_row.pack(fill="x", pady=(2, 8))

        src_frame = ctk.CTkFrame(lang_row, fg_color="transparent")
        src_frame.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(src_frame, text="Source:", font=("", 11)).pack(anchor="w")
        self.source_lang = ctk.CTkComboBox(src_frame, values=LANG_NAMES, state="readonly", height=30)
        self.source_lang.set("English")
        self.source_lang.pack(fill="x", pady=(2, 0))

        tgt_frame = ctk.CTkFrame(lang_row, fg_color="transparent")
        tgt_frame.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(tgt_frame, text="Target:", font=("", 11)).pack(anchor="w")
        self.target_lang = ctk.CTkComboBox(tgt_frame, values=LANG_NAMES, state="readonly", height=30)
        self.target_lang.set("Chinese")
        self.target_lang.pack(fill="x", pady=(2, 0))

        # --- Row 3: Provider + Model ---
        ctk.CTkLabel(inner, text="LLM API", font=("", 12, "bold")).pack(anchor="w")
        pm_row = ctk.CTkFrame(inner, fg_color="transparent")
        pm_row.pack(fill="x", pady=(2, 4))

        prov_frame = ctk.CTkFrame(pm_row, fg_color="transparent")
        prov_frame.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(prov_frame, text="Provider:", font=("", 11)).pack(anchor="w")
        self.provider = ctk.CTkComboBox(
            prov_frame, values=list(PROVIDER_PRESETS.keys()),
            state="readonly", height=30, command=self._on_provider_change
        )
        self.provider.set("deepseek")
        self.provider.pack(fill="x", pady=(2, 0))

        model_frame = ctk.CTkFrame(pm_row, fg_color="transparent")
        model_frame.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(model_frame, text="Model:", font=("", 11)).pack(anchor="w")
        self.model_entry = ctk.CTkEntry(model_frame, height=30)
        self.model_entry.insert(0, PROVIDER_PRESETS["deepseek"][1])
        self.model_entry.pack(fill="x", pady=(2, 0))

        # --- Row 4: API Key ---
        ctk.CTkLabel(inner, text="API Key:", font=("", 11)).pack(anchor="w", pady=(4, 0))
        self.api_key_entry = ctk.CTkEntry(
            inner, placeholder_text="sk-xxxxxxxxxxxxxxxxxxxxxxxx", height=30, show="*"
        )
        self.api_key_entry.pack(fill="x", pady=(2, 0))

        # --- Advanced (collapsible) ---
        self.advanced_visible = False
        self.advanced_button = ctk.CTkButton(
            inner, text="+ Advanced", command=self._toggle_advanced,
            fg_color="transparent", text_color=("gray40", "gray60"),
            hover_color=("gray85", "gray25"), height=24, font=("", 11),
        )
        self.advanced_button.pack(anchor="w", pady=(6, 0))

        self.advanced_frame = ctk.CTkFrame(inner, fg_color="transparent")
        adv_row = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        adv_row.pack(fill="x", pady=(4, 0))

        bf = ctk.CTkFrame(adv_row, fg_color="transparent")
        bf.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkLabel(bf, text="Batch Size:", font=("", 11)).pack(anchor="w")
        self.batch_size = ctk.CTkEntry(bf, height=30)
        self.batch_size.insert(0, "30")
        self.batch_size.pack(fill="x", pady=(2, 0))

        wf = ctk.CTkFrame(adv_row, fg_color="transparent")
        wf.pack(side="right", fill="x", expand=True, padx=(6, 0))
        ctk.CTkLabel(wf, text="Max Workers:", font=("", 11)).pack(anchor="w")
        self.max_workers = ctk.CTkEntry(wf, height=30)
        self.max_workers.insert(0, "10")
        self.max_workers.pack(fill="x", pady=(2, 0))

    def _on_provider_change(self, provider_name: str):
        """Update default model when provider changes."""
        preset = PROVIDER_PRESETS.get(provider_name)
        if preset:
            self.model_entry.delete(0, "end")
            self.model_entry.insert(0, preset[1])

    def _browse_rom(self):
        """Open file dialog to select ROM."""
        filename = filedialog.askopenfilename(
            title="Select GBA ROM",
            filetypes=[("GBA ROM files", "*.gba"), ("All files", "*.*")],
        )
        if filename:
            self.rom_entry.delete(0, "end")
            self.rom_entry.insert(0, filename)

    def _toggle_advanced(self):
        """Toggle advanced settings visibility."""
        if self.advanced_visible:
            self.advanced_frame.pack_forget()
            self.advanced_button.configure(text="+ Advanced")
            self.advanced_visible = False
        else:
            self.advanced_frame.pack(fill="x")
            self.advanced_button.configure(text="- Advanced")
            self.advanced_visible = True

    def _lang_name_to_code(self, name: str) -> str:
        return LANGUAGES.get(name, "en")

    def get_config(self) -> TranslationConfig:
        """Get current configuration."""
        provider = self.provider.get()
        preset = PROVIDER_PRESETS.get(provider)
        api_key = self.api_key_entry.get().strip()
        return TranslationConfig(
            source_lang=self._lang_name_to_code(self.source_lang.get()),
            target_lang=self._lang_name_to_code(self.target_lang.get()),
            provider=provider if provider else None,
            model=self.model_entry.get().strip() or (preset[1] if preset else None),
            api_key_env=preset[2] if preset else None,
            api_key=api_key if api_key else None,
            batch_size=int(self.batch_size.get()) if self.batch_size.get().isdigit() else 30,
            max_workers=int(self.max_workers.get()) if self.max_workers.get().isdigit() else 10,
            rom_path=Path(self.rom_entry.get()) if self.rom_entry.get() else None,
        )

    def validate(self) -> tuple[bool, str]:
        """Validate configuration."""
        if not self.rom_entry.get():
            return False, "Please select a ROM file"
        rom_path = Path(self.rom_entry.get())
        if not rom_path.exists():
            return False, f"ROM file not found: {rom_path}"
        if not self.api_key_entry.get().strip():
            return False, "Please enter your API key"
        return True, ""

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Daniel Nylander <daniel@danielnylander.se>

"""Main entry point for Glossary Editor."""

import csv
import sys
import gettext
import json
import locale
import os

# i18n setup
LOCALE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'po')
if not os.path.isdir(LOCALE_DIR):
    LOCALE_DIR = '/usr/share/locale'
gettext.bindtextdomain('l10n-glossary', LOCALE_DIR)
gettext.textdomain('l10n-glossary')
_ = gettext.gettext

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GObject

from l10n_glossary.glossary import Glossary, Term
from l10n_glossary.io_handler import (
    load_glossary, save_glossary, import_po_terms, import_ts_terms
)
from l10n_glossary.consistency import check_consistency
from datetime import datetime as _dt_now
from l10n_glossary.accessibility import AccessibilityManager



def _settings_path():
    import os
    xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    d = os.path.join(xdg, "l10n-glossary")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")

def _load_settings():
    import os, json
    p = _settings_path()
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {}

def _save_settings(s):
    import json
    with open(_settings_path(), "w") as f:
        json.dump(s, f, indent=2)

class GlossaryWindow(Adw.ApplicationWindow):
    """Main application window."""

    def __init__(self, **kwargs):
        kwargs.pop("default_width", None)
        kwargs.pop("default_height", None)
        super().__init__(**kwargs)
        self.glossary = Glossary()
        self.current_file = None
        self.filtered_terms = []
        self._refreshing = False

        self.set_title(_("Glossary Editor"))
        self.set_default_size(900, 600)
        self.set_size_request(600, 400)

        self._build_ui()

        # Add sample terms so the view isn't empty on first launch
        if len(self.glossary.terms) == 0:
            for src, tgt, ctx, cmt in [
                ("Hello", "Hej", "", "Common greeting"),
                ("File", "Fil", "menu", "Menu item"),
                ("Save", "Spara", "action", ""),
                ("Open", "Öppna", "action", ""),
                ("Error", "Fel", "dialog", "Error message title"),
            ]:
                self.glossary.terms.append(Term(src, tgt, "sv", ctx, cmt))

        self._refresh_list()

    def _build_ui(self):
        """Build the UI."""
        # Use ToolbarView for proper header bar handling
        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        # Header bar (must be first)
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        toolbar_view.set_content(main_box)

        # Status bar
        self._status_bar = Gtk.Label(label="", halign=Gtk.Align.START,
                                     margin_start=12, margin_end=12, margin_bottom=4)
        self._status_bar.add_css_class("dim-label")
        self._status_bar.add_css_class("caption")

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu = Gio.Menu()
        menu.append(_("New Glossary"), "win.new")
        menu.append(_("Open…"), "win.open")
        menu.append(_("Save"), "win.save")
        menu.append(_("Save As…"), "win.save_as")

        import_section = Gio.Menu()
        import_section.append(_("Import from PO…"), "win.import_po")
        import_section.append(_("Import from TS…"), "win.import_ts")
        import_section.append(_("Merge Glossary…"), "win.merge")
        menu.append_section(_("Import"), import_section)

        export_section = Gio.Menu()
        export_section.append(_("Export as TBX…"), "win.export_tbx")
        export_section.append(_("Export as CSV…"), "win.export_csv")
        export_section.append(_("Export as TSV…"), "win.export_tsv")
        menu.append_section(_("Export"), export_section)

        check_section = Gio.Menu()
        check_section.append(_("Check Consistency…"), "win.check_consistency")
        menu.append_section(_("Tools"), check_section)

        about_section = Gio.Menu()
        about_section.append(_("About"), "win.about")
        menu.append_section(None, about_section)

        menu_button.set_menu_model(menu)
        header.pack_end(menu_button)

        # Theme toggle
        self._theme_btn = Gtk.Button(icon_name="weather-clear-night-symbolic",
                                     tooltip_text="Toggle dark/light theme")
        self._theme_btn.connect("clicked", self._on_theme_toggle)
        header.pack_end(self._theme_btn)

        # Export button
        export_btn = Gtk.Button(icon_name="document-save-symbolic",
                                tooltip_text=_("Export data"))
        export_btn.connect("clicked", self._on_export_clicked)
        header.pack_end(export_btn)

        # Add term button
        add_button = Gtk.Button(icon_name="list-add-symbolic")
        add_button.set_tooltip_text(_("Add Term"))
        add_button.connect("clicked", self._on_add_term)
        header.pack_start(add_button)

        # Search bar
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_("Search terms…"))
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.set_margin_start(12)
        search_box.set_margin_end(12)
        search_box.set_margin_top(6)
        search_box.set_margin_bottom(6)
        search_box.append(self.search_entry)

        # Language filter
        self.lang_filter = Gtk.DropDown.new_from_strings([_("All Languages")])
        self.lang_filter.connect("notify::selected", self._on_search_changed)
        search_box.append(self.lang_filter)

        main_box.append(search_box)

        # Term list (scrollable)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        # Column view for terms
        self.list_store = Gio.ListStore.new(TermObject)
        self.selection = Gtk.SingleSelection.new(self.list_store)

        self.column_view = Gtk.ColumnView.new(self.selection)
        self.column_view.set_show_column_separators(True)
        self.column_view.set_show_row_separators(True)

        # Source column
        factory_src = Gtk.SignalListItemFactory()
        factory_src.connect("setup", self._setup_label)
        factory_src.connect("bind", self._bind_source)
        col_src = Gtk.ColumnViewColumn.new(_("Source"), factory_src)
        col_src.set_expand(True)
        self.column_view.append_column(col_src)

        # Target column
        factory_tgt = Gtk.SignalListItemFactory()
        factory_tgt.connect("setup", self._setup_label)
        factory_tgt.connect("bind", self._bind_target)
        col_tgt = Gtk.ColumnViewColumn.new(_("Target"), factory_tgt)
        col_tgt.set_expand(True)
        self.column_view.append_column(col_tgt)

        # Language column
        factory_lang = Gtk.SignalListItemFactory()
        factory_lang.connect("setup", self._setup_label)
        factory_lang.connect("bind", self._bind_language)
        col_lang = Gtk.ColumnViewColumn.new(_("Language"), factory_lang)
        col_lang.set_fixed_width(100)
        self.column_view.append_column(col_lang)

        # Context column
        factory_ctx = Gtk.SignalListItemFactory()
        factory_ctx.connect("setup", self._setup_label)
        factory_ctx.connect("bind", self._bind_context)
        col_ctx = Gtk.ColumnViewColumn.new(_("Context"), factory_ctx)
        col_ctx.set_expand(True)
        self.column_view.append_column(col_ctx)

        # Comment column
        factory_cmt = Gtk.SignalListItemFactory()
        factory_cmt.connect("setup", self._setup_label)
        factory_cmt.connect("bind", self._bind_comment)
        col_cmt = Gtk.ColumnViewColumn.new(_("Comment"), factory_cmt)
        col_cmt.set_expand(True)
        self.column_view.append_column(col_cmt)

        scrolled.set_child(self.column_view)
        scrolled.set_size_request(600, 300)
        main_box.append(scrolled)

        # Status bar
        self.status_label = Gtk.Label(label=_("No glossary loaded"))
        self.status_label.set_margin_start(12)
        self.status_label.set_margin_end(12)
        self.status_label.set_margin_top(4)
        self.status_label.set_margin_bottom(4)
        self.status_label.set_xalign(0)
        main_box.append(self.status_label)

        # Actions
        self._setup_actions()

        # Double-click to edit
        gesture = Gtk.GestureClick.new()
        gesture.set_button(1)
        gesture.connect("released", self._on_row_activated)
        self.column_view.add_controller(gesture)

    def _setup_actions(self):
        """Set up window actions."""
        actions = {
            "new": self._on_new,
            "open": self._on_open,
            "save": self._on_save,
            "save_as": self._on_save_as,
            "import_po": self._on_import_po,
            "import_ts": self._on_import_ts,
            "merge": self._on_merge,
            "export_tbx": lambda *a: self._on_export("tbx"),
            "export_csv": lambda *a: self._on_export("csv"),
            "export_tsv": lambda *a: self._on_export("tsv"),
            "check_consistency": self._on_check_consistency,
            "about": self._on_about,
        }
        for name, callback in actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def _setup_label(self, factory, list_item):
        label = Gtk.Label()
        label.set_xalign(0)
        label.set_margin_start(6)
        label.set_margin_end(6)
        label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        list_item.set_child(label)

    def _bind_source(self, factory, list_item):
        obj = list_item.get_item()
        list_item.get_child().set_text(obj.term.source)

    def _bind_target(self, factory, list_item):
        obj = list_item.get_item()
        list_item.get_child().set_text(obj.term.target)

    def _bind_language(self, factory, list_item):
        obj = list_item.get_item()
        list_item.get_child().set_text(obj.term.language)

    def _bind_context(self, factory, list_item):
        obj = list_item.get_item()
        list_item.get_child().set_text(obj.term.context)

    def _bind_comment(self, factory, list_item):
        obj = list_item.get_item()
        list_item.get_child().set_text(obj.term.comment)

    def _refresh_list(self, search_text="", lang_filter=""):
        """Refresh the term list."""
        if self._refreshing:
            return
        self._refreshing = True
        self.list_store.remove_all()
        for term in self.glossary.terms:
            if search_text:
                q = search_text.lower()
                if not (q in term.source.lower() or q in term.target.lower()
                        or q in term.context.lower() or q in term.comment.lower()):
                    continue
            if lang_filter and lang_filter != _("All Languages"):
                if term.language != lang_filter:
                    continue
            self.list_store.append(TermObject(term))

        count = self.list_store.get_n_items()
        total = len(self.glossary.terms)
        if count == total:
            self.status_label.set_text(_("{} terms").format(total))
        else:
            self.status_label.set_text(
                _("{} of {} terms shown").format(count, total))

        self._update_lang_filter()
        self._refreshing = False

    def _update_lang_filter(self):
        """Update language filter dropdown."""
        langs = sorted(set(t.language for t in self.glossary.terms if t.language))
        strings = [_("All Languages")] + langs
        model = Gtk.StringList.new(strings)
        self.lang_filter.set_model(model)

    def _on_search_changed(self, *args):
        search_text = self.search_entry.get_text()
        idx = self.lang_filter.get_selected()
        model = self.lang_filter.get_model()
        lang = ""
        if model and idx < model.get_n_items():
            lang = model.get_string(idx)
        self._refresh_list(search_text, lang)

    def _on_export_clicked(self, *_args):
        dialog = Adw.MessageDialog(transient_for=self,
                                   heading=_("Export Data"),
                                   body=_("Choose export format:"))
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("csv", "CSV")
        dialog.add_response("json", "JSON")
        dialog.set_response_appearance("csv", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_export_format_chosen)
        dialog.present()

    def _on_export_format_chosen(self, dialog, response):
        if response not in ("csv", "json"):
            return
        self._export_fmt = response
        fd = Gtk.FileDialog()
        fd.set_initial_name(f"glossary.{response}")
        fd.save(self, None, self._on_export_save)

    def _on_export_save(self, dialog, result):
        try:
            path = dialog.save_finish(result).get_path()
        except Exception:
            return
        data = [{"source": t.source, "target": t.target, "language": t.language,
                 "context": t.context, "comment": t.comment}
                for t in self.glossary.terms]
        if not data:
            return
        if self._export_fmt == "csv":
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=data[0].keys())
                w.writeheader()
                w.writerows(data)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def _on_add_term(self, button):
        self._show_term_dialog(None)

    def _on_row_activated(self, gesture, n_press, x, y):
        if n_press == 2:
            pos = self.selection.get_selected()
            if pos != Gtk.INVALID_LIST_POSITION:
                obj = self.list_store.get_item(pos)
                if obj:
                    self._show_term_dialog(obj.term)

    def _show_term_dialog(self, term):
        """Show dialog to add or edit a term."""
        is_edit = term is not None
        dialog = Adw.Dialog.new()
        dialog.set_title(_("Edit Term") if is_edit else _("Add Term"))
        dialog.set_content_width(450)
        dialog.set_content_height(400)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()

        # Cancel button
        cancel_btn = Gtk.Button(label=_("Cancel"))
        cancel_btn.connect("clicked", lambda b: dialog.close())
        header.pack_start(cancel_btn)

        # Save button
        save_btn = Gtk.Button(label=_("Save"))
        save_btn.add_css_class("suggested-action")
        header.pack_end(save_btn)

        # Delete button (only for edit)
        if is_edit:
            delete_btn = Gtk.Button(label=_("Delete"))
            delete_btn.add_css_class("destructive-action")
            header.pack_end(delete_btn)

        toolbar_view.add_top_bar(header)

        # Form
        prefs = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        prefs.add(group)

        source_row = Adw.EntryRow(title=_("Source term"))
        target_row = Adw.EntryRow(title=_("Target term"))
        lang_row = Adw.EntryRow(title=_("Language code"))
        ctx_row = Adw.EntryRow(title=_("Context"))
        comment_row = Adw.EntryRow(title=_("Comment"))

        for row in [source_row, target_row, lang_row, ctx_row, comment_row]:
            group.add(row)

        if is_edit:
            source_row.set_text(term.source)
            target_row.set_text(term.target)
            lang_row.set_text(term.language)
            ctx_row.set_text(term.context)
            comment_row.set_text(term.comment)

        toolbar_view.set_content(prefs)
        dialog.set_child(toolbar_view)

        def on_save(btn):
            new_term = Term(
                source=source_row.get_text(),
                target=target_row.get_text(),
                language=lang_row.get_text(),
                context=ctx_row.get_text(),
                comment=comment_row.get_text(),
            )
            if is_edit:
                idx = self.glossary.terms.index(term)
                self.glossary.terms[idx] = new_term
            else:
                self.glossary.terms.append(new_term)
            self._refresh_list(self.search_entry.get_text())
            dialog.close()

        save_btn.connect("clicked", on_save)

        if is_edit:
            def on_delete(btn):
                self.glossary.terms.remove(term)
                self._refresh_list(self.search_entry.get_text())
                dialog.close()
            delete_btn.connect("clicked", on_delete)

        dialog.present(self)

    def _on_new(self, *args):
        self.glossary = Glossary()
        self.current_file = None
        self._refresh_list()
        self.set_title(_("Glossary Editor"))

    def _on_open(self, *args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_("Open Glossary"))
        f = Gtk.FileFilter()
        f.set_name(_("Glossary files"))
        for pat in ["*.tbx", "*.csv", "*.tsv"]:
            f.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_open_response)

    def _on_open_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            path = file.get_path()
            self.glossary = load_glossary(path)
            self.current_file = path
            self.set_title(os.path.basename(path) + " — " + _("Glossary Editor"))
            self._refresh_list()
        except Exception as e:
            self._show_error(str(e))

    def _on_save(self, *args):
        if self.current_file:
            save_glossary(self.glossary, self.current_file)
        else:
            self._on_save_as()

    def _on_save_as(self, *args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_("Save Glossary"))
        dialog.save(self, None, self._on_save_response)

    def _on_save_response(self, dialog, result):
        try:
            file = dialog.save_finish(result)
            path = file.get_path()
            save_glossary(self.glossary, path)
            self.current_file = path
            self.set_title(os.path.basename(path) + " — " + _("Glossary Editor"))
        except Exception as e:
            self._show_error(str(e))

    def _on_import_po(self, *args):
        self._import_file("po")

    def _on_import_ts(self, *args):
        self._import_file("ts")

    def _import_file(self, fmt):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_("Import from {} file").format(fmt.upper()))
        f = Gtk.FileFilter()
        f.set_name(_("{} files").format(fmt.upper()))
        f.add_pattern(f"*.{fmt}")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self, None, lambda d, r: self._on_import_response(d, r, fmt))

    def _on_import_response(self, dialog, result, fmt):
        try:
            file = dialog.open_finish(result)
            path = file.get_path()
            if fmt == "po":
                terms = import_po_terms(path)
            else:
                terms = import_ts_terms(path)
            self.glossary.terms.extend(terms)
            self._refresh_list()
            self._show_info(_("{} terms imported").format(len(terms)))
        except Exception as e:
            self._show_error(str(e))

    def _on_merge(self, *args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_("Merge Glossary"))
        f = Gtk.FileFilter()
        f.set_name(_("Glossary files"))
        for pat in ["*.tbx", "*.csv", "*.tsv"]:
            f.add_pattern(pat)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_merge_response)

    def _on_merge_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            path = file.get_path()
            other = load_glossary(path)
            added = self.glossary.merge(other)
            self._refresh_list()
            self._show_info(_("{} new terms merged").format(added))
        except Exception as e:
            self._show_error(str(e))

    def _on_export(self, fmt):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_("Export as {}").format(fmt.upper()))
        dialog.save(self, None, lambda d, r: self._on_export_response(d, r, fmt))

    def _on_export_response(self, dialog, result, fmt):
        try:
            file = dialog.save_finish(result)
            path = file.get_path()
            if not path.endswith(f".{fmt}"):
                path += f".{fmt}"
            save_glossary(self.glossary, path, fmt)
        except Exception as e:
            self._show_error(str(e))

    def _on_check_consistency(self, *args):
        dialog = Gtk.FileDialog.new()
        dialog.set_title(_("Select PO/TS file to check"))
        f = Gtk.FileFilter()
        f.set_name(_("Translation files"))
        f.add_pattern("*.po")
        f.add_pattern("*.ts")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dialog.set_filters(filters)
        dialog.open(self, None, self._on_check_response)

    def _on_check_response(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            path = file.get_path()
            issues = check_consistency(self.glossary, path)
            if not issues:
                self._show_info(_("No inconsistencies found!"))
            else:
                self._show_consistency_results(issues)
        except Exception as e:
            self._show_error(str(e))

    def _show_consistency_results(self, issues):
        """Show consistency check results in a dialog."""
        dialog = Adw.Dialog.new()
        dialog.set_title(_("Consistency Issues"))
        dialog.set_content_width(600)
        dialog.set_content_height(400)

        toolbar_view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        close_btn = Gtk.Button(label=_("Close"))
        close_btn.connect("clicked", lambda b: dialog.close())
        header.pack_start(close_btn)
        toolbar_view.add_top_bar(header)

        scrolled = Gtk.ScrolledWindow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(12)
        box.set_margin_end(12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)

        for issue in issues:
            row = Adw.ActionRow()
            row.set_title(issue["source"])
            row.set_subtitle(
                _("Expected: {expected} — Found: {found}").format(**issue))
            box.append(row)

        scrolled.set_child(box)
        toolbar_view.set_content(scrolled)
        dialog.set_child(toolbar_view)
        dialog.present(self)

    def _show_error(self, message):
        dialog = Adw.AlertDialog.new(_("Error"), message)
        dialog.add_response("ok", _("OK"))
        dialog.present(self)

    def _show_info(self, message):
        dialog = Adw.AlertDialog.new(_("Info"), message)
        dialog.add_response("ok", _("OK"))
        dialog.present(self)

    def _on_about(self, *args):
        about = Adw.AboutDialog.new()
        about.set_application_name(_("Glossary Editor"))
        about.set_application_icon("l10n-glossary")
        about.set_version("0.1.0")
        about.set_developer_name("Daniel Nylander")
        about.set_license_type(Gtk.License.GPL_3_0)
        about.set_comments(_("A localization tool by Daniel Nylander"))
        about.set_website("https://github.com/yeager/l10n-glossary")
        about.set_issue_url("https://github.com/yeager/l10n-glossary/issues")
        about.set_translate_url("https://app.transifex.com/danielnylander/l10n-glossary/")
        about.set_developers(["Daniel Nylander <daniel@danielnylander.se>"])
        about.set_translator_credits(_("Translate this app: https://www.transifex.com/danielnylander/l10n-glossary/"))
        about.present(self)



    def _on_theme_toggle(self, _btn):
        sm = Adw.StyleManager.get_default()
        if sm.get_color_scheme() == Adw.ColorScheme.FORCE_DARK:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            self._theme_btn.set_icon_name("weather-clear-night-symbolic")
        else:
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self._theme_btn.set_icon_name("weather-clear-symbolic")

    def _update_status_bar(self):
        self._status_bar.set_text("Last updated: " + _dt_now.now().strftime("%Y-%m-%d %H:%M"))

class TermObject(GObject.Object):
    """Wrapper to put Term in a Gio.ListStore."""

    def __init__(self, term):
        super().__init__()
        self.term = term



class GlossaryApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="se.danielnylander.l10n_glossary",
            flags=Gio.ApplicationFlags.NON_UNIQUE,
        )

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        self.set_accels_for_action("app.refresh", ["F5"])
        self.set_accels_for_action("app.shortcuts", ["<Control>slash"])
        self.set_accels_for_action("app.export", ["<Control>e"])
        for n, cb in [("quit", lambda *_: self.quit()),
                      ("refresh", lambda *_: self._do_refresh()),
                      ("shortcuts", self._show_shortcuts_window),
                      ("export", lambda *_: self.get_active_window() and self.get_active_window()._on_export_clicked())]:
            a = Gio.SimpleAction.new(n, None); a.connect("activate", cb); self.add_action(a)

    def _do_refresh(self):
        w = self.get_active_window()
        if w and hasattr(w, '_refresh_list'): w._refresh_list()

    def _show_shortcuts_window(self, *_args):
        win = Gtk.ShortcutsWindow(transient_for=self.get_active_window(), modal=True)
        section = Gtk.ShortcutsSection(visible=True, max_height=10)
        group = Gtk.ShortcutsGroup(visible=True, title="General")
        for accel, title in [("<Control>q", "Quit"), ("F5", "Refresh"), ("<Control>slash", "Keyboard shortcuts")]:
            s = Gtk.ShortcutsShortcut(visible=True, accelerator=accel, title=title)
            group.append(s)
        section.append(group)
        win.add_child(section)
        win.present()
        if not self.settings.get("welcome_shown"):
            self._show_welcome(self if hasattr(self, "set_content") else win)


    def do_activate(self):
        self.settings = _load_settings()
        win = self.props.active_window
        if not win:
            win = GlossaryWindow(application=self)
        win.present()


def main():
    """Entry point."""
    app = GlossaryApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

    # ── Welcome Dialog ───────────────────────────────────────

    def _show_welcome(self, win):
        dialog = Adw.Dialog()
        dialog.set_title(_("Welcome"))
        dialog.set_content_width(420)
        dialog.set_content_height(480)

        page = Adw.StatusPage()
        page.set_icon_name("accessories-dictionary-symbolic")
        page.set_title(_("Welcome to L10n Glossary"))
        page.set_description(_(
            "Manage translation glossaries for consistent translations.\n\n✓ Create and edit term databases\n✓ Search across glossaries\n✓ Import/export CSV and TBX\n✓ Share glossaries with teams"
        ))

        btn = Gtk.Button(label=_("Get Started"))
        btn.add_css_class("suggested-action")
        btn.add_css_class("pill")
        btn.set_halign(Gtk.Align.CENTER)
        btn.set_margin_top(12)
        btn.connect("clicked", self._on_welcome_close, dialog)
        page.set_child(btn)

        box = Adw.ToolbarView()
        hb = Adw.HeaderBar()
        hb.set_show_title(False)
        box.add_top_bar(hb)
        box.set_content(page)
        dialog.set_child(box)
        dialog.present(win)

    def _on_welcome_close(self, btn, dialog):
        self.settings["welcome_shown"] = True
        _save_settings(self.settings)
        dialog.close()



# --- Session restore ---
import json as _json
import os as _os

def _save_session(window, app_name):
    config_dir = _os.path.join(_os.path.expanduser('~'), '.config', app_name)
    _os.makedirs(config_dir, exist_ok=True)
    state = {'width': window.get_width(), 'height': window.get_height(),
             'maximized': window.is_maximized()}
    try:
        with open(_os.path.join(config_dir, 'session.json'), 'w') as f:
            _json.dump(state, f)
    except OSError:
        pass

def _restore_session(window, app_name):
    path = _os.path.join(_os.path.expanduser('~'), '.config', app_name, 'session.json')
    try:
        with open(path) as f:
            state = _json.load(f)
        window.set_default_size(state.get('width', 800), state.get('height', 600))
        if state.get('maximized'):
            window.maximize()
    except (FileNotFoundError, _json.JSONDecodeError, OSError):
        pass


# --- Fullscreen toggle (F11) ---
def _setup_fullscreen(window, app):
    """Add F11 fullscreen toggle."""
    from gi.repository import Gio
    if not app.lookup_action('toggle-fullscreen'):
        action = Gio.SimpleAction.new('toggle-fullscreen', None)
        action.connect('activate', lambda a, p: (
            window.unfullscreen() if window.is_fullscreen() else window.fullscreen()
        ))
        app.add_action(action)
        app.set_accels_for_action('app.toggle-fullscreen', ['F11'])


# --- Plugin system ---
import importlib.util
import os as _pos

def _load_plugins(app_name):
    """Load plugins from ~/.config/<app>/plugins/."""
    plugin_dir = _pos.path.join(_pos.path.expanduser('~'), '.config', app_name, 'plugins')
    plugins = []
    if not _pos.path.isdir(plugin_dir):
        return plugins
    for fname in sorted(_pos.listdir(plugin_dir)):
        if fname.endswith('.py') and not fname.startswith('_'):
            path = _pos.path.join(plugin_dir, fname)
            try:
                spec = importlib.util.spec_from_file_location(fname[:-3], path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                plugins.append(mod)
            except Exception as e:
                print(f"Plugin {fname}: {e}")
    return plugins

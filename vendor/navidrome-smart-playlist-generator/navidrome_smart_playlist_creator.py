#!/usr/bin/env python3
"""
Navidrome Smart Playlist Creator
A guided CLI tool to create .nsp files for Navidrome smart playlists
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.rule import Rule
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Note: Install 'rich' for a better experience: pip install rich")


def strip_markup(text: str) -> str:
    return re.sub(r'\[/?[^\]]*\]', '', text)


class SmartPlaylistCreator:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.config_file = Path.home() / ".navidrome_playlist_config.json"
        self.playlist_dir = self.load_config()

        # Complete field list matching Navidrome / Feishin NDSongQueryFields
        # (field_key, description, type)
        self.fields: Dict[str, List[Tuple[str, str, str]]] = {
            "Core Track Info": [
                ("title",        "Track title",            "string"),
                ("album",        "Album name",             "string"),
                ("artist",       "Artist name",            "string"),
                ("albumartist",  "Album artist",           "string"),
                ("genre",        "Genre",                  "string"),
                ("composer",     "Composer",               "string"),
                ("year",         "Year",                   "number"),
                ("track",        "Track number",           "number"),
                ("discnumber",   "Disc number",            "number"),
                ("duration",     "Duration (seconds)",     "number"),
                ("bpm",          "Beats per minute",       "number"),
            ],
            "Artists & People": [
                ("albumartists", "Album artists (multi)",  "string"),
                ("artists",      "Artists (multi)",        "string"),
                ("arranger",     "Arranger",               "string"),
                ("conductor",    "Conductor",              "string"),
                ("director",     "Director",               "string"),
                ("djmixer",      "DJ mixer",               "string"),
                ("engineer",     "Engineer",               "string"),
                ("lyricist",     "Lyricist",               "string"),
                ("mixer",        "Mixer",                  "string"),
                ("performer",    "Performer",              "string"),
                ("producer",     "Producer",               "string"),
                ("remixer",      "Remixer",                "string"),
            ],
            "Album Details": [
                ("albumcomment",    "Album comment",       "string"),
                ("albumtype",       "Album type",          "string"),
                ("albumversion",    "Album version",       "string"),
                ("catalognumber",   "Catalog number",      "string"),
                ("compilation",     "Is a compilation",    "boolean"),
                ("recordlabel",     "Record label",        "string"),
                ("releasecountry",  "Release country",     "string"),
                ("releasestatus",   "Release status",      "string"),
                ("releasetype",     "Release type",        "string"),
            ],
            "File & Quality": [
                ("filepath",         "File path",                     "string"),
                ("filetype",         "File type (e.g. flac, mp3)",    "string"),
                ("bitrate",          "Bitrate (kbps)",                "number"),
                ("bitdepth",         "Bit depth",                     "number"),
                ("size",             "File size (bytes)",             "number"),
                ("channels",         "Audio channels",                "number"),
                ("hascoverart",      "Has cover art",                 "boolean"),
                ("explicitstatus",   "Explicit status",               "string"),
                ("encodedby",        "Encoded by",                    "string"),
                ("encodersettings",  "Encoder settings",              "string"),
            ],
            "Listening & Favorites": [
                ("playcount",  "Play count",            "number"),
                ("rating",     "Rating (0-5)",          "number"),
                ("loved",      "Is favorite / loved",   "boolean"),
                ("lastplayed", "Date last played",      "date"),
                ("dateloved",  "Date favorited",        "date"),
            ],
            "Dates": [
                ("dateadded",      "Date added to library",     "date"),
                ("datemodified",   "Date file modified",        "date"),
                ("originaldate",   "Original release date",     "date"),
                ("originalyear",   "Original year",             "date"),
                ("recordingdate",  "Recording date",            "date"),
                ("releasedate",    "Release date",              "date"),
            ],
            "Text Tags": [
                ("comment",       "Comment",           "string"),
                ("lyrics",        "Lyrics",            "string"),
                ("grouping",      "Grouping",          "string"),
                ("discsubtitle",  "Disc subtitle",     "string"),
                ("subtitle",      "Track subtitle",    "string"),
                ("mood",          "Mood",              "string"),
                ("movement",      "Movement",          "string"),
                ("movementname",  "Movement name",     "string"),
            ],
            "Numeric Tags": [
                ("disctotal",              "Total discs",              "number"),
                ("tracktotal",             "Total tracks",             "number"),
                ("movementtotal",          "Total movements",          "number"),
                ("r128_album_gain",        "R128 album gain",          "number"),
                ("r128_track_gain",        "R128 track gain",          "number"),
                ("replaygain_album_gain",  "ReplayGain album gain",    "number"),
                ("replaygain_album_peak",  "ReplayGain album peak",    "number"),
                ("replaygain_track_gain",  "ReplayGain track gain",    "number"),
                ("replaygain_track_peak",  "ReplayGain track peak",    "number"),
            ],
            "Sort Fields": [
                ("titlesort",          "Sort name",            "string"),
                ("albumsort",          "Sort album",           "string"),
                ("albumartistsort",    "Sort album artist",    "string"),
                ("albumartistssort",   "Sort album artists",   "string"),
                ("artistsort",         "Sort artist",          "string"),
                ("artistssort",        "Sort artists",         "string"),
                ("composersort",       "Sort composer",        "string"),
                ("lyricistsort",       "Sort lyricist",        "string"),
            ],
            "Identifiers & Technical": [
                ("library_id",  "Library ID",          "string"),
                ("isrc",        "ISRC code",           "string"),
                ("asin",        "Amazon ASIN",         "string"),
                ("barcode",     "Barcode",             "string"),
                ("key",         "Musical key",         "string"),
                ("language",    "Language",             "string"),
                ("license",     "License",             "string"),
                ("media",       "Media type",          "string"),
                ("script",      "Script",              "string"),
                ("copyright",   "Copyright",           "string"),
                ("website",     "Website",             "string"),
                ("work",        "Work",                "string"),
            ],
            "MusicBrainz IDs": [
                ("mbz_album_id",              "Album ID",           "string"),
                ("mbz_album_artist_id",       "Album Artist ID",    "string"),
                ("mbz_artist_id",             "Artist ID",          "string"),
                ("mbz_recording_id",          "Recording ID",       "string"),
                ("mbz_release_group_id",      "Release Group ID",   "string"),
                ("mbz_release_track_id",      "Release Track ID",   "string"),
                ("musicbrainz_arrangerid",    "Arranger ID",        "string"),
                ("musicbrainz_composerid",    "Composer ID",        "string"),
                ("musicbrainz_conductorid",   "Conductor ID",       "string"),
                ("musicbrainz_directorid",    "Director ID",        "string"),
                ("musicbrainz_discid",        "Disc ID",            "string"),
                ("musicbrainz_djmixerid",     "DJ Mixer ID",        "string"),
                ("musicbrainz_engineerid",    "Engineer ID",        "string"),
                ("musicbrainz_lyricistid",    "Lyricist ID",        "string"),
                ("musicbrainz_mixerid",       "Mixer ID",           "string"),
                ("musicbrainz_performerid",   "Performer ID",       "string"),
                ("musicbrainz_producerid",    "Producer ID",        "string"),
                ("musicbrainz_remixerid",     "Remixer ID",         "string"),
                ("musicbrainz_trackid",       "Track ID",           "string"),
                ("musicbrainz_workid",        "Work ID",            "string"),
            ],
            "Playlist": [
                ("id", "Playlist (for in/not-in playlist filters)", "playlist"),
            ],
        }

        self.operators: Dict[str, List[Tuple[str, str]]] = {
            "string": [
                ("is",           "Is exactly"),
                ("isNot",        "Is not"),
                ("contains",     "Contains"),
                ("notContains",  "Does not contain"),
                ("startsWith",   "Starts with"),
                ("endsWith",     "Ends with"),
            ],
            "number": [
                ("is",           "Is exactly"),
                ("isNot",        "Is not"),
                ("contains",     "Contains"),
                ("notContains",  "Does not contain"),
                ("gt",           "Is greater than"),
                ("lt",           "Is less than"),
                ("inTheRange",   "Is between (range)"),
            ],
            "boolean": [
                ("is",    "Is"),
                ("isNot", "Is not"),
            ],
            "date": [
                ("is",            "Is exactly (date)"),
                ("isNot",         "Is not (date)"),
                ("before",        "Before a date"),
                ("after",         "After a date"),
                ("inTheLast",     "Within the last N days"),
                ("notInTheLast",  "Not within the last N days"),
                ("inTheRange",    "Between two dates"),
            ],
            "playlist": [
                ("inPlaylist",     "Is in playlist"),
                ("notInPlaylist",  "Is not in playlist"),
            ],
        }

        self.sort_options: List[Tuple[str, str]] = [
            ("random",      "Random (shuffle)"),
            ("title",       "Title"),
            ("album",       "Album"),
            ("artist",      "Artist"),
            ("albumartist", "Album Artist"),
            ("year",        "Year"),
            ("rating",      "Rating"),
            ("playcount",   "Play Count"),
            ("lastplayed",  "Last Played"),
            ("dateadded",   "Date Added"),
            ("duration",    "Duration"),
            ("bitrate",     "Bitrate"),
            ("genre",       "Genre"),
            ("bpm",         "BPM"),
            ("track",       "Track Number"),
            ("size",        "File Size"),
        ]

    # ── Output helpers ────────────────────────────────────────────────────────

    def out(self, text: str = "", style: str = "") -> None:
        if RICH_AVAILABLE and self.console:
            self.console.print(text, style=style)
        else:
            print(strip_markup(text))

    def rule(self, title: str = "") -> None:
        if RICH_AVAILABLE and self.console:
            self.console.print(Rule(f" {title} " if title else "", style="cyan"))
        else:
            print(f"\n{'─' * 60}")
            if title:
                print(f"  {title}")

    def banner(self) -> None:
        if RICH_AVAILABLE and self.console:
            self.console.print(Panel(
                "[bold cyan]Navidrome Smart Playlist Creator[/bold cyan]\n"
                "[dim]Generate .nsp files for Navidrome dynamic playlists[/dim]",
                border_style="cyan",
                padding=(1, 4),
            ))
        else:
            print("\n" + "=" * 60)
            print("  NAVIDROME SMART PLAYLIST CREATOR")
            print("=" * 60)

    def panel(self, content: str, title: str = "") -> None:
        if RICH_AVAILABLE and self.console:
            self.console.print(Panel(
                content,
                title=f"[bold cyan]{title}[/bold cyan]" if title else "",
                border_style="cyan",
                padding=(1, 2),
            ))
        else:
            print(f"\n{'=' * 60}")
            if title:
                print(f"  {strip_markup(title)}")
                print('=' * 60)
            print(strip_markup(content))
            print('=' * 60)

    def prompt(self, question: str, default: str = "") -> str:
        if RICH_AVAILABLE and self.console:
            return Prompt.ask(f"[bold]{question}[/bold]", default=default, console=self.console)
        suffix = f" [{default}]" if default else ""
        ans = input(f"{strip_markup(question)}{suffix}: ").strip()
        return ans if ans else default

    def confirm(self, question: str, default: bool = True) -> bool:
        if RICH_AVAILABLE and self.console:
            return Confirm.ask(f"[bold]{question}[/bold]", default=default, console=self.console)
        suffix = "Y/n" if default else "y/N"
        ans = input(f"{strip_markup(question)} [{suffix}]: ").strip().lower()
        return default if not ans else ans in ("y", "yes")

    def select_option(
        self,
        title: str,
        options: List[Tuple[Any, str]],
        allow_back: bool = False,
    ) -> Optional[Any]:
        """Show a numbered menu and return the chosen value, or None if user chose back."""
        while True:
            self.out()
            if RICH_AVAILABLE and self.console:
                self.console.print(f"[bold]{title}[/bold]")
                t = Table(show_header=False, box=None, padding=(0, 1, 0, 2))
                t.add_column(style="bold cyan", no_wrap=True, width=5)
                t.add_column()
                for i, (_, label) in enumerate(options, 1):
                    t.add_row(f"{i}.", label)
                if allow_back:
                    t.add_row("0.", "[dim]<- Cancel / Go back[/dim]")
                self.console.print(t)
            else:
                print(f"\n{strip_markup(title)}")
                for i, (_, label) in enumerate(options, 1):
                    print(f"  {i}. {strip_markup(label)}")
                if allow_back:
                    print("  0. <- Cancel / Go back")

            raw = self.prompt("Select", default="1")
            try:
                n = int(raw)
                if allow_back and n == 0:
                    return None
                if 1 <= n <= len(options):
                    return options[n - 1][0]
            except ValueError:
                pass
            self.out("[red]Invalid choice — please enter a number from the list.[/red]")

    # ── Config ────────────────────────────────────────────────────────────────

    def load_config(self) -> Optional[Path]:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    val = json.load(f).get("playlist_directory", "")
                    return Path(val) if val else None
            except Exception:
                pass
        return None

    def save_config(self, path: Path) -> None:
        with open(self.config_file, "w") as f:
            json.dump({"playlist_directory": str(path)}, f)

    def set_playlist_directory(self) -> None:
        self.rule("Save Directory")
        self.out(
            "\nThis is where your [cyan].nsp[/cyan] files will be written.\n"
            "It must be a folder that Navidrome can scan (inside your music library).\n"
        )
        if self.playlist_dir:
            self.out(f"[green]Current:[/green] {self.playlist_dir}\n")
            if not self.confirm("Change directory?", default=False):
                return

        while True:
            raw = self.prompt("Enter path")
            if not raw:
                self.out("[red]Path cannot be empty.[/red]")
                continue
            path = Path(raw).expanduser()
            if not path.exists():
                if self.confirm("Directory does not exist. Create it?", default=True):
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        self.out(f"[green]Created:[/green] {path}")
                    except Exception as e:
                        self.out(f"[red]Could not create directory: {e}[/red]")
                        continue
                else:
                    continue
            if not path.is_dir():
                self.out("[red]That path exists but is not a directory.[/red]")
                continue
            self.playlist_dir = path
            self.save_config(path)
            self.out(f"[green]Saved:[/green] {path}")
            break

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_number(raw: str) -> Any:
        """Parse as int if possible, otherwise float."""
        try:
            return int(raw)
        except ValueError:
            return float(raw)

    # ── Condition builder ─────────────────────────────────────────────────────

    def build_condition(self, depth: int = 0) -> Optional[Dict[str, Any]]:
        """Guide the user through building one rule or nested rule group.

        Back-navigation: cancel at field → back to category,
        cancel at operator → back to field, cancel at category → return None.
        """
        self.rule(f"{'Sub-' * depth}Add a Rule")

        while True:  # ── Category loop (back here = cancel to caller)
            cat_options: List[Tuple[str, str]] = [(c, c) for c in self.fields]
            cat_options.append(
                ("__group__", "[bold magenta]+ Nested rule group[/bold magenta]  [dim](sub-AND/OR)[/dim]")
            )
            category = self.select_option(
                "Choose a field category:",
                cat_options,
                allow_back=True,
            )
            if category is None:
                return None

            if category == "__group__":
                result = self._build_rule_group(depth + 1)
                if result is not None:
                    return result
                continue  # group cancelled → back to category list

            # ── Field loop (back → re-show categories)
            while True:
                field_entries = self.fields[str(category)]
                f_options: List[Tuple[str, str]] = [
                    (key, f"{desc}  [dim]({ftype})[/dim]")
                    for key, desc, ftype in field_entries
                ]
                field_key = self.select_option(
                    f"Choose a field  [dim][{category}][/dim]:",
                    f_options,
                    allow_back=True,
                )
                if field_key is None:
                    break  # back to category
                field_key = str(field_key)

                _, field_label, field_type = next(
                    (k, d, t) for k, d, t in field_entries if k == field_key
                )
                self.out(f"\n  [cyan]Field:[/cyan] {field_label}  [dim]({field_type})[/dim]")

                # ── Operator loop (back → re-show fields)
                while True:
                    op_entries = self.operators.get(field_type, self.operators["string"])
                    operator = self.select_option(
                        "Choose a condition:",
                        list(op_entries),
                        allow_back=True,
                    )
                    if operator is None:
                        break  # back to field
                    operator = str(operator)
                    op_label = next(d for k, d in op_entries if k == operator)
                    self.out(f"  [cyan]Condition:[/cyan] {field_label} -> {op_label}")

                    # ── Value (always completes)
                    value = self._prompt_value(field_key, field_label, field_type, operator)

                    condition = {operator: {field_key: value}}
                    self.out(f"\n[bold green]Rule added:[/bold green] [dim]{json.dumps(condition)}[/dim]")
                    return condition

                # Operator cancelled → back to field list
                continue

            # Field cancelled → back to category list
            continue

    def _build_rule_group(self, depth: int = 1) -> Optional[Dict[str, Any]]:
        """Build a nested rule group (sub-group with its own AND/OR logic)."""
        self.out(
            "\n[dim]A rule group lets you nest rules with their own AND/OR logic.\n"
            "For example: (artist is 'X' OR artist is 'Y') as part of a larger AND query.[/dim]\n"
        )
        logic = self.select_option(
            "Logic for this sub-group:",
            [
                ("all", "[bold]ALL[/bold] must match   [dim](AND)[/dim]"),
                ("any", "[bold]ANY[/bold] can match    [dim](OR)[/dim]"),
            ],
            allow_back=True,
        )
        if logic is None:
            return None
        logic = str(logic)

        result = self._manage_conditions_loop(logic, depth=depth, group=True)
        if not result:
            return None
        return {logic: result}

    def _prompt_value(self, field: str, label: str, ftype: str, operator: str) -> Any:
        """Prompt for a value with type-appropriate guidance."""

        if ftype == "boolean":
            result = self.select_option(
                f"Value for \"{label}\":",
                [("__true__", "Yes / True"), ("__false__", "No / False")],
            )
            return result == "__true__"

        if ftype == "playlist":
            self.out(
                "[dim]Enter the playlist ID from Navidrome.\n"
                "You can find it in the URL when viewing a playlist: /playlists/<ID>[/dim]"
            )
            return self.prompt("Playlist ID")

        if operator in ("inTheLast", "notInTheLast"):
            self.out("[dim]How many days back?  (e.g. 7 = last week · 30 = last month · 365 = last year)[/dim]")
            while True:
                raw = self.prompt("Days", default="30")
                try:
                    return int(raw)
                except ValueError:
                    self.out("[red]Please enter a whole number.[/red]")

        if operator == "inTheRange" and ftype == "number":
            self.out(f"[dim]Enter the start and end values for \"{label}\".[/dim]")
            while True:
                try:
                    return [self._parse_number(self.prompt("From")),
                            self._parse_number(self.prompt("To"))]
                except ValueError:
                    self.out("[red]Please enter valid numbers.[/red]")

        if operator == "inTheRange" and ftype == "date":
            self.out("[dim]Dates must be in YYYY-MM-DD format.[/dim]")
            return [
                self.prompt("From date", default="2020-01-01"),
                self.prompt("To date",   default="2025-12-31"),
            ]

        if ftype == "date":
            self.out("[dim]Format: YYYY-MM-DD  (e.g. 2024-06-15)[/dim]")
            return self.prompt("Date")

        if ftype == "number":
            hints = {
                "year":        "e.g. 1990",
                "rating":      "0 to 5",
                "playcount":   "e.g. 10",
                "bitrate":     "e.g. 320 for MP3, 900+ for lossless",
                "duration":    "in seconds  (e.g. 180 = 3 min)",
                "bpm":         "e.g. 120",
                "track":       "e.g. 1",
                "discnumber":  "e.g. 1",
                "size":        "in bytes  (e.g. 10000000 ~ 10 MB)",
                "channels":    "e.g. 2 for stereo",
                "bitdepth":    "e.g. 16, 24, 32",
            }
            if field in hints:
                self.out(f"[dim]{hints[field]}[/dim]")
            while True:
                raw = self.prompt(f"Value for \"{label}\"")
                try:
                    return self._parse_number(raw)
                except ValueError:
                    self.out("[red]Please enter a number.[/red]")

        # String
        examples = {
            "filetype":       "e.g. flac · mp3 · aac · ogg",
            "artist":         "e.g. Geto Boys",
            "albumartist":    "e.g. Geto Boys",
            "genre":          "e.g. Hip-Hop",
            "filepath":       "relative to music folder,  e.g. G/Geto Boys",
            "language":       "e.g. eng, fra, deu",
            "key":            "e.g. Cmaj, Amin",
            "releasetype":    "e.g. album, single, ep, compilation",
            "releasestatus":  "e.g. official, promotional, bootleg",
            "releasecountry": "e.g. US, GB, DE",
            "explicitstatus": "e.g. explicit, clean",
        }
        if field in examples:
            self.out(f"[dim]{examples[field]}[/dim]")
        return self.prompt(f"Value for \"{label}\"")

    def _show_conditions_summary(self, conditions: List[Dict], logic: str) -> None:
        if not conditions:
            return
        logic_label = "ALL must match" if logic == "all" else "ANY can match"
        lines = "\n".join(f"  {i}. {json.dumps(c)}" for i, c in enumerate(conditions, 1))
        self.panel(f"Logic: [bold]{logic_label}[/bold]\n\n{lines}", title="Rules so far")

    # ── Condition management helpers ─────────────────────────────────────────

    def _manage_conditions_loop(
        self,
        logic: str,
        depth: int = 0,
        group: bool = False,
    ) -> Optional[List[Dict[str, Any]]]:
        """Build a conditions list with add/remove/reorder support.

        Returns the completed list, or None if the user cancels with no conditions.
        """
        conditions: List[Dict[str, Any]] = []
        noun = "group" if group else "playlist"

        while True:
            if not conditions:
                condition = self.build_condition(depth)
                if condition:
                    conditions.append(condition)
                else:
                    if not self.confirm(
                        f"No rules added yet. Keep building this {noun}?", default=True
                    ):
                        return None
            else:
                self._show_conditions_summary(conditions, logic)
                action = self.select_option(
                    "What would you like to do?",
                    [
                        ("add",    "Add another rule"),
                        ("remove", f"Remove a rule  [dim]({len(conditions)} total)[/dim]"),
                        ("move",   "Reorder rules"),
                        ("done",   "[bold green]Done[/bold green] — finish adding rules"),
                    ],
                )
                action = str(action)
                if action == "done":
                    return conditions
                elif action == "remove":
                    self._remove_condition(conditions, logic)
                elif action == "move":
                    self._reorder_conditions(conditions, logic)
                elif action == "add":
                    condition = self.build_condition(depth)
                    if condition:
                        conditions.append(condition)

    def _remove_condition(self, conditions: List[Dict[str, Any]], logic: str) -> None:
        if not conditions:
            self.out("[yellow]No rules to remove.[/yellow]")
            return
        options = [
            (i, f"{i + 1}. {json.dumps(c)[:80]}{'...' if len(json.dumps(c)) > 80 else ''}")
            for i, c in enumerate(conditions)
        ]
        idx = self.select_option("Which rule do you want to remove?", options, allow_back=True)
        if idx is not None:
            removed = conditions.pop(int(str(idx)))
            self.out(f"[yellow]Removed rule {int(str(idx)) + 1}.[/yellow] [dim]{json.dumps(removed)[:60]}[/dim]")

    def _reorder_conditions(self, conditions: List[Dict[str, Any]], logic: str) -> None:
        if len(conditions) < 2:
            self.out("[yellow]Need at least 2 rules to reorder.[/yellow]")
            return
        options = [
            (i, f"{i + 1}. {json.dumps(c)[:70]}{'...' if len(json.dumps(c)) > 70 else ''}")
            for i, c in enumerate(conditions)
        ]
        idx = self.select_option("Which rule do you want to move?", options, allow_back=True)
        if idx is None:
            return
        idx = int(str(idx))
        move_options: List[Tuple[str, str]] = []
        if idx > 0:
            move_options.append(("up",   f"Move up    (swap with rule {idx})"))
        if idx < len(conditions) - 1:
            move_options.append(("down", f"Move down  (swap with rule {idx + 2})"))
        direction = self.select_option("Direction:", move_options, allow_back=True)
        if direction == "up":
            conditions[idx - 1], conditions[idx] = conditions[idx], conditions[idx - 1]
            self.out(f"[green]Moved to position {idx}.[/green]")
        elif direction == "down":
            conditions[idx], conditions[idx + 1] = conditions[idx + 1], conditions[idx]
            self.out(f"[green]Moved to position {idx + 2}.[/green]")

    def _edit_conditions(
        self, conditions: List[Dict[str, Any]], logic: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Interactively manage an existing conditions list.

        Returns the updated list, or None if the user cancels (discard changes).
        """
        working = list(conditions)
        while True:
            if working:
                self._show_conditions_summary(working, logic)
            else:
                self.out("[dim]No rules defined yet.[/dim]")
            action = self.select_option(
                "Manage rules:",
                [
                    ("add",    "Add a new rule"),
                    ("remove", f"Remove a rule  [dim]({len(working)} total)[/dim]"),
                    ("move",   "Reorder rules"),
                    ("done",   "[bold green]Done[/bold green]"),
                ],
                allow_back=True,
            )
            if action is None:
                return None
            action = str(action)
            if action == "add":
                condition = self.build_condition()
                if condition:
                    working.append(condition)
            elif action == "remove":
                self._remove_condition(working, logic)
            elif action == "move":
                self._reorder_conditions(working, logic)
            elif action == "done":
                return working

    # ── Playlist wizard ───────────────────────────────────────────────────────

    def create_smart_playlist(self) -> Optional[Dict[str, Any]]:
        playlist: Dict[str, Any] = {}

        # ── Logic (ALL / ANY)
        self.rule("Rule Logic")
        self.out(
            "\n[dim]When you have multiple rules, should [bold]ALL[/bold] of them match,\n"
            "or is it enough for just [bold]ANY ONE[/bold] to match?[/dim]"
        )
        logic: str = self.select_option(
            "Combine rules with:",
            [
                ("all", "[bold]ALL[/bold] must match   [dim](AND - more selective)[/dim]"),
                ("any", "[bold]ANY[/bold] can match    [dim](OR  - more inclusive)[/dim]"),
            ],
        )  # type: ignore
        logic = str(logic)

        # ── Conditions
        self.rule("Build Rules")
        self.out(
            "\n[dim]Rules decide which tracks are included. You need at least one.\n"
            "Choose a category to add a rule, or select 'Nested rule group' for sub-AND/OR logic.[/dim]\n"
        )
        result = self._manage_conditions_loop(logic, depth=0, group=False)
        if result is None:
            return None
        conditions = result

        playlist[logic] = conditions

        # ── Sorting
        self.rule("Sort Order")
        self.out("\n[dim]How should tracks be ordered in the playlist?[/dim]")

        sort_parts: List[str] = []
        while True:
            sort_key = self.select_option("Sort by:", self.sort_options)
            sort_key = str(sort_key)

            if sort_key == "random":
                sort_parts = ["random"]
                break

            direction = self.select_option(
                f"Direction for \"{sort_key}\":",
                [
                    ("asc",  "Ascending   [dim](oldest / lowest first)[/dim]"),
                    ("desc", "Descending  [dim](newest / highest first)[/dim]"),
                ],
            )
            direction = str(direction)
            prefix_char = "-" if direction == "desc" else "+"
            sort_parts.append(f"{prefix_char}{sort_key}")

            if not self.confirm("Add another sort field?", default=False):
                break

        if len(sort_parts) == 1:
            if sort_parts[0] == "random":
                playlist["sort"] = "random"
            else:
                field = sort_parts[0].lstrip("+-")
                is_desc = sort_parts[0].startswith("-")
                playlist["sort"] = field
                playlist["order"] = "desc" if is_desc else "asc"
        else:
            playlist["sort"] = ",".join(sort_parts)

        # ── Limit
        self.rule("Track Limit")
        if self.confirm("Limit the number of tracks in this playlist?", default=True):
            self.out("\n[dim]e.g. 50, 100, 500[/dim]")
            while True:
                raw = self.prompt("Max tracks", default="100")
                try:
                    playlist["limit"] = int(raw)
                    break
                except ValueError:
                    self.out("[red]Please enter a whole number.[/red]")

        # ── Name & description (at the end so you know what the playlist does)
        self.rule("Playlist Details")
        self.out("\n[dim]Now that you've built your rules, give the playlist a name.[/dim]")
        name = self.prompt("Name", default="My Smart Playlist")
        if name:
            playlist["name"] = name

        self.out("\n[dim]Optional: a short description (press Enter to skip).[/dim]")
        comment = self.prompt("Description", default="")
        if comment:
            playlist["comment"] = comment

        return playlist

    # ── "This is ..." playlist ────────────────────────────────────────────────

    def create_this_is_playlist(self) -> None:
        """Interactive builder for artist-focused 'This is ...' playlists."""
        self.rule('Create a "This is ..." Playlist')
        self.out(
            '\n[dim]Build a smart playlist centred on a single album artist — similar\n'
            'to Spotify\'s "This is ..." playlists but with full control over\n'
            'track selection, sort order, and limits.[/dim]\n'
        )

        # ── Artist name
        artist = self.prompt("Album artist name").strip()
        if not artist:
            self.out("[yellow]No artist entered — cancelled.[/yellow]")
            return

        # ── Generation method
        self.rule("Generation Method")
        self.out(
            f'\n[dim]How should tracks be chosen for "This is {artist}"?[/dim]'
        )

        method = self.select_option(
            "Pick a generation method:",
            [
                ("random",          "Random selection — a shuffled mix"),
                ("top_rated",       "Top rated — highest-rated tracks first"),
                ("most_played",     "Most played — sort by play count"),
                ("recently_played", "Recently played — tracks you\'ve been listening to"),
                ("recently_added",  "Recently added — newest additions first"),
                ("loved",           "Loved tracks only — just your favourites"),
                ("deep_cuts",       "Deep cuts — skip the obvious hits (track 4+)"),
                ("greatest_hits",   "Greatest hits — loved OR rated 4+ OR played 10+"),
                ("chronological",   "Chronological — every track by release year"),
                ("reverse_chrono",  "Reverse chronological — newest releases first"),
                ("longest",         "Longest tracks — epic deep listens"),
                ("shortest",        "Shortest tracks — quick-fire hits"),
                ("high_energy",     "High energy — highest BPM first"),
                ("chill",           "Chill — lowest BPM first"),
                ("lossless_only",   "Lossless only — FLAC / hi-res tracks"),
                ("unplayed",        "Unplayed — tracks you haven\'t heard yet"),
                ("rare_gems",       "Rare gems — low play count but high rating"),
                ("album_openers",   "Album openers — track 1 from every album"),
                ("album_closers",   "Album closers — the last tracks on each album"),
                ("singles",         "Singles — short tracks from early in the album"),
            ],
            allow_back=True,
        )
        if method is None:
            return
        method = str(method)

        # ── Build the playlist dict based on method
        playlist: Dict[str, Any] = {}
        conditions: List[Dict[str, Any]] = []

        # Base condition: match the album artist
        artist_condition = {"is": {"albumartist": artist}}

        if method == "random":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "random"

        elif method == "top_rated":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "rating"
            playlist["order"] = "desc"

        elif method == "most_played":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "playcount"
            playlist["order"] = "desc"

        elif method == "recently_played":
            conditions.append(artist_condition)
            conditions.append({"inTheLast": {"lastplayed": 90}})
            playlist["all"] = conditions
            playlist["sort"] = "lastplayed"
            playlist["order"] = "desc"

        elif method == "recently_added":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "dateadded"
            playlist["order"] = "desc"

        elif method == "loved":
            conditions.append(artist_condition)
            conditions.append({"is": {"loved": True}})
            playlist["all"] = conditions
            playlist["sort"] = "random"

        elif method == "deep_cuts":
            conditions.append(artist_condition)
            conditions.append({"gt": {"track": 3}})
            playlist["all"] = conditions
            playlist["sort"] = "random"

        elif method == "greatest_hits":
            conditions.append(artist_condition)
            conditions.append(
                {"any": [
                    {"is": {"loved": True}},
                    {"gt": {"rating": 3}},
                    {"gt": {"playcount": 9}},
                ]}
            )
            playlist["all"] = conditions
            playlist["sort"] = "playcount"
            playlist["order"] = "desc"

        elif method == "chronological":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "+year,+discnumber,+track"

        elif method == "reverse_chrono":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "-year,+discnumber,+track"

        elif method == "longest":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "duration"
            playlist["order"] = "desc"

        elif method == "shortest":
            conditions.append(artist_condition)
            playlist["all"] = conditions
            playlist["sort"] = "duration"
            playlist["order"] = "asc"

        elif method == "high_energy":
            conditions.append(artist_condition)
            conditions.append({"gt": {"bpm": 0}})
            playlist["all"] = conditions
            playlist["sort"] = "bpm"
            playlist["order"] = "desc"

        elif method == "chill":
            conditions.append(artist_condition)
            conditions.append({"gt": {"bpm": 0}})
            playlist["all"] = conditions
            playlist["sort"] = "bpm"
            playlist["order"] = "asc"

        elif method == "lossless_only":
            conditions.append(artist_condition)
            conditions.append({"is": {"filetype": "flac"}})
            playlist["all"] = conditions
            playlist["sort"] = "+year,+discnumber,+track"

        elif method == "unplayed":
            conditions.append(artist_condition)
            conditions.append({"is": {"playcount": 0}})
            playlist["all"] = conditions
            playlist["sort"] = "random"

        elif method == "rare_gems":
            conditions.append(artist_condition)
            conditions.append({"gt": {"rating": 3}})
            conditions.append({"lt": {"playcount": 5}})
            playlist["all"] = conditions
            playlist["sort"] = "rating"
            playlist["order"] = "desc"

        elif method == "album_openers":
            conditions.append(artist_condition)
            conditions.append({"is": {"track": 1}})
            playlist["all"] = conditions
            playlist["sort"] = "+year,+album"

        elif method == "album_closers":
            conditions.append(artist_condition)
            conditions.append({"gt": {"track": 8}})
            conditions.append({"gt": {"duration": 180}})
            playlist["all"] = conditions
            playlist["sort"] = "+year,+album"

        elif method == "singles":
            conditions.append(artist_condition)
            conditions.append({"lt": {"track": 4}})
            conditions.append({"lt": {"duration": 270}})
            playlist["all"] = conditions
            playlist["sort"] = "playcount"
            playlist["order"] = "desc"

        # ── Customise sort order?
        self.rule("Sort Order")
        self.out(
            f'\n[dim]Default sort: [cyan]{playlist.get("sort", "random")}[/cyan]'
            f'{" " + playlist.get("order", "") if "order" in playlist else ""}[/dim]'
        )
        if self.confirm("Change the sort order?", default=False):
            sort_parts: List[str] = []
            while True:
                sort_key = self.select_option("Sort by:", self.sort_options)
                sort_key = str(sort_key)

                if sort_key == "random":
                    sort_parts = ["random"]
                    break

                direction = self.select_option(
                    f'Direction for "{sort_key}":',
                    [
                        ("asc",  "Ascending   [dim](oldest / lowest first)[/dim]"),
                        ("desc", "Descending  [dim](newest / highest first)[/dim]"),
                    ],
                )
                direction = str(direction)
                prefix_char = "-" if direction == "desc" else "+"
                sort_parts.append(f"{prefix_char}{sort_key}")

                if not self.confirm("Add another sort field?", default=False):
                    break

            # Remove existing sort/order before re-setting
            playlist.pop("sort", None)
            playlist.pop("order", None)

            if len(sort_parts) == 1:
                if sort_parts[0] == "random":
                    playlist["sort"] = "random"
                else:
                    field = sort_parts[0].lstrip("+-")
                    is_desc = sort_parts[0].startswith("-")
                    playlist["sort"] = field
                    playlist["order"] = "desc" if is_desc else "asc"
            else:
                playlist["sort"] = ",".join(sort_parts)

        # ── Track limit
        self.rule("Track Limit")
        default_limit = "50"
        self.out(
            f'\n[dim]How many tracks should the playlist contain? (default: {default_limit})[/dim]'
        )
        while True:
            raw = self.prompt("Max tracks", default=default_limit)
            try:
                limit = int(raw)
                if limit > 0:
                    playlist["limit"] = limit
                    break
                self.out("[red]Please enter a positive number.[/red]")
            except ValueError:
                self.out("[red]Please enter a whole number.[/red]")

        # ── Finalise
        default_name = f"This is {artist}"
        method_labels = {
            "random": "shuffled mix",
            "top_rated": "top rated",
            "most_played": "most played",
            "recently_played": "recently played",
            "recently_added": "recently added",
            "loved": "loved tracks",
            "deep_cuts": "deep cuts",
            "greatest_hits": "greatest hits",
            "chronological": "chronological",
            "reverse_chrono": "reverse chronological",
            "longest": "longest tracks",
            "shortest": "shortest tracks",
            "high_energy": "high energy",
            "chill": "chill",
            "lossless_only": "lossless only",
            "unplayed": "unplayed",
            "rare_gems": "rare gems",
            "album_openers": "album openers",
            "album_closers": "album closers",
            "singles": "singles",
        }
        method_desc = method_labels.get(method, method)
        default_comment = f"A \"This is {artist}\" playlist — {method_desc}"

        # Allow renaming
        self.rule("Playlist Details")
        name = self.prompt("Playlist name", default=default_name)
        playlist["name"] = name

        comment = self.prompt("Description", default=default_comment)
        if comment:
            playlist["comment"] = comment

        # ── Preview & save
        self.preview_and_save(playlist)

    # ── Save ──────────────────────────────────────────────────────────────────

    def preview_and_save(self, playlist: Dict[str, Any]) -> None:
        self.rule("Preview")
        self.panel(json.dumps(playlist, indent=2), title="Generated Playlist JSON")

        if not self.confirm("\nSave this playlist?", default=True):
            self.out("[yellow]Discarded — nothing was saved.[/yellow]")
            return

        if not self.playlist_dir:
            self.out("[red]No save directory configured. Please set one first.[/red]")
            return

        default_name = "".join(
            c for c in playlist.get("name", "playlist").lower().replace(" ", "-")
            if c.isalnum() or c in "-_"
        ) or "playlist"
        self.out("\n[dim]Choose a filename (the .nsp extension will be added automatically).[/dim]")
        filename = self.prompt("Filename", default=default_name)
        if not filename.endswith(".nsp"):
            filename += ".nsp"

        filepath = self.playlist_dir / filename
        if filepath.exists():
            if not self.confirm(f"[yellow]{filename}[/yellow] already exists. Overwrite?", default=False):
                self.out("[yellow]Save cancelled.[/yellow]")
                return

        try:
            with open(filepath, "w") as f:
                json.dump(playlist, f, indent=2)
            self.out(f"\n[bold green]Saved to:[/bold green] {filepath}")
        except Exception as e:
            self.out(f"[red]Could not save: {e}[/red]")

    # ── Manage deployed playlists ─────────────────────────────────────────────

    def list_deployed_playlists(self) -> None:
        """Interactively list, preview, edit, and delete deployed .nsp files."""
        self.rule("Manage Deployed Playlists")
        while True:
            if not self.playlist_dir or not self.playlist_dir.exists():
                self.out("[red]Save directory not found.[/red]")
                return
            nsp_files = sorted(self.playlist_dir.glob("*.nsp"))
            if not nsp_files:
                self.out(f"[yellow]No .nsp files found in {self.playlist_dir}[/yellow]")
                return
            options: List[Tuple[Any, str]] = []
            for f in nsp_files:
                try:
                    with open(f) as fp:
                        name = json.load(fp).get("name", f.stem)
                except Exception:
                    name = "(unreadable)"
                options.append((f, f"{f.name}  [dim]— {name}[/dim]"))
            filepath = self.select_option(
                f"[cyan]{self.playlist_dir}[/cyan]  "
                f"({len(nsp_files)} playlist{'s' if len(nsp_files) != 1 else ''}):",
                options,
                allow_back=True,
            )
            if filepath is None:
                return
            try:
                with open(filepath, "r") as fp:
                    data = json.load(fp)
            except Exception as e:
                self.out(f"[red]Could not read {filepath.name}: {e}[/red]")
                continue
            self.panel(json.dumps(data, indent=2), title=data.get("name", filepath.stem))
            action = self.select_option(
                "Action:",
                [
                    ("edit",   "Edit this playlist"),
                    ("delete", "[red]Delete this file[/red]"),
                ],
                allow_back=True,
            )
            if action == "edit":
                self._edit_playlist_file(filepath, data)
            elif action == "delete":
                if self.confirm(
                    f"[bold red]Permanently delete[/bold red] [yellow]{filepath.name}[/yellow]?",
                    default=False,
                ):
                    try:
                        filepath.unlink()
                        self.out(f"[green]Deleted:[/green] {filepath.name}")
                    except Exception as e:
                        self.out(f"[red]Could not delete: {e}[/red]")

    def _edit_playlist_file(self, filepath: Path, data: Dict[str, Any]) -> None:
        """Edit a loaded .nsp playlist interactively and save it."""
        playlist: Dict[str, Any] = json.loads(json.dumps(data))  # deep copy via round-trip
        while True:
            logic = "all" if "all" in playlist else ("any" if "any" in playlist else "all")
            if logic not in playlist:
                playlist[logic] = []
            conditions: List[Dict[str, Any]] = playlist[logic]

            self.rule(f"Editing: {filepath.name}")
            self.panel(json.dumps(playlist, indent=2), title=playlist.get("name", filepath.stem))

            action = self.select_option(
                "What would you like to edit?",
                [
                    ("name",    f"Name         [dim]{playlist.get('name', '')}[/dim]"),
                    ("comment", f"Description  [dim]{playlist.get('comment', '')}[/dim]"),
                    ("logic",   f"Rule logic   [dim]{logic.upper()} — {len(conditions)} rule(s)[/dim]"),
                    ("rules",   "Manage rules  [dim](add / remove / reorder)[/dim]"),
                    ("sort",    f"Sort order   [dim]{playlist.get('sort', '')} {playlist.get('order', '')}[/dim]"),
                    ("limit",   f"Track limit  [dim]{playlist.get('limit', 'none')}[/dim]"),
                    ("save",    "[bold green]Preview & save[/bold green]"),
                ],
                allow_back=True,
            )
            if action is None:
                if self.confirm("Discard changes and go back?", default=False):
                    return
                continue
            action = str(action)

            if action == "name":
                name = self.prompt("Name", default=playlist.get("name", ""))
                if name:
                    playlist["name"] = name

            elif action == "comment":
                comment = self.prompt("Description", default=playlist.get("comment", ""))
                if comment:
                    playlist["comment"] = comment
                elif "comment" in playlist and self.confirm("Remove description?", default=False):
                    del playlist["comment"]

            elif action == "logic":
                new_logic = self.select_option(
                    "Rule logic:",
                    [
                        ("all", "[bold]ALL[/bold] must match  [dim](AND)[/dim]"),
                        ("any", "[bold]ANY[/bold] can match   [dim](OR)[/dim]"),
                    ],
                )
                new_logic = str(new_logic)
                if new_logic != logic:
                    playlist[new_logic] = playlist.pop(logic)

            elif action == "rules":
                updated = self._edit_conditions(list(conditions), logic)
                if updated is not None:
                    playlist[logic] = updated

            elif action == "sort":
                sort_parts: List[str] = []
                while True:
                    sort_key = self.select_option("Sort by:", self.sort_options)
                    sort_key = str(sort_key)
                    if sort_key == "random":
                        sort_parts = ["random"]
                        break
                    direction = self.select_option(
                        f'Direction for "{sort_key}":',
                        [
                            ("asc",  "Ascending   [dim](oldest / lowest first)[/dim]"),
                            ("desc", "Descending  [dim](newest / highest first)[/dim]"),
                        ],
                    )
                    prefix_char = "-" if str(direction) == "desc" else "+"
                    sort_parts.append(f"{prefix_char}{sort_key}")
                    if not self.confirm("Add another sort field?", default=False):
                        break
                playlist.pop("sort", None)
                playlist.pop("order", None)
                if len(sort_parts) == 1:
                    if sort_parts[0] == "random":
                        playlist["sort"] = "random"
                    else:
                        field = sort_parts[0].lstrip("+-")
                        playlist["sort"] = field
                        playlist["order"] = "desc" if sort_parts[0].startswith("-") else "asc"
                else:
                    playlist["sort"] = ",".join(sort_parts)

            elif action == "limit":
                if self.confirm("Set a track limit?", default="limit" in playlist):
                    while True:
                        raw = self.prompt("Max tracks", default=str(playlist.get("limit", 100)))
                        try:
                            playlist["limit"] = int(raw)
                            break
                        except ValueError:
                            self.out("[red]Please enter a whole number.[/red]")
                elif "limit" in playlist:
                    del playlist["limit"]

            elif action == "save":
                self.panel(json.dumps(playlist, indent=2), title="Updated Playlist JSON")
                save_choice = self.select_option(
                    "Save where?",
                    [
                        ("same", f"Overwrite [cyan]{filepath.name}[/cyan]"),
                        ("new",  "Save as a new file"),
                    ],
                    allow_back=True,
                )
                if save_choice == "same":
                    try:
                        with open(filepath, "w") as fp:
                            json.dump(playlist, fp, indent=2)
                        self.out(f"[bold green]Saved:[/bold green] {filepath}")
                        return
                    except Exception as e:
                        self.out(f"[red]Could not save: {e}[/red]")
                elif save_choice == "new":
                    self.preview_and_save(playlist)
                    return

    def list_deployed_cli(self) -> None:
        """Non-interactive: print deployed .nsp files to stdout."""
        if not self.playlist_dir or not self.playlist_dir.exists():
            print(
                "Error: no save directory configured (use --output to set one).",
                file=sys.stderr,
            )
            sys.exit(1)
        nsp_files = sorted(self.playlist_dir.glob("*.nsp"))
        if not nsp_files:
            print(f"No .nsp files in {self.playlist_dir}")
            return
        print(f"Deployed playlists in {self.playlist_dir}:")
        for f in nsp_files:
            try:
                with open(f) as fp:
                    name = json.load(fp).get("name", f.stem)
                print(f"  {f.name:<40}  {name}")
            except Exception:
                print(f"  {f.name:<40}  (unreadable)")

    def deploy_preset_by_name(self, slug: str) -> None:
        """Non-interactive: deploy a preset by its filename slug."""
        if not self.playlist_dir:
            print(
                "Error: no save directory configured. Use --output to set one.",
                file=sys.stderr,
            )
            sys.exit(1)
        matches = [
            (label, filename, preset)
            for label, filename, _, preset in self.PRESETS
            if filename == slug
        ]
        if not matches:
            print(f"Error: no preset found with slug '{slug}'.", file=sys.stderr)
            print("Run without arguments to browse available presets.", file=sys.stderr)
            sys.exit(1)
        label, filename, preset = matches[0]
        self._save_preset(filename, preset)

    # ── Examples ─────────────────────────────────────────────────────────────

    def show_examples(self) -> None:
        examples = [
            ("Recently Played", {
                "name": "Recently Played",
                "comment": "Tracks played in the last 30 days",
                "all": [{"inTheLast": {"lastplayed": 30}}],
                "sort": "lastplayed", "order": "desc", "limit": 100,
            }),
            ("80s Favorites (nested logic)", {
                "name": "80s Favorites",
                "comment": "Loved or highly-rated songs from the 1980s",
                "all": [
                    {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
                    {"inTheRange": {"year": [1980, 1989]}},
                ],
                "sort": "year", "order": "desc", "limit": 50,
            }),
            ("High Quality (FLAC)", {
                "name": "High Quality",
                "comment": "Lossless tracks only",
                "all": [{"gt": {"bitrate": 900}}, {"is": {"filetype": "flac"}}],
                "sort": "random", "limit": 200,
            }),
            ("Loved Tracks", {
                "name": "Loved",
                "all": [{"is": {"loved": True}}],
                "sort": "dateloved", "order": "desc", "limit": 500,
            }),
            ("Never Played", {
                "name": "Never Played",
                "comment": "Tracks you haven't played yet",
                "all": [{"is": {"playcount": 0}}],
                "sort": "random", "limit": 200,
            }),
            ("Multi-sort Example", {
                "name": "By Artist then Year",
                "comment": "Sorted by artist ascending, then year descending",
                "all": [{"gt": {"playcount": -1}}],
                "sort": "+artist,-year",
            }),
        ]
        self.rule("Example Playlists")
        for title, data in examples:
            self.out(f"\n[bold yellow]{title}[/bold yellow]")
            self.out(json.dumps(data, indent=2))
        self.out()

    def show_all_fields(self) -> None:
        self.rule("Available Fields")
        if RICH_AVAILABLE and self.console:
            for category, entries in self.fields.items():
                t = Table(title=category, show_header=True, header_style="bold magenta", box=None)
                t.add_column("Field",       style="cyan", width=30)
                t.add_column("Description", style="white")
                t.add_column("Type",        style="dim",  width=10)
                for key, desc, ftype in entries:
                    t.add_row(key, desc, ftype)
                self.console.print(t)
                self.console.print()
        else:
            for category, entries in self.fields.items():
                print(f"\n{category}:")
                for key, desc, ftype in entries:
                    print(f"  {key:<30} {desc} ({ftype})")

    # ── Presets ─────────────────────────────────────────────────────────────

    PRESETS: List[Tuple[str, str, str, Dict[str, Any]]] = [
        # (menu_label, filename, category, playlist_dict)

        # ── Essentials ─────────────────────────────────────────────────
        ("Recently Played", "recently-played", "Essentials", {
            "name": "Recently Played",
            "comment": "Tracks played in the last 30 days",
            "all": [{"inTheLast": {"lastplayed": 30}}],
            "sort": "lastplayed", "order": "desc", "limit": 100,
        }),
        ("Recently Added", "recently-added", "Essentials", {
            "name": "Recently Added",
            "comment": "Tracks added to the library in the last 30 days",
            "all": [{"inTheLast": {"dateadded": 30}}],
            "sort": "dateadded", "order": "desc", "limit": 200,
        }),
        ("Most Played", "most-played", "Essentials", {
            "name": "Most Played",
            "comment": "Your top 100 most-played tracks of all time",
            "all": [{"gt": {"playcount": 0}}],
            "sort": "playcount", "order": "desc", "limit": 100,
        }),
        ("Never Played", "never-played", "Essentials", {
            "name": "Never Played",
            "comment": "Tracks you haven't listened to yet",
            "all": [{"is": {"playcount": 0}}],
            "sort": "random", "limit": 200,
        }),
        ("Loved Tracks", "loved-tracks", "Essentials", {
            "name": "Loved Tracks",
            "comment": "All your favourited tracks, newest first",
            "all": [{"is": {"loved": True}}],
            "sort": "dateloved", "order": "desc", "limit": 500,
        }),
        ("Top Rated", "top-rated", "Essentials", {
            "name": "Top Rated",
            "comment": "Tracks rated 4 stars or higher",
            "all": [{"gt": {"rating": 3}}],
            "sort": "rating", "order": "desc", "limit": 200,
        }),

        # ── Discovery ──────────────────────────────────────────────────
        ("Fresh Blood", "fresh-blood", "Discovery", {
            "name": "Fresh Blood",
            "comment": "Added in the last 7 days and never played — your unheard new arrivals",
            "all": [
                {"inTheLast": {"dateadded": 7}},
                {"is": {"playcount": 0}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Vinyl Roulette", "vinyl-roulette", "Discovery", {
            "name": "Vinyl Roulette",
            "comment": "50 completely random tracks — spin the wheel",
            "all": [{"gt": {"duration": 0}}],
            "sort": "random", "limit": 50,
        }),
        ("One-Hit Wonders", "one-hit-wonders", "Discovery", {
            "name": "One-Hit Wonders",
            "comment": "Tracks you've played exactly once — give them a second chance",
            "all": [{"is": {"playcount": 1}}],
            "sort": "random", "limit": 100,
        }),
        ("Album Openers", "album-openers", "Discovery", {
            "name": "Album Openers",
            "comment": "Track 1 from every album — first impressions only",
            "all": [{"is": {"track": 1}}],
            "sort": "random", "limit": 100,
        }),

        # ── Rediscovery ────────────────────────────────────────────────
        ("Forgotten Gems", "forgotten-gems", "Rediscovery", {
            "name": "Forgotten Gems",
            "comment": "Loved or highly-rated tracks you haven't played in 6+ months",
            "all": [
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
                {"notInTheLast": {"lastplayed": 180}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Comebacks", "comebacks", "Rediscovery", {
            "name": "Comebacks",
            "comment": "Played 5+ times but not in the last 6 months — old favourites gathering dust",
            "all": [
                {"gt": {"playcount": 4}},
                {"notInTheLast": {"lastplayed": 180}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Buried Treasure", "buried-treasure", "Rediscovery", {
            "name": "Buried Treasure",
            "comment": "Added over a year ago and never played — lost in the stacks",
            "all": [
                {"notInTheLast": {"dateadded": 365}},
                {"is": {"playcount": 0}},
            ],
            "sort": "random", "limit": 100,
        }),

        # ── Moods & Vibes ──────────────────────────────────────────────
        ("Long Drives", "long-drives", "Moods & Vibes", {
            "name": "Long Drives",
            "comment": "Epic tracks over 6 minutes — settle in for the ride",
            "all": [{"gt": {"duration": 360}}],
            "sort": "duration", "order": "desc", "limit": 100,
        }),
        ("Short & Sweet", "short-and-sweet", "Moods & Vibes", {
            "name": "Short & Sweet",
            "comment": "Quick hits under 3 minutes",
            "all": [{"lt": {"duration": 180}}],
            "sort": "random", "limit": 100,
        }),
        ("Deep Cuts", "deep-cuts", "Moods & Vibes", {
            "name": "Deep Cuts",
            "comment": "Tracks 5+ on the album — beyond the singles",
            "all": [{"gt": {"track": 4}}],
            "sort": "random", "limit": 100,
        }),
        ("Slow Burners", "slow-burners", "Moods & Vibes", {
            "name": "Slow Burners",
            "comment": "Tracks under 100 BPM — chill, downtempo, mellow",
            "all": [
                {"lt": {"bpm": 100}},
                {"gt": {"bpm": 0}},
            ],
            "sort": "bpm", "order": "asc", "limit": 100,
        }),
        ("Bangers Only", "bangers-only", "Moods & Vibes", {
            "name": "Bangers Only",
            "comment": "High-energy tracks over 140 BPM",
            "all": [{"gt": {"bpm": 140}}],
            "sort": "bpm", "order": "desc", "limit": 100,
        }),

        # ── Quality & Format ──────────────────────────────────────────
        ("FLAC Attack", "flac-attack", "Quality & Format", {
            "name": "FLAC Attack",
            "comment": "Lossless FLAC files only — audiophile approved",
            "all": [{"is": {"filetype": "flac"}}],
            "sort": "random", "limit": 200,
        }),
        ("Hi-Res Audio", "hi-res-audio", "Quality & Format", {
            "name": "Hi-Res Audio",
            "comment": "24-bit or higher — studio master quality",
            "all": [{"gt": {"bitdepth": 16}}],
            "sort": "random", "limit": 200,
        }),
        ("Lossy Leftovers", "lossy-leftovers", "Quality & Format", {
            "name": "Lossy Leftovers",
            "comment": "Tracks under 320kbps — candidates for upgrade",
            "all": [{"lt": {"bitrate": 320}}],
            "sort": "+artist,+album,+track",
        }),

        # ── Decades ───────────────────────────────────────────────────
        ("60s Classics", "60s-classics", "Decades", {
            "name": "60s Classics",
            "comment": "Everything from 1960–1969",
            "all": [{"inTheRange": {"year": [1960, 1969]}}],
            "sort": "random", "limit": 200,
        }),
        ("70s Classics", "70s-classics", "Decades", {
            "name": "70s Classics",
            "comment": "Everything from 1970–1979",
            "all": [{"inTheRange": {"year": [1970, 1979]}}],
            "sort": "random", "limit": 200,
        }),
        ("80s Classics", "80s-classics", "Decades", {
            "name": "80s Classics",
            "comment": "Everything from 1980–1989",
            "all": [{"inTheRange": {"year": [1980, 1989]}}],
            "sort": "random", "limit": 200,
        }),
        ("90s Classics", "90s-classics", "Decades", {
            "name": "90s Classics",
            "comment": "Everything from 1990–1999",
            "all": [{"inTheRange": {"year": [1990, 1999]}}],
            "sort": "random", "limit": 200,
        }),
        ("2000s Classics", "2000s-classics", "Decades", {
            "name": "2000s Classics",
            "comment": "Everything from 2000–2009",
            "all": [{"inTheRange": {"year": [2000, 2009]}}],
            "sort": "random", "limit": 200,
        }),
        ("2010s Classics", "2010s-classics", "Decades", {
            "name": "2010s Classics",
            "comment": "Everything from 2010–2019",
            "all": [{"inTheRange": {"year": [2010, 2019]}}],
            "sort": "random", "limit": 200,
        }),

        # ── Complex / Nested ──────────────────────────────────────────
        ("80s Gold", "80s-gold", "Complex / Nested", {
            "name": "80s Gold",
            "comment": "Loved or highly-rated tracks from the 1980s (nested logic)",
            "all": [
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
                {"inTheRange": {"year": [1980, 1989]}},
            ],
            "sort": "year", "order": "desc", "limit": 50,
        }),
        ("The Collector", "the-collector", "Complex / Nested", {
            "name": "The Collector",
            "comment": "Played 10+ times AND (loved OR rated 4+) — your true obsessions",
            "all": [
                {"gt": {"playcount": 9}},
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
            ],
            "sort": "playcount", "order": "desc",
        }),
        ("Guilty Pleasures", "guilty-pleasures", "Complex / Nested", {
            "name": "Guilty Pleasures",
            "comment": "High play count but never loved or rated — your secret shames",
            "all": [
                {"gt": {"playcount": 5}},
                {"isNot": {"loved": True}},
                {"is": {"rating": 0}},
            ],
            "sort": "playcount", "order": "desc", "limit": 100,
        }),
        ("Compilation Cuts", "compilation-cuts", "Complex / Nested", {
            "name": "Compilation Cuts",
            "comment": "Tracks from compilation albums you've loved or played often",
            "all": [
                {"is": {"compilation": True}},
                {"any": [{"is": {"loved": True}}, {"gt": {"playcount": 3}}]},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Peak Album Experience", "peak-album-experience", "Complex / Nested", {
            "name": "Peak Album Experience",
            "comment": "Loved tracks from their original disc 1, ordered by album then track",
            "all": [
                {"is": {"loved": True}},
                {"is": {"discnumber": 1}},
            ],
            "sort": "+albumartist,+album,+track",
        }),
        ("The Graveyard", "the-graveyard", "Complex / Nested", {
            "name": "The Graveyard",
            "comment": "Tracks added over 2 years ago, played once or never, and not loved — do they deserve to stay?",
            "all": [
                {"notInTheLast": {"dateadded": 730}},
                {"lt": {"playcount": 2}},
                {"isNot": {"loved": True}},
            ],
            "sort": "dateadded", "order": "asc", "limit": 200,
        }),

        # ── Decades (additional) ─────────────────────────────────────
        ("Pre-1960 Vintage", "pre-1960-vintage", "Decades", {
            "name": "Pre-1960 Vintage",
            "comment": "Music from before 1960 — the golden oldies",
            "all": [{"lt": {"year": 1960}}, {"gt": {"year": 0}}],
            "sort": "year", "order": "asc", "limit": 200,
        }),
        ("2020s Fresh", "2020s-fresh", "Decades", {
            "name": "2020s Fresh",
            "comment": "Everything from 2020 onwards — the latest era",
            "all": [{"gt": {"year": 2019}}],
            "sort": "random", "limit": 200,
        }),
        ("Turn of the Century", "turn-of-the-century", "Decades", {
            "name": "Turn of the Century",
            "comment": "Music from 1998-2002 — straddling the millennium",
            "all": [{"inTheRange": {"year": [1998, 2002]}}],
            "sort": "random", "limit": 200,
        }),

        # ── Eras ──────────────────────────────────────────────────────
        ("British Invasion", "british-invasion", "Eras", {
            "name": "British Invasion",
            "comment": "1963-1966 — when Britain conquered the airwaves",
            "all": [{"inTheRange": {"year": [1963, 1966]}}],
            "sort": "random", "limit": 200,
        }),
        ("Summer of Love", "summer-of-love", "Eras", {
            "name": "Summer of Love",
            "comment": "1967 — peace, love, and psychedelia",
            "all": [{"is": {"year": 1967}}],
            "sort": "random", "limit": 200,
        }),
        ("Punk '77", "punk-77", "Eras", {
            "name": "Punk '77",
            "comment": "1977 — the year punk broke",
            "all": [{"is": {"year": 1977}}],
            "sort": "random", "limit": 200,
        }),
        ("MTV Generation", "mtv-generation", "Eras", {
            "name": "MTV Generation",
            "comment": "1981-1992 — I want my MTV",
            "all": [{"inTheRange": {"year": [1981, 1992]}}],
            "sort": "random", "limit": 200,
        }),
        ("Grunge Era", "grunge-era", "Eras", {
            "name": "Grunge Era",
            "comment": "1991-1994 — flannel shirts and distortion pedals",
            "all": [{"inTheRange": {"year": [1991, 1994]}}],
            "sort": "random", "limit": 200,
        }),
        ("Y2K Era", "y2k-era", "Eras", {
            "name": "Y2K Era",
            "comment": "1999-2003 — millennium madness and nu-metal",
            "all": [{"inTheRange": {"year": [1999, 2003]}}],
            "sort": "random", "limit": 200,
        }),
        ("Disco Fever", "disco-fever", "Eras", {
            "name": "Disco Fever",
            "comment": "1975-1980 — mirror balls and platform shoes",
            "all": [{"inTheRange": {"year": [1975, 1980]}}],
            "sort": "random", "limit": 200,
        }),
        ("New Wave", "new-wave", "Eras", {
            "name": "New Wave",
            "comment": "1978-1985 — synths, sharp suits, and angular guitars",
            "all": [{"inTheRange": {"year": [1978, 1985]}}],
            "sort": "random", "limit": 200,
        }),
        ("Golden Age Hip-Hop", "golden-age-hip-hop", "Eras", {
            "name": "Golden Age Hip-Hop",
            "comment": "1986-1996 — the boom-bap golden era",
            "all": [{"inTheRange": {"year": [1986, 1996]}}],
            "sort": "random", "limit": 200,
        }),
        ("Britpop", "britpop", "Eras", {
            "name": "Britpop",
            "comment": "1993-1997 — Blur vs Oasis and everything in between",
            "all": [{"inTheRange": {"year": [1993, 1997]}}],
            "sort": "random", "limit": 200,
        }),

        # ── Duration ─────────────────────────────────────────────────
        ("Epic Odysseys", "epic-odysseys", "Duration", {
            "name": "Epic Odysseys",
            "comment": "Mammoth tracks over 10 minutes — bring snacks",
            "all": [{"gt": {"duration": 600}}],
            "sort": "duration", "order": "desc", "limit": 100,
        }),
        ("Marathon Tracks", "marathon-tracks", "Duration", {
            "name": "Marathon Tracks",
            "comment": "Ultra-long tracks over 15 minutes — the ultimate endurance test",
            "all": [{"gt": {"duration": 900}}],
            "sort": "duration", "order": "desc", "limit": 50,
        }),
        ("The Sweet Spot", "the-sweet-spot", "Duration", {
            "name": "The Sweet Spot",
            "comment": "Goldilocks tracks — between 3 and 5 minutes",
            "all": [{"inTheRange": {"duration": [180, 300]}}],
            "sort": "random", "limit": 200,
        }),
        ("Micro Tracks", "micro-tracks", "Duration", {
            "name": "Micro Tracks",
            "comment": "Blink-and-you'll-miss-it — under 60 seconds",
            "all": [{"lt": {"duration": 60}}, {"gt": {"duration": 0}}],
            "sort": "duration", "order": "asc", "limit": 100,
        }),
        ("The Four-Twenty", "the-four-twenty", "Duration", {
            "name": "The Four-Twenty",
            "comment": "Tracks roughly 4 minutes 20 seconds long — nice",
            "all": [{"inTheRange": {"duration": [258, 262]}}],
            "sort": "random", "limit": 100,
        }),
        ("Commute Friendly", "commute-friendly", "Duration", {
            "name": "Commute Friendly",
            "comment": "3-7 minute tracks — perfect for the daily commute",
            "all": [{"inTheRange": {"duration": [180, 420]}}],
            "sort": "random", "limit": 200,
        }),

        # ── Tempo & Energy ───────────────────────────────────────────
        ("Comatose", "comatose", "Tempo & Energy", {
            "name": "Comatose",
            "comment": "Sub-70 BPM — practically horizontal music",
            "all": [{"lt": {"bpm": 70}}, {"gt": {"bpm": 0}}],
            "sort": "bpm", "order": "asc", "limit": 100,
        }),
        ("The Heartbeat Zone", "the-heartbeat-zone", "Tempo & Energy", {
            "name": "The Heartbeat Zone",
            "comment": "60-80 BPM — synced to your resting heart rate",
            "all": [{"inTheRange": {"bpm": [60, 80]}}],
            "sort": "random", "limit": 100,
        }),
        ("Walking Pace", "walking-pace", "Tempo & Energy", {
            "name": "Walking Pace",
            "comment": "90-110 BPM — perfect for a stroll",
            "all": [{"inTheRange": {"bpm": [90, 110]}}],
            "sort": "random", "limit": 100,
        }),
        ("Jogging Mix", "jogging-mix", "Tempo & Energy", {
            "name": "Jogging Mix",
            "comment": "120-140 BPM — keep that pace steady",
            "all": [{"inTheRange": {"bpm": [120, 140]}}],
            "sort": "random", "limit": 100,
        }),
        ("Sprint Mode", "sprint-mode", "Tempo & Energy", {
            "name": "Sprint Mode",
            "comment": "160+ BPM — all-out sonic assault",
            "all": [{"gt": {"bpm": 160}}],
            "sort": "bpm", "order": "desc", "limit": 100,
        }),
        ("Workout Fuel", "workout-fuel", "Tempo & Energy", {
            "name": "Workout Fuel",
            "comment": "120-160 BPM, 3-5 minutes — gym-ready bangers",
            "all": [
                {"inTheRange": {"bpm": [120, 160]}},
                {"inTheRange": {"duration": [180, 300]}},
            ],
            "sort": "bpm", "order": "desc", "limit": 100,
        }),

        # ── Stats & Data ─────────────────────────────────────────────
        ("Heavy Rotation", "heavy-rotation", "Stats & Data", {
            "name": "Heavy Rotation",
            "comment": "Played 20+ times — your most-spun records",
            "all": [{"gt": {"playcount": 19}}],
            "sort": "playcount", "order": "desc", "limit": 200,
        }),
        ("The Obsessions", "the-obsessions", "Stats & Data", {
            "name": "The Obsessions",
            "comment": "Played 50+ times — you might have a problem",
            "all": [{"gt": {"playcount": 49}}],
            "sort": "playcount", "order": "desc",
        }),
        ("The Centurion Club", "the-centurion-club", "Stats & Data", {
            "name": "The Centurion Club",
            "comment": "Played 100+ times — welcome to the triple-digit club",
            "all": [{"gt": {"playcount": 99}}],
            "sort": "playcount", "order": "desc",
        }),
        ("The Untouchables", "the-untouchables", "Stats & Data", {
            "name": "The Untouchables",
            "comment": "Perfect 5-star rated tracks — flawless victories",
            "all": [{"is": {"rating": 5}}],
            "sort": "random", "limit": 200,
        }),
        ("The Indifferent", "the-indifferent", "Stats & Data", {
            "name": "The Indifferent",
            "comment": "Rated exactly 3 stars — aggressively mediocre or secretly brilliant?",
            "all": [{"is": {"rating": 3}}],
            "sort": "random", "limit": 100,
        }),
        ("Underrated Gems", "underrated-gems", "Stats & Data", {
            "name": "Underrated Gems",
            "comment": "Rated 4+ stars but played fewer than 5 times — criminally underplayed",
            "all": [{"gt": {"rating": 3}}, {"lt": {"playcount": 5}}],
            "sort": "rating", "order": "desc", "limit": 100,
        }),
        ("Rising Stars", "rising-stars", "Stats & Data", {
            "name": "Rising Stars",
            "comment": "Added in the last 90 days and already played 3+ times — instant favourites",
            "all": [{"inTheLast": {"dateadded": 90}}, {"gt": {"playcount": 2}}],
            "sort": "playcount", "order": "desc", "limit": 100,
        }),
        ("Falling Stars", "falling-stars", "Stats & Data", {
            "name": "Falling Stars",
            "comment": "Loved tracks you haven't played in over a year — falling out of favour",
            "all": [{"is": {"loved": True}}, {"notInTheLast": {"lastplayed": 365}}],
            "sort": "random", "limit": 100,
        }),
        ("The Loyalists", "the-loyalists", "Stats & Data", {
            "name": "The Loyalists",
            "comment": "Played recently AND loved — your ride-or-die tracks",
            "all": [
                {"inTheLast": {"lastplayed": 30}},
                {"is": {"loved": True}},
            ],
            "sort": "lastplayed", "order": "desc", "limit": 100,
        }),
        ("Statistical Anomalies", "statistical-anomalies", "Stats & Data", {
            "name": "Statistical Anomalies",
            "comment": "Played 10+ times but rated 1 or 2 — why do you keep listening?",
            "all": [
                {"gt": {"playcount": 9}},
                {"lt": {"rating": 3}},
                {"gt": {"rating": 0}},
            ],
            "sort": "playcount", "order": "desc", "limit": 100,
        }),
        ("The One Percent", "the-one-percent", "Stats & Data", {
            "name": "The One Percent",
            "comment": "Loved AND 5-star AND played 20+ times — the absolute elite",
            "all": [
                {"is": {"loved": True}},
                {"is": {"rating": 5}},
                {"gt": {"playcount": 19}},
            ],
            "sort": "playcount", "order": "desc",
        }),

        # ── Track Position ───────────────────────────────────────────
        ("The B-Team", "the-b-team", "Track Position", {
            "name": "The B-Team",
            "comment": "Track 2 — the eternal runner-up, always the bridesmaid",
            "all": [{"is": {"track": 2}}],
            "sort": "random", "limit": 100,
        }),
        ("The Middle Child", "the-middle-child", "Track Position", {
            "name": "The Middle Child",
            "comment": "Tracks 4-7 — the overlooked middle of the album",
            "all": [{"inTheRange": {"track": [4, 7]}}],
            "sort": "random", "limit": 200,
        }),
        ("The Lucky Seven", "the-lucky-seven", "Track Position", {
            "name": "The Lucky Seven",
            "comment": "Track 7 from every album — lucky number listening",
            "all": [{"is": {"track": 7}}],
            "sort": "random", "limit": 100,
        }),
        ("Double Digits", "double-digits", "Track Position", {
            "name": "Double Digits",
            "comment": "Track 10 and beyond — deep album territory",
            "all": [{"gt": {"track": 9}}],
            "sort": "random", "limit": 200,
        }),
        ("Track 13", "track-13", "Track Position", {
            "name": "Track 13",
            "comment": "The unlucky thirteenth track — cursed bangers only",
            "all": [{"is": {"track": 13}}],
            "sort": "random", "limit": 100,
        }),
        ("Disc Two Deep Cuts", "disc-two-deep-cuts", "Track Position", {
            "name": "Disc Two Deep Cuts",
            "comment": "Everything from disc 2 onwards — the stuff casual fans never reach",
            "all": [{"gt": {"discnumber": 1}}],
            "sort": "random", "limit": 200,
        }),
        ("Hidden Tracks", "hidden-tracks", "Track Position", {
            "name": "Hidden Tracks",
            "comment": "Extremely high track numbers and long duration — the secret Easter eggs",
            "all": [
                {"gt": {"track": 15}},
                {"gt": {"duration": 300}},
            ],
            "sort": "track", "order": "desc", "limit": 100,
        }),
        ("Singles Material", "singles-material", "Track Position", {
            "name": "Singles Material",
            "comment": "Tracks 1-3, under 4 minutes — the obvious single choices",
            "all": [
                {"inTheRange": {"track": [1, 3]}},
                {"lt": {"duration": 240}},
            ],
            "sort": "random", "limit": 200,
        }),

        # ── Moods & Vibes (additional) ───────────────────────────────
        ("Night Owls", "night-owls", "Moods & Vibes", {
            "name": "Night Owls",
            "comment": "Long, slow, deep — music for 3 AM",
            "all": [
                {"gt": {"duration": 300}},
                {"lt": {"bpm": 90}},
                {"gt": {"bpm": 0}},
            ],
            "sort": "bpm", "order": "asc", "limit": 100,
        }),
        ("Morning Coffee", "morning-coffee", "Moods & Vibes", {
            "name": "Morning Coffee",
            "comment": "Moderate tempo, not too long — ease into the day",
            "all": [
                {"inTheRange": {"bpm": [85, 120]}},
                {"lt": {"duration": 300}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Study Session", "study-session", "Moods & Vibes", {
            "name": "Study Session",
            "comment": "Under 100 BPM and over 4 minutes — focus-friendly background music",
            "all": [
                {"lt": {"bpm": 100}},
                {"gt": {"bpm": 0}},
                {"gt": {"duration": 240}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Road Trip", "road-trip", "Moods & Vibes", {
            "name": "Road Trip",
            "comment": "4-7 minute favourites — windows down, volume up",
            "all": [
                {"inTheRange": {"duration": [240, 420]}},
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Dinner Party", "dinner-party", "Moods & Vibes", {
            "name": "Dinner Party",
            "comment": "Mellow tempo, mid-length, well-rated — sophisticated background music",
            "all": [
                {"inTheRange": {"bpm": [70, 110]}},
                {"inTheRange": {"duration": [180, 360]}},
                {"gt": {"rating": 2}},
            ],
            "sort": "random", "limit": 100,
        }),

        # ── Seasonal ─────────────────────────────────────────────────
        ("Summer Anthems", "summer-anthems", "Seasonal", {
            "name": "Summer Anthems",
            "comment": "Upbeat, high-energy, well-loved — soundtrack to endless summers",
            "all": [
                {"gt": {"bpm": 110}},
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Winter Warmers", "winter-warmers", "Seasonal", {
            "name": "Winter Warmers",
            "comment": "Slow, long, and cozy — music for blankets and hot chocolate",
            "all": [
                {"lt": {"bpm": 100}},
                {"gt": {"bpm": 0}},
                {"gt": {"duration": 240}},
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Rainy Day", "rainy-day", "Seasonal", {
            "name": "Rainy Day",
            "comment": "Melancholic tempo, mid-length — perfect for watching the rain",
            "all": [
                {"inTheRange": {"bpm": [70, 100]}},
                {"inTheRange": {"duration": [180, 360]}},
            ],
            "sort": "random", "limit": 100,
        }),

        # ── Quality & Format (additional) ────────────────────────────
        ("Sonic Giants", "sonic-giants", "Quality & Format", {
            "name": "Sonic Giants",
            "comment": "Files over 50 MB — your storage-devouring monsters",
            "all": [{"gt": {"size": 52428800}}],
            "sort": "size", "order": "desc", "limit": 100,
        }),
        ("The Featherweights", "the-featherweights", "Quality & Format", {
            "name": "The Featherweights",
            "comment": "Files under 2 MB — tiny but mighty",
            "all": [{"lt": {"size": 2097152}}, {"gt": {"size": 0}}],
            "sort": "size", "order": "asc", "limit": 100,
        }),
        ("MP3 Nostalgia", "mp3-nostalgia", "Quality & Format", {
            "name": "MP3 Nostalgia",
            "comment": "Good old MP3 files — Napster would be proud",
            "all": [{"is": {"filetype": "mp3"}}],
            "sort": "random", "limit": 200,
        }),
        ("AAC Collection", "aac-collection", "Quality & Format", {
            "name": "AAC Collection",
            "comment": "AAC/M4A files — the iTunes generation",
            "all": [{"is": {"filetype": "aac"}}],
            "sort": "random", "limit": 200,
        }),
        ("Mono Classics", "mono-classics", "Quality & Format", {
            "name": "Mono Classics",
            "comment": "Single-channel audio — pre-stereo charm",
            "all": [{"is": {"channels": 1}}],
            "sort": "random", "limit": 200,
        }),
        ("Surround Sound", "surround-sound", "Quality & Format", {
            "name": "Surround Sound",
            "comment": "Multi-channel tracks — more than stereo",
            "all": [{"gt": {"channels": 2}}],
            "sort": "random", "limit": 200,
        }),
        ("Lo-Fi Charm", "lo-fi-charm", "Quality & Format", {
            "name": "Lo-Fi Charm",
            "comment": "Low bitrate but high play count — proof that quality isn't everything",
            "all": [{"lt": {"bitrate": 192}}, {"gt": {"playcount": 5}}],
            "sort": "playcount", "order": "desc", "limit": 100,
        }),
        ("The Audiophile", "the-audiophile", "Quality & Format", {
            "name": "The Audiophile",
            "comment": "FLAC, 24-bit, and rated 4+ — golden ears only",
            "all": [
                {"is": {"filetype": "flac"}},
                {"gt": {"bitdepth": 16}},
                {"gt": {"rating": 3}},
            ],
            "sort": "random", "limit": 200,
        }),

        # ── Library Housekeeping ─────────────────────────────────────
        ("Missing Artwork", "missing-artwork", "Library Housekeeping", {
            "name": "Missing Artwork",
            "comment": "Tracks without cover art — naked albums",
            "all": [{"is": {"hascoverart": False}}],
            "sort": "+artist,+album,+track",
        }),
        ("Recently Modified", "recently-modified", "Library Housekeeping", {
            "name": "Recently Modified",
            "comment": "Files modified in the last 30 days — recently re-tagged or updated",
            "all": [{"inTheLast": {"datemodified": 30}}],
            "sort": "datemodified", "order": "desc", "limit": 200,
        }),
        ("Explicit Only", "explicit-only", "Library Housekeeping", {
            "name": "Explicit Only",
            "comment": "Tracks marked as explicit — parental advisory",
            "all": [{"is": {"explicitstatus": "explicit"}}],
            "sort": "random", "limit": 200,
        }),
        ("The Void", "the-void", "Library Housekeeping", {
            "name": "The Void",
            "comment": "Not rated, not loved, never played — do these tracks even exist?",
            "all": [
                {"is": {"rating": 0}},
                {"isNot": {"loved": True}},
                {"is": {"playcount": 0}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Digital Archaeology", "digital-archaeology", "Library Housekeeping", {
            "name": "Digital Archaeology",
            "comment": "Files not modified in over 5 years — digital fossils",
            "all": [{"notInTheLast": {"datemodified": 1825}}],
            "sort": "datemodified", "order": "asc", "limit": 200,
        }),

        # ── Albums & Collections ─────────────────────────────────────
        ("Pure Albums Only", "pure-albums-only", "Albums & Collections", {
            "name": "Pure Albums Only",
            "comment": "No compilations — original album tracks only",
            "all": [{"isNot": {"compilation": True}}],
            "sort": "random", "limit": 200,
        }),
        ("Compilation Discovery", "compilation-discovery", "Albums & Collections", {
            "name": "Compilation Discovery",
            "comment": "Unplayed compilation tracks — hidden in the various artists pile",
            "all": [{"is": {"compilation": True}}, {"is": {"playcount": 0}}],
            "sort": "random", "limit": 100,
        }),

        # ── Discovery (additional) ───────────────────────────────────
        ("Fresh Favorites", "fresh-favorites", "Discovery", {
            "name": "Fresh Favorites",
            "comment": "Loved in the last 30 days — your latest sonic crushes",
            "all": [{"inTheLast": {"dateloved": 30}}],
            "sort": "dateloved", "order": "desc", "limit": 100,
        }),
        ("The Slow Burn", "the-slow-burn", "Discovery", {
            "name": "The Slow Burn",
            "comment": "Added over 6 months ago, played for the first time recently — late discovery",
            "all": [
                {"notInTheLast": {"dateadded": 180}},
                {"inTheLast": {"lastplayed": 30}},
                {"lt": {"playcount": 3}},
            ],
            "sort": "lastplayed", "order": "desc", "limit": 100,
        }),

        # ── Rediscovery (additional) ─────────────────────────────────
        ("Abandoned Ships", "abandoned-ships", "Rediscovery", {
            "name": "Abandoned Ships",
            "comment": "Loved once but not played in 2+ years — what happened?",
            "all": [
                {"is": {"loved": True}},
                {"notInTheLast": {"lastplayed": 730}},
            ],
            "sort": "lastplayed", "order": "asc", "limit": 100,
        }),
        ("Late Bloomers", "late-bloomers", "Rediscovery", {
            "name": "Late Bloomers",
            "comment": "Added over a year ago, first plays in the last 3 months — finally getting attention",
            "all": [
                {"notInTheLast": {"dateadded": 365}},
                {"inTheLast": {"lastplayed": 90}},
                {"lt": {"playcount": 5}},
            ],
            "sort": "lastplayed", "order": "desc", "limit": 100,
        }),

        # ── Weird & Wonderful ────────────────────────────────────────
        ("Earworms", "earworms", "Weird & Wonderful", {
            "name": "Earworms",
            "comment": "Short tracks with high play counts — catchy hooks that won't leave your head",
            "all": [
                {"lt": {"duration": 210}},
                {"gt": {"playcount": 10}},
            ],
            "sort": "playcount", "order": "desc", "limit": 100,
        }),
        ("Party Starters", "party-starters", "Weird & Wonderful", {
            "name": "Party Starters",
            "comment": "Fast, short, and frequently played — instant party igniters",
            "all": [
                {"gt": {"bpm": 120}},
                {"lt": {"duration": 240}},
                {"gt": {"playcount": 5}},
            ],
            "sort": "bpm", "order": "desc", "limit": 100,
        }),
        ("Perfectionist's Pick", "perfectionists-pick", "Weird & Wonderful", {
            "name": "Perfectionist's Pick",
            "comment": "Lossless, loved, and rated 5 — the pinnacle of your collection",
            "all": [
                {"is": {"filetype": "flac"}},
                {"is": {"loved": True}},
                {"is": {"rating": 5}},
            ],
            "sort": "+albumartist,+album,+track",
        }),
        ("The Completionist", "the-completionist", "Weird & Wonderful", {
            "name": "The Completionist",
            "comment": "Loved, rated 5, played 10+ times, with cover art — peak curation",
            "all": [
                {"is": {"loved": True}},
                {"is": {"rating": 5}},
                {"gt": {"playcount": 9}},
                {"is": {"hascoverart": True}},
            ],
            "sort": "+albumartist,+album,+track",
        }),
        ("The Time Capsule", "the-time-capsule", "Weird & Wonderful", {
            "name": "The Time Capsule",
            "comment": "Original release date before 1970 — prehistoric recordings in your library",
            "all": [{"before": {"originaldate": "1970-01-01"}}],
            "sort": "random", "limit": 200,
        }),
        ("New Classics", "new-classics", "Weird & Wonderful", {
            "name": "New Classics",
            "comment": "Released 2020+ and already rated 4+ — instant modern classics",
            "all": [
                {"gt": {"year": 2019}},
                {"gt": {"rating": 3}},
            ],
            "sort": "rating", "order": "desc", "limit": 100,
        }),
        ("Vintage Lossless", "vintage-lossless", "Weird & Wonderful", {
            "name": "Vintage Lossless",
            "comment": "Pre-1970 music in FLAC — old soul, pristine quality",
            "all": [
                {"lt": {"year": 1970}},
                {"gt": {"year": 0}},
                {"is": {"filetype": "flac"}},
            ],
            "sort": "year", "order": "asc", "limit": 200,
        }),
        ("The Growers", "the-growers", "Weird & Wonderful", {
            "name": "The Growers",
            "comment": "Played 10+ times but still not loved — they grew on you quietly",
            "all": [
                {"gt": {"playcount": 9}},
                {"isNot": {"loved": True}},
            ],
            "sort": "playcount", "order": "desc", "limit": 100,
        }),
        ("The Soundtrack", "the-soundtrack", "Weird & Wonderful", {
            "name": "The Soundtrack",
            "comment": "Your loved tracks, album-ordered — the movie of your life",
            "all": [{"is": {"loved": True}}],
            "sort": "+year,+albumartist,+album,+track",
        }),
        ("The Anti-Shuffle", "the-anti-shuffle", "Weird & Wonderful", {
            "name": "The Anti-Shuffle",
            "comment": "Your best tracks in strict chronological order — no randomness allowed",
            "all": [
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
            ],
            "sort": "+year,+album,+track",
        }),
        ("Zero to Hero", "zero-to-hero", "Weird & Wonderful", {
            "name": "Zero to Hero",
            "comment": "Never played but recently added — fresh arrivals awaiting their debut",
            "all": [
                {"is": {"playcount": 0}},
                {"inTheLast": {"dateadded": 14}},
            ],
            "sort": "dateadded", "order": "desc", "limit": 200,
        }),
        ("The Shapeshifters", "the-shapeshifters", "Weird & Wonderful", {
            "name": "The Shapeshifters",
            "comment": "Tracks from multi-disc albums — sprawling artistic statements",
            "all": [{"gt": {"discnumber": 1}}],
            "sort": "+albumartist,+album,+discnumber,+track",
        }),
        ("Format Roulette", "format-roulette", "Weird & Wonderful", {
            "name": "Format Roulette",
            "comment": "Non-FLAC, non-MP3 files — the weird and wonderful formats",
            "all": [
                {"isNot": {"filetype": "flac"}},
                {"isNot": {"filetype": "mp3"}},
            ],
            "sort": "random", "limit": 200,
        }),

        # ── Complex / Nested (additional) ────────────────────────────
        ("The Renaissance", "the-renaissance", "Complex / Nested", {
            "name": "The Renaissance",
            "comment": "Not played in 6+ months but recently loved or rated — rediscovered and reborn",
            "all": [
                {"notInTheLast": {"lastplayed": 180}},
                {"any": [
                    {"inTheLast": {"dateloved": 60}},
                    {"gt": {"rating": 3}},
                ]},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Genre Hopper", "genre-hopper", "Complex / Nested", {
            "name": "Genre Hopper",
            "comment": "Loved tracks from compilations or multi-disc sets — eclectic by nature",
            "all": [
                {"is": {"loved": True}},
                {"any": [
                    {"is": {"compilation": True}},
                    {"gt": {"discnumber": 1}},
                ]},
            ],
            "sort": "random", "limit": 100,
        }),
        ("The Paradox", "the-paradox", "Complex / Nested", {
            "name": "The Paradox",
            "comment": "Low-rated tracks you've played a lot OR high-rated ones you've barely touched",
            "any": [
                {"all": [{"lt": {"rating": 3}}, {"gt": {"rating": 0}}, {"gt": {"playcount": 10}}]},
                {"all": [{"gt": {"rating": 3}}, {"lt": {"playcount": 3}}]},
            ],
            "sort": "random", "limit": 100,
        }),
        ("The Upgrade List", "the-upgrade-list", "Complex / Nested", {
            "name": "The Upgrade List",
            "comment": "Loved tracks in lossy format — candidates for a lossless upgrade",
            "all": [
                {"is": {"loved": True}},
                {"any": [
                    {"is": {"filetype": "mp3"}},
                    {"is": {"filetype": "aac"}},
                    {"is": {"filetype": "ogg"}},
                ]},
            ],
            "sort": "+albumartist,+album,+track",
        }),
        ("Peak Discovery", "peak-discovery", "Complex / Nested", {
            "name": "Peak Discovery",
            "comment": "Added in the last 90 days AND (already loved OR rated 4+) — love at first listen",
            "all": [
                {"inTheLast": {"dateadded": 90}},
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
            ],
            "sort": "dateadded", "order": "desc", "limit": 100,
        }),
        ("The Deep End", "the-deep-end", "Complex / Nested", {
            "name": "The Deep End",
            "comment": "Long tracks (7+ min), loved or highly rated, from deep in the album — sonic journeys",
            "all": [
                {"gt": {"duration": 420}},
                {"gt": {"track": 5}},
                {"any": [{"is": {"loved": True}}, {"gt": {"rating": 3}}]},
            ],
            "sort": "duration", "order": "desc", "limit": 100,
        }),
        ("The Full Circle", "the-full-circle", "Complex / Nested", {
            "name": "The Full Circle",
            "comment": "Track 1 from albums where you've loved it AND played 5+ times — iconic opening moments",
            "all": [
                {"is": {"track": 1}},
                {"is": {"loved": True}},
                {"gt": {"playcount": 4}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("The Shelf Life", "the-shelf-life", "Complex / Nested", {
            "name": "The Shelf Life",
            "comment": "Added 1-2 years ago, played 1-3 times, not loved — the forgotten middle ground",
            "all": [
                {"notInTheLast": {"dateadded": 365}},
                {"inTheLast": {"dateadded": 730}},
                {"inTheRange": {"playcount": [1, 3]}},
                {"isNot": {"loved": True}},
            ],
            "sort": "random", "limit": 100,
        }),

        # ── Genre ────────────────────────────────────────────────────
        ("Rock Essentials", "rock-essentials", "Genre", {
            "name": "Rock Essentials",
            "comment": "All your rock tracks — the backbone of any collection",
            "all": [{"contains": {"genre": "rock"}}],
            "sort": "random", "limit": 200,
        }),
        ("Pop Hits", "pop-hits", "Genre", {
            "name": "Pop Hits",
            "comment": "Pure pop — catchy, polished, irresistible",
            "all": [{"contains": {"genre": "pop"}}],
            "sort": "random", "limit": 200,
        }),
        ("Hip-Hop & Rap", "hip-hop-and-rap", "Genre", {
            "name": "Hip-Hop & Rap",
            "comment": "Beats, bars, and bass — every hip-hop track in your library",
            "any": [
                {"contains": {"genre": "hip-hop"}},
                {"contains": {"genre": "hip hop"}},
                {"contains": {"genre": "rap"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Electronic & EDM", "electronic-and-edm", "Genre", {
            "name": "Electronic & EDM",
            "comment": "Synths, beats, and drops — the electronic spectrum",
            "any": [
                {"contains": {"genre": "electronic"}},
                {"contains": {"genre": "edm"}},
                {"contains": {"genre": "techno"}},
                {"contains": {"genre": "house"}},
                {"contains": {"genre": "trance"}},
                {"contains": {"genre": "drum and bass"}},
                {"contains": {"genre": "dubstep"}},
                {"contains": {"genre": "electro"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Jazz Collection", "jazz-collection", "Genre", {
            "name": "Jazz Collection",
            "comment": "Smooth, free, bebop, fusion — all that jazz",
            "all": [{"contains": {"genre": "jazz"}}],
            "sort": "random", "limit": 200,
        }),
        ("Blues Sessions", "blues-sessions", "Genre", {
            "name": "Blues Sessions",
            "comment": "12 bars of feeling — every shade of blue",
            "all": [{"contains": {"genre": "blues"}}],
            "sort": "random", "limit": 200,
        }),
        ("Metal Mayhem", "metal-mayhem", "Genre", {
            "name": "Metal Mayhem",
            "comment": "Heavy, heavier, heaviest — all metal subgenres welcome",
            "all": [{"contains": {"genre": "metal"}}],
            "sort": "random", "limit": 200,
        }),
        ("Classical Corner", "classical-corner", "Genre", {
            "name": "Classical Corner",
            "comment": "Centuries of composed genius — from baroque to modern classical",
            "all": [{"contains": {"genre": "classical"}}],
            "sort": "random", "limit": 200,
        }),
        ("Country Roads", "country-roads", "Genre", {
            "name": "Country Roads",
            "comment": "Twang, steel guitars, and storytelling — country & western",
            "any": [
                {"contains": {"genre": "country"}},
                {"contains": {"genre": "western"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("R&B & Soul", "rnb-and-soul", "Genre", {
            "name": "R&B & Soul",
            "comment": "Rhythm, blues, and soul — smooth grooves",
            "any": [
                {"contains": {"genre": "r&b"}},
                {"contains": {"genre": "soul"}},
                {"contains": {"genre": "rhythm and blues"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Folk & Acoustic", "folk-and-acoustic", "Genre", {
            "name": "Folk & Acoustic",
            "comment": "Stripped back, honest, raw — campfire music",
            "any": [
                {"contains": {"genre": "folk"}},
                {"contains": {"genre": "acoustic"}},
                {"contains": {"genre": "singer-songwriter"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Punk Rock", "punk-rock", "Genre", {
            "name": "Punk Rock",
            "comment": "Three chords and the truth — fast, loud, attitude",
            "all": [{"contains": {"genre": "punk"}}],
            "sort": "random", "limit": 200,
        }),
        ("Reggae & Dub", "reggae-and-dub", "Genre", {
            "name": "Reggae & Dub",
            "comment": "Island rhythms and bass-heavy echoes",
            "any": [
                {"contains": {"genre": "reggae"}},
                {"contains": {"genre": "dub"}},
                {"contains": {"genre": "ska"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Funk Machine", "funk-machine", "Genre", {
            "name": "Funk Machine",
            "comment": "Get up offa that thing — pure funk",
            "all": [{"contains": {"genre": "funk"}}],
            "sort": "random", "limit": 200,
        }),
        ("Disco Nights", "disco-nights", "Genre", {
            "name": "Disco Nights",
            "comment": "Mirror balls and four-on-the-floor — disco never died",
            "all": [{"contains": {"genre": "disco"}}],
            "sort": "random", "limit": 200,
        }),
        ("Indie & Alternative", "indie-and-alternative", "Genre", {
            "name": "Indie & Alternative",
            "comment": "Left of the dial — indie and alt everything",
            "any": [
                {"contains": {"genre": "indie"}},
                {"contains": {"genre": "alternative"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Ambient & Downtempo", "ambient-and-downtempo", "Genre", {
            "name": "Ambient & Downtempo",
            "comment": "Sonic wallpaper — ambient textures and slow atmospheres",
            "any": [
                {"contains": {"genre": "ambient"}},
                {"contains": {"genre": "downtempo"}},
                {"contains": {"genre": "chillout"}},
                {"contains": {"genre": "new age"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Latin Flavours", "latin-flavours", "Genre", {
            "name": "Latin Flavours",
            "comment": "Salsa, bossa nova, reggaeton, and more — ritmo latino",
            "any": [
                {"contains": {"genre": "latin"}},
                {"contains": {"genre": "salsa"}},
                {"contains": {"genre": "bossa nova"}},
                {"contains": {"genre": "reggaeton"}},
                {"contains": {"genre": "samba"}},
                {"contains": {"genre": "cumbia"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Soundtrack & Score", "soundtrack-and-score", "Genre", {
            "name": "Soundtrack & Score",
            "comment": "Film scores, game soundtracks, and musical theatre",
            "any": [
                {"contains": {"genre": "soundtrack"}},
                {"contains": {"genre": "score"}},
                {"contains": {"genre": "film"}},
                {"contains": {"genre": "game"}},
                {"contains": {"genre": "musical"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("World Music", "world-music", "Genre", {
            "name": "World Music",
            "comment": "Global sounds — music from every corner of the planet",
            "any": [
                {"contains": {"genre": "world"}},
                {"contains": {"genre": "afrobeat"}},
                {"contains": {"genre": "celtic"}},
                {"contains": {"genre": "flamenco"}},
                {"contains": {"genre": "african"}},
                {"contains": {"genre": "arabic"}},
                {"contains": {"genre": "indian"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Experimental & Avant-Garde", "experimental-and-avant-garde", "Genre", {
            "name": "Experimental & Avant-Garde",
            "comment": "The outer limits — music that defies categorisation",
            "any": [
                {"contains": {"genre": "experimental"}},
                {"contains": {"genre": "avant-garde"}},
                {"contains": {"genre": "noise"}},
                {"contains": {"genre": "industrial"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Gospel & Spiritual", "gospel-and-spiritual", "Genre", {
            "name": "Gospel & Spiritual",
            "comment": "Hallelujah — uplifting gospel and spiritual music",
            "any": [
                {"contains": {"genre": "gospel"}},
                {"contains": {"genre": "spiritual"}},
                {"contains": {"genre": "christian"}},
            ],
            "sort": "random", "limit": 200,
        }),

        # ── Genre Fusions ────────────────────────────────────────────
        ("Loved Rock", "loved-rock", "Genre Fusions", {
            "name": "Loved Rock",
            "comment": "Rock tracks you've loved — your personal rock hall of fame",
            "all": [{"contains": {"genre": "rock"}}, {"is": {"loved": True}}],
            "sort": "random", "limit": 200,
        }),
        ("Jazz in FLAC", "jazz-in-flac", "Genre Fusions", {
            "name": "Jazz in FLAC",
            "comment": "Jazz the way it should be heard — lossless and warm",
            "all": [{"contains": {"genre": "jazz"}}, {"is": {"filetype": "flac"}}],
            "sort": "random", "limit": 200,
        }),
        ("Top Rated Electronic", "top-rated-electronic", "Genre Fusions", {
            "name": "Top Rated Electronic",
            "comment": "Your best electronic tracks — rated 4 or higher",
            "all": [
                {"any": [
                    {"contains": {"genre": "electronic"}},
                    {"contains": {"genre": "techno"}},
                    {"contains": {"genre": "house"}},
                ]},
                {"gt": {"rating": 3}},
            ],
            "sort": "rating", "order": "desc", "limit": 100,
        }),
        ("Metal Marathons", "metal-marathons", "Genre Fusions", {
            "name": "Metal Marathons",
            "comment": "Metal tracks over 7 minutes — epic prog and doom journeys",
            "all": [{"contains": {"genre": "metal"}}, {"gt": {"duration": 420}}],
            "sort": "duration", "order": "desc", "limit": 100,
        }),
        ("Mellow Classics", "mellow-classics", "Genre Fusions", {
            "name": "Mellow Classics",
            "comment": "Classical tracks under 100 BPM — serene and peaceful",
            "all": [
                {"contains": {"genre": "classical"}},
                {"lt": {"bpm": 100}},
                {"gt": {"bpm": 0}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Unplayed Genres", "unplayed-genres", "Genre Fusions", {
            "name": "Unplayed Genres",
            "comment": "Never-played tracks from jazz, classical, or folk — explore your blind spots",
            "all": [
                {"any": [
                    {"contains": {"genre": "jazz"}},
                    {"contains": {"genre": "classical"}},
                    {"contains": {"genre": "folk"}},
                ]},
                {"is": {"playcount": 0}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Hip-Hop Classics", "hip-hop-classics", "Genre Fusions", {
            "name": "Hip-Hop Classics",
            "comment": "Pre-2000 hip-hop — golden age bars and beats",
            "all": [
                {"any": [
                    {"contains": {"genre": "hip-hop"}},
                    {"contains": {"genre": "hip hop"}},
                    {"contains": {"genre": "rap"}},
                ]},
                {"lt": {"year": 2000}},
                {"gt": {"year": 0}},
            ],
            "sort": "year", "order": "asc", "limit": 200,
        }),
        ("Pop Perfection", "pop-perfection", "Genre Fusions", {
            "name": "Pop Perfection",
            "comment": "Pop tracks rated 5 stars — verified bangers only",
            "all": [{"contains": {"genre": "pop"}}, {"is": {"rating": 5}}],
            "sort": "random", "limit": 200,
        }),
        ("Punk Under 2 Minutes", "punk-under-2-minutes", "Genre Fusions", {
            "name": "Punk Under 2 Minutes",
            "comment": "The punkest tracks — blisteringly short, maximum energy",
            "all": [{"contains": {"genre": "punk"}}, {"lt": {"duration": 120}}],
            "sort": "duration", "order": "asc", "limit": 100,
        }),
        ("Epic Soundtracks", "epic-soundtracks", "Genre Fusions", {
            "name": "Epic Soundtracks",
            "comment": "Soundtrack tracks over 5 mins — cinematic epics",
            "all": [
                {"any": [
                    {"contains": {"genre": "soundtrack"}},
                    {"contains": {"genre": "score"}},
                ]},
                {"gt": {"duration": 300}},
            ],
            "sort": "duration", "order": "desc", "limit": 100,
        }),

        # ── Mood ─────────────────────────────────────────────────────
        ("Happy Vibes", "happy-vibes", "Mood", {
            "name": "Happy Vibes",
            "comment": "Tracks tagged with a happy mood — guaranteed smiles",
            "any": [
                {"contains": {"mood": "happy"}},
                {"contains": {"mood": "cheerful"}},
                {"contains": {"mood": "joyful"}},
                {"contains": {"mood": "upbeat"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Sad Songs", "sad-songs", "Mood", {
            "name": "Sad Songs",
            "comment": "Permission to feel — melancholy, sad, somber tracks",
            "any": [
                {"contains": {"mood": "sad"}},
                {"contains": {"mood": "melancholy"}},
                {"contains": {"mood": "somber"}},
                {"contains": {"mood": "sorrowful"}},
                {"contains": {"mood": "lonely"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Energetic", "energetic", "Mood", {
            "name": "Energetic",
            "comment": "High-energy mood tags — for when you need a boost",
            "any": [
                {"contains": {"mood": "energetic"}},
                {"contains": {"mood": "uplifting"}},
                {"contains": {"mood": "powerful"}},
                {"contains": {"mood": "exciting"}},
                {"contains": {"mood": "exhilarating"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Relaxing", "relaxing", "Mood", {
            "name": "Relaxing",
            "comment": "Chill, calm, peaceful — music to decompress to",
            "any": [
                {"contains": {"mood": "relaxing"}},
                {"contains": {"mood": "calm"}},
                {"contains": {"mood": "peaceful"}},
                {"contains": {"mood": "soothing"}},
                {"contains": {"mood": "tranquil"}},
                {"contains": {"mood": "serene"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Aggressive", "aggressive", "Mood", {
            "name": "Aggressive",
            "comment": "Raw, angry, intense — music with teeth",
            "any": [
                {"contains": {"mood": "aggressive"}},
                {"contains": {"mood": "angry"}},
                {"contains": {"mood": "intense"}},
                {"contains": {"mood": "fierce"}},
                {"contains": {"mood": "hostile"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Romantic", "romantic", "Mood", {
            "name": "Romantic",
            "comment": "Love songs and tender feelings — set the mood",
            "any": [
                {"contains": {"mood": "romantic"}},
                {"contains": {"mood": "love"}},
                {"contains": {"mood": "tender"}},
                {"contains": {"mood": "passionate"}},
                {"contains": {"mood": "sensual"}},
                {"contains": {"mood": "intimate"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Dark & Brooding", "dark-and-brooding", "Mood", {
            "name": "Dark & Brooding",
            "comment": "Gothic, moody, ominous — for your darker moments",
            "any": [
                {"contains": {"mood": "dark"}},
                {"contains": {"mood": "brooding"}},
                {"contains": {"mood": "ominous"}},
                {"contains": {"mood": "gothic"}},
                {"contains": {"mood": "menacing"}},
                {"contains": {"mood": "eerie"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Dreamy", "dreamy", "Mood", {
            "name": "Dreamy",
            "comment": "Ethereal, floating, otherworldly — music from another dimension",
            "any": [
                {"contains": {"mood": "dreamy"}},
                {"contains": {"mood": "ethereal"}},
                {"contains": {"mood": "atmospheric"}},
                {"contains": {"mood": "hypnotic"}},
                {"contains": {"mood": "mystical"}},
                {"contains": {"mood": "trippy"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Nostalgic", "nostalgic", "Mood", {
            "name": "Nostalgic",
            "comment": "Wistful, bittersweet, sentimental — music that takes you back",
            "any": [
                {"contains": {"mood": "nostalgic"}},
                {"contains": {"mood": "bittersweet"}},
                {"contains": {"mood": "wistful"}},
                {"contains": {"mood": "sentimental"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Epic & Cinematic", "epic-and-cinematic", "Mood", {
            "name": "Epic & Cinematic",
            "comment": "Grand, triumphant, sweeping — your life needs a soundtrack",
            "any": [
                {"contains": {"mood": "epic"}},
                {"contains": {"mood": "cinematic"}},
                {"contains": {"mood": "triumphant"}},
                {"contains": {"mood": "heroic"}},
                {"contains": {"mood": "majestic"}},
                {"contains": {"mood": "grandiose"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Groovy", "groovy", "Mood", {
            "name": "Groovy",
            "comment": "Funky, groovy, rhythmic — get your head nodding",
            "any": [
                {"contains": {"mood": "groovy"}},
                {"contains": {"mood": "funky"}},
                {"contains": {"mood": "rhythmic"}},
                {"contains": {"mood": "bouncy"}},
                {"contains": {"mood": "swagger"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Rebellious", "rebellious", "Mood", {
            "name": "Rebellious",
            "comment": "Defiant, rebellious, anarchic — music that fights back",
            "any": [
                {"contains": {"mood": "rebellious"}},
                {"contains": {"mood": "defiant"}},
                {"contains": {"mood": "anarchic"}},
                {"contains": {"mood": "provocative"}},
                {"contains": {"mood": "confrontational"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Spooky", "spooky", "Mood", {
            "name": "Spooky",
            "comment": "Creepy, haunting, sinister — perfect for Halloween or 3AM listening",
            "any": [
                {"contains": {"mood": "spooky"}},
                {"contains": {"mood": "creepy"}},
                {"contains": {"mood": "haunting"}},
                {"contains": {"mood": "sinister"}},
                {"contains": {"mood": "scary"}},
                {"contains": {"mood": "eerie"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Uplifting", "uplifting", "Mood", {
            "name": "Uplifting",
            "comment": "Inspirational, hopeful, uplifting — music to lift your spirits",
            "any": [
                {"contains": {"mood": "uplifting"}},
                {"contains": {"mood": "inspirational"}},
                {"contains": {"mood": "hopeful"}},
                {"contains": {"mood": "optimistic"}},
                {"contains": {"mood": "encouraging"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Sexy", "sexy", "Mood", {
            "name": "Sexy",
            "comment": "Sultry, seductive, steamy — after-dark listening",
            "any": [
                {"contains": {"mood": "sexy"}},
                {"contains": {"mood": "sultry"}},
                {"contains": {"mood": "seductive"}},
                {"contains": {"mood": "steamy"}},
                {"contains": {"mood": "sensual"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Playful", "playful", "Mood", {
            "name": "Playful",
            "comment": "Quirky, whimsical, fun — music that doesn't take itself seriously",
            "any": [
                {"contains": {"mood": "playful"}},
                {"contains": {"mood": "quirky"}},
                {"contains": {"mood": "whimsical"}},
                {"contains": {"mood": "fun"}},
                {"contains": {"mood": "humorous"}},
                {"contains": {"mood": "silly"}},
            ],
            "sort": "random", "limit": 200,
        }),

        # ── Mood Fusions ────────────────────────────────────────────
        ("Happy & Loved", "happy-and-loved", "Mood Fusions", {
            "name": "Happy & Loved",
            "comment": "Tracks tagged happy that you've also loved — double the joy",
            "all": [
                {"any": [
                    {"contains": {"mood": "happy"}},
                    {"contains": {"mood": "cheerful"}},
                    {"contains": {"mood": "joyful"}},
                ]},
                {"is": {"loved": True}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Sad & Highly Rated", "sad-and-highly-rated", "Mood Fusions", {
            "name": "Sad & Highly Rated",
            "comment": "Beautiful sadness — melancholy tracks you rated 4 or higher",
            "all": [
                {"any": [
                    {"contains": {"mood": "sad"}},
                    {"contains": {"mood": "melancholy"}},
                    {"contains": {"mood": "somber"}},
                ]},
                {"gt": {"rating": 3}},
            ],
            "sort": "rating", "order": "desc", "limit": 100,
        }),
        ("Dark & Heavy", "dark-and-heavy", "Mood Fusions", {
            "name": "Dark & Heavy",
            "comment": "Dark mood + metal genre — the heaviest, darkest corner of your library",
            "all": [
                {"any": [
                    {"contains": {"mood": "dark"}},
                    {"contains": {"mood": "ominous"}},
                    {"contains": {"mood": "aggressive"}},
                ]},
                {"contains": {"genre": "metal"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Chill Electronic", "chill-electronic", "Mood Fusions", {
            "name": "Chill Electronic",
            "comment": "Relaxing mood meets electronic genre — ambient beats and warm synths",
            "all": [
                {"any": [
                    {"contains": {"mood": "relaxing"}},
                    {"contains": {"mood": "calm"}},
                    {"contains": {"mood": "peaceful"}},
                    {"contains": {"mood": "dreamy"}},
                ]},
                {"any": [
                    {"contains": {"genre": "electronic"}},
                    {"contains": {"genre": "ambient"}},
                    {"contains": {"genre": "downtempo"}},
                ]},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Moody Discoveries", "moody-discoveries", "Mood Fusions", {
            "name": "Moody Discoveries",
            "comment": "Tracks with a mood tag but never played — what vibe are you missing?",
            "all": [
                {"notContains": {"mood": ""}},
                {"is": {"playcount": 0}},
            ],
            "sort": "random", "limit": 100,
        }),

        # ── ReplayGain & Loudness ────────────────────────────────────
        ("The Loudness War", "the-loudness-war", "ReplayGain & Loudness", {
            "name": "The Loudness War",
            "comment": "Tracks with very low ReplayGain — mastered LOUD, brickwalled, no mercy",
            "all": [{"lt": {"replaygain_track_gain": -12}}],
            "sort": "replaygain_track_gain", "order": "asc", "limit": 100,
        }),
        ("Whisper Quiet", "whisper-quiet", "ReplayGain & Loudness", {
            "name": "Whisper Quiet",
            "comment": "Tracks with high ReplayGain — delicately mastered, natural dynamics",
            "all": [{"gt": {"replaygain_track_gain": 5}}],
            "sort": "replaygain_track_gain", "order": "desc", "limit": 100,
        }),
        ("Dynamic Range Kings", "dynamic-range-kings", "ReplayGain & Loudness", {
            "name": "Dynamic Range Kings",
            "comment": "Low peak values with moderate gain — well-mastered with real dynamics",
            "all": [
                {"lt": {"replaygain_track_peak": 0.9}},
                {"gt": {"replaygain_track_gain": -6}},
            ],
            "sort": "replaygain_track_peak", "order": "asc", "limit": 100,
        }),
        ("Clipping Danger", "clipping-danger", "ReplayGain & Loudness", {
            "name": "Clipping Danger",
            "comment": "Tracks with peak at or near 1.0 — pushing the hard limits of digital audio",
            "all": [{"gt": {"replaygain_track_peak": 0.99}}],
            "sort": "replaygain_track_peak", "order": "desc", "limit": 100,
        }),
        ("Hot Albums", "hot-albums", "ReplayGain & Loudness", {
            "name": "Hot Albums",
            "comment": "Albums mastered loud — low album ReplayGain means a hot master",
            "all": [{"lt": {"replaygain_album_gain": -10}}],
            "sort": "replaygain_album_gain", "order": "asc", "limit": 100,
        }),
        ("Gentle Albums", "gentle-albums", "ReplayGain & Loudness", {
            "name": "Gentle Albums",
            "comment": "Albums with high positive gain — mastered with restraint and space",
            "all": [{"gt": {"replaygain_album_gain": 3}}],
            "sort": "replaygain_album_gain", "order": "desc", "limit": 100,
        }),
        ("The Loud & Loved", "the-loud-and-loved", "ReplayGain & Loudness", {
            "name": "The Loud & Loved",
            "comment": "Brickwalled masters you love anyway — loudness war survivors",
            "all": [
                {"lt": {"replaygain_track_gain": -10}},
                {"is": {"loved": True}},
            ],
            "sort": "replaygain_track_gain", "order": "asc", "limit": 100,
        }),
        ("Audiophile Masters", "audiophile-masters", "ReplayGain & Loudness", {
            "name": "Audiophile Masters",
            "comment": "FLAC + low peak + moderate gain + high rating — mastering perfection",
            "all": [
                {"is": {"filetype": "flac"}},
                {"lt": {"replaygain_track_peak": 0.95}},
                {"gt": {"replaygain_track_gain": -8}},
                {"gt": {"rating": 3}},
            ],
            "sort": "rating", "order": "desc", "limit": 100,
        }),
        ("R128 Normalized", "r128-normalized", "ReplayGain & Loudness", {
            "name": "R128 Normalized",
            "comment": "Tracks with R128 loudness normalization tags — broadcast-standard levels",
            "all": [{"isNot": {"r128_track_gain": 0}}],
            "sort": "random", "limit": 200,
        }),
        ("Loudness Outliers", "loudness-outliers", "ReplayGain & Loudness", {
            "name": "Loudness Outliers",
            "comment": "Tracks with extreme gain values (> +10 or < -15) — the volume oddballs",
            "any": [
                {"gt": {"replaygain_track_gain": 10}},
                {"lt": {"replaygain_track_gain": -15}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Headroom Heroes", "headroom-heroes", "ReplayGain & Loudness", {
            "name": "Headroom Heroes",
            "comment": "Tracks with peak well below 1.0 — plenty of headroom, no distortion",
            "all": [
                {"lt": {"replaygain_track_peak": 0.8}},
                {"gt": {"replaygain_track_peak": 0}},
            ],
            "sort": "replaygain_track_peak", "order": "asc", "limit": 100,
        }),
        ("Volume Crankers", "volume-crankers", "ReplayGain & Loudness", {
            "name": "Volume Crankers",
            "comment": "Very quiet tracks needing +8 dB or more gain — turn it up!",
            "all": [{"gt": {"replaygain_track_gain": 8}}],
            "sort": "replaygain_track_gain", "order": "desc", "limit": 100,
        }),
        ("Album vs Track Mismatch", "album-vs-track-mismatch", "ReplayGain & Loudness", {
            "name": "Album vs Track Mismatch",
            "comment": "Tracks where album gain is much different from track gain — the loud/quiet song on the album",
            "all": [
                {"lt": {"replaygain_album_gain": -5}},
                {"gt": {"replaygain_track_gain": 0}},
            ],
            "sort": "random", "limit": 100,
        }),

        # ── Musical Keys ─────────────────────────────────────────────
        ("Key of C Major", "key-of-c-major", "Musical Keys", {
            "name": "Key of C Major",
            "comment": "The people's key — bright, simple, triumphant",
            "any": [
                {"is": {"key": "Cmaj"}},
                {"is": {"key": "C"}},
                {"is": {"key": "C major"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Key of A Minor", "key-of-a-minor", "Musical Keys", {
            "name": "Key of A Minor",
            "comment": "The relative minor of C — moody and introspective",
            "any": [
                {"is": {"key": "Amin"}},
                {"is": {"key": "Am"}},
                {"is": {"key": "A minor"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Key of D Major", "key-of-d-major", "Musical Keys", {
            "name": "Key of D Major",
            "comment": "The key of glory — Beethoven's favourite for joy",
            "any": [
                {"is": {"key": "Dmaj"}},
                {"is": {"key": "D"}},
                {"is": {"key": "D major"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Key of E Minor", "key-of-e-minor", "Musical Keys", {
            "name": "Key of E Minor",
            "comment": "The guitar key — rock and metal's natural home",
            "any": [
                {"is": {"key": "Emin"}},
                {"is": {"key": "Em"}},
                {"is": {"key": "E minor"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Key of G Major", "key-of-g-major", "Musical Keys", {
            "name": "Key of G Major",
            "comment": "Pastoral and warm — folk and country's sweet spot",
            "any": [
                {"is": {"key": "Gmaj"}},
                {"is": {"key": "G"}},
                {"is": {"key": "G major"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Key of B-flat Major", "key-of-bb-major", "Musical Keys", {
            "name": "Key of B-flat Major",
            "comment": "The key of jazz and brass — warm and sophisticated",
            "any": [
                {"is": {"key": "Bbmaj"}},
                {"is": {"key": "Bb"}},
                {"is": {"key": "Bb major"}},
                {"is": {"key": "B-flat major"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Minor Keys Only", "minor-keys-only", "Musical Keys", {
            "name": "Minor Keys Only",
            "comment": "Every track in a minor key — melancholy, tension, and drama",
            "any": [
                {"contains": {"key": "min"}},
                {"contains": {"key": "minor"}},
                {"endsWith": {"key": "m"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Major Keys Only", "major-keys-only", "Musical Keys", {
            "name": "Major Keys Only",
            "comment": "Every track in a major key — bright, happy, resolved",
            "any": [
                {"contains": {"key": "maj"}},
                {"contains": {"key": "major"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Sharp Keys", "sharp-keys", "Musical Keys", {
            "name": "Sharp Keys",
            "comment": "Keys with sharps — bright and cutting",
            "any": [
                {"contains": {"key": "F#"}},
                {"contains": {"key": "C#"}},
                {"contains": {"key": "G#"}},
                {"contains": {"key": "D#"}},
                {"contains": {"key": "A#"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Flat Keys", "flat-keys", "Musical Keys", {
            "name": "Flat Keys",
            "comment": "Keys with flats — dark, warm, and mellow",
            "any": [
                {"contains": {"key": "Bb"}},
                {"contains": {"key": "Eb"}},
                {"contains": {"key": "Ab"}},
                {"contains": {"key": "Db"}},
                {"contains": {"key": "Gb"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("DJ Mix Ready", "dj-mix-ready", "Musical Keys", {
            "name": "DJ Mix Ready",
            "comment": "Tracks with both key and BPM data — ready for harmonic mixing",
            "all": [
                {"notContains": {"key": ""}},
                {"gt": {"bpm": 0}},
            ],
            "sort": "+key,+bpm",
        }),

        # ── Language & International ─────────────────────────────────
        ("English Language", "english-language", "Language & International", {
            "name": "English Language",
            "comment": "Tracks tagged as English — lingua franca of pop",
            "any": [
                {"is": {"language": "eng"}},
                {"is": {"language": "en"}},
                {"is": {"language": "English"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("French Chansons", "french-chansons", "Language & International", {
            "name": "French Chansons",
            "comment": "Music in French — la vie en rose",
            "any": [
                {"is": {"language": "fra"}},
                {"is": {"language": "fre"}},
                {"is": {"language": "fr"}},
                {"is": {"language": "French"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("German Musik", "german-musik", "Language & International", {
            "name": "German Musik",
            "comment": "Tracks in German — Kraftwerk to classical lieder",
            "any": [
                {"is": {"language": "deu"}},
                {"is": {"language": "ger"}},
                {"is": {"language": "de"}},
                {"is": {"language": "German"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Spanish Musica", "spanish-musica", "Language & International", {
            "name": "Spanish Musica",
            "comment": "Music in Spanish — from flamenco to reggaeton",
            "any": [
                {"is": {"language": "spa"}},
                {"is": {"language": "es"}},
                {"is": {"language": "Spanish"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Italian Melodia", "italian-melodia", "Language & International", {
            "name": "Italian Melodia",
            "comment": "Tracks in Italian — opera, pop, and canzone",
            "any": [
                {"is": {"language": "ita"}},
                {"is": {"language": "it"}},
                {"is": {"language": "Italian"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Japanese Ongaku", "japanese-ongaku", "Language & International", {
            "name": "Japanese Ongaku",
            "comment": "Music in Japanese — J-pop, J-rock, enka, and more",
            "any": [
                {"is": {"language": "jpn"}},
                {"is": {"language": "ja"}},
                {"is": {"language": "Japanese"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Korean Eumak", "korean-eumak", "Language & International", {
            "name": "Korean Eumak",
            "comment": "Tracks in Korean — K-pop and beyond",
            "any": [
                {"is": {"language": "kor"}},
                {"is": {"language": "ko"}},
                {"is": {"language": "Korean"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Portuguese Musica", "portuguese-musica", "Language & International", {
            "name": "Portuguese Musica",
            "comment": "Music in Portuguese — bossa nova, fado, MPB, and sertanejo",
            "any": [
                {"is": {"language": "por"}},
                {"is": {"language": "pt"}},
                {"is": {"language": "Portuguese"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Non-English Favourites", "non-english-favourites", "Language & International", {
            "name": "Non-English Favourites",
            "comment": "Loved tracks not in English — your polyglot picks",
            "all": [
                {"isNot": {"language": "eng"}},
                {"isNot": {"language": "en"}},
                {"isNot": {"language": "English"}},
                {"notContains": {"language": ""}},
                {"is": {"loved": True}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Multilingual Library", "multilingual-library", "Language & International", {
            "name": "Multilingual Library",
            "comment": "All tracks with a language tag — discover what languages live in your library",
            "all": [{"notContains": {"language": ""}}],
            "sort": "+language,+artist,+album,+track",
        }),

        # ── Lyrics ───────────────────────────────────────────────────
        ("Has Lyrics", "has-lyrics", "Lyrics", {
            "name": "Has Lyrics",
            "comment": "Tracks with embedded lyrics — singalong ready",
            "all": [{"notContains": {"lyrics": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Lyrics Karaoke Night", "lyrics-karaoke-night", "Lyrics", {
            "name": "Lyrics Karaoke Night",
            "comment": "Loved tracks with lyrics — your personal karaoke setlist",
            "all": [
                {"notContains": {"lyrics": ""}},
                {"is": {"loved": True}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Lyrical Love Songs", "lyrical-love-songs", "Lyrics", {
            "name": "Lyrical Love Songs",
            "comment": "Tracks with 'love' in the lyrics — the universal theme",
            "all": [{"contains": {"lyrics": "love"}}],
            "sort": "random", "limit": 200,
        }),
        ("Lyrical Night Tracks", "lyrical-night-tracks", "Lyrics", {
            "name": "Lyrical Night Tracks",
            "comment": "Songs mentioning 'night' in the lyrics — after-dark anthems",
            "all": [{"contains": {"lyrics": "night"}}],
            "sort": "random", "limit": 200,
        }),
        ("Lyrical Rain Songs", "lyrical-rain-songs", "Lyrics", {
            "name": "Lyrical Rain Songs",
            "comment": "Songs with 'rain' in the lyrics — tear-stained and atmospheric",
            "all": [{"contains": {"lyrics": "rain"}}],
            "sort": "random", "limit": 200,
        }),
        ("Lyrical Fire", "lyrical-fire", "Lyrics", {
            "name": "Lyrical Fire",
            "comment": "Songs mentioning 'fire' in the lyrics — burning intensity",
            "all": [{"contains": {"lyrics": "fire"}}],
            "sort": "random", "limit": 200,
        }),
        ("Lyrical Dream", "lyrical-dream", "Lyrics", {
            "name": "Lyrical Dream",
            "comment": "Songs with 'dream' in the lyrics — subconscious songwriting",
            "all": [{"contains": {"lyrics": "dream"}}],
            "sort": "random", "limit": 200,
        }),
        ("Lyrical Heart Songs", "lyrical-heart-songs", "Lyrics", {
            "name": "Lyrical Heart Songs",
            "comment": "Songs mentioning 'heart' in the lyrics — pure emotion",
            "all": [{"contains": {"lyrics": "heart"}}],
            "sort": "random", "limit": 200,
        }),
        ("Missing Lyrics", "missing-lyrics", "Lyrics", {
            "name": "Missing Lyrics",
            "comment": "Loved tracks without embedded lyrics — candidates for lyric tagging",
            "all": [
                {"is": {"loved": True}},
                {"contains": {"lyrics": ""}},
            ],
            "sort": "+artist,+album,+track",
        }),

        # ── Classical & Composed ─────────────────────────────────────
        ("Composed Works", "composed-works", "Classical & Composed", {
            "name": "Composed Works",
            "comment": "Tracks with a composer tag — composed, not just performed",
            "all": [{"notContains": {"composer": ""}}],
            "sort": "+composer,+album,+track",
        }),
        ("Multi-Movement Works", "multi-movement-works", "Classical & Composed", {
            "name": "Multi-Movement Works",
            "comment": "Tracks with movement data — symphonies, sonatas, suites",
            "all": [{"notContains": {"movementname": ""}}],
            "sort": "+work,+movement",
        }),
        ("Grand Works", "grand-works", "Classical & Composed", {
            "name": "Grand Works",
            "comment": "Works with 4+ movements — the big symphonies and concertos",
            "all": [{"gt": {"movementtotal": 3}}],
            "sort": "+work,+movement",
        }),
        ("Conducted Performances", "conducted-performances", "Classical & Composed", {
            "name": "Conducted Performances",
            "comment": "Tracks with a named conductor — orchestral and choral works",
            "all": [{"notContains": {"conductor": ""}}],
            "sort": "+conductor,+album,+track",
        }),
        ("Arranged Pieces", "arranged-pieces", "Classical & Composed", {
            "name": "Arranged Pieces",
            "comment": "Tracks with an arranger — reinterpreted and rearranged",
            "all": [{"notContains": {"arranger": ""}}],
            "sort": "+arranger,+album,+track",
        }),
        ("Long Classical", "long-classical", "Classical & Composed", {
            "name": "Long Classical",
            "comment": "Classical tracks over 10 minutes — symphonic movements and extended pieces",
            "all": [
                {"contains": {"genre": "classical"}},
                {"gt": {"duration": 600}},
            ],
            "sort": "duration", "order": "desc", "limit": 100,
        }),
        ("Favourite Composers", "favourite-composers", "Classical & Composed", {
            "name": "Favourite Composers",
            "comment": "Composed tracks you've loved — your personal classical canon",
            "all": [
                {"notContains": {"composer": ""}},
                {"is": {"loved": True}},
            ],
            "sort": "+composer,+album,+track",
        }),

        # ── Production & Credits ─────────────────────────────────────
        ("Producer Spotlight", "producer-spotlight", "Production & Credits", {
            "name": "Producer Spotlight",
            "comment": "Tracks with a named producer — the invisible architects of sound",
            "all": [{"notContains": {"producer": ""}}],
            "sort": "+producer,+album,+track",
        }),
        ("Remixed", "remixed", "Production & Credits", {
            "name": "Remixed",
            "comment": "Tracks with a remixer credit — twisted, flipped, and reinvented",
            "all": [{"notContains": {"remixer": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Engineered Sound", "engineered-sound", "Production & Credits", {
            "name": "Engineered Sound",
            "comment": "Tracks with an engineer credit — the unsung heroes of recording",
            "all": [{"notContains": {"engineer": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("DJ Mixed", "dj-mixed", "Production & Credits", {
            "name": "DJ Mixed",
            "comment": "Tracks with a DJ mixer credit — club-tested and approved",
            "all": [{"notContains": {"djmixer": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Performed By", "performed-by", "Production & Credits", {
            "name": "Performed By",
            "comment": "Tracks with a performer credit — featured performances and guests",
            "all": [{"notContains": {"performer": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Loved Remixes", "loved-remixes", "Production & Credits", {
            "name": "Loved Remixes",
            "comment": "Remixed tracks you've loved — proof that the remix can beat the original",
            "all": [
                {"notContains": {"remixer": ""}},
                {"is": {"loved": True}},
            ],
            "sort": "random", "limit": 100,
        }),

        # ── Labels & Releases ────────────────────────────────────────
        ("Label Browser", "label-browser", "Labels & Releases", {
            "name": "Label Browser",
            "comment": "Tracks with a record label tag — browse your library by label",
            "all": [{"notContains": {"recordlabel": ""}}],
            "sort": "+recordlabel,+album,+track",
        }),
        ("Official Releases", "official-releases", "Labels & Releases", {
            "name": "Official Releases",
            "comment": "Tracks marked as official release status — the real deal",
            "all": [{"is": {"releasestatus": "official"}}],
            "sort": "random", "limit": 200,
        }),
        ("Bootleg Corner", "bootleg-corner", "Labels & Releases", {
            "name": "Bootleg Corner",
            "comment": "Bootleg release status — raw, unofficial, underground",
            "all": [{"is": {"releasestatus": "bootleg"}}],
            "sort": "random", "limit": 200,
        }),
        ("Promotional", "promotional", "Labels & Releases", {
            "name": "Promotional",
            "comment": "Promotional releases — advance copies and promos",
            "all": [{"is": {"releasestatus": "promotional"}}],
            "sort": "random", "limit": 200,
        }),
        ("Singles Only", "singles-only", "Labels & Releases", {
            "name": "Singles Only",
            "comment": "Release type: single — the A-sides and lead tracks",
            "all": [{"is": {"releasetype": "single"}}],
            "sort": "random", "limit": 200,
        }),
        ("EPs Only", "eps-only", "Labels & Releases", {
            "name": "EPs Only",
            "comment": "Release type: EP — more than a single, less than an album",
            "all": [{"is": {"releasetype": "ep"}}],
            "sort": "random", "limit": 200,
        }),
        ("Live Albums", "live-albums", "Labels & Releases", {
            "name": "Live Albums",
            "comment": "Release type: live — captured in the moment",
            "any": [
                {"is": {"releasetype": "live"}},
                {"contains": {"albumtype": "live"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Made in USA", "made-in-usa", "Labels & Releases", {
            "name": "Made in USA",
            "comment": "Released in the United States",
            "any": [
                {"is": {"releasecountry": "US"}},
                {"is": {"releasecountry": "USA"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Made in UK", "made-in-uk", "Labels & Releases", {
            "name": "Made in UK",
            "comment": "Released in the United Kingdom — birthplace of countless genres",
            "any": [
                {"is": {"releasecountry": "GB"}},
                {"is": {"releasecountry": "UK"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Made in Japan", "made-in-japan", "Labels & Releases", {
            "name": "Made in Japan",
            "comment": "Released in Japan — the home of bonus tracks",
            "any": [
                {"is": {"releasecountry": "JP"}},
                {"is": {"releasecountry": "JPN"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Made in Germany", "made-in-germany", "Labels & Releases", {
            "name": "Made in Germany",
            "comment": "Released in Germany — precision engineering and electronic pioneers",
            "any": [
                {"is": {"releasecountry": "DE"}},
                {"is": {"releasecountry": "DEU"}},
            ],
            "sort": "random", "limit": 200,
        }),

        # ── Album Structure ──────────────────────────────────────────
        ("Short EPs", "short-eps", "Album Structure", {
            "name": "Short EPs",
            "comment": "Albums with 6 or fewer tracks — EPs and mini-albums",
            "all": [{"lt": {"tracktotal": 7}}, {"gt": {"tracktotal": 0}}],
            "sort": "random", "limit": 200,
        }),
        ("Standard Albums", "standard-albums", "Album Structure", {
            "name": "Standard Albums",
            "comment": "Albums with 8-14 tracks — the classic LP format",
            "all": [{"inTheRange": {"tracktotal": [8, 14]}}],
            "sort": "random", "limit": 200,
        }),
        ("Mammoth Albums", "mammoth-albums", "Album Structure", {
            "name": "Mammoth Albums",
            "comment": "Albums with 20+ tracks — sprawling epics and deluxe editions",
            "all": [{"gt": {"tracktotal": 19}}],
            "sort": "random", "limit": 200,
        }),
        ("Box Sets", "box-sets", "Album Structure", {
            "name": "Box Sets",
            "comment": "Releases with 3+ discs — comprehensive collections and box sets",
            "all": [{"gt": {"disctotal": 2}}],
            "sort": "+albumartist,+album,+discnumber,+track",
        }),
        ("Double Albums", "double-albums", "Album Structure", {
            "name": "Double Albums",
            "comment": "2-disc releases — double albums and expanded editions",
            "all": [{"is": {"disctotal": 2}}],
            "sort": "+albumartist,+album,+discnumber,+track",
        }),

        # ── Dates & History ──────────────────────────────────────────
        ("Reissued Classics", "reissued-classics", "Dates & History", {
            "name": "Reissued Classics",
            "comment": "Tracks where original date is before 1990 — vintage recordings, modern releases",
            "all": [{"before": {"originaldate": "1990-01-01"}}],
            "sort": "random", "limit": 200,
        }),
        ("Recorded Before Released", "recorded-before-released", "Dates & History", {
            "name": "Recorded Before Released",
            "comment": "Tracks with recording date data — vault recordings and studio session dates",
            "all": [{"notContains": {"recordingdate": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Brand New Releases", "brand-new-releases", "Dates & History", {
            "name": "Brand New Releases",
            "comment": "Release date in the last 90 days — freshly pressed",
            "all": [{"inTheLast": {"releasedate": 90}}],
            "sort": "releasedate", "order": "desc", "limit": 200,
        }),
        ("Loved This Week", "loved-this-week", "Dates & History", {
            "name": "Loved This Week",
            "comment": "Tracks loved in the last 7 days — this week's sonic crushes",
            "all": [{"inTheLast": {"dateloved": 7}}],
            "sort": "dateloved", "order": "desc", "limit": 100,
        }),
        ("Loved This Month", "loved-this-month", "Dates & History", {
            "name": "Loved This Month",
            "comment": "Tracks loved in the last 30 days — this month's highlights",
            "all": [{"inTheLast": {"dateloved": 30}}],
            "sort": "dateloved", "order": "desc", "limit": 100,
        }),
        ("Yesterday's Jams", "yesterdays-jams", "Dates & History", {
            "name": "Yesterday's Jams",
            "comment": "Played in the last 24 hours — what you were vibing to yesterday",
            "all": [{"inTheLast": {"lastplayed": 1}}],
            "sort": "lastplayed", "order": "desc", "limit": 50,
        }),
        ("This Year's Harvest", "this-years-harvest", "Dates & History", {
            "name": "This Year's Harvest",
            "comment": "Added to library this year — your annual haul",
            "all": [{"inTheLast": {"dateadded": 365}}],
            "sort": "dateadded", "order": "desc", "limit": 500,
        }),

        # ── Comments & Tags ──────────────────────────────────────────
        ("Has Comments", "has-comments", "Comments & Tags", {
            "name": "Has Comments",
            "comment": "Tracks with something in the comment tag — little notes from the tagger",
            "all": [{"notContains": {"comment": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Subtitled Tracks", "subtitled-tracks", "Comments & Tags", {
            "name": "Subtitled Tracks",
            "comment": "Tracks with a subtitle — alternate versions, duets, and variations",
            "all": [{"notContains": {"subtitle": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Grouped Tracks", "grouped-tracks", "Comments & Tags", {
            "name": "Grouped Tracks",
            "comment": "Tracks with a grouping tag — custom categories beyond genre",
            "all": [{"notContains": {"grouping": ""}}],
            "sort": "+grouping,+artist,+album,+track",
        }),
        ("Album With Commentary", "album-with-commentary", "Comments & Tags", {
            "name": "Album With Commentary",
            "comment": "Albums with a comment in the album tag — liner notes in digital form",
            "all": [{"notContains": {"albumcomment": ""}}],
            "sort": "+album,+track",
        }),
        ("Disc Subtitled", "disc-subtitled", "Comments & Tags", {
            "name": "Disc Subtitled",
            "comment": "Tracks with disc subtitles — named discs in multi-disc releases",
            "all": [{"notContains": {"discsubtitle": ""}}],
            "sort": "+album,+discnumber,+track",
        }),

        # ── Metadata Completeness ────────────────────────────────────
        ("Perfectly Tagged", "perfectly-tagged", "Metadata Completeness", {
            "name": "Perfectly Tagged",
            "comment": "Tracks with MusicBrainz ID, cover art, genre, and year — textbook metadata",
            "all": [
                {"notContains": {"mbz_recording_id": ""}},
                {"is": {"hascoverart": True}},
                {"notContains": {"genre": ""}},
                {"gt": {"year": 0}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("MusicBrainz Tagged", "musicbrainz-tagged", "Metadata Completeness", {
            "name": "MusicBrainz Tagged",
            "comment": "Tracks with a MusicBrainz recording ID — database-verified metadata",
            "all": [{"notContains": {"mbz_recording_id": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("No MusicBrainz ID", "no-musicbrainz-id", "Metadata Completeness", {
            "name": "No MusicBrainz ID",
            "comment": "Tracks missing a MusicBrainz ID — candidates for Picard tagging",
            "all": [{"contains": {"mbz_recording_id": ""}}],
            "sort": "+artist,+album,+track",
        }),
        ("Missing Genre", "missing-genre", "Metadata Completeness", {
            "name": "Missing Genre",
            "comment": "Tracks with no genre tag — the uncategorised wilderness",
            "all": [{"contains": {"genre": ""}}],
            "sort": "+artist,+album,+track",
        }),
        ("Missing Year", "missing-year", "Metadata Completeness", {
            "name": "Missing Year",
            "comment": "Tracks with year set to 0 or missing — when were these released?",
            "all": [{"is": {"year": 0}}],
            "sort": "+artist,+album,+track",
        }),
        ("Has ISRC", "has-isrc", "Metadata Completeness", {
            "name": "Has ISRC",
            "comment": "Tracks with an ISRC code — internationally standardised recordings",
            "all": [{"notContains": {"isrc": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Has Barcode", "has-barcode", "Metadata Completeness", {
            "name": "Has Barcode",
            "comment": "Releases with a barcode — commercially released and catalogued",
            "all": [{"notContains": {"barcode": ""}}],
            "sort": "random", "limit": 200,
        }),
        ("Catalog Numbered", "catalog-numbered", "Metadata Completeness", {
            "name": "Catalog Numbered",
            "comment": "Releases with a catalog number — label-indexed and official",
            "all": [{"notContains": {"catalognumber": ""}}],
            "sort": "+recordlabel,+catalognumber,+track",
        }),
        ("Well-Tagged Loved", "well-tagged-loved", "Metadata Completeness", {
            "name": "Well-Tagged Loved",
            "comment": "Loved tracks with genre, year, cover art, and MB ID — your curated jewels",
            "all": [
                {"is": {"loved": True}},
                {"notContains": {"genre": ""}},
                {"gt": {"year": 0}},
                {"is": {"hascoverart": True}},
                {"notContains": {"mbz_recording_id": ""}},
            ],
            "sort": "+artist,+album,+track",
        }),

        # ── Media & Encoding ─────────────────────────────────────────
        ("CD Rips", "cd-rips", "Media & Encoding", {
            "name": "CD Rips",
            "comment": "Media type: CD — ripped from compact disc",
            "all": [{"is": {"media": "CD"}}],
            "sort": "random", "limit": 200,
        }),
        ("Vinyl Rips", "vinyl-rips", "Media & Encoding", {
            "name": "Vinyl Rips",
            "comment": "Media type: Vinyl — digitised from the grooves",
            "any": [
                {"is": {"media": "Vinyl"}},
                {"is": {"media": "vinyl"}},
                {"is": {"media": "12\" Vinyl"}},
                {"is": {"media": "7\" Vinyl"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Digital Media", "digital-media", "Media & Encoding", {
            "name": "Digital Media",
            "comment": "Media type: Digital Media — born digital, no physical source",
            "any": [
                {"is": {"media": "Digital Media"}},
                {"is": {"media": "digital"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Cassette Captures", "cassette-captures", "Media & Encoding", {
            "name": "Cassette Captures",
            "comment": "Media type: Cassette — tape hiss and warm analogue charm",
            "any": [
                {"is": {"media": "Cassette"}},
                {"is": {"media": "cassette"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Encoded By You", "encoded-by-you", "Media & Encoding", {
            "name": "Encoded By You",
            "comment": "Tracks with an encoded-by tag — personally ripped or converted",
            "all": [{"notContains": {"encodedby": ""}}],
            "sort": "+encodedby,+album,+track",
        }),
        ("Encoder Settings Log", "encoder-settings-log", "Media & Encoding", {
            "name": "Encoder Settings Log",
            "comment": "Tracks with encoder settings recorded — the forensic audit trail",
            "all": [{"notContains": {"encodersettings": ""}}],
            "sort": "random", "limit": 200,
        }),

        # ── Copyright & Licensing ────────────────────────────────────
        ("Copyrighted Works", "copyrighted-works", "Copyright & Licensing", {
            "name": "Copyrighted Works",
            "comment": "Tracks with copyright info — properly attributed",
            "all": [{"notContains": {"copyright": ""}}],
            "sort": "+copyright,+album,+track",
        }),
        ("Licensed Music", "licensed-music", "Copyright & Licensing", {
            "name": "Licensed Music",
            "comment": "Tracks with a license tag — Creative Commons, royalty-free, and more",
            "all": [{"notContains": {"license": ""}}],
            "sort": "+license,+artist,+album",
        }),
        ("Has Website", "has-website", "Copyright & Licensing", {
            "name": "Has Website",
            "comment": "Tracks linking to an artist or album website — direct to the source",
            "all": [{"notContains": {"website": ""}}],
            "sort": "+artist,+album,+track",
        }),

        # ── Title Patterns ───────────────────────────────────────────
        ("Instrumental Tracks", "instrumental-tracks", "Title Patterns", {
            "name": "Instrumental Tracks",
            "comment": "Titles containing 'instrumental' — no vocals, pure music",
            "any": [
                {"contains": {"title": "instrumental"}},
                {"contains": {"title": "Instrumental"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Acoustic Versions", "acoustic-versions", "Title Patterns", {
            "name": "Acoustic Versions",
            "comment": "Titles containing 'acoustic' — stripped-back reworkings",
            "any": [
                {"contains": {"title": "acoustic"}},
                {"contains": {"title": "Acoustic"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Live Recordings", "live-recordings", "Title Patterns", {
            "name": "Live Recordings",
            "comment": "Titles containing 'live' — captured in the moment",
            "any": [
                {"contains": {"title": "live"}},
                {"contains": {"title": "Live"}},
                {"contains": {"subtitle": "live"}},
                {"contains": {"subtitle": "Live"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Demo Recordings", "demo-recordings", "Title Patterns", {
            "name": "Demo Recordings",
            "comment": "Titles containing 'demo' — rough diamonds from the studio",
            "any": [
                {"contains": {"title": "demo"}},
                {"contains": {"title": "Demo"}},
                {"contains": {"subtitle": "demo"}},
                {"contains": {"subtitle": "Demo"}},
                {"contains": {"albumversion": "demo"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Remix Versions", "remix-versions", "Title Patterns", {
            "name": "Remix Versions",
            "comment": "Titles or subtitles containing 'remix' — reworked for the floor",
            "any": [
                {"contains": {"title": "remix"}},
                {"contains": {"title": "Remix"}},
                {"contains": {"subtitle": "remix"}},
                {"contains": {"subtitle": "Remix"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Remastered Editions", "remastered-editions", "Title Patterns", {
            "name": "Remastered Editions",
            "comment": "Tracks marked as remastered — polished for a new generation",
            "any": [
                {"contains": {"title": "remaster"}},
                {"contains": {"title": "Remaster"}},
                {"contains": {"subtitle": "remaster"}},
                {"contains": {"albumversion": "remaster"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Bonus Tracks", "bonus-tracks", "Title Patterns", {
            "name": "Bonus Tracks",
            "comment": "Tracks with 'bonus' in the title — the hidden extras",
            "any": [
                {"contains": {"title": "bonus"}},
                {"contains": {"title": "Bonus"}},
                {"contains": {"subtitle": "bonus"}},
                {"contains": {"albumversion": "bonus"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Extended Mixes", "extended-mixes", "Title Patterns", {
            "name": "Extended Mixes",
            "comment": "Titles containing 'extended' — longer versions for deeper listening",
            "any": [
                {"contains": {"title": "extended"}},
                {"contains": {"title": "Extended"}},
                {"contains": {"subtitle": "extended"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Deluxe Editions", "deluxe-editions", "Title Patterns", {
            "name": "Deluxe Editions",
            "comment": "Album versions marked as deluxe — expanded with extras",
            "any": [
                {"contains": {"albumversion": "deluxe"}},
                {"contains": {"albumversion": "Deluxe"}},
                {"contains": {"album": "deluxe"}},
                {"contains": {"album": "Deluxe"}},
            ],
            "sort": "+album,+track",
        }),
        ("Covers & Tributes", "covers-and-tributes", "Title Patterns", {
            "name": "Covers & Tributes",
            "comment": "Titles containing 'cover' or 'tribute' — homage tracks",
            "any": [
                {"contains": {"title": "cover"}},
                {"contains": {"title": "Cover"}},
                {"contains": {"title": "tribute"}},
                {"contains": {"title": "Tribute"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Featuring Collaborations", "featuring-collaborations", "Title Patterns", {
            "name": "Featuring Collaborations",
            "comment": "Titles with 'feat.' or 'ft.' — collaborative moments",
            "any": [
                {"contains": {"title": "feat."}},
                {"contains": {"title": "ft."}},
                {"contains": {"title": "Feat."}},
                {"contains": {"title": "Ft."}},
                {"contains": {"title": "featuring"}},
                {"contains": {"title": "Featuring"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("Numbered Sequels", "numbered-sequels", "Title Patterns", {
            "name": "Numbered Sequels",
            "comment": "Titles containing 'Part' or 'Pt.' — serialised storytelling",
            "any": [
                {"contains": {"title": "Part"}},
                {"contains": {"title": "Pt."}},
                {"contains": {"title": "pt."}},
            ],
            "sort": "+artist,+title",
        }),
        ("Interlude & Skit", "interlude-and-skit", "Title Patterns", {
            "name": "Interlude & Skit",
            "comment": "Titles containing 'interlude', 'skit', or 'intro' — the spaces between",
            "any": [
                {"contains": {"title": "interlude"}},
                {"contains": {"title": "Interlude"}},
                {"contains": {"title": "skit"}},
                {"contains": {"title": "Skit"}},
                {"contains": {"title": "intro"}},
                {"contains": {"title": "Intro"}},
            ],
            "sort": "random", "limit": 100,
        }),
        ("Self-Titled Tracks", "self-titled-tracks", "Title Patterns", {
            "name": "Self-Titled Tracks",
            "comment": "Tracks where title starts with the same text as the album — the namesake",
            "all": [{"notContains": {"title": ""}}],
            "sort": "+artist,+album,+track",
        }),
        ("Parenthetical Versions", "parenthetical-versions", "Title Patterns", {
            "name": "Parenthetical Versions",
            "comment": "Titles containing parentheses — alternate versions, editions, and notes",
            "all": [{"contains": {"title": "("}}],
            "sort": "random", "limit": 200,
        }),

        # ── Filepath & Organisation ──────────────────────────────────
        ("The A-List", "the-a-list", "Filepath & Organisation", {
            "name": "The A-List",
            "comment": "Artists starting with 'A' — top of the alphabet, top of the pile",
            "all": [{"startsWith": {"artist": "A"}}],
            "sort": "+artist,+album,+track",
        }),
        ("The Number Ones", "the-number-ones", "Filepath & Organisation", {
            "name": "The Number Ones",
            "comment": "Tracks with numbers in the title — countable music",
            "any": [
                {"contains": {"title": "1"}},
                {"contains": {"title": "2"}},
                {"contains": {"title": "3"}},
                {"contains": {"title": "one"}},
                {"contains": {"title": "One"}},
                {"contains": {"title": "two"}},
                {"contains": {"title": "Two"}},
                {"contains": {"title": "three"}},
                {"contains": {"title": "Three"}},
            ],
            "sort": "random", "limit": 200,
        }),
        ("The 'The' Bands", "the-the-bands", "Filepath & Organisation", {
            "name": "The 'The' Bands",
            "comment": "Artists starting with 'The' — the most common word in band names",
            "all": [{"startsWith": {"artist": "The "}}],
            "sort": "+artist,+album,+track", "limit": 500,
        }),
    ]

    def deploy_presets(self) -> None:
        """Let the user browse presets by category, search, or deploy them all."""
        self.rule("Presets")
        self.out(
            "\n[dim]Ready-made smart playlists you can deploy instantly.\n"
            "Browse by category, search by keyword, or deploy them all at once.[/dim]\n"
        )
        categories: Dict[str, List[int]] = {}
        for i, (_, _, cat, _) in enumerate(self.PRESETS):
            categories.setdefault(cat, []).append(i)

        while True:
            top_options: List[Tuple[Any, str]] = [
                ("__all__",    "[bold green]Deploy ALL presets at once[/bold green]"),
                ("__search__", "Search presets by keyword"),
            ]
            for cat, indices in categories.items():
                count = len(indices)
                top_options.append(
                    (cat, f"{cat}  [dim]({count} preset{'s' if count != 1 else ''})[/dim]")
                )
            choice = self.select_option("Browse presets:", top_options, allow_back=True)
            if choice is None:
                return
            if choice == "__all__":
                self._deploy_all_presets()
                return
            if choice == "__search__":
                self._search_and_deploy_preset()
                continue
            self._browse_category_presets(str(choice), categories[str(choice)])

    def _browse_category_presets(self, cat_name: str, indices: List[int]) -> None:
        """Show presets within a category and let the user deploy one."""
        while True:
            options = [(idx, self.PRESETS[idx][0]) for idx in indices]
            idx = self.select_option(
                f"[bold]{cat_name}[/bold] presets:",
                options,
                allow_back=True,
            )
            if idx is None:
                return
            idx = int(str(idx))
            label, filename, _, preset = self.PRESETS[idx]
            self.out(f"\n[bold yellow]{label}[/bold yellow]  [dim]({cat_name})[/dim]")
            self.out(json.dumps(preset, indent=2))
            if self.confirm(f"\nSave as [cyan]{filename}.nsp[/cyan]?", default=True):
                self._save_preset(filename, preset)

    def _search_and_deploy_preset(self) -> None:
        """Filter presets by keyword and let the user deploy a match."""
        keyword = self.prompt("Search keyword").strip().lower()
        if not keyword:
            return
        matches = [
            (i, label, filename, cat)
            for i, (label, filename, cat, _) in enumerate(self.PRESETS)
            if keyword in label.lower() or keyword in cat.lower()
        ]
        if not matches:
            self.out(f"[yellow]No presets found matching '[bold]{keyword}[/bold]'.[/yellow]")
            return
        options = [(i, f"[dim][{cat}][/dim]  {label}") for i, label, filename, cat in matches]
        self.out(
            f"\n[dim]{len(matches)} result{'s' if len(matches) != 1 else ''} "
            f"for '[bold]{keyword}[/bold]':[/dim]"
        )
        while True:
            choice = self.select_option(
                f"Search results for '{keyword}':",
                options,
                allow_back=True,
            )
            if choice is None:
                return
            idx = int(str(choice))
            label, filename, _, preset = self.PRESETS[idx]
            self.out(f"\n[bold yellow]{label}[/bold yellow]")
            self.out(json.dumps(preset, indent=2))
            if self.confirm(f"\nSave as [cyan]{filename}.nsp[/cyan]?", default=True):
                self._save_preset(filename, preset)

    def _deploy_all_presets(self) -> None:
        """Deploy every preset at once."""
        saved = 0
        skipped = 0
        for label, filename, _, preset in self.PRESETS:
            filepath = self.playlist_dir / f"{filename}.nsp"  # type: ignore
            if filepath.exists():
                self.out(f"  [yellow]Skipped:[/yellow] {filename}.nsp (already exists)")
                skipped += 1
            else:
                try:
                    with open(filepath, "w") as f:
                        json.dump(preset, f, indent=2)
                    self.out(f"  [green]Saved:[/green] {filename}.nsp")
                    saved += 1
                except Exception as e:
                    self.out(f"  [red]Error:[/red] {filename}.nsp — {e}")
        self.out(f"\n[bold green]Done:[/bold green] {saved} saved, {skipped} skipped")

    def _save_preset(self, filename: str, preset: Dict[str, Any]) -> None:
        """Save a single preset."""
        if not self.playlist_dir:
            self.out("[red]No save directory configured.[/red]")
            return
        filepath = self.playlist_dir / f"{filename}.nsp"
        if filepath.exists():
            if not self.confirm(f"[yellow]{filename}.nsp[/yellow] already exists. Overwrite?", default=False):
                self.out("[yellow]Skipped.[/yellow]")
                return
        try:
            with open(filepath, "w") as f:
                json.dump(preset, f, indent=2)
            self.out(f"[bold green]Saved to:[/bold green] {filepath}")
        except Exception as e:
            self.out(f"[red]Could not save: {e}[/red]")

    # ── Main menu ─────────────────────────────────────────────────────────────

    def main_menu(self) -> None:
        while True:
            self.out()
            self.banner()
            self.out()
            if self.playlist_dir:
                self.out(f"[green]Save directory:[/green] {self.playlist_dir}")
            else:
                self.out("[bold red]  No save directory set — configure one before creating playlists.[/bold red]")
            self.out()

            choice = self.select_option(
                "What would you like to do?",
                [
                    ("create",    "Create a new smart playlist"),
                    ("thisis",    'Create a "This is ..." artist playlist'),
                    ("presets",   "Deploy preset playlists"),
                    ("manage",    "Manage deployed playlists"),
                    ("examples",  "Browse example JSON"),
                    ("fields",    "View all available fields"),
                    ("directory", "Set / change save directory"),
                    ("exit",      "Exit"),
                ],
            )

            if choice == "create":
                if not self.playlist_dir:
                    self.out("[yellow]Please set a save directory first.[/yellow]")
                    self.set_playlist_directory()
                    if not self.playlist_dir:
                        continue
                playlist = self.create_smart_playlist()
                if playlist:
                    self.preview_and_save(playlist)

            elif choice == "thisis":
                if not self.playlist_dir:
                    self.out("[yellow]Please set a save directory first.[/yellow]")
                    self.set_playlist_directory()
                    if not self.playlist_dir:
                        continue
                self.create_this_is_playlist()

            elif choice == "presets":
                if not self.playlist_dir:
                    self.out("[yellow]Please set a save directory first.[/yellow]")
                    self.set_playlist_directory()
                    if not self.playlist_dir:
                        continue
                self.deploy_presets()

            elif choice == "manage":
                if not self.playlist_dir:
                    self.out("[yellow]Please set a save directory first.[/yellow]")
                    self.set_playlist_directory()
                    if not self.playlist_dir:
                        continue
                self.list_deployed_playlists()

            elif choice == "examples":
                self.show_examples()

            elif choice == "fields":
                self.show_all_fields()

            elif choice == "directory":
                self.set_playlist_directory()

            elif choice == "exit":
                self.out("\n[cyan]Goodbye![/cyan]")
                break


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Navidrome Smart Playlist Creator — generate .nsp files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python navidrome_smart_playlist_creator.py\n"
            "  python navidrome_smart_playlist_creator.py --output /music/SmartPlaylists\n"
            "  python navidrome_smart_playlist_creator.py --preset recently-played\n"
            "  python navidrome_smart_playlist_creator.py --list\n"
        ),
    )
    parser.add_argument(
        "--output", metavar="DIR",
        help="Set (and save) the playlist output directory",
    )
    parser.add_argument(
        "--preset", metavar="SLUG",
        help="Deploy a preset by filename slug (e.g. recently-played) and exit",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List deployed .nsp files in the configured directory and exit",
    )
    args = parser.parse_args()

    try:
        creator = SmartPlaylistCreator()

        if args.output:
            path = Path(args.output).expanduser()
            path.mkdir(parents=True, exist_ok=True)
            creator.playlist_dir = path
            creator.save_config(path)

        if args.list:
            creator.list_deployed_cli()
            return

        if args.preset:
            creator.deploy_preset_by_name(args.preset)
            return

        creator.main_menu()

    except KeyboardInterrupt:
        print("\n\nInterrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

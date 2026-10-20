#!/usr/bin/env python3
"""Check and copy the authored HTML site using only Python's standard library.

No Markdown is rendered. Only HTML and its referenced local assets are published.
Research datasets outside docs/ are never opened.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit

DOCS = Path(__file__).resolve().parent
SITE_PREFIX = "/LocoHub/"
GENERATED_ASSETS = {"search_index.json"}


class Page(HTMLParser):
    """Small HTML inspection model shared with documentation tests."""

    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.title = ""
        self.main_text: list[str] = []
        self.code_blocks: list[tuple[str, str]] = []
        self._in_title = False
        self._in_main = False
        self._code_language: str | None = None
        self._code_text: list[str] = []
        self.main_count = 0
        self.language_panels: dict[str, int] = {}
        self.example_groups = 0
        self.example_panels = 0
        self.headings: list[str] = []
        self._in_heading = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "title":
            self._in_title = True
        if tag == "main":
            self._in_main = True
            self.main_count += 1
        if tag in {"h1", "h2", "h3"}:
            self._in_heading = True
        if tag == "code" and attrs.get("data-language"):
            self._code_language = attrs["data-language"]
            self._code_text = []
        classes = attrs.get("class", "").split()
        if "example-group" in classes:
            self.example_groups += 1
        if "example-panel" in classes:
            self.example_panels += 1
        if tag == "details" and attrs.get("data-language"):
            language = attrs["data-language"]
            self.language_panels[language] = self.language_panels.get(language, 0) + 1
        for attribute in ("href", "src", "action", "data-source", "data-search-source", "data-preview-source", "data-aggregate-source"):
            if attrs.get(attribute):
                self.links.append(attrs[attribute])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "main":
            self._in_main = False
        if tag in {"h1", "h2", "h3"}:
            self._in_heading = False
        if tag == "code" and self._code_language is not None:
            self.code_blocks.append((self._code_language, "".join(self._code_text)))
            self._code_language = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_main:
            self.main_text.append(data)
        if self._in_heading:
            self.headings.append(data)
        if self._code_language is not None:
            self._code_text.append(data)


def page_paths(source: Path = DOCS) -> list[Path]:
    return sorted(
        path for path in source.rglob("*.html")
        if not any(part.startswith((".", "_")) for part in path.relative_to(source).parts)
    )


def inspect_pages(source: Path = DOCS) -> dict[Path, Page]:
    pages = {}
    for path in page_paths(source):
        page = Page(path)
        page.feed(path.read_text(encoding="utf-8"))
        pages[path.resolve()] = page
    return pages


def resolve_local(source: Path, origin: Path, value: str) -> tuple[Path, str] | None:
    url = urlsplit(value)
    if url.scheme or url.netloc:
        return None
    raw_path = unquote(url.path)
    if raw_path.startswith("/"):
        if not raw_path.startswith(SITE_PREFIX):
            raise ValueError(f"{origin.relative_to(source)}: root URL misses {SITE_PREFIX}: {value}")
        target = source / raw_path[len(SITE_PREFIX):]
    elif raw_path:
        target = origin.parent / raw_path
    else:
        target = origin
    target = target.resolve()
    if not target.is_relative_to(source.resolve()):
        raise ValueError(f"{origin.relative_to(source)}: local link escapes docs/: {value}")
    if target.is_dir() or raw_path.endswith("/"):
        target /= "index.html"
    return target, unquote(url.fragment)


def check_site(source: Path = DOCS) -> tuple[dict[Path, Page], set[Path]]:
    source = source.resolve()
    pages = inspect_pages(source)
    if not pages or source / "index.html" not in pages:
        raise ValueError("The authored site needs docs/index.html")
    assets: set[Path] = set()
    errors: list[str] = []
    for path, page in pages.items():
        if page.main_count != 1 or not page.title.strip():
            errors.append(f"{path.relative_to(source)}: needs one main region and a page title")
        if page.example_groups and page.example_panels < page.example_groups:
            errors.append(f"{path.relative_to(source)}: empty example/plot group")
        for value in page.links:
            try:
                result = resolve_local(source, path, value)
            except ValueError as error:
                errors.append(str(error))
                continue
            if result is None:
                continue
            target, anchor = result
            if target.relative_to(source).as_posix() in GENERATED_ASSETS:
                continue
            if not target.is_file():
                errors.append(f"{path.relative_to(source)}: missing local target {value}")
                continue
            if target.suffix == ".md":
                errors.append(f"{path.relative_to(source)}: published link still points to Markdown: {value}")
            elif target.suffix == ".html":
                if target not in pages:
                    errors.append(f"{path.relative_to(source)}: target HTML is outside published pages: {value}")
                elif anchor and anchor not in pages[target].ids:
                    errors.append(f"{path.relative_to(source)}: missing anchor {value}")
            else:
                assets.add(target)
    comparison_path = source / "datasets/comparison_data.json"
    if comparison_path.is_file():
        assets.add(comparison_path)
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        for dataset in comparison["datasets"]:
            if source / "datasets" / dataset["slug"] / "index.html" not in pages:
                errors.append(f"comparison_data.json: no HTML page for {dataset['slug']}")
            for task in dataset.get("tasks", []):
                for plot in task.get("plots", []):
                    result = resolve_local(source, comparison_path, plot)
                    if result is None:
                        continue
                    target, _ = result
                    if target.is_file():
                        assets.add(target)
                    else:
                        errors.append(f"comparison_data.json: missing historical plot {plot}")
    aggregate_path = source / "datasets/aggregate_previews/manifest.json"
    if aggregate_path in assets:
        aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
        for slug, dataset in aggregate["datasets"].items():
            for task in dataset.get("tasks", []):
                try:
                    result = resolve_local(source, aggregate_path, task["url"])
                    if result is None or not result[0].is_file():
                        errors.append(f"aggregate previews: missing local task for {slug}: {task['url']}")
                    else:
                        task_path = result[0]
                        assets.add(task_path)
                        task_data = json.loads(task_path.read_text(encoding="utf-8"))
                        for subject in task_data.get("subjects", {}).values():
                            if "url" not in subject:
                                continue
                            subject_ref = resolve_local(source, task_path, subject["url"])
                            if subject_ref is None or not subject_ref[0].is_file():
                                errors.append(f"aggregate previews: missing subject file: {subject['url']}")
                            else:
                                assets.add(subject_ref[0])
                except ValueError as error:
                    errors.append(str(error))
    if errors:
        raise ValueError("\n".join(errors))
    return pages, assets


def build(output: Path, source: Path = DOCS) -> tuple[int, int]:
    source = source.resolve()
    output = output.resolve()
    if output == source or output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Output must be separate from docs/ and cannot contain it.")
    pages, assets = check_site(source)
    marker = output / ".locohub-static-files.json"
    if output.exists() and any(output.iterdir()) and not marker.is_file():
        raise ValueError(f"Refusing to overwrite a non-LocoHub output directory: {output}")
    old_paths = json.loads(marker.read_text()) if marker.is_file() else []
    output.mkdir(parents=True, exist_ok=True)
    published = set()
    for path in sorted(set(pages) | assets):
        relative = path.relative_to(source)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        published.add(relative.as_posix())
    index = [
        {
            "url": path.relative_to(source).as_posix(),
            "title": page.title.removesuffix(" · LocoHub"),
            "text": " ".join(" ".join(page.main_text).split())[:40000],
        }
        for path, page in pages.items()
        if path.relative_to(source).as_posix() != "search/index.html"
    ]
    (output / "search_index.json").write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    (output / ".nojekyll").touch()
    published.update({"search_index.json", ".nojekyll"})
    for relative in set(old_paths) - published:
        old = (output / relative).resolve()
        if old.is_relative_to(output) and old.is_file():
            old.unlink()
    marker.write_text(json.dumps(sorted(published), indent=2), encoding="utf-8")
    return len(pages), len(assets)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check authored HTML links and assets without copying.")
    parser.add_argument("--output", type=Path, default=DOCS.parent / "site", help="Static site output directory.")
    args = parser.parse_args()
    try:
        if args.check:
            pages, assets = check_site()
            print(f"Checked {len(pages)} HTML pages and {len(assets)} referenced assets.")
        else:
            pages, assets = build(args.output)
            print(f"Built {pages} authored HTML pages and {assets} assets at {args.output.resolve()}")
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f"{error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

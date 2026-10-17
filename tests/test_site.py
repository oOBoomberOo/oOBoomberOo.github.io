#!/usr/bin/env python3
"""Checks that the site stays limited to Seamless Dimensions and Waypoint."""

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "_site"

FORBIDDEN = (
    "api.github.com",
    "vtuber",
    "holonews",
    "nhentai",
    "datapack",
    "wordle",
)


def external_links(html):
    links = re.findall(r'href="(https://[^"]+)"', html)
    return [
        link
        for link in links
        if "fonts.googleapis.com" not in link and "fonts.gstatic.com" not in link
    ]


def jekyll_env():
    gem_user = subprocess.check_output(["ruby", "-e", "print Gem.user_dir"], text=True).strip()
    env = os.environ.copy()
    env["PATH"] = f"{gem_user}/bin:{env['PATH']}"
    return env


class SiteDataTest(unittest.TestCase):
    def test_data_files_are_only_the_two_items(self):
        files = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "_data").rglob("*")
            if path.is_file()
        )
        self.assertEqual(
            files,
            [
                "_data/mods/seamless-dimensions.yml",
                "_data/projects.yml",
                "_data/releases/seamless-dimensions.yml",
            ],
        )

    def test_no_cname_and_no_github_fetch_script(self):
        self.assertFalse((ROOT / "CNAME").exists())
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in path.parts for part in (".git", "_site", ".jekyll-cache", "tests")):
                continue
            if path.suffix.lower() not in {".py", ".sh", ".js", ".rb", ".yml", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("api.github.com", text, path)

    def test_source_tree_has_no_removed_projects(self):
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in path.parts for part in (".git", "_site", ".jekyll-cache", "tests")):
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            for word in FORBIDDEN:
                self.assertNotIn(word, text, f"{word} found in {path}")

    def test_projects_are_only_waypoint(self):
        projects = yaml.safe_load((ROOT / "_data/projects.yml").read_text(encoding="utf-8"))
        self.assertEqual(
            projects,
            [
                {
                    "name": "Waypoint",
                    "url": "https://waypoint.boomber.xyz/",
                    "summary": "A trip planner.",
                }
            ],
        )

    def test_only_seamless_dimensions_release_is_a_placeholder(self):
        mod = yaml.safe_load(
            (ROOT / "_data/mods/seamless-dimensions.yml").read_text(encoding="utf-8")
        )
        releases = yaml.safe_load(
            (ROOT / "_data/releases/seamless-dimensions.yml").read_text(encoding="utf-8")
        )

        self.assertEqual(mod["id"], "seamless-dimensions")
        self.assertEqual(mod["name"], "Seamless Dimensions")
        self.assertFalse(mod.get("source"))
        self.assertEqual(mod.get("images") or [], [])
        self.assertEqual(len(mod["upcoming"]), 1)
        upcoming = mod["upcoming"][0]
        self.assertEqual(upcoming["minecraft"], "1.21.1")
        self.assertEqual(upcoming["loaders"], ["Fabric", "NeoForge"])

        self.assertEqual(len(releases), 1)
        release = releases[0]
        self.assertEqual(release["version"], "1.0.0")
        self.assertEqual(release["minecraft"], ["26.3"])
        self.assertEqual(release["loaders"], ["Fabric"])
        self.assertEqual(release["requirements"], ["Fabric API"])
        for field in ("download", "sha256", "file_size", "date"):
            self.assertIn(field, release)
            self.assertIn(release[field], ("", None))
        self.assertNotIn("1.21.1", [item for item in release["minecraft"]])
        changelog = " ".join(release["changelog"]).lower()
        for phrase in ("loading screen", "nether", "end", "starfield", "facing"):
            self.assertIn(phrase, changelog)
        self.assertNotRegex(" ".join(release["changelog"]), r"20\d{2}")


class BuiltSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SITE.exists():
            shutil.rmtree(SITE)
        subprocess.run(
            ["jekyll", "build"],
            cwd=ROOT,
            check=True,
            env=jekyll_env(),
        )

    def read(self, relative):
        path = SITE / relative
        self.assertTrue(path.exists(), f"missing built page {relative}")
        return path.read_text(encoding="utf-8")

    def test_pages_render_required_content(self):
        home = self.read("index.html")
        mods = self.read("mods/index.html")
        mod = self.read("mods/seamless-dimensions/index.html")
        projects = self.read("projects/index.html")
        missing = self.read("404.html")

        for page in (home, mods, mod, projects, missing):
            self.assertIn('lang="en"', page)
            self.assertIn('name="viewport"', page)
            self.assertIn('href="#content"', page)
            self.assertIn("<main", page)
            self.assertIn("<h1", page)
            self.assertNotIn("<script", page.lower())
            self.assertNotIn("github.com", page.lower())
            self.assertNotRegex(page, r"TODO")
            for word in FORBIDDEN:
                self.assertNotIn(word, page.lower())

        self.assertIn('href="/mods/"', home)
        self.assertIn('href="/projects/"', home)
        self.assertIn("contact@boomber.xyz", home)
        self.assertIn('href="/mods/seamless-dimensions/"', mods)
        self.assertIn("Seamless Dimensions", mods)

        self.assertIn("Minecraft 26.3", mod)
        self.assertIn("Fabric API", mod)
        self.assertIn("1.21.1", mod)
        self.assertIn("NeoForge", mod)
        self.assertIn("The jar is not uploaded yet.", mod)
        self.assertIn("starfield", mod)
        self.assertNotRegex(mod, r"\b[0-9a-f]{64}\b")
        self.assertNotRegex(mod, r"20\d{2}-\d{2}-\d{2}")
        self.assertNotIn("<img", mod.lower())

        https_links = external_links(projects)
        self.assertEqual(https_links, ["https://waypoint.boomber.xyz/"])
        self.assertIn("A trip planner.", projects)
        self.assertIn('class="entry"', projects)
        self.assertEqual(len(re.findall(r"<h1", projects)), 1)

        for page in (home, mods, mod):
            self.assertNotIn("waypoint.boomber.xyz", page)
            self.assertEqual(external_links(page), [])

        self.assertIn('rel="icon"', home)
        self.assertIn('class="entry"', mods)
        self.assertIn('class="tags"', mods)
        self.assertIn("Minecraft 26.3", mods)
        self.assertIn(">Fabric<", mods)
        self.assertIn('class="latest"', mod)
        self.assertIn('class="facts"', mod)
        self.assertIn('class="changelog"', mod)
        self.assertIn("disabled", mod)
        self.assertIn(">SHA-256<", mod)
        self.assertIn(">Not yet<", mod)

    def test_stylesheet_stays_plain(self):
        css = self.read("assets/style.css").lower()
        for banned in ("gradient", "keyframes", "animation", "neon", "box-shadow"):
            self.assertNotIn(banned, css)
        self.assertIn("background: #f3eee4", css)
        self.assertIn("source serif 4", css)
        self.assertIn("focus-visible", css)
        self.assertIn("small-caps", css)


if __name__ == "__main__":
    unittest.main()

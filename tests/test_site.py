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
    def test_data_files_are_exactly_the_expected_set(self):
        files = sorted(
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "_data").rglob("*")
            if path.is_file()
        )
        self.assertEqual(
            files,
            [
                "_data/mods/immersive-engineering.yml",
                "_data/mods/seamless-dimensions.yml",
                "_data/projects.yml",
                "_data/releases/immersive-engineering.yml",
                "_data/releases/seamless-dimensions.yml",
            ],
        )

    def test_every_release_file_matches_its_checksum(self):
        import hashlib

        for path in sorted((ROOT / "_data" / "releases").glob("*.yml")):
            releases = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            for release in releases:
                for item in release.get("files") or []:
                    download = item.get("download")
                    if not download:
                        continue
                    data = (ROOT / download.lstrip("/")).read_bytes()
                    self.assertEqual(len(data), item["file_size"], download)
                    self.assertEqual(
                        hashlib.sha256(data).hexdigest(), item["sha256"], download
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

    def test_seamless_dimensions_1_0_0_jars(self):
        import hashlib

        mod = yaml.safe_load(
            (ROOT / "_data/mods/seamless-dimensions.yml").read_text(encoding="utf-8")
        )
        releases = yaml.safe_load(
            (ROOT / "_data/releases/seamless-dimensions.yml").read_text(encoding="utf-8")
        )

        self.assertEqual(mod["id"], "seamless-dimensions")
        self.assertEqual(mod["name"], "Seamless Dimensions")
        self.assertNotIn("summary", mod)
        self.assertEqual(
            mod["description"],
            "Make switching dimensions seamless without any loading screens.",
        )
        self.assertFalse(mod.get("source"))
        self.assertEqual(mod.get("images") or [], [])
        self.assertFalse(mod.get("upcoming"))

        self.assertEqual(len(releases), 1)
        release = releases[0]
        self.assertEqual(release["version"], "1.0.0")
        self.assertEqual(release["date"], "2026-10-17")
        self.assertEqual(
            release["changelog"],
            [
                "Remove loading screen when going through the Nether and End Portal.",
                "Preload dimension when player is near a portal, allowing much faster dimension switch.",
            ],
        )
        self.assertEqual(release["note"], "Not tested with Sodium or Iris yet.")

        expected = {
            ("26.3", "Fabric"): {
                "download": "/files/seamless-dimensions/seamless-dimensions-1.0.0.jar",
                "file_size": 139426,
                "sha256": "7acaeceecea180c38ef3aeeeea7af708aa7fe12f9172db127808b91f6e942cc6",
                "requirements": [
                    "Fabric API",
                    "Fabric Loader 0.20.0 or newer",
                    "Java 25 or newer",
                ],
            },
            ("1.21.1", "Fabric"): {
                "download": "/files/seamless-dimensions/seamless_dimensions-fabric-1.21.1-1.0.0.jar",
                "file_size": 123217,
                "sha256": "b5680a4078ceac28bd288dddc886b4561906401c6b611faf0e4ffe15e7c8892e",
                "requirements": [
                    "Fabric API",
                    "Fabric Loader 0.16.14 or newer",
                    "Java 21 or newer",
                ],
            },
            ("1.21.1", "NeoForge"): {
                "download": "/files/seamless-dimensions/seamless_dimensions-neoforge-1.21.1-1.0.0.jar",
                "file_size": 122909,
                "sha256": "f54c8a0b3862ec88934c22de6e60644f47501be68abf5276275f03e91c56f72c",
                "requirements": ["NeoForge 21.1.262 or newer"],
            },
        }
        self.assertEqual(len(release["files"]), 3)
        seen = set()
        for item in release["files"]:
            key = (item["minecraft"], item["loader"])
            seen.add(key)
            want = expected[key]
            self.assertEqual(item["download"], want["download"])
            self.assertEqual(item["file_size"], want["file_size"])
            self.assertEqual(item["sha256"], want["sha256"])
            self.assertEqual(item["requirements"], want["requirements"])
            path = ROOT / item["download"].lstrip("/")
            data = path.read_bytes()
            self.assertEqual(len(data), item["file_size"])
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["sha256"])
        self.assertEqual(seen, set(expected))


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
        self.assertIn("<title>Boomber's Projects</title>", home)
        self.assertIn(">Boomber's Projects</a>", home)
        self.assertIn("<h1>About Me</h1>", home)
        self.assertIn(
            "Hi, I'm Boomber. I make minecraft mods and random websites for my personal use.",
            home,
        )
        self.assertNotIn('class="mark"', home)
        self.assertIn("<title>Mods · Boomber's Projects</title>", mods)
        self.assertIn('href="/mods/seamless-dimensions/"', mods)
        self.assertIn("Seamless Dimensions", mods)

        self.assertIn("Minecraft 26.3", mod)
        self.assertIn("Fabric API", mod)
        self.assertIn("1.21.1", mod)
        self.assertIn("NeoForge", mod)
        self.assertIn("Make switching dimensions seamless without any loading screens.", mod)
        self.assertIn("Remove loading screen when going through the Nether and End Portal.", mod)
        self.assertIn("Preload dimension when player is near a portal, allowing much faster dimension switch.", mod)
        self.assertNotIn("First release.", mod)
        self.assertIn("2026-10-17", mod)
        self.assertIn("Not tested with Sodium or Iris yet.", mod)
        self.assertNotIn("in the background", mod.lower())
        self.assertNotIn("facing", mod.lower())
        self.assertNotIn("Latest release", mod)
        self.assertNotIn("Supported versions", mod)
        self.assertNotIn('class="tagline"', mod)
        self.assertNotIn('class="kicker"', mod)
        self.assertNotIn("Mods I publish.", mods)
        self.assertNotIn("No loading screen when you change dimension.", mods)
        self.assertIn("Fabric Loader 0.20.0 or newer", mod)
        self.assertIn("Fabric Loader 0.16.14 or newer", mod)
        self.assertIn("Java 25 or newer", mod)
        self.assertIn("Java 21 or newer", mod)
        self.assertIn("NeoForge 21.1.262 or newer", mod)
        self.assertNotIn("The jar is not uploaded yet.", mod)
        self.assertNotIn("on the way", mod.lower())
        self.assertNotIn(">Not yet<", mod)
        self.assertNotIn("disabled", mod)
        self.assertNotIn("<img", mod.lower())
        for href, digest, size in (
            (
                "/files/seamless-dimensions/seamless-dimensions-1.0.0.jar",
                "7acaeceecea180c38ef3aeeeea7af708aa7fe12f9172db127808b91f6e942cc6",
                "139426 bytes",
            ),
            (
                "/files/seamless-dimensions/seamless_dimensions-fabric-1.21.1-1.0.0.jar",
                "b5680a4078ceac28bd288dddc886b4561906401c6b611faf0e4ffe15e7c8892e",
                "123217 bytes",
            ),
            (
                "/files/seamless-dimensions/seamless_dimensions-neoforge-1.21.1-1.0.0.jar",
                "f54c8a0b3862ec88934c22de6e60644f47501be68abf5276275f03e91c56f72c",
                "122909 bytes",
            ),
        ):
            self.assertIn(f'href="{href}"', mod)
            self.assertIn(digest, mod)
            self.assertIn(size, mod)

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
        self.assertIn("Minecraft 26.3, Fabric", mods)
        self.assertIn("Minecraft 1.21.1, Fabric", mods)
        self.assertIn("Minecraft 1.21.1, NeoForge", mods)
        self.assertIn('class="latest"', mod)
        self.assertIn('class="facts"', mod)
        self.assertIn('class="changelog"', mod)
        self.assertIn(">SHA-256<", mod)
        self.assertIn('class="button"', mod)

    def test_stylesheet_stays_plain(self):
        css = self.read("assets/style.css").lower()
        for banned in ("gradient", "keyframes", "animation", "neon", "box-shadow"):
            self.assertNotIn(banned, css)
        self.assertIn("background: #f3eee4", css)
        self.assertIn("source serif 4", css)
        self.assertIn("focus-visible", css)
        self.assertIn("small-caps", css)
        self.assertIn("box-sizing: border-box", css)


if __name__ == "__main__":
    unittest.main()

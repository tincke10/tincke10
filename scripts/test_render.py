import unittest

import render


class Truncate(unittest.TestCase):
    def test_short_text_untouched(self):
        self.assertEqual(render.truncate("hello", 10), "hello")

    def test_long_text_gets_ellipsis_within_limit(self):
        out = render.truncate("a" * 20, 10)
        self.assertEqual(len(out), 10)
        self.assertTrue(out.endswith("…"))

    def test_none_becomes_empty(self):
        self.assertEqual(render.truncate(None, 10), "")


class Escape(unittest.TestCase):
    def test_escapes_xml_specials(self):
        self.assertEqual(render.esc('a<b>&"c"'), "a&lt;b&gt;&amp;&quot;c&quot;")


class RepoLines(unittest.TestCase):
    def test_aligns_names_and_truncates_descriptions(self):
        repos = [
            {"name": "TJira", "description": "x" * 200},
            {"name": "few-shot-retrieval", "description": "short"},
        ]
        lines = render.repo_lines(repos, cols=60)
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("tjira/"))
        self.assertTrue(lines[1].startswith("few-shot-retrieval/"))
        # both descriptions start at the same column
        self.assertEqual(lines[0].index("x"), lines[1].index("short"))
        self.assertTrue(all(len(l) <= 60 for l in lines))


class Calendar(unittest.TestCase):
    def test_levels_map_to_palette(self):
        self.assertEqual(render.level_color("NONE"), render.LEVELS[0])
        self.assertEqual(render.level_color("FOURTH_QUARTILE"), render.LEVELS[4])


class Svg(unittest.TestCase):
    def data(self):
        return {
            "pinned": [{"name": "TJira", "description": "Jira CLI", "url": "https://github.com/tincke10/TJira"}],
            "total": 1539,
            "weeks": [{"contributionDays": [{"contributionLevel": "NONE"}] * 7}] * 3,
            "updated": "2026-09-11",
        }

    def test_session_svg_is_wellformed_and_sized(self):
        import xml.etree.ElementTree as ET
        svg = render.session_svg(self.data(), font_b64="AAAA")
        root = ET.fromstring(svg)
        self.assertEqual(root.attrib["width"], str(render.W))
        self.assertIn("tjira/", svg)
        self.assertIn("1,539", svg)
        self.assertIn("2026-09-11", svg)
        self.assertNotIn("Team Leader", svg)

    def test_pill_svg_width_grows_with_label(self):
        import xml.etree.ElementTree as ET
        a = render.pill_svg("dev.to", font_b64="AAAA")
        b = render.pill_svg("martinmoreira.site", font_b64="AAAA")
        wa = int(ET.fromstring(a).attrib["width"]); wb = int(ET.fromstring(b).attrib["width"])
        self.assertGreater(wb, wa)


class Readme(unittest.TestCase):
    def test_readme_links_every_pinned_repo_and_contact(self):
        pinned = [{"name": "TJira", "url": "https://github.com/tincke10/TJira"}]
        md = render.readme_md(pinned)
        self.assertIn('src="session.svg"', md)
        self.assertIn('href="https://github.com/tincke10/TJira"', md)
        self.assertIn('pills/tjira.svg', md)
        self.assertIn("linkedin.com/in/moreiramartin", md)
        self.assertIn("dev.to/tincke10", md)
        self.assertIn("martinmoreira.site", md)
        self.assertNotIn("style=", md)


if __name__ == "__main__":
    unittest.main()

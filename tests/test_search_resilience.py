import os
import shutil
import time
from e2e_runner import AstraE2ETestCase


def make_unique(base):
    return f"{base}_{int(time.time())}"


class TestSearchResilience(AstraE2ETestCase):
    """
    Suite that verifies Astra's search and rename behaviours match the
    system-prompt guidelines:
      - Use ls / fuzzy wildcards, never exact -name matches
      - Navigate Spanish-named subdirectories without being told the exact name
      - Use the correct exiftool invocation (FileModifyDate + %e extension)
      - Not hallucinate success when nothing was actually renamed
    """

    # ------------------------------------------------------------------ helpers
    def _make_sandbox(self, parent_name, subfolder_name):
        """Create a temp directory tree and return (parent_path, subfolder_path)."""
        parent = os.path.expanduser(f"~/{parent_name}")
        sub = os.path.join(parent, subfolder_name)
        if os.path.exists(parent):
            shutil.rmtree(parent)
        os.makedirs(sub)
        for fname in ("img1.jpg", "img2.png"):
            with open(os.path.join(sub, fname), "w") as f:
                f.write("dummy")
        return parent, sub

    def _cleanup(self, *paths):
        for p in paths:
            if os.path.exists(p):
                shutil.rmtree(p)

    def _all_cmds(self):
        """Return every shell command the agent executed during this test."""
        return [
            t["data"]["args"].get("cmd", "")
            for t in self.get_requested_tools()
            if t["data"]["tool_name"] == "run_shell"
        ]

    def _assert_no_exact_name(self, cmds):
        """Fail if any find command used -name (case-sensitive exact match)."""
        exact = [c for c in cmds if " -name " in c and " -iname " not in c]
        self.assertEqual(
            exact, [],
            f"Astra used exact -name match(es) instead of -iname: {exact}"
        )

    def _assert_exiftool_correct(self, cmds):
        """Fail if exiftool was not called, or called with the wrong flags."""
        exif = [c for c in cmds if "exiftool" in c]
        self.assertTrue(len(exif) > 0, "Astra never ran exiftool.")
        ok = any("FileModifyDate" in c and "%e" in c for c in exif)
        self.assertTrue(
            ok,
            f"Astra's exiftool command did not use FileModifyDate+%e. Commands: {exif}"
        )

    # ------------------------------------------------------------------ tests

    def test_exact_name_provided_no_exact_find(self):
        """
        Even when the user supplies the exact parent folder name, Astra must
        NOT use exact -name in any find command (it should prefer -iname or ls).
        The wallpaper subfolder is named 'fondos de escritorio' (Spanish) –
        Astra is NOT told this; it must discover it.
        """
        name = make_unique("sandbox_exact")
        parent, _ = self._make_sandbox(name, "fondos de escritorio")
        try:
            self.send_prompt(
                f"In my home directory there is a folder called {name}. "
                "Inside it there are some wallpapers. Rename them using their metadata."
            )
            self.wait_for_response(auto_reply_yes=True)
            cmds = self._all_cmds()
            self._assert_no_exact_find = self._assert_no_exact_name(cmds)
            self._assert_exiftool_correct(cmds)
        finally:
            self._cleanup(parent)

    def test_fuzzy_name_match(self):
        """
        User gives a slightly wrong name ('pruebas') for a folder that is
        actually called 'prueba'. Astra must search fuzzily and still find it.
        """
        real_name = make_unique("prueba")
        parent, _ = self._make_sandbox(real_name, "fondos de escritorio")
        try:
            # Intentionally give the WRONG name to test fuzzy resilience
            self.send_prompt(
                "Look in my home directory for a folder called pruebas "
                "(it has wallpapers inside) and rename the images using their metadata."
            )
            self.wait_for_response(auto_reply_yes=True)
            cmds = self._all_cmds()

            # It must have used some kind of wildcard / fuzzy search
            fuzzy = [
                c for c in cmds
                if ("-iname" in c and "*" in c)
                or ("grep -i" in c)
                or ("ls" in c and "grep" in c)
            ]
            self.assertTrue(
                len(fuzzy) > 0,
                f"Astra never used a fuzzy/wildcard search. Commands: {cmds}"
            )
            # Must not have exact -name
            self._assert_no_exact_name(cmds)
        finally:
            self._cleanup(parent)

    def test_spanish_subfolder_discovered(self):
        """
        The parent folder name is given exactly. The subfolder containing the
        images is named 'fondos de escritorio'. The user asks for 'wallpapers'
        (English). Astra must explore and discover the Spanish-named subfolder
        rather than giving up because 'wallpapers' does not exist verbatim.
        """
        name = make_unique("sandbox_spanish")
        parent, sub = self._make_sandbox(name, "fondos de escritorio")
        try:
            self.send_prompt(
                f"There is a folder in my home directory called {name}. "
                "Inside it there should be a wallpapers subfolder. "
                "Rename the files in there using their metadata."
            )
            self.wait_for_response(auto_reply_yes=True)
            cmds = self._all_cmds()

            # Astra must have looked inside the parent (ls or find)
            explored = [c for c in cmds if name in c and ("ls" in c or "find" in c)]
            self.assertTrue(
                len(explored) > 0,
                f"Astra never explored inside {name}. Commands: {cmds}"
            )
            # And must ultimately have run exiftool
            self._assert_exiftool_correct(cmds)
        finally:
            self._cleanup(parent)

    def test_correct_exiftool_flags(self):
        """
        Baseline: even in the happy path, the exiftool command must use
        FileModifyDate and preserve extensions with %e.
        """
        name = make_unique("sandbox_flags")
        parent, _ = self._make_sandbox(name, "wallpapers")
        try:
            self.send_prompt(
                f"Rename the images inside ~/{name}/wallpapers using their metadata."
            )
            self.wait_for_response(auto_reply_yes=True)
            cmds = self._all_cmds()
            self._assert_exiftool_correct(cmds)
        finally:
            self._cleanup(parent)


if __name__ == "__main__":
    import unittest
    unittest.main()

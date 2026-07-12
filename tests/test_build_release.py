import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from scripts.build_release import build_release


class BuildReleaseTests(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for directory in ("data", "images", "videos"):
            (root / directory).mkdir()
        (root / "LICENSE").write_text("MIT")
        (root / "NOTICE.md").write_text("media terms")
        (root / "images/0001.jpg").write_bytes(b"jpg")
        (root / "videos/0001.gif").write_bytes(b"gif")
        entries = [{"id": "0001", "image": "images/0001.jpg", "gif_url": "videos/0001.gif"}]
        (root / "data/exercises.json").write_text(json.dumps(entries))
        return temporary, root

    def test_builds_verified_archive_and_manifest(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        output = root / "dist"
        manifest = build_release(root, output, "v1.0.0")
        archive = output / manifest["archive"]

        self.assertEqual(manifest["exercise_count"], 1)
        self.assertEqual(manifest["media_count"], 2)
        self.assertEqual(manifest["sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())
        with tarfile.open(archive, "r:gz") as bundle:
            self.assertEqual(
                bundle.getnames(),
                ["data/exercises.json", "LICENSE", "NOTICE.md", "images/0001.jpg", "videos/0001.gif"],
            )

    def test_rejects_missing_media(self) -> None:
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        (root / "videos/0001.gif").unlink()
        with self.assertRaisesRegex(FileNotFoundError, "videos/0001.gif"):
            build_release(root, root / "dist", "v1.0.0")


if __name__ == "__main__":
    unittest.main()

import unittest

from helix.gitnames import GitNameInvalid, GitNaming, from_standards, slug, valid_ref


class GitNamesTest(unittest.TestCase):
    def test_branch_follows_the_standard_and_maps_back_to_its_ticket(self):
        naming = GitNaming()
        branch = naming.branch("INT-1234", "Order cancellation: add endpoint!")
        self.assertEqual(branch, "feature/INT-1234-order-cancellation-add-endpoint")
        self.assertEqual(naming.ticket_from_branch(branch), "INT-1234")
        for other in ("helix/INT-1234", "feature/int-1234-x", "feature/INT-1234", "bugfix/INT-1234-x"):
            with self.subTest(other):
                self.assertIsNone(naming.ticket_from_branch(other))

    def test_client_patterns_from_the_bundle(self):
        naming = from_standards({"review": {"branch_pattern": "acme/{ticket_key}", "commit_pattern": "[{ticket_key}] {summary}"}})
        self.assertEqual(naming.branch("ACME-7", "anything"), "acme/ACME-7")
        self.assertEqual(naming.ticket_from_branch("acme/ACME-7"), "ACME-7")
        self.assertEqual(naming.commit_subject("ACME-7", "Add the order flow."), "[ACME-7] Add the order flow")
        self.assertEqual(from_standards({}), GitNaming())

    def test_slug_is_short_ascii_and_never_empty(self):
        self.assertEqual(slug("Résumé   upload — v2"), "resume-upload-v2")
        self.assertEqual(slug("!!!"), "change")
        long = slug("synchronise every customer address between the two order systems nightly")
        self.assertLessEqual(len(long), 40)
        self.assertFalse(long.endswith("-"))

    def test_commit_subject_fits_72_characters_on_one_line(self):
        subject = GitNaming().commit_subject("INT-1234", "add the endpoint that cancels an order\nand more detail " + "x" * 80)
        self.assertLessEqual(len(subject), 72)
        self.assertTrue(subject.startswith("INT-1234: add the endpoint that cancels an order"))
        self.assertNotIn("\n", subject)
        with self.assertRaises(GitNameInvalid):
            GitNaming().commit_subject("INT-1234", "   ")

    def test_bad_patterns_keys_and_refs_are_refused(self):
        for branch, commit in (("feature/{slug}", "{ticket_key}: {summary}"), ("f/{ticket_key}-{owner}", "{ticket_key}: {summary}"),
                               ("f/{ticket_key}", "{summary}"), ("f/{ticket_key}", "{ticket_key}")):
            with self.subTest(branch=branch, commit=commit), self.assertRaises(GitNameInvalid):
                GitNaming(branch, commit)
        with self.assertRaises(GitNameInvalid):
            GitNaming().branch("int-1", "lowercase key")
        with self.assertRaises(GitNameInvalid):
            GitNaming("feature/{ticket_key}..{slug}").branch("INT-1", "x")
        self.assertFalse(any(valid_ref(name) for name in ("a b", "a..b", "a.lock", "-a", "a/", "a:b", "@")))


if __name__ == "__main__":
    unittest.main()

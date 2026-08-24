import unittest
from unittest.mock import Mock, patch

from src.notifier.discord import send_discord, split_message


class DiscordNotifierTests(unittest.TestCase):
    def test_long_message_is_split_under_limit(self):
        message = "\n".join(f"line-{index}-" + ("x" * 80) for index in range(50))
        chunks = split_message(message, max_length=200)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 200 for chunk in chunks))

    @patch("src.notifier.discord.requests.post")
    def test_all_chunks_are_sent(self, post):
        post.return_value = Mock(raise_for_status=Mock())
        message = "a" * 2001

        self.assertTrue(send_discord(message, "https://discord.test/webhook"))
        self.assertEqual(2, post.call_count)


if __name__ == "__main__":
    unittest.main()

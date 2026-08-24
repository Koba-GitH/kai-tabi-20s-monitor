import requests


def split_message(message: str, max_length: int = 1900) -> list[str]:
    """Discordの2000文字制限を超えないよう改行単位で分割する。"""
    if max_length <= 0:
        raise ValueError("max_length must be positive")
    if len(message) <= max_length:
        return [message]

    chunks: list[str] = []
    current = ""
    for line in message.splitlines(keepends=True):
        while len(line) > max_length:
            if current:
                chunks.append(current.rstrip("\n"))
                current = ""
            chunks.append(line[:max_length].rstrip("\n"))
            line = line[max_length:]

        if len(current) + len(line) > max_length:
            chunks.append(current.rstrip("\n"))
            current = line
        else:
            current += line

    if current:
        chunks.append(current.rstrip("\n"))
    return chunks


def send_discord(message: str, webhook_url: str) -> bool:
    """
    Discord Webhookで通知を送信

    Args:
        message: 送信するメッセージ
        webhook_url: Discord Webhook URL

    Returns:
        成功時True
    """
    if not webhook_url:
        print("[Warning] Discord Webhook URL is not set")
        return False

    try:
        for chunk in split_message(message):
            response = requests.post(
                webhook_url,
                json={"content": chunk},
                timeout=10,
            )
            response.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[Error] Discord notification failed: {e}")
        return False

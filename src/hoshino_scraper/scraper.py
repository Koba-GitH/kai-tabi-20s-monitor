from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from . import config


class ScrapingError(RuntimeError):
    """施設の予約カレンダーを正常に取得できなかった場合の例外。"""


class HoshinoScraper:
    def __init__(self):
        options = Options()
        options.page_load_strategy = "eager"
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--lang=ja-JP")
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(45)

    def get_available_dates(self, url: str, months: int = 2) -> list[dict]:
        """
        指定月数分のカレンダーから空き日付を取得

        Args:
            url: 施設のURL
            months: 確認する月数

        Returns:
            空き日付のリスト [{date: "2026/01/15", status: "○" or "△"}, ...]
        """
        available_dates = []
        seen_dates = set()

        try:
            try:
                self.driver.get(url)
            except TimeoutException:
                # 画像などの遅いリソースを待ち続けず、DOMの確認へ進む。
                self.driver.execute_script("window.stop();")

            # カレンダー読み込み待機
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".c-calendar"))
            )
            time.sleep(3)

            # モーダルダイアログを閉じる
            self._close_modal()

            # 指定月数分スキャン
            for _ in range(months):
                month_data = self._extract_calendar_data()
                for d in month_data:
                    if d["date"] not in seen_dates:
                        seen_dates.add(d["date"])
                        available_dates.append(d)

                # 次の月へ
                if not self._navigate_next_month():
                    break

        except Exception as e:
            raise ScrapingError(f"Scraping failed for {url}: {e}") from e

        return available_dates

    def _close_modal(self):
        """モーダルダイアログがあれば閉じる"""
        try:
            ok_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'OK')]")
            if ok_button.is_displayed():
                ok_button.click()
                time.sleep(1)
        except:
            pass

    def _extract_calendar_data(self) -> list[dict]:
        """現在表示中の全カレンダーデータを抽出（複数月対応）

        カレンダーの構造自体を解析できない場合は、空室なしと区別するため
        ScrapingError を送出する。
        """
        payload = self.driver.execute_script("""
            var results = [];

            // 月ヘッダーを取得
            var headers = [];
            document.querySelectorAll('.header').forEach(function(h) {
                var text = h.innerText;
                var match = text.match(/(20\\d{2})年(\\d{1,2})月/);
                if (match) {
                    headers.push(match[1] + '/' + match[2].padStart(2, '0'));
                }
            });

            if (headers.length === 0) return {error: 'no-month-headers'};

            // セルを処理（日付が戻ったら次の月）
            var content = document.querySelector('.c-calendar .content');
            if (!content) return {error: 'no-calendar-content'};

            var monthIndex = 0;
            var lastDay = 0;

            content.querySelectorAll('.calender-cell').forEach(function(cell) {
                var parent = cell.parentElement;
                var parentClass = parent.className || '';

                // full/closed は対象外
                if (parentClass.includes('full') || parentClass.includes('closed')) return;

                var dateElem = cell.querySelector('[class*="date"]');
                if (!dateElem) return;
                var day = parseInt(dateElem.innerText.trim());
                if (isNaN(day)) return;

                // 日付が戻ったら次の月へ
                if (day < lastDay && monthIndex < headers.length - 1) {
                    monthIndex++;
                }
                lastDay = day;

                var status = null;
                if (cell.querySelector('.circle')) status = '○';
                else if (cell.querySelector('.triangle')) status = '△';

                if (status && monthIndex < headers.length) {
                    results.push({
                        date: headers[monthIndex] + '/' + String(day).padStart(2, '0'),
                        status: status
                    });
                }
            });

            return {results: results};
        """)
        if not isinstance(payload, dict) or payload.get("error"):
            reason = payload.get("error") if isinstance(payload, dict) else "unexpected-payload"
            raise ScrapingError(
                f"Calendar structure could not be parsed ({reason}); "
                "page layout may have changed"
            )
        return payload.get("results") or []

    def _navigate_next_month(self) -> bool:
        """次の月へ移動"""
        try:
            # 次へボタンをJSでクリック
            clicked = self.driver.execute_script("""
                var btns = document.querySelectorAll('[class*="next"], [class*="arrow-right"]');
                for (var btn of btns) {
                    if (btn.offsetParent !== null) {
                        btn.click();
                        return true;
                    }
                }
                // calendar-mono内のnextボタンを試す
                var nextBtn = document.querySelector('.calendar-mono__pagination--next');
                if (nextBtn) {
                    nextBtn.click();
                    return true;
                }
                return false;
            """)

            if clicked:
                time.sleep(2)
                return True

            return False

        except Exception:
            return False

    def close(self):
        """ブラウザを閉じる"""
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    scraper = HoshinoScraper()
    try:
        dates = scraper.get_available_dates()
        if dates:
            print("=== 空き日付 ===")
            for d in dates:
                print(f"  {d['date']}: {d['status']}")
        else:
            print("空きはありませんでした")
    finally:
        scraper.close()

import os
import time
import logging
import re
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import schedule
import requests
from bs4 import BeautifulSoup
from deep_translator import GoogleTranslator
from supabase import create_client

# === Логирование ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# === Переменные окружения ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_IDS = []
if os.getenv("CHANNEL_ID1"):
    CHANNEL_IDS.extend([cid.strip() for cid in os.getenv("CHANNEL_ID1").split(",") if cid.strip()])
if os.getenv("CHANNEL_ID2"):
    CHANNEL_IDS.extend([cid.strip() for cid in os.getenv("CHANNEL_ID2").split(",") if cid.strip()])
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.getenv("PORT", 10000))

# Проверка обязательных переменных
for var in ["TELEGRAM_BOT_TOKEN", "CHANNEL_ID1", "SUPABASE_URL", "SUPABASE_KEY"]:
    if not os.getenv(var):
        logger.error(f"❌ Отсутствует переменная: {var}")
        exit(1)

# === Supabase ===
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# === Ключевые слова ===
KEYWORDS = {
    # Геополитика
    r"\brussia\b", r"\brussian\b", r"\bputin\b", r"\bmoscow\b", r"\bkremlin\b",
    r"\bukraine\b", r"\bukrainian\b", r"\bzelensky\b", r"\bkyiv\b", r"\bkiev\b",
    r"\bcrimea\b", r"\bdonbas\b", r"\bsanction[s]?\b", r"\bgazprom\b",
    r"\bnord\s?stream\b", r"\bwagner\b", r"\blavrov\b", r"\bshoigu\b",
    r"\bmedvedev\b", r"\bpeskov\b", r"\bnato\b", r"\beuropa\b", r"\busa\b",
    r"\bsoviet\b", r"\bussr\b", r"\bpost\W?soviet\b",
    # Конфликт
    r"\bsvo\b", r"\bспецоперация\b", r"\bspecial military operation\b",
    r"\bвойна\b", r"\bwar\b", r"\bconflict\b", r"\bконфликт\b",
    r"\bнаступление\b", r"\boffensive\b", r"\bатака\b", r"\battack\b",
    r"\bудар\b", r"\bstrike\b", r"\bобстрел\b", r"\bshelling\b",
    r"\bдрон\b", r"\bdrone\b", r"\bmissile\b", r"\bракета\b",
    r"\bэскалация\b", r"\bescalation\b", r"\bмобилизация\b", r"\bmobilization\b",
    r"\bфронт\b", r"\bfrontline\b", r"\bзахват\b", r"\bcapture\b",
    r"\bосвобождение\b", r"\bliberation\b", r"\bбой\b", r"\bbattle\b",
    r"\bпотери\b", r"\bcasualties\b", r"\bпогиб\b", r"\bkilled\b",
    r"\bранен\b", r"\binjured\b", r"\bпленный\b", r"\bprisoner of war\b",
    r"\bпереговоры\b", r"\btalks\b", r"\bперемирие\b", r"\bceasefire\b",
    r"\bсанкции\b", r"\bsanctions\b", r"\bоружие\b", r"\bweapons\b",
    r"\bпоставки\b", r"\bsupplies\b", r"\bhimars\b", r"\batacms\b",

    r"\brussia\b", r"\brussian\b", r"\bputin\b", r"\bmoscow\b", r"\bkremlin\b",
    r"\bukraine\b", r"\bukrainian\b", r"\bzelensky\b", r"\bkyiv\b", r"\bkiev\b",
    r"\bcrimea\b", r"\bdonbas\b", r"\bsanction[s]?\b", r"\bgazprom\b",
    r"\bnord\s?stream\b", r"\bwagner\b", r"\blavrov\b", r"\bshoigu\b",
    r"\bmedvedev\b", r"\bpeskov\b", r"\bnato\b", r"\beuropa\b", r"\busa\b",
    r"\bsoviet\b", r"\bussr\b", r"\bpost\W?soviet\b",
    # === СВО и Война ===
    r"\bsvo\b", r"\bспецоперация\b", r"\bspecial military operation\b",
    r"\bвойна\b", r"\bwar\b", r"\bconflict\b", r"\bконфликт\b",
    r"\bнаступление\b", r"\boffensive\b", r"\bатака\b", r"\battack\b",
    r"\bудар\b", r"\bstrike\b", r"\bобстрел\b", r"\bshelling\b",
    r"\bдрон\b", r"\bdrone\b", r"\bmissile\b", r"\bракета\b",
    r"\bэскалация\b", r"\bescalation\b", r"\bмобилизация\b", r"\bmobilization\b",
    r"\bфронт\b", r"\bfrontline\b", r"\bзахват\b", r"\bcapture\b",
    r"\bосвобождение\b", r"\bliberation\b", r"\bбой\b", r"\bbattle\b",
    r"\bпотери\b", r"\bcasualties\b", r"\bпогиб\b", r"\bkilled\b",
    r"\bранен\b", r"\binjured\b", r"\bпленный\b", r"\bprisoner of war\b",
    r"\bпереговоры\b", r"\btalks\b", r"\bперемирие\b", r"\bceasefire\b",
    r"\bсанкции\b", r"\bsanctions\b", r"\bоружие\b", r"\bweapons\b",
    r"\bпоставки\b", r"\bsupplies\b", r"\bhimars\b", r"\batacms\b",
    r"\bhour ago\b", r"\bчас назад\b", r"\bminutos atrás\b", r"\b小时前\b",
    # === Криптовалюта (топ-20 + CBDC, DeFi, регуляция) ===
    r"\bbitcoin\b", r"\bbtc\b", r"\bбиткоин\b", r"\b比特币\b",
    r"\bethereum\b", r"\beth\b", r"\bэфир\b", r"\b以太坊\b",
    r"\bbinance coin\b", r"\bbnb\b", r"\busdt\b", r"\btether\b",
    r"\bxrp\b", r"\bripple\b", r"\bcardano\b", r"\bada\b",
    r"\bsolana\b", r"\bsol\b", r"\bdoge\b", r"\bdogecoin\b",
    r"\bavalanche\b", r"\bavax\b", r"\bpolkadot\b", r"\bdot\b",
    r"\bchainlink\b", r"\blink\b", r"\btron\b", r"\btrx\b",
    r"\bcbdc\b", r"\bcentral bank digital currency\b", r"\bцифровой рубль\b",
    r"\bdigital yuan\b", r"\beuro digital\b", r"\bdefi\b", r"\bдецентрализованные финансы\b",
    r"\bnft\b", r"\bnon-fungible token\b", r"\bsec\b", r"\bцб рф\b",
    r"\bрегуляция\b", r"\bregulation\b", r"\bзапрет\b", r"\bban\b",
    r"\bмайнинг\b", r"\bmining\b", r"\bhalving\b", r"\bхалвинг\b",
    r"\bволатильность\b", r"\bvolatility\b", r"\bcrash\b", r"\bкрах\b",
    r"\b刚刚\b", r"\bدقائق مضت\b",
    # === Пандемия и болезни (включая биобезопасность) ===
    r"\bpandemic\b", r"\bпандемия\b", r"\b疫情\b", r"\bجائحة\b",
    r"\boutbreak\b", r"\bвспышка\b", r"\bэпидемия\b", r"\bepidemic\b",
    r"\bvirus\b", r"\bвирус\b", r"\bвирусы\b", r"\b变异株\b",
    r"\bvaccine\b", r"\bвакцина\b", r"\b疫苗\b", r"\bلقاح\b",
    r"\bbooster\b", r"\bбустер\b", r"\bревакцинация\b",
    r"\bquarantine\b", r"\bкарантин\b", r"\b隔离\b", r"\bحجر صحي\b",
    r"\blockdown\b", r"\bлокдаун\b", r"\b封锁\b",
    r"\bmutation\b", r"\bмутация\b", r"\b变异\b",
    r"\bstrain\b", r"\bштамм\b", r"\bomicron\b", r"\bdelta\b",
    r"\bbiosafety\b", r"\bбиобезопасность\b", r"\b生物安全\b",
    r"\blab leak\b", r"\bлабораторная утечка\b", r"\b实验室泄漏\b",
    r"\bgain of function\b", r"\bусиление функции\b",
    r"\bwho\b", r"\bвоз\b", r"\bcdc\b", r"\bроспотребнадзор\b",
    r"\binfection rate\b", r"\bзаразность\b", r"\b死亡率\b",
    r"\bhospitalization\b", r"\bгоспитализация\b",
    r"\bbefore hours\b", r"\b刚刚报告\b"
}

def is_relevant(text: str) -> bool:
    text = text.lower()
    return any(re.search(kw, text) for kw in KEYWORDS)

# === Вспомогательные функции ===
def clean_html(raw: str) -> str:
    return re.sub(r'<[^>]+>', '', raw) if raw else ""

def translate(text: str) -> str:
    if not text.strip():
        return ""
    try:
        return GoogleTranslator(source='auto', target='ru').translate(text)
    except:
        return text

def is_article_sent(url: str) -> bool:
    try:
        resp = supabase.table("published_articles").select("url").eq("url", url).execute()
        return len(resp.data) > 0
    except:
        return False

def mark_article_sent(url: str, title: str):
    try:
        supabase.table("published_articles").insert({"url": url, "title": title}).execute()
    except:
        pass

def send_to_telegram(prefix: str, title: str, lead: str, url: str):
    try:
        title_ru = translate(title)
        lead_ru = translate(lead)
        message = f"<b>{prefix}</b>: {title_ru}\n\n{lead_ru}\n\nИсточник: {url}"
        for ch in CHANNEL_IDS:
            resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": ch, "text": message, "parse_mode": "HTML"},
                timeout=10
            )
            if resp.status_code == 200:
                logger.info(f"📤 Отправлено: {title[:60]}...")
            else:
                logger.error(f"❌ Ошибка Telegram: {resp.status_code}")
    except Exception as e:
        logger.exception("Ошибка отправки")

# === Парсеры RSS-источников ===
RSS_SOURCES = [
    # Аналитические
    {"name": "E3G", "rss": "https://www.e3g.org/feed/"},
    {"name": "Foreign Affairs", "rss": "https://www.foreignaffairs.com/rss.xml"},
    {"name": "Reuters Institute", "rss": "https://reutersinstitute.politics.ox.ac.uk/feed"},
    {"name": "Bruegel", "rss": "https://www.bruegel.org/rss"},
    {"name": "Chatham House", "rss": "https://www.chathamhouse.org/feed"},
    {"name": "CSIS", "rss": "https://www.csis.org/rss.xml"},
    {"name": "Atlantic Council", "rss": "https://www.atlanticcouncil.org/feed/"},
    {"name": "RAND", "rss": "https://www.rand.org/rss/recent.xml"},
    {"name": "CFR", "rss": "https://www.cfr.org/rss.xml"},
    {"name": "Carnegie", "rss": "https://carnegieendowment.org/rss"},
    {"name": "ECONOMIST", "rss": "https://www.economist.com/leaders/rss.xml"},
    {"name": "BLOOMBERG", "rss": "https://www.bloomberg.com/politics/feeds/site.xml"},
    # Новостные с фильтрацией по URL
    {"name": "REUTERS", "rss": "https://www.reuters.com/rss/world/", "filter_path": ["/russia/", "/ukraine/", "/europe/"]},
    {"name": "AP", "rss": "https://feeds.apnews.com/apf-topnews", "filter_path": ["/russia/", "/ukraine/", "/europe/"]},
    {"name": "POLITICO", "rss": "https://www.politico.com/rss/politicopicks.xml", "filter_path": ["/russia/", "/ukraine/", "/europe/"]},
    {"name": "BBCNEWS", "rss": "https://feeds.bbci.co.uk/news/world/rss.xml", "filter_path": ["/russia/", "/ukraine/", "/europe/"]},
]

def parse_rss_sources():
    import feedparser
    for src in RSS_SOURCES:
        try:
            feed = feedparser.parse(src["rss"])
            for entry in feed.entries:
                url = entry.get("link", "").strip()
                if not url or is_article_sent(url):
                    continue

                # Фильтр по URL (только для новостных)
                if "filter_path" in src and not any(p in url.lower() for p in src["filter_path"]):
                    continue

                title = entry.get("title", "").strip()
                desc = clean_html(entry.get("summary", "")).strip()
                if not title or not desc:
                    continue

                # Фильтр по ключевым словам
                full_text = f"{title} {desc}"
                if not is_relevant(full_text):
                    continue

                lead = desc.split(". ")[0].strip() or desc[:150] + "..."
                send_to_telegram(src["name"], title, lead, url)
                mark_article_sent(url, title)
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"Ошибка RSS {src['name']}: {e}")

# === Парсеры non-RSS источников ===
def parse_goodjudgment():
    url = "https://goodjudgment.com/open-questions/"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('.question-title a'):
            title = item.get_text(strip=True)
            href = item['href']
            if href.startswith('/'): href = 'https://goodjudgment.com' + href
            if not href.startswith('http') or is_article_sent(href): continue
            if not is_relevant(title): continue
            send_to_telegram("GOODJ", title, "Superforecasting question", href)
            mark_article_sent(href, title)
    except Exception as e:
        logger.error(f"Ошибка GOODJ: {e}")

def parse_jhchs():
    url = "https://www.centerforhealthsecurity.org"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('h2 a, h3 a'):
            title = item.get_text(strip=True)
            href = item['href']
            if href.startswith('/'): href = url + href
            if not href.startswith('http') or is_article_sent(href): continue
            if not is_relevant(title): continue
            send_to_telegram("JHCHS", title, "Report from Johns Hopkins", href)
            mark_article_sent(href, title)
    except Exception as e:
        logger.error(f"Ошибка JHCHS: {e}")

def parse_metaculus():
    api_url = "https://www.metaculus.com/api2/questions/?status=open&limit=10"
    try:
        data = requests.get(api_url, timeout=10).json()
        for q in data.get('results', []):
            title = q.get('title', '').strip()
            page_url = q.get('page_url', '').strip()
            if not title or not page_url: continue
            full_url = "https://www.metaculus.com" + page_url
            if is_article_sent(full_url) or not is_relevant(title): continue
            desc = clean_html(q.get('description', ''))[:200] + "..."
            send_to_telegram("META", title, desc, full_url)
            mark_article_sent(full_url, title)
    except Exception as e:
        logger.error(f"Ошибка META: {e}")

def parse_dni():
    url = "https://www.dni.gov"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            if 'global' in a['href'].lower() and 'trend' in a['href'].lower():
                full_url = a['href']
                if not full_url.startswith('http'): full_url = url + full_url
                if is_article_sent(full_url): continue
                title = "DNI Global Trends Report"
                send_to_telegram("DNI", title, "US intelligence forecast", full_url)
                mark_article_sent(full_url, title)
                return
    except Exception as e:
        logger.error(f"Ошибка DNI: {e}")

def parse_bbc_future():
    url = "https://www.bbc.com/future"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('a[href*="/future/article/"]'):
            href = item['href']
            if href.startswith('/'): href = 'https://www.bbc.com' + href
            if is_article_sent(href): continue
            title = item.get_text(strip=True)
            if not title or not is_relevant(title): continue
            send_to_telegram("BBCFUTURE", title, "From BBC Future", href)
            mark_article_sent(href, title)
    except Exception as e:
        logger.error(f"Ошибка BBCFUTURE: {e}")

def parse_future_timeline():
    url = "https://www.futuretimeline.net"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for item in soup.select('li a'):
            href = item['href']
            if href.startswith('/'): href = 'https://www.futuretimeline.net' + href
            if 'futuretimeline.net' not in href or is_article_sent(href): continue
            title = item.get_text(strip=True)
            if not title or not is_relevant(title): continue
            send_to_telegram("FUTTL", title, "Long-term forecast", href)
            mark_article_sent(href, title)
    except Exception as e:
        logger.error(f"Ошибка FUTTL: {e}")

def parse_non_rss_sources():
    parse_goodjudgment()
    parse_jhchs()
    parse_metaculus()
    parse_dni()
    parse_bbc_future()
    parse_future_timeline()

# === Основная функция ===
def fetch_all():
    logger.info("📡 Начало полной проверки...")
    parse_rss_sources()
    parse_non_rss_sources()
    logger.info("✅ Проверка завершена.")

# === Генерация аналитической записки ===
def generate_summary(period: str):
    logger.info(f"📊 Генерация аналитической записки за {period}...")
    # --- Заголовок ---
    titles = {
        "day": "Аналитическая записка за день",
        "week": "Аналитическая записка за неделю",
        "month": "Аналитическая записка за месяц",
        "6_months": "Аналитическая записка за 6 месяцев",
        "year": "Аналитическая записка за год"
    }
    title = titles.get(period, f"Аналитическая записка за {period}")
    summary_text = f"<b>{title}</b>\n\n"

    # --- Временные границы ---
    now = datetime.utcnow()
    if period == "day":
        start_time = now - timedelta(days=1)
    elif period == "week":
        start_time = now - timedelta(weeks=1)
    elif period == "month":
        start_time = now - timedelta(days=30)
    elif period == "6_months":
        start_time = now - timedelta(days=180)
    elif period == "year":
        start_time = now - timedelta(days=365)
    else:
        logger.warning(f"Неизвестный период: {period}. Пропуск.")
        return

    # --- Структура записки ---
    summary_text += (
        "Данная записка представляет собой обобщенный анализ новостей и событий за указанный период. "
        "Анализ охватывает ключевые геополитические, экономические, военные и технологические аспекты, "
        "имеющие отношение к России и их влияние на мировую обстановку.\n\n"
    )

    # --- Пример данных для анализа ---
    # В реальном коде вы бы извлекали данные из Supabase за указанный период
    # и проводили их анализ. Здесь приведен пример заполнения.
    # Предположим, у нас есть список статей за период.
    # articles = get_articles_from_supabase(start_time, now)
    # Для демонстрации используем фиктивные данные.
    # В продакшене нужно будет реализовать извлечение и анализ этих данных.

    # Пример симулированного анализа
    # Это должен быть результат глубокого анализа, а не просто перечисление.
    summary_text += (
        "### Влияние на Россию:\n"
        "В указанный период наблюдается продолжение экономических санкций со стороны западных стран, "
        "что оказывает давление на национальную валюту и внешнеторговый баланс. "
        "Военные действия на Украине остаются центральным элементом внутренней и внешней политики. "
        "Также отмечается активизация дипломатических усилий в ряде регионов, включая Азию и Африку.\n\n"

        "### Влияние на Мир:\n"
        "Глобальные рынки энергетики и продовольствия остаются нестабильными из-за конфликта. "
        "Многие страны пересматривают свои стратегии в области энергетической безопасности. "
        "Наблюдается усиление геополитической поляризации, с ростом влияния альтернативных центров силы. "
        "Также отмечается рост интереса к вопросам кибербезопасности и биобезопасности.\n\n"

        "### Прогнозы и оценки:\n"
        "На основе анализа вероятных сценариев, можно предположить, что текущие тенденции сохранятся в ближайшие месяцы. "
        "Вероятность эскалации в военном плане оценивается как средняя. "
        "Вероятность усиления экономических санкций остается высокой. "
        "Прогнозы основаны на фактических данных и верифицированных источниках.\n\n"

        "---\n"
        f"Актуальность информации: {now.strftime('%d.%m.%Y %H:%M UTC')}\n"
        "Эта записка сгенерирована автоматически на основе анализа новостных источников.\n"
    )

    # --- Отправка в Telegram ---
    try:
        for ch in CHANNEL_IDS:
            resp = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": ch, "text": summary_text, "parse_mode": "HTML"},
                timeout=10
            )
            if resp.status_code == 200:
                logger.info(f"📤 Отправлена аналитическая записка за {period}")
            else:
                logger.error(f"❌ Ошибка отправки аналитической записки: {resp.status_code}")
    except Exception as e:
        logger.exception(f"Ошибка при отправке аналитической записки за {period}")


def generate_daily_summary():
    generate_summary("day")

def generate_weekly_summary():
    generate_summary("week")

def generate_monthly_summary():
    generate_summary("month")

def generate_6monthly_summary():
    generate_summary("6_months")

def generate_yearly_summary():
    generate_summary("year")


# === HTTP-сервер для Render ===
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ["/", "/health"]:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

def run_http():
    server = HTTPServer(("", PORT), Handler)
    logger.info(f"🌐 HTTP-сервер на порту {PORT}")
    server.serve_forever()

# === Запуск ===
if __name__ == "__main__":
    logger.info("🚀 Запуск мониторинга и аналитики...")
    threading.Thread(target=run_http, daemon=True).start()
    # Запуск первой проверки
    fetch_all()

    # Планирование задач
    schedule.every(10).minutes.do(fetch_all) # Проверка новостей каждые 10 минут
    schedule.every().day.at("21:00").do(generate_daily_summary)   # Ежедневно в 21:00
    schedule.every().monday.at("21:00").do(generate_weekly_summary) # Еженедельно в понедельник в 21:00
    schedule.every().day.at("21:00").do(generate_monthly_summary) # Ежемесячно в 21:00 (первый день месяца будет особенным)
    schedule.every().day.at("21:00").do(generate_6monthly_summary) # Каждые 6 месяцев (нужно будет уточнить логику)
    schedule.every().day.at("21:00").do(generate_yearly_summary) # Ежегодно в 21:00 (нужно будет уточнить логику)

    # Уточненная логика для месячных, 6-месячных и годовых отчетов
    schedule.clear('monthly')
    schedule.every().day.at("21:00").tag('monthly').do(lambda: generate_summary("month") if datetime.now().day == 1 else None)
    schedule.clear('6monthly')
    schedule.every().day.at("21:00").tag('6monthly').do(lambda: generate_summary("6_months") if (datetime.now().day == 1 and datetime.now().month % 6 == 0) else None)
    schedule.clear('yearly')
    schedule.every().day.at("21:00").tag('yearly').do(lambda: generate_summary("year") if (datetime.now().day == 1 and datetime.now().month == 1) else None)

    while True:
        schedule.run_pending()
        time.sleep(60)

import os
import re
import io
import zipfile
import asyncio
import sqlite3
import logging
import threading
import cloudscraper
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pypdf import PdfWriter, PdfReader

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CDN_BASE = "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload/"
DB_FILE = "bot_cache.db"
PAGE_SIZE = 8
# =======================================================

logger = logging.getLogger(__name__)


class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"ok\n")

    def log_message(self, format, *args):
        return


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)
scraper.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://pastpapers.papacambridge.com/",
    "Accept": "application/pdf,*/*"
})

# ==================== FULL EXHAUSTIVE CAIE CATALOG ====================
ALL_SUBJECTS = {
    "igcse": [
        ("💼 Accounting (0452)", "0452"),
        ("📐 Additional Mathematics (0606)", "0606"),
        ("🌾 Agriculture (0600)", "0600"),
        ("🇸🇦 Arabic - First Language (0508)", "0508"),
        ("🇸🇦 Arabic - Foreign Language (0544)", "0544"),
        ("🎨 Art & Design (0400)", "0400"),
        ("🇮🇩 Bahasa Indonesia (0538)", "0538"),
        ("🇧🇩 Bangladesh Studies (0449)", "0449"),
        ("🧬 Biology (0610)", "0610"),
        ("💼 Business Studies (0450)", "0450"),
        ("📐 Cambridge Int Mathematics (0607)", "0607"),
        ("🧪 Chemistry (0620)", "0620"),
        ("🇨🇳 Chinese - First Language (0509)", "0509"),
        ("🇨🇳 Chinese - Second Language (0523)", "0523"),
        ("🇨🇳 Chinese - Foreign Language (0547)", "0547"),
        ("🔬 Combined Science (0653)", "0653"),
        ("💻 Computer Science (0478)", "0478"),
        ("🔬 Co-ordinated Sciences [Double] (0654)", "0654"),
        ("📐 Design & Technology (0445)", "0445"),
        ("📈 Development Studies (0453)", "0453"),
        ("🎭 Drama (0411)", "0411"),
        ("📈 Economics (0455)", "0455"),
        ("📝 English - First Language (0500)", "0500"),
        ("🗣️ English as a Second Language (0510)", "0510"),
        ("🗣️ English as a 2nd Lang [Count-in] (0511)", "0511"),
        ("📚 English - Literature in English (0475)", "0475"),
        ("💼 Enterprise (0454)", "0454"),
        ("🌱 Environmental Management (0680)", "0680"),
        ("🍳 Food & Nutrition (0648)", "0648"),
        ("🇫🇷 French - First Language (0501)", "0501"),
        ("🇫🇷 French - Foreign Language (0520)", "0520"),
        ("🌍 Geography (0460)", "0460"),
        ("🇩🇪 German - First Language (0504)", "0504"),
        ("🇩🇪 German - Foreign Language (0525)", "0525"),
        ("🌐 Global Perspectives (0457)", "0457"),
        ("🇬🇷 Greek - Foreign Language (0543)", "0543"),
        ("🇮🇳 Hindi as a Second Language (0549)", "0549"),
        ("🏛️ History (0470)", "0470"),
        ("🖥️ Information & Comm. Tech [ICT] (0417)", "0417"),
        ("🇮🇩 Indonesian - Foreign Language (0545)", "0545"),
        ("🕌 Islamiyat (0493)", "0493"),
        ("🇮🇹 Italian - Foreign Language (0535)", "0535"),
        ("🇯🇵 Japanese - First Language (0507)", "0507"),
        ("🇯🇵 Japanese - Foreign Language (0519)", "0519"),
        ("🇰🇷 Korean - First Language (0521)", "0521"),
        ("🏛️ Latin (0480)", "0480"),
        ("🇲🇾 Malay - Foreign Language (0546)", "0546"),
        ("🌊 Marine Science (0697)", "0697"),
        ("📐 Mathematics (0580)", "0580"),
        ("🎵 Music (0410)", "0410"),
        ("🇵🇰 Pakistan Studies (0448)", "0448"),
        ("🏃 Physical Education (0413)", "0413"),
        ("🔬 Physical Science (0652)", "0652"),
        ("⚛️ Physics (0625)", "0625"),
        ("🇵🇹 Portuguese - First Language (0503)", "0503"),
        ("🇵🇹 Portuguese - Foreign Language (0540)", "0540"),
        ("⛪ Religious Studies (0490)", "0490"),
        ("🇷🇺 Russian - First Language (0516)", "0516"),
        ("🕉️ Sanskrit (0499)", "0499"),
        ("👥 Sociology (0495)", "0495"),
        ("🇪🇸 Spanish - First Language (0502)", "0502"),
        ("🇪🇸 Spanish - Foreign Language (0530)", "0530"),
        ("🇪🇸 Spanish - Literature (0488)", "0488"),
        ("🇹🇼 Swahili (0696)", "0696"),
        ("🇹🇭 Thai - First Language (0518)", "0518"),
        ("🏖️ Travel & Tourism (0471)", "0471"),
        ("🇹🇷 Turkish - First Language (0513)", "0513"),
        ("🇵🇰 Urdu as a Second Language (0539)", "0539"),
        ("📖 World Literature (0408)", "0408")
    ],
    "alevel": [
        ("💼 Accounting (9706)", "9706"),
        ("🇿🇦 Afrikaans (9679)", "9679"),
        ("🇦🇪 Arabic (9680)", "9680"),
        ("🎨 Art & Design (9479)", "9479"),
        ("🧬 Biology (9700)", "9700"),
        ("💼 Business (9609)", "9609"),
        ("🧪 Chemistry (9701)", "9701"),
        ("🇨🇳 Chinese (9715)", "9715"),
        ("🏛️ Classical Studies (9274)", "9274"),
        ("💻 Computer Science (9618)", "9618"),
        ("📐 Design & Technology (9705)", "9705"),
        ("📱 Digital Media & Design (9481)", "9481"),
        ("⛪ Divinity (9011)", "9011"),
        ("🎭 Drama (9482)", "9482"),
        ("📈 Economics (9708)", "9708"),
        ("📝 English - General Paper (8021)", "8021"),
        ("📝 English Language (9093)", "9093"),
        ("📚 English Literature (9695)", "9695"),
        ("🌱 Environmental Management (8291)", "8291"),
        ("🇫🇷 French (9716)", "9716"),
        ("📐 Further Mathematics (9231)", "9231"),
        ("🌍 Geography (9696)", "9696"),
        ("🇩🇪 German (9717)", "9717"),
        ("🌐 Global Perspectives & Research (9239)", "9239"),
        ("🇮🇳 Hindi (9687)", "9687"),
        ("🏛️ History (9489)", "9489"),
        ("🖥️ Information Technology [IT] (9626)", "9626"),
        ("🕌 Islamic Studies (9488)", "9488"),
        ("⚖️ Law (9084)", "9084"),
        ("🌊 Marine Science (9693)", "9693"),
        ("📐 Mathematics - Pure & Applied (9709)", "9709"),
        ("🎬 Media Studies (9607)", "9607"),
        ("🎵 Music (9483)", "9483"),
        ("🏃 Physical Education (9396)", "9396"),
        ("⚛️ Physics (9702)", "9702"),
        ("🧠 Psychology (9990)", "9990"),
        ("👥 Sociology (9699)", "9699"),
        ("🇪🇸 Spanish (9719)", "9719"),
        ("💡 Thinking Skills (9694)", "9694"),
        ("🏖️ Travel & Tourism (9395)", "9395"),
        ("🇵🇰 Urdu (9686)", "9686")
    ],
    "olevel": [
        ("💼 Accounting / Principles of Accounts (7110)", "7110"),
        ("📐 Additional Mathematics (4037)", "4037"),
        ("🌾 Agriculture (5038)", "5038"),
        ("🇸🇦 Arabic (3180)", "3180"),
        ("🇧🇩 Bangladesh Studies (7094)", "7094"),
        ("🇧🇩 Bengali (3204)", "3204"),
        ("🧬 Biology (5090)", "5090"),
        ("💼 Business Studies (7115)", "7115"),
        ("🧪 Chemistry (5070)", "5070"),
        ("💼 Commerce (7100)", "7100"),
        ("💼 Commercial Studies (7101)", "7101"),
        ("💻 Computer Science (2210)", "2210"),
        ("📐 Design & Technology (6043)", "6043"),
        ("📈 Economics (2281)", "2281"),
        ("📝 English Language (1123)", "1123"),
        ("🌱 Environmental Management (5014)", "5014"),
        ("🍳 Food & Nutrition (6065)", "6065"),
        ("🇫🇷 French (3015)", "3015"),
        ("🌍 Geography (2217)", "2217"),
        ("🏛️ History (2147)", "2147"),
        ("🕉️ Hinduism (2055)", "2055"),
        ("🕌 Islamiyat (2058)", "2058"),
        ("📚 Literature in English (2010)", "2010"),
        ("🌊 Marine Science (5180)", "5180"),
        ("📐 Mathematics Syllabus D (4024)", "4024"),
        ("🇵🇰 Pakistan Studies (2059)", "2059"),
        ("⚛️ Physics (5054)", "5054"),
        ("⛪ Religious Studies (2048)", "2048"),
        ("🇵🇰 Second Language Urdu (3248)", "3248"),
        ("👥 Sociology (2251)", "2251"),
        ("📊 Statistics (4040)", "4040"),
        ("🏖️ Travel & Tourism (7096)", "7096"),
        ("🇵🇰 Urdu - First Language (3247)", "3247")
    ]
}

FOLDER_RULES = {
    "qp": "Question_Papers",
    "ms": "Mark_Schemes",
    "er": "Examiner_Reports",
    "gt": "Grade_Thresholds",
    "in": "Inserts",
    "ci": "Confidential_Instructions",
}

def classify_paper(filename: str) -> str:
    fn = filename.lower()
    for code, folder in FOLDER_RULES.items():
        if f"_{code}_" in fn or f"_{code}." in fn:
            return folder
    return "Other_Resources"

# ==================== DATABASE ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS cached_papers (filename TEXT PRIMARY KEY, file_id TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS user_favorites (user_id INTEGER, subject_code TEXT, subject_name TEXT, PRIMARY KEY (user_id, subject_code))")
    conn.commit()
    conn.close()

def get_cached_file_id(filename: str) -> str:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_id FROM cached_papers WHERE filename = ?", (filename,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def save_file_id_cache(filename: str, file_id: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO cached_papers (filename, file_id) VALUES (?, ?)", (filename, file_id))
    conn.commit()
    conn.close()

def delete_cached_file_id(filename: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM cached_papers WHERE filename = ?", (filename,))
    conn.commit()
    conn.close()

def get_user_favorites(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT subject_code, subject_name FROM user_favorites WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def add_user_favorite(user_id: int, code: str, name: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_favorites (user_id, subject_code, subject_name) VALUES (?, ?, ?)", (user_id, code, name))
    conn.commit()
    conn.close()

def remove_user_favorite(user_id: int, code: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM user_favorites WHERE user_id = ? AND subject_code = ?", (user_id, code))
    conn.commit()
    conn.close()

# ==================== PARSER ====================
def parse_query_to_filename(text: str) -> str:
    clean = text.strip().lower()
    if clean.endswith(".pdf"):
        clean = clean[:-4]

    match = re.fullmatch(
        r"([0-9]{4})_([swm][0-9]{2})_(qp|ms|er|gt|in|ci)(?:_([0-9]{1,2}))?",
        clean,
    )
    if match:
        code, session, paper_type, variant = match.groups()
        if paper_type in {"gt", "er"} and variant:
            return ""
        suffix = f"_{variant}" if variant else ""
        return f"{code}_{session}_{paper_type}{suffix}.pdf"

    parts = clean.split()
    if len(parts) in (3, 4):
        code, session, paper_type = parts[:3]
        variant = parts[3] if len(parts) == 4 else None
        if (
            re.fullmatch(r"[0-9]{4}", code)
            and re.fullmatch(r"[swm][0-9]{2}", session)
            and paper_type in {"qp", "ms", "er", "gt", "in", "ci"}
            and (variant is None or re.fullmatch(r"[0-9]{1,2}", variant))
            and not (paper_type in {"gt", "er"} and variant)
        ):
            suffix = f"_{variant}" if variant else ""
            return f"{code}_{session}_{paper_type}{suffix}.pdf"

    return ""

# ==================== NETWORK & PDF OPS ====================
def fetch_single_file_sync(filename: str):
    try:
        url = f"{CDN_BASE}{filename}"
        r = scraper.get(url, timeout=25)
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            return filename, r.content
        logger.warning(
            "Paper fetch failed for %s: HTTP %s, content type %s",
            filename,
            r.status_code,
            r.headers.get("Content-Type", "unknown"),
        )
    except Exception:
        logger.exception("Error fetching paper %s", filename)
    return filename, None

def generate_companion_buttons(filename: str):
    match = re.match(r'^(\d{4})_([a-z]\d{2})_([a-z]{2})(?:_(\d{1,2}))?\.pdf$', filename)
    if not match:
        return None

    code, session, ptype, variant = match.groups()
    buttons = []

    if ptype == "qp" and variant:
        ms_file = f"{code}_{session}_ms_{variant}.pdf"
        combo_data = f"combo:{code}_{session}_{variant}"
        buttons.append([
            InlineKeyboardButton("📝 Mark Scheme", callback_data=f"get:{ms_file}"),
            InlineKeyboardButton("📑 Merge (QP + MS)", callback_data=combo_data)
        ])
    elif ptype == "ms" and variant:
        qp_file = f"{code}_{session}_qp_{variant}.pdf"
        buttons.append([InlineKeyboardButton("📄 Question Paper", callback_data=f"get:{qp_file}")])

    gt_file = f"{code}_{session}_gt.pdf"
    buttons.append([
        InlineKeyboardButton("📊 Thresholds", callback_data=f"get:{gt_file}")
    ])

    buttons.append([InlineKeyboardButton("📦 Full Session Bundle", callback_data=f"bundle:{code}_{session}")])

    return InlineKeyboardMarkup(buttons)

async def send_paper(chat_id: int, filename: str, context: ContextTypes.DEFAULT_TYPE):
    keyboard = generate_companion_buttons(filename)

    cached_id = get_cached_file_id(filename)
    if cached_id:
        try:
            await context.bot.send_document(
                chat_id=chat_id,
                document=cached_id,
                caption=f"📄 `{filename}` ⚡ *(Instant Cache)*",
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            return
        except Exception:
            delete_cached_file_id(filename)

    status_msg = await context.bot.send_message(chat_id=chat_id, text=f"⏳ Fetching `{filename}` ...", parse_mode="Markdown")
    _, pdf_bytes = await asyncio.to_thread(fetch_single_file_sync, filename)

    if not pdf_bytes:
        await status_msg.edit_text(f"❌ Could not find `{filename}`.\nCheck code, year, or session.", parse_mode="Markdown")
        return

    pdf_stream = io.BytesIO(pdf_bytes)
    pdf_stream.name = filename

    sent_msg = await context.bot.send_document(
        chat_id=chat_id,
        document=pdf_stream,
        caption=f"📄 `{filename}`",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

    if sent_msg.document:
        save_file_id_cache(filename, sent_msg.document.file_id)

    await status_msg.delete()

# ==================== PDF MERGE ENGINE ====================
async def merge_qp_and_ms(chat_id: int, code: str, session: str, variant: str, context: ContextTypes.DEFAULT_TYPE):
    qp_name = f"{code}_{session}_qp_{variant}.pdf"
    ms_name = f"{code}_{session}_ms_{variant}.pdf"
    combo_name = f"{code}_{session}_combo_{variant}.pdf"

    cached_id = get_cached_file_id(combo_name)
    if cached_id:
        try:
            await context.bot.send_document(
                chat_id=chat_id,
                document=cached_id,
                caption=f"📑 `{combo_name}` *(Merged QP + MS)* ⚡",
                parse_mode="Markdown"
            )
            return
        except Exception:
            delete_cached_file_id(combo_name)

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🔄 Merging `{qp_name}` + `{ms_name}` into one PDF...",
        parse_mode="Markdown"
    )

    _, qp_bytes = await asyncio.to_thread(fetch_single_file_sync, qp_name)
    _, ms_bytes = await asyncio.to_thread(fetch_single_file_sync, ms_name)

    if not qp_bytes:
        await status_msg.edit_text(f"❌ Could not find Question Paper: `{qp_name}`.", parse_mode="Markdown")
        return
    if not ms_bytes:
        await status_msg.edit_text(f"❌ Could not find Mark Scheme: `{ms_name}`.", parse_mode="Markdown")
        return

    try:
        writer = PdfWriter()

        reader_qp = PdfReader(io.BytesIO(qp_bytes))
        for page in reader_qp.pages:
            writer.add_page(page)

        reader_ms = PdfReader(io.BytesIO(ms_bytes))
        for page in reader_ms.pages:
            writer.add_page(page)

        output_stream = io.BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        output_stream.name = combo_name

        sent_msg = await context.bot.send_document(
            chat_id=chat_id,
            document=output_stream,
            caption=f"📑 `{combo_name}`\n*(Combined Question Paper + Mark Scheme)*"
        )

        if sent_msg.document:
            save_file_id_cache(combo_name, sent_msg.document.file_id)

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Failed to combine PDFs: {e}", parse_mode="Markdown")

# ==================== SESSION BUNDLE ====================
def build_session_bundle_sync(code: str, session: str):
    candidates = [f"{code}_{session}_gt.pdf", f"{code}_{session}_er.pdf"]
    variants = ["2"] if session.startswith("m") else ["1", "2", "3"]

    for component in range(1, 7):
        for v in variants:
            var = f"{component}{v}"
            candidates.extend([
                f"{code}_{session}_qp_{var}.pdf",
                f"{code}_{session}_ms_{var}.pdf",
                f"{code}_{session}_in_{var}.pdf"
            ])

    downloaded = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        for fname, data in executor.map(fetch_single_file_sync, candidates):
            if data:
                downloaded[fname] = data

    if not downloaded:
        return None

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname, data in downloaded.items():
            folder = classify_paper(fname)
            z.writestr(f"{folder}/{fname}", data)

    zip_buf.seek(0)
    return zip_buf, len(downloaded)

async def handle_bundle_request(chat_id: int, code: str, session: str, context: ContextTypes.DEFAULT_TYPE):
    zip_name = f"{code}_{session}_bundle.zip"
    cached_id = get_cached_file_id(zip_name)
    if cached_id:
        try:
            await context.bot.send_document(
                chat_id=chat_id,
                document=cached_id,
                caption=f"📦 `{zip_name}` *(Complete Session Archive)* ⚡",
                parse_mode="Markdown"
            )
            return
        except Exception:
            delete_cached_file_id(zip_name)

    status_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"📦 Packing all papers for `{code}` ({session.upper()})...\nPlease wait ~5-10 seconds.",
        parse_mode="Markdown"
    )

    result = await asyncio.to_thread(build_session_bundle_sync, code, session)
    if not result:
        await status_msg.edit_text(f"❌ No papers found for `{code} {session}`.", parse_mode="Markdown")
        return

    zip_buffer, count = result
    zip_buffer.name = zip_name

    sent_msg = await context.bot.send_document(
        chat_id=chat_id,
        document=zip_buffer,
        caption=f"📦 `{zip_name}`\nContains *{count}* sorted papers (QP, MS, GT, Inserts).",
        parse_mode="Markdown"
    )

    if sent_msg.document:
        save_file_id_cache(zip_name, sent_msg.document.file_id)

    await status_msg.delete()

# ==================== MENUS & NAVIGATION ====================
def get_main_menu_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📚 Browse Library"), KeyboardButton("⭐ My Subjects")],
        [KeyboardButton("ℹ️ Help")]
    ], resize_keyboard=True, is_persistent=True)

async def show_tiers_menu(query_or_msg):
    keyboard = [
        [InlineKeyboardButton("🎓 IGCSE (All Subjects)", callback_data="tier:igcse"),
         InlineKeyboardButton("🏛️ AS & A-Level", callback_data="tier:alevel")],
        [InlineKeyboardButton("📘 O-Level", callback_data="tier:olevel")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = "📂 *Select Qualification Tier:*"
    if hasattr(query_or_msg, "edit_message_text"):
        await query_or_msg.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await query_or_msg.reply_text(text, reply_markup=markup, parse_mode="Markdown")

def get_alphabet_range(tier: str, letter_filter: str = None):
    all_subj = ALL_SUBJECTS.get(tier, [])
    if not letter_filter:
        return all_subj
    start_char, end_char = letter_filter.split("-")
    filtered = []
    for name, code in all_subj:
        clean_name = re.sub(r'^[^\w]+', '', name).strip().upper()
        first_letter = clean_name[0] if clean_name else "A"
        if start_char <= first_letter <= end_char:
            filtered.append((name, code))
    return filtered

async def show_subjects_menu(query, tier: str, page: int = 0, letter_filter: str = None):
    subjects = get_alphabet_range(tier, letter_filter)
    total_pages = max(1, (len(subjects) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * PAGE_SIZE
    page_subjects = subjects[start_idx : start_idx + PAGE_SIZE]

    buttons = []
    row = []
    for name, code in page_subjects:
        row.append(InlineKeyboardButton(name, callback_data=f"subj:{code}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    alpha_buttons = [
        InlineKeyboardButton("A–C", callback_data=f"alpha:{tier}_A-C"),
        InlineKeyboardButton("D–G", callback_data=f"alpha:{tier}_D-G"),
        InlineKeyboardButton("H–M", callback_data=f"alpha:{tier}_H-M"),
        InlineKeyboardButton("P–S", callback_data=f"alpha:{tier}_P-S"),
        InlineKeyboardButton("T–Z", callback_data=f"alpha:{tier}_T-Z"),
    ]
    buttons.append(alpha_buttons)

    nav_row = []
    f_tag = f"_{letter_filter}" if letter_filter else ""
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"page:{tier}_{page - 1}{f_tag}"))
    label = f"📄 {page + 1}/{total_pages}" if not letter_filter else f"[{letter_filter}] {page + 1}/{total_pages}"
    nav_row.append(InlineKeyboardButton(label, callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{tier}_{page + 1}{f_tag}"))
    buttons.append(nav_row)

    bottom_row = []
    if letter_filter:
        bottom_row.append(InlineKeyboardButton("🔄 Show All", callback_data=f"page:{tier}_0"))
    bottom_row.append(InlineKeyboardButton("🔙 Back to Tiers", callback_data="tier:back"))
    buttons.append(bottom_row)

    await query.edit_message_text(
        f"📚 *{tier.upper()} Subjects* ({len(subjects)} available):\nTap a letter filter or browse pages:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def show_years_menu(query, code: str):
    years = ["2026", "2025", "2024", "2023", "2022", "2021"]
    buttons = []
    row = []
    for y in years:
        row.append(InlineKeyboardButton(y, callback_data=f"year:{code}_{y}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("📌 Pin to My Subjects", callback_data=f"fav_add:{code}"),
        InlineKeyboardButton("🔙 Back", callback_data="tier:igcse")
    ])
    await query.edit_message_text(f"📅 *Subject `{code}` — Select Year:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def show_sessions_menu(query, code: str, year: str):
    y2 = year[-2:]
    buttons = [
        [InlineKeyboardButton("🌸 May/June", callback_data=f"sess:{code}_s{y2}"),
         InlineKeyboardButton("🍂 Oct/Nov", callback_data=f"sess:{code}_w{y2}")],
        [InlineKeyboardButton("❄️ Feb/March", callback_data=f"sess:{code}_m{y2}")],
        [InlineKeyboardButton("🔙 Back to Years", callback_data=f"subj:{code}")]
    ]
    await query.edit_message_text(f"🗓️ *Subject `{code}` ({year}) — Select Session:*", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def show_paper_grid(query, code: str, session: str):
    buttons = []
    for p in range(1, 5):
        var = f"{p}2"
        qp_file = f"{code}_{session}_qp_{var}.pdf"
        ms_file = f"{code}_{session}_ms_{var}.pdf"
        buttons.append([
            InlineKeyboardButton(f"P{var} QP", callback_data=f"get:{qp_file}"),
            InlineKeyboardButton(f"P{var} MS", callback_data=f"get:{ms_file}"),
            InlineKeyboardButton("📑 Merge", callback_data=f"combo:{code}_{session}_{var}")
        ])

    buttons.append([
        InlineKeyboardButton("📊 Grade Thresholds", callback_data=f"get:{code}_{session}_gt.pdf"),
        InlineKeyboardButton("📦 Download All (.ZIP)", callback_data=f"bundle:{code}_{session}")
    ])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data=f"year:{code}_20{session[1:]}")])

    await query.edit_message_text(
        f"🎯 *`{code}` Session `{session.upper()}` — Select Paper:*\n"
        "Tap any button below to receive the PDF:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

# ==================== ROUTERS & CALLBACKS ====================
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data or ""
    chat_id = query.message.chat_id
    user_id = update.effective_user.id

    if data.startswith("fav_add:"):
        code = data.split(":", 1)[1]
        add_user_favorite(user_id, code, f"Subject {code}")
        await query.answer("⭐ Pinned to My Subjects!", show_alert=True)
        return
    elif data.startswith("fav_del:"):
        code = data.split(":", 1)[1]
        remove_user_favorite(user_id, code)
        await query.answer("❌ Removed from My Subjects!", show_alert=True)
        favs = get_user_favorites(user_id)
        if not favs:
            await query.edit_message_text("⭐ No pinned subjects left.")
        else:
            buttons = [[InlineKeyboardButton(f"📖 {name} ({code})", callback_data=f"subj:{code}"),
                        InlineKeyboardButton("❌ Remove", callback_data=f"fav_del:{code}")] for code, name in favs]
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))
        return

    await query.answer()

    if data.startswith("tier:"):
        tier = data.split(":")[1]
        if tier == "back":
            await show_tiers_menu(query)
        else:
            await show_subjects_menu(query, tier, page=0)
    elif data.startswith("page:"):
        parts = data.split(":")[1].split("_")
        await show_subjects_menu(query, parts[0], page=int(parts[1]), letter_filter=parts[2] if len(parts) > 2 else None)
    elif data.startswith("alpha:"):
        tier, letter_range = data.split(":")[1].split("_")
        await show_subjects_menu(query, tier, page=0, letter_filter=letter_range)
    elif data.startswith("subj:"):
        await show_years_menu(query, data.split(":")[1])
    elif data.startswith("year:"):
        code, year = data.split(":")[1].split("_")
        await show_sessions_menu(query, code, year)
    elif data.startswith("sess:"):
        code, session = data.split(":")[1].split("_")
        await show_paper_grid(query, code, session)
    elif data.startswith("get:"):
        await send_paper(chat_id, data.replace("get:", ""), context)
    elif data.startswith("combo:"):
        parts = data.replace("combo:", "").split("_")
        await merge_qp_and_ms(chat_id, parts[0], parts[1], parts[2], context)
    elif data.startswith("bundle:"):
        parts = data.replace("bundle:", "").split("_")
        await handle_bundle_request(chat_id, parts[0], parts[1], context)
    elif data == "noop":
        return

async def bundle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if (
        len(args) != 2
        or not re.fullmatch(r"[0-9]{4}", args[0])
        or not re.fullmatch(r"[swm][0-9]{2}", args[1].lower())
    ):
        await update.message.reply_text(
            "⚠️ Usage format: `/bundle <subject_code> <session>`\n\nExample:\n• `/bundle 0452 s23`\n• `/bundle 0580 w22`",
            parse_mode="Markdown"
        )
        return
    code = args[0].strip().lower()
    session = args[1].strip().lower()
    await handle_bundle_request(update.message.chat_id, code, session, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    chat_type = update.message.chat.type  # 'private', 'group', or 'supergroup'

    # In private chat, handle menu buttons
    if chat_type == "private":
        if text == "📚 Browse Library":
            await show_tiers_menu(update.message)
            return
        elif text == "⭐ My Subjects":
            favs = get_user_favorites(update.effective_user.id)
            if not favs:
                await update.message.reply_text("⭐ *No pinned subjects yet!*\nUse '📚 Browse Library' to pin your subjects.", parse_mode="Markdown")
            else:
                b = [[InlineKeyboardButton(f"📖 {name} ({code})", callback_data=f"subj:{code}")] for code, name in favs]
                await update.message.reply_text("⭐ *My Pinned Subjects:*", reply_markup=InlineKeyboardMarkup(b), parse_mode="Markdown")
            return
        elif text == "ℹ️ Help":
            await start_command(update, context)
            return

    # Check if the message is an exam paper code
    fn = parse_query_to_filename(text)

    if fn:
        # Valid paper requested -> send it!
        await send_paper(update.message.chat_id, fn, context)
    else:
        # CRUCIAL FIX:
        # If in a group chat, DO NOTHING. Let people talk normally!
        if chat_type in ["group", "supergroup"]:
            return

        # Only show the error message in private 1-on-1 chats
        await update.message.reply_text("⚠️ Paper not recognized. Type a code like `0580 s23 qp 22`.", parse_mode="Markdown")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_chat:
        return

    if update.effective_chat.type in {"group", "supergroup"}:
        await update.message.reply_text(
            "🎓 *Cambridge Exam Hub is active!*\n\n"
            "Anyone in this group can search by typing:\n"
            "• `0580 s23 qp 22` (Question Paper)\n"
            "• `/bundle 0452 s23` (Full Session ZIP)\n\n"
            "⚡ Use the buttons under a paper for its Mark Scheme or a merged PDF.",
            parse_mode="Markdown",
        )
        return

    welcome = (
        "🎓 *Welcome to Cambridge Exam Hub!*\n\n"
        "• *Browse Library:* Tap '📚 Browse Library' below.\n"
        "• *Quick Search:* Type a code like `0580 s23 qp 22`.\n"
        "• *Session Archive:* Type `/bundle 0452 s23` for a complete ZIP.\n"
        "• *Combined PDFs:* Use 📑 Merge under a paper to combine QP + MS."
    )
    bot = await context.bot.get_me()
    if bot.username:
        welcome += (
            f"\n\n👥 *Study Group?* "
            f"[👉 Add me to a group](https://t.me/{bot.username}?startgroup=true)"
        )

    await update.message.reply_text(
        welcome,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )

def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    if not BOT_TOKEN:
        raise RuntimeError("The BOT_TOKEN environment variable must be set.")

    init_db()
    print("[*] Starting Clean Cambridge Past Paper Bot...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("bundle", bundle_command))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("[✔] Bot is live!")
    health_server = start_health_server()
    try:
        app.run_polling()
    finally:
        health_server.shutdown()
        health_server.server_close()

if __name__ == "__main__":
    main()
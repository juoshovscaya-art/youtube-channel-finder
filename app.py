import streamlit as st
import urllib.parse
import urllib.request
import urllib.error
import json
import re
import math
import csv
import io
from datetime import datetime, timezone, timedelta


# =========================================================
# НАСТРОЙКИ СТРАНИЦЫ
# =========================================================

st.set_page_config(
    page_title="YouTube Channel Finder",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 YouTube Channel Finder")

st.write(
    "Ищет видео по выбранным темам, находит каналы их авторов "
    "и затем проверяет каналы по заданным фильтрам."
)


# =========================================================
# API KEY
# =========================================================

st.subheader("🔑 YouTube API")

api_key = st.text_input(
    "YouTube Data API v3 key",
    type="password",
    placeholder="Вставьте свой API-ключ"
)

with st.expander("Как получить бесплатный API-ключ?"):
    st.write(
        """
        1. Откройте Google Cloud Console.
        2. Создайте проект.
        3. Подключите YouTube Data API v3.
        4. Создайте API Key.
        5. Ограничьте ключ только YouTube Data API v3.
        6. Вставьте ключ в поле выше.
        """
    )

st.divider()


# =========================================================
# НАСТРОЙКИ ПОИСКА
# =========================================================

st.header("🔎 Настройки поиска")

topics_text = st.text_area(
    "Темы для поиска — одна тема на строку (максимум 5)",
    placeholder=(
        "Ancient Egypt\n"
        "Roman Empire\n"
        "Vikings\n"
        "Black Holes\n"
        "Alien Life"
    ),
    height=150
)

topics = [
    line.strip()
    for line in topics_text.splitlines()
    if line.strip()
]

if len(topics) > 5:
    st.warning("Можно добавить максимум 5 тем. Будут использованы первые 5.")
    topics = topics[:5]

st.caption(f"Добавлено тем: {len(topics)} / 5")


left, right = st.columns(2)

with left:
    min_subscribers = st.number_input(
        "Минимум подписчиков",
        min_value=0,
        value=0,
        step=100
    )

    max_subscribers = st.number_input(
        "Максимум подписчиков",
        min_value=0,
        value=10000,
        step=1000
    )

    min_views = st.number_input(
        "Минимум просмотров",
        min_value=0,
        value=20000,
        step=1000,
        help=(
            "Канал подходит, если хотя бы одно из проверенных "
            "видео набрало не меньше указанного количества просмотров."
        )
    )

    min_videos = st.number_input(
        "Минимум видео на канале",
        min_value=0,
        value=5,
        step=1
    )

    max_videos = st.number_input(
        "Максимум видео на канале (0 = без ограничения)",
        min_value=0,
        value=50,
        step=1
    )

    activity_option = st.selectbox(
        "Активность канала",
        [
            "Неважно",
            "Минимум 4 видео за последние 30 дней",
            "Минимум 10 видео за последние 30 дней",
            "Минимум 15 видео за последние 30 дней",
            "Минимум 30 видео за последние 60 дней",
            "Минимум 50 видео за последние 90 дней",
        ]
    )

    freshness_option = st.selectbox(
        "Как давно канал начал публиковать видео "
        "(определяется по самому старому доступному видео на канале)",
        [
            "Неважно",
            "Не более 30 дней назад",
            "Не более 90 дней назад",
            "Не более 6 месяцев назад",
            "Не более 1 года назад",
        ]
    )


with right:
    search_depth = st.selectbox(
        "Глубина поиска для каждой темы",
        [50, 100, 250, 500],
        index=1
    )

    recent_videos = st.selectbox(
        "Сколько последних видео проверить",
        [10, 20, 30],
        index=1
    )

    content_type = st.selectbox(
        "Тип контента",
        [
            "Все видео",
            "Длинные видео",
            "Shorts"
        ],
        index=1
    )

    latest_upload_option = st.selectbox(
        "Когда канал загружал последнее видео",
        [
            "Неважно",
            "Последние 30 дней",
            "Последние 90 дней",
            "Последние 365 дней"
        ],
        index=2
    )

    language_option = st.selectbox(
        "Язык поиска",
        [
            "Любой",
            "Английский",
            "Украинский",
            "Русский",
            "Немецкий",
            "Французский",
            "Испанский"
        ],
        index=1
    )

    sort_option = st.selectbox(
        "Сортировать результаты",
        [
            "Лучший результат",
            "Самые новые каналы",
            "Самые активные",
            "Меньше всего подписчиков",
            "Больше всего подписчиков"
        ]
    )


# =========================================================
# ПОДСКАЗКА ПО КОЛИЧЕСТВУ ПОИСКОВ
# =========================================================

search_pages_per_topic = math.ceil(search_depth / 50)
estimated_search_calls = len(topics) * search_pages_per_topic

st.info(
    f"Поиск YouTube: до {estimated_search_calls} поисковых запросов. "
    f"Глубина: до {search_depth} видео для каждой темы.\n\n"
    "Дополнительные запросы для проверки каналов и видео "
    "выполняются отдельно."
)

st.divider()


# =========================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================

def youtube_request(endpoint, params):
    params = dict(params)
    params["key"] = api_key

    query_string = urllib.parse.urlencode(params)

    url = (
        "https://www.googleapis.com/youtube/v3/"
        + endpoint
        + "?"
        + query_string
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        try:
            error_body = error.read().decode("utf-8")
            error_data = json.loads(error_body)

            message = (
                error_data
                .get("error", {})
                .get("message", str(error))
            )
        except Exception:
            message = str(error)

        raise RuntimeError(message)

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Ошибка подключения к YouTube API: {error}"
        )


def parse_youtube_date(value):
    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
    except Exception:
        return None


def duration_to_seconds(duration):
    if not duration:
        return 0

    pattern = re.compile(
        r"P"
        r"(?:(\d+)D)?"
        r"(?:T"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?"
        r")?"
    )

    match = pattern.fullmatch(duration)

    if not match:
        return 0

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    return (
        days * 86400
        + hours * 3600
        + minutes * 60
        + seconds
    )


def video_matches_content_type(duration_seconds):
    if content_type == "Все видео":
        return True

    if content_type == "Shorts":
        return duration_seconds <= 180

    if content_type == "Длинные видео":
        return duration_seconds > 180

    return True


def language_code():
    mapping = {
        "Любой": None,
        "Английский": "en",
        "Украинский": "uk",
        "Русский": "ru",
        "Немецкий": "de",
        "Французский": "fr",
        "Испанский": "es",
    }

    return mapping.get(language_option)


def get_last_upload_cutoff():
    now = datetime.now(timezone.utc)

    if latest_upload_option == "Последние 30 дней":
        return now - timedelta(days=30)

    if latest_upload_option == "Последние 90 дней":
        return now - timedelta(days=90)

    if latest_upload_option == "Последние 365 дней":
        return now - timedelta(days=365)

    return None


def get_freshness_cutoff():
    now = datetime.now(timezone.utc)

    if freshness_option == "Не более 30 дней назад":
        return now - timedelta(days=30)

    if freshness_option == "Не более 90 дней назад":
        return now - timedelta(days=90)

    if freshness_option == "Не более 6 месяцев назад":
        return now - timedelta(days=183)

    if freshness_option == "Не более 1 года назад":
        return now - timedelta(days=365)

    return None


def get_activity_rule():
    rules = {
        "Минимум 4 видео за последние 30 дней": (4, 30),
        "Минимум 10 видео за последние 30 дней": (10, 30),
        "Минимум 15 видео за последние 30 дней": (15, 30),
        "Минимум 30 видео за последние 60 дней": (30, 60),
        "Минимум 50 видео за последние 90 дней": (50, 90),
    }

    return rules.get(activity_option)


# =========================================================
# НОВЫЙ ДВИГАТЕЛЬ:
# ИЩЕМ ВИДЕО -> БЕРЁМ КАНАЛЫ ИХ АВТОРОВ
# =========================================================

def search_channels_through_videos(topic):
    """
    Ищет ВИДЕО по теме.
    Затем берёт channelId автора каждого найденного видео.

    Возвращает словарь:
    {
        channel_id: {
            "topics": set(...),
            "matched_video_ids": set(...)
        }
    }
    """

    candidates = {}

    next_page_token = None
    collected = 0

    while collected < search_depth:
        amount = min(50, search_depth - collected)

        params = {
            "part": "snippet",
            "q": topic,
            "type": "video",
            "maxResults": amount,
            "order": "relevance",
        }

        lang = language_code()

        if lang:
            params["relevanceLanguage"] = lang

        if next_page_token:
            params["pageToken"] = next_page_token

        data = youtube_request("search", params)

        items = data.get("items", [])

        if not items:
            break

        for item in items:
            snippet = item.get("snippet", {})

            channel_id = snippet.get("channelId")

            video_id = (
                item
                .get("id", {})
                .get("videoId")
            )

            if not channel_id:
                continue

            if channel_id not in candidates:
                candidates[channel_id] = {
                    "topics": set(),
                    "matched_video_ids": set()
                }

            candidates[channel_id]["topics"].add(topic)

            if video_id:
                candidates[channel_id][
                    "matched_video_ids"
                ].add(video_id)

        collected += len(items)

        next_page_token = data.get("nextPageToken")

        if not next_page_token:
            break

    return candidates


def get_channel_details(channel_ids):
    results = {}

    channel_ids = list(channel_ids)

    for start in range(0, len(channel_ids), 50):
        batch = channel_ids[start:start + 50]

        data = youtube_request(
            "channels",
            {
                "part": "snippet,statistics,contentDetails",
                "id": ",".join(batch),
                "maxResults": 50
            }
        )

        for item in data.get("items", []):
            results[item["id"]] = item

    return results


def get_recent_uploads(uploads_playlist_id, limit):
    videos = []

    next_page_token = None

    while len(videos) < limit:
        amount = min(50, limit - len(videos))

        params = {
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": amount
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        data = youtube_request(
            "playlistItems",
            params
        )

        items = data.get("items", [])

        if not items:
            break

        for item in items:
            snippet = item.get("snippet", {})
            content_details = item.get(
                "contentDetails", {}
            )

            video_id = content_details.get("videoId")

            published_at = (
                content_details.get("videoPublishedAt")
                or snippet.get("publishedAt")
            )

            if video_id:
                videos.append(
                    {
                        "video_id": video_id,
                        "published_at": published_at
                    }
                )

            if len(videos) >= limit:
                break

        next_page_token = data.get("nextPageToken")

        if not next_page_token:
            break

    return videos


def get_upload_dates(uploads_playlist_id, max_needed=100):
    dates = []

    next_page_token = None

    while len(dates) < max_needed:
        amount = min(50, max_needed - len(dates))

        params = {
            "part": "contentDetails,snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": amount
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        data = youtube_request(
            "playlistItems",
            params
        )

        items = data.get("items", [])

        if not items:
            break

        for item in items:
            published = (
                item
                .get("contentDetails", {})
                .get("videoPublishedAt")
            )

            if not published:
                published = (
                    item
                    .get("snippet", {})
                    .get("publishedAt")
                )

            dt = parse_youtube_date(published)

            if dt:
                dates.append(dt)

        next_page_token = data.get("nextPageToken")

        if not next_page_token:
            break

    return dates


def get_oldest_upload_date(
    uploads_playlist_id,
    reported_video_count
):
    """
    Получает самое старое доступное публичное видео.

    Для маленьких каналов это быстро.
    Для больших каналов может потребоваться несколько страниц.
    """

    oldest = None
    next_page_token = None
    processed = 0

    # Защита от слишком большого количества запросов.
    # Для нашей задачи в основном интересны небольшие каналы.
    maximum_to_scan = min(
        max(reported_video_count, 1),
        500
    )

    while processed < maximum_to_scan:
        amount = min(
            50,
            maximum_to_scan - processed
        )

        params = {
            "part": "contentDetails,snippet",
            "playlistId": uploads_playlist_id,
            "maxResults": amount
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        data = youtube_request(
            "playlistItems",
            params
        )

        items = data.get("items", [])

        if not items:
            break

        for item in items:
            published = (
                item
                .get("contentDetails", {})
                .get("videoPublishedAt")
            )

            if not published:
                published = (
                    item
                    .get("snippet", {})
                    .get("publishedAt")
                )

            dt = parse_youtube_date(published)

            if dt and (
                oldest is None
                or dt < oldest
            ):
                oldest = dt

        processed += len(items)

        next_page_token = data.get("nextPageToken")

        if not next_page_token:
            break

    return oldest


def get_video_details(video_ids):
    results = {}

    video_ids = list(video_ids)

    for start in range(0, len(video_ids), 50):
        batch = video_ids[start:start + 50]

        if not batch:
            continue

        data = youtube_request(
            "videos",
            {
                "part": "statistics,contentDetails,snippet",
                "id": ",".join(batch),
                "maxResults": 50
            }
        )

        for item in data.get("items", []):
            results[item["id"]] = item

    return results


def format_date(dt):
    if not dt:
        return ""

    return dt.strftime("%Y-%m-%d")


# =========================================================
# ПОИСК
# =========================================================

search_clicked = st.button(
    "🚀 Найти каналы",
    type="primary",
    use_container_width=True
)


if search_clicked:

    if not api_key:
        st.error(
            "Сначала вставьте YouTube API-ключ."
        )
        st.stop()

    if not topics:
        st.error(
            "Добавьте хотя бы одну тему для поиска."
        )
        st.stop()

    if (
        max_subscribers > 0
        and min_subscribers > max_subscribers
    ):
        st.error(
            "Минимум подписчиков не может быть больше максимума."
        )
        st.stop()

    if (
        max_videos > 0
        and min_videos > max_videos
    ):
        st.error(
            "Минимум видео не может быть больше максимума."
        )
        st.stop()

    st.divider()
    st.header("📊 Результаты")

    progress = st.progress(0)

    status = st.empty()

    try:

        # -------------------------------------------------
        # 1. ИЩЕМ ВИДЕО И СОБИРАЕМ КАНАЛЫ
        # -------------------------------------------------

        all_candidates = {}

        for index, topic in enumerate(topics):

            status.write(
                f"🔎 Ищу видео по теме: **{topic}**..."
            )

            found = search_channels_through_videos(
                topic
            )

            for channel_id, info in found.items():

                if channel_id not in all_candidates:
                    all_candidates[channel_id] = {
                        "topics": set(),
                        "matched_video_ids": set()
                    }

                all_candidates[
                    channel_id
                ]["topics"].update(
                    info["topics"]
                )

                all_candidates[
                    channel_id
                ]["matched_video_ids"].update(
                    info["matched_video_ids"]
                )

            progress.progress(
                int(
                    ((index + 1) / len(topics))
                    * 20
                )
            )

        if not all_candidates:
            status.empty()
            progress.empty()

            st.warning(
                "YouTube не вернул видео по этим темам."
            )

            st.stop()

        status.write(
            f"🎬 Найдено уникальных каналов-кандидатов: "
            f"**{len(all_candidates)}**. Проверяю..."
        )

        # -------------------------------------------------
        # 2. ПОЛУЧАЕМ ДАННЫЕ КАНАЛОВ
        # -------------------------------------------------

        channel_details = get_channel_details(
            all_candidates.keys()
        )

        results = []

        candidate_ids = list(
            all_candidates.keys()
        )

        now = datetime.now(timezone.utc)

        latest_cutoff = get_last_upload_cutoff()
        freshness_cutoff = get_freshness_cutoff()
        activity_rule = get_activity_rule()

        total_candidates = len(candidate_ids)

        # -------------------------------------------------
        # 3. ПРОВЕРЯЕМ КАЖДЫЙ КАНАЛ
        # -------------------------------------------------

        for position, channel_id in enumerate(
            candidate_ids
        ):

            item = channel_details.get(channel_id)

            if not item:
                continue

            snippet = item.get(
                "snippet", {}
            )

            statistics = item.get(
                "statistics", {}
            )

            content_details = item.get(
                "contentDetails", {}
            )

            # Скрытые подписчики
            if statistics.get(
                "hiddenSubscriberCount",
                False
            ):
                continue

            subscribers = int(
                statistics.get(
                    "subscriberCount",
                    0
                )
            )

            video_count = int(
                statistics.get(
                    "videoCount",
                    0
                )
            )

            total_channel_views = int(
                statistics.get(
                    "viewCount",
                    0
                )
            )

            # Подписчики
            if subscribers < min_subscribers:
                continue

            if (
                max_subscribers > 0
                and subscribers > max_subscribers
            ):
                continue

            # Количество видео
            if video_count < min_videos:
                continue

            if (
                max_videos > 0
                and video_count > max_videos
            ):
                continue

            uploads_playlist_id = (
                content_details
                .get("relatedPlaylists", {})
                .get("uploads")
            )

            if not uploads_playlist_id:
                continue

            # ---------------------------------------------
            # ПОСЛЕДНИЕ ВИДЕО КАНАЛА
            # ---------------------------------------------

            recent_uploads = get_recent_uploads(
                uploads_playlist_id,
                recent_videos
            )

            if not recent_uploads:
                continue

            recent_dates = []

            for upload in recent_uploads:
                dt = parse_youtube_date(
                    upload.get(
                        "published_at"
                    )
                )

                if dt:
                    recent_dates.append(dt)

            latest_video_date = (
                max(recent_dates)
                if recent_dates
                else None
            )

            # Последняя активность
            if latest_cutoff:

                if not latest_video_date:
                    continue

                if latest_video_date < latest_cutoff:
                    continue

            # ---------------------------------------------
            # ДЕТАЛИ ПОСЛЕДНИХ ВИДЕО
            # ---------------------------------------------

            recent_video_ids = [
                upload["video_id"]
                for upload in recent_uploads
            ]

            video_details = get_video_details(
                recent_video_ids
            )

            checked_views = []

            checked_count = 0

            for video_id in recent_video_ids:

                video = video_details.get(
                    video_id
                )

                if not video:
                    continue

                duration = (
                    video
                    .get("contentDetails", {})
                    .get("duration")
                )

                seconds = duration_to_seconds(
                    duration
                )

                if not video_matches_content_type(
                    seconds
                ):
                    continue

                views = int(
                    video
                    .get("statistics", {})
                    .get("viewCount", 0)
                )

                checked_views.append(views)

                checked_count += 1

            if not checked_views:
                continue

            highest_views = max(
                checked_views
            )

            average_views = int(
                sum(checked_views)
                / len(checked_views)
            )

            # Минимум просмотров:
            # хотя бы одно проверенное видео
            if highest_views < min_views:
                continue

            # ---------------------------------------------
            # АКТИВНОСТЬ КАНАЛА
            # ---------------------------------------------

            if activity_rule:
                required_count, days = (
                    activity_rule
                )

                amount_to_scan = min(
                    max(
                        required_count + 10,
                        50
                    ),
                    100
                )

            else:
                amount_to_scan = 50

            upload_dates = get_upload_dates(
                uploads_playlist_id,
                amount_to_scan
            )

            videos_last_30 = sum(
                1
                for dt in upload_dates
                if dt >= (
                    now
                    - timedelta(days=30)
                )
            )

            if activity_rule:
                required_count, days = (
                    activity_rule
                )

                activity_count = sum(
                    1
                    for dt in upload_dates
                    if dt >= (
                        now
                        - timedelta(days=days)
                    )
                )

                if (
                    activity_count
                    < required_count
                ):
                    continue

            # ---------------------------------------------
            # САМОЕ СТАРОЕ ДОСТУПНОЕ ВИДЕО
            # ---------------------------------------------

            oldest_video_date = (
                get_oldest_upload_date(
                    uploads_playlist_id,
                    video_count
                )
            )

            if freshness_cutoff:

                if not oldest_video_date:
                    continue

                if (
                    oldest_video_date
                    < freshness_cutoff
                ):
                    continue

            # ---------------------------------------------
            # РЕЗУЛЬТАТ
            # ---------------------------------------------

            if subscribers > 0:
                best_ratio = round(
                    highest_views
                    / subscribers,
                    2
                )
            else:
                best_ratio = highest_views

            topics_found = sorted(
                all_candidates[
                    channel_id
                ]["topics"]
            )

            result = {
                "Канал": snippet.get(
                    "title",
                    ""
                ),

                "Ссылка": (
                    "https://www.youtube.com/channel/"
                    + channel_id
                ),

                "Подписчики": subscribers,

                "Видео на канале": video_count,

                "Лучший результат": highest_views,

                "Средние просмотры": average_views,

                "Лучшее видео / подписчики": best_ratio,

                "Видео за 30 дней": videos_last_30,

                "Первое доступное видео":
                    format_date(
                        oldest_video_date
                    ),

                "Последнее видео":
                    format_date(
                        latest_video_date
                    ),

                "Возраст контента (дни)":
                    (
                        (
                            now
                            - oldest_video_date
                        ).days
                        if oldest_video_date
                        else 999999
                    ),

                "Всего просмотров":
                    total_channel_views,

                "Проверено видео":
                    checked_count,

                "Найден по темам":
                    ", ".join(
                        topics_found
                    ),
            }

            results.append(result)

            progress_value = (
                20
                + int(
                    (
                        (position + 1)
                        / max(
                            total_candidates,
                            1
                        )
                    )
                    * 80
                )
            )

            progress.progress(
                min(
                    progress_value,
                    100
                )
            )

        progress.progress(100)

        status.empty()

        # -------------------------------------------------
        # 4. СОРТИРОВКА
        # -------------------------------------------------

        if sort_option == "Лучший результат":
            results.sort(
                key=lambda x: x[
                    "Лучший результат"
                ],
                reverse=True
            )

        elif sort_option == "Самые новые каналы":
            results.sort(
                key=lambda x: x[
                    "Возраст контента (дни)"
                ]
            )

        elif sort_option == "Самые активные":
            results.sort(
                key=lambda x: x[
                    "Видео за 30 дней"
                ],
                reverse=True
            )

        elif (
            sort_option
            == "Меньше всего подписчиков"
        ):
            results.sort(
                key=lambda x: x[
                    "Подписчики"
                ]
            )

        elif (
            sort_option
            == "Больше всего подписчиков"
        ):
            results.sort(
                key=lambda x: x[
                    "Подписчики"
                ],
                reverse=True
            )

        # -------------------------------------------------
        # 5. ПОКАЗ РЕЗУЛЬТАТОВ
        # -------------------------------------------------

        if not results:

            st.warning(
                "По заданным фильтрам подходящих каналов "
                "не найдено. Теперь поиск выполнялся именно "
                "через видео, поэтому можно попробовать "
                "немного ослабить один из фильтров."
            )

        else:

            st.success(
                f"Подходящих каналов: "
                f"{len(results)}"
            )

            display_results = []

            for row in results:
                clean_row = dict(row)

                clean_row.pop(
                    "Возраст контента (дни)",
                    None
                )

                display_results.append(
                    clean_row
                )

            st.dataframe(
                display_results,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Ссылка": st.column_config.LinkColumn(
                        "Ссылка",
                        display_text="Открыть канал"
                    )
                }
            )

            # ---------------------------------------------
            # CSV
            # ---------------------------------------------

            output = io.StringIO()

            writer = csv.DictWriter(
                output,
                fieldnames=list(
                    display_results[0].keys()
                )
            )

            writer.writeheader()

            writer.writerows(
                display_results
            )

            csv_data = output.getvalue()

            st.download_button(
                "⬇️ Скачать результаты CSV",
                data=csv_data,
                file_name=(
                    "youtube_channel_results.csv"
                ),
                mime="text/csv"
            )

    except Exception as error:

        progress.empty()
        status.empty()

        st.error(
            "Во время поиска произошла ошибка."
        )

        with st.expander(
            "Показать техническую ошибку"
        ):
            st.code(str(error))

import streamlit as st
import urllib.parse
import urllib.request
import urllib.error
import json
import re
import math
from datetime import datetime, timezone, timedelta


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Поиск YouTube-каналов",
    page_icon="🔎",
    layout="wide"
)

st.title("🔎 Поиск YouTube-каналов")
st.write(
    "Ищи новые и активно растущие YouTube-каналы "
    "по нескольким темам и фильтрам."
)

st.divider()


# =========================================================
# API KEY
# =========================================================

st.subheader("🔐 YouTube API")

api_key = st.text_input(
    "Ваш YouTube API-ключ",
    type="password",
    placeholder="Вставьте API-ключ"
)

with st.expander("Как получить бесплатный YouTube API-ключ?"):
    st.markdown(
        """
1. Откройте Google Cloud Console.
2. Создайте проект.
3. Откройте **APIs & Services → Library**.
4. Подключите **YouTube Data API v3**.
5. Откройте **Credentials → Create credentials → API key**.
6. Ограничьте ключ только для **YouTube Data API v3**.
7. Вставьте ключ в поле выше.

**Не публикуйте API-ключ и не добавляйте его прямо в код.**
"""
    )

st.divider()


# =========================================================
# SEARCH SETTINGS
# =========================================================

st.subheader("🔎 Настройки поиска")

topics_text = st.text_area(
    "Темы для поиска — одна тема на строку (максимум 5)",
    height=150,
    placeholder=(
        "Ancient Egypt\n"
        "Roman Empire\n"
        "Vikings\n"
        "Medieval History\n"
        "Ancient Greece"
    )
)

all_topics = [
    topic.strip()
    for topic in topics_text.splitlines()
    if topic.strip()
]

topics = all_topics[:5]

st.caption(f"Добавлено тем: {len(all_topics)} / 5")


# =========================================================
# FILTERS
# =========================================================

col1, col2 = st.columns(2)

with col1:

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
            "Канал проходит фильтр, если хотя бы одно "
            "из проверяемых последних видео набрало "
            "не меньше указанного количества просмотров."
        )
    )

    min_videos = st.number_input(
        "Минимум видео на канале",
        min_value=0,
        value=10,
        step=1
    )

    max_videos = st.number_input(
        "Максимум видео на канале (0 = без ограничения)",
        min_value=0,
        value=0,
        step=10
    )

    channel_activity = st.selectbox(
        "Активность канала",
        [
            "Неважно",
            "Минимум 4 видео за последние 30 дней",
            "Минимум 10 видео за последние 30 дней",
            "Минимум 15 видео за последние 30 дней",
            "Минимум 30 видео за последние 60 дней",
            "Минимум 50 видео за последние 90 дней"
        ]
    )

    channel_freshness = st.selectbox(
        (
            "Как давно канал начал публиковать видео "
            "(определяется по самому старому доступному "
            "видео на канале)"
        ),
        [
            "Неважно",
            "Не более 30 дней назад",
            "Не более 90 дней назад",
            "Не более 6 месяцев назад",
            "Не более 1 года назад"
        ]
    )


with col2:

    search_depth = st.selectbox(
        "Глубина поиска для каждой темы",
        [50, 100, 250, 500],
        index=2
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
        ]
    )

    upload_recency = st.selectbox(
        "Когда канал загружал последнее видео",
        [
            "Последние 30 дней",
            "Последние 90 дней",
            "Последние 365 дней",
            "Неважно"
        ],
        index=1
    )

    language = st.selectbox(
        "Язык поиска",
        [
            "Любой",
            "Английский",
            "Испанский",
            "Французский",
            "Немецкий",
            "Итальянский",
            "Португальский",
            "Украинский",
            "Русский"
        ]
    )

    sort_by = st.selectbox(
        "Сортировать результаты",
        [
            "Лучший результат",
            "Самые новые каналы",
            "Самые активные",
            "Меньше всего подписчиков",
            "Больше всего подписчиков"
        ]
    )


language_codes = {
    "Английский": "en",
    "Испанский": "es",
    "Французский": "fr",
    "Немецкий": "de",
    "Итальянский": "it",
    "Португальский": "pt",
    "Украинский": "uk",
    "Русский": "ru"
}


activity_settings = {
    "Неважно": None,
    "Минимум 4 видео за последние 30 дней": (4, 30),
    "Минимум 10 видео за последние 30 дней": (10, 30),
    "Минимум 15 видео за последние 30 дней": (15, 30),
    "Минимум 30 видео за последние 60 дней": (30, 60),
    "Минимум 50 видео за последние 90 дней": (50, 90)
}


freshness_days = {
    "Неважно": None,
    "Не более 30 дней назад": 30,
    "Не более 90 дней назад": 90,
    "Не более 6 месяцев назад": 183,
    "Не более 1 года назад": 365
}


pages_per_topic = math.ceil(search_depth / 50)

if topics:
    estimated_search_calls = len(topics) * pages_per_topic

    st.info(
        f"Поиск YouTube: до {estimated_search_calls} "
        f"поисковых запросов. "
        f"Глубина: до {search_depth} результатов "
        f"для каждой темы.\n\n"
        "Дополнительные запросы для проверки каналов "
        "и видео выполняются отдельно."
    )


if content_type == "Shorts":
    st.caption(
        "⚠️ Shorts определяются приблизительно "
        "по длительности видео до 3 минут."
    )

st.divider()


# =========================================================
# YOUTUBE API
# =========================================================

def youtube_request(endpoint, params):

    request_params = dict(params)
    request_params["key"] = api_key

    url = (
        "https://www.googleapis.com/youtube/v3/"
        + endpoint
        + "?"
        + urllib.parse.urlencode(request_params)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "YouTube-Channel-Finder/2.0"
        }
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:

        try:

            body = json.loads(
                error.read().decode("utf-8")
            )

            message = body.get(
                "error",
                {}
            ).get(
                "message",
                f"HTTP ошибка {error.code}"
            )

        except Exception:

            message = f"HTTP ошибка {error.code}"

        raise RuntimeError(message)

    except urllib.error.URLError:

        raise RuntimeError(
            "Не удалось подключиться к YouTube API."
        )


# =========================================================
# HELPERS
# =========================================================

def parse_youtube_date(value):

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except ValueError:

        return None


def duration_to_seconds(duration):

    match = re.fullmatch(
        r"P(?:(\d+)D)?T?"
        r"(?:(\d+)H)?"
        r"(?:(\d+)M)?"
        r"(?:(\d+)S)?",
        duration
    )

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


def video_matches_content_type(video):

    if content_type == "Все видео":
        return True

    duration = video.get(
        "contentDetails",
        {}
    ).get(
        "duration",
        "PT0S"
    )

    seconds = duration_to_seconds(duration)

    if content_type == "Shorts":
        return seconds <= 180

    if content_type == "Длинные видео":
        return seconds > 180

    return True


def get_last_upload_cutoff():

    days_map = {
        "Последние 30 дней": 30,
        "Последние 90 дней": 90,
        "Последние 365 дней": 365
    }

    if upload_recency == "Неважно":
        return None

    return (
        datetime.now(timezone.utc)
        - timedelta(
            days=days_map[upload_recency]
        )
    )


# =========================================================
# SEARCH CHANNELS
# =========================================================

def search_channels(topic):

    channel_ids = []

    page_token = None
    remaining = search_depth

    while remaining > 0:

        amount = min(50, remaining)

        params = {
            "part": "snippet",
            "q": topic,
            "type": "channel",
            "maxResults": amount
        }

        if language != "Любой":

            params["relevanceLanguage"] = (
                language_codes[language]
            )

        if page_token:

            params["pageToken"] = page_token

        data = youtube_request(
            "search",
            params
        )

        items = data.get(
            "items",
            []
        )

        for item in items:

            channel_id = item.get(
                "id",
                {}
            ).get(
                "channelId"
            )

            if (
                channel_id
                and channel_id not in channel_ids
            ):
                channel_ids.append(channel_id)

        remaining -= len(items)

        page_token = data.get(
            "nextPageToken"
        )

        if not page_token or not items:
            break

    return channel_ids


# =========================================================
# CHANNEL DETAILS
# =========================================================

def get_channel_details(channel_ids):

    channels = []

    for start in range(
        0,
        len(channel_ids),
        50
    ):

        batch = channel_ids[
            start:start + 50
        ]

        data = youtube_request(
            "channels",
            {
                "part":
                    "snippet,statistics,contentDetails",
                "id": ",".join(batch),
                "maxResults": 50
            }
        )

        channels.extend(
            data.get(
                "items",
                []
            )
        )

    return channels


# =========================================================
# UPLOADS PLAYLIST
# =========================================================

def get_recent_uploads(
    uploads_playlist_id,
    amount
):

    data = youtube_request(
        "playlistItems",
        {
            "part": "contentDetails",
            "playlistId":
                uploads_playlist_id,
            "maxResults":
                min(amount, 50)
        }
    )

    uploads = []

    for item in data.get(
        "items",
        []
    ):

        details = item.get(
            "contentDetails",
            {}
        )

        video_id = details.get(
            "videoId"
        )

        published_at = details.get(
            "videoPublishedAt"
        )

        if video_id:

            uploads.append(
                {
                    "video_id": video_id,
                    "published_at": published_at
                }
            )

    return uploads


def get_all_upload_dates(
    uploads_playlist_id,
    max_needed=100
):

    dates = []

    page_token = None

    while len(dates) < max_needed:

        params = {
            "part": "contentDetails",
            "playlistId":
                uploads_playlist_id,
            "maxResults": 50
        }

        if page_token:
            params["pageToken"] = page_token

        data = youtube_request(
            "playlistItems",
            params
        )

        items = data.get(
            "items",
            []
        )

        for item in items:

            published_at = item.get(
                "contentDetails",
                {}
            ).get(
                "videoPublishedAt"
            )

            date = parse_youtube_date(
                published_at
            )

            if date:
                dates.append(date)

        page_token = data.get(
            "nextPageToken"
        )

        if not page_token or not items:
            break

    return dates


def get_oldest_upload_date(
    uploads_playlist_id,
    video_count
):

    if video_count <= 0:
        return None

    last_page = max(
        1,
        math.ceil(video_count / 50)
    )

    page_token = None
    data = None

    for _ in range(last_page):

        params = {
            "part": "contentDetails",
            "playlistId":
                uploads_playlist_id,
            "maxResults": 50
        }

        if page_token:
            params["pageToken"] = page_token

        data = youtube_request(
            "playlistItems",
            params
        )

        page_token = data.get(
            "nextPageToken"
        )

        if not page_token:
            break

    if not data:
        return None

    dates = []

    for item in data.get(
        "items",
        []
    ):

        published_at = item.get(
            "contentDetails",
            {}
        ).get(
            "videoPublishedAt"
        )

        date = parse_youtube_date(
            published_at
        )

        if date:
            dates.append(date)

    if not dates:
        return None

    return min(dates)


# =========================================================
# VIDEO DETAILS
# =========================================================

def get_video_details(video_ids):

    if not video_ids:
        return []

    videos = []

    for start in range(
        0,
        len(video_ids),
        50
    ):

        batch = video_ids[
            start:start + 50
        ]

        data = youtube_request(
            "videos",
            {
                "part":
                    "statistics,contentDetails,snippet",
                "id":
                    ",".join(batch)
            }
        )

        videos.extend(
            data.get(
                "items",
                []
            )
        )

    return videos


# =========================================================
# RUN
# =========================================================

if st.button(
    "🚀 Найти каналы",
    type="primary",
    use_container_width=True
):

    if not api_key:

        st.error(
            "Введите YouTube API-ключ."
        )

    elif not all_topics:

        st.error(
            "Введите хотя бы одну тему."
        )

    elif len(all_topics) > 5:

        st.error(
            "Можно добавить максимум 5 тем."
        )

    elif (
        max_subscribers > 0
        and min_subscribers > max_subscribers
    ):

        st.error(
            "Минимум подписчиков не может быть "
            "больше максимума."
        )

    elif (
        max_videos > 0
        and min_videos > max_videos
    ):

        st.error(
            "Минимум видео не может быть "
            "больше максимума."
        )

    else:

        try:

            found_channels = {}

            progress = st.progress(0)
            status = st.empty()

            # =================================================
            # SEARCH
            # =================================================

            for index, topic in enumerate(
                topics
            ):

                status.write(
                    f"🔎 Ищу каналы по теме: "
                    f"**{topic}**"
                )

                ids = search_channels(
                    topic
                )

                for channel_id in ids:

                    if channel_id not in found_channels:

                        found_channels[
                            channel_id
                        ] = {
                            "topics": []
                        }

                    if (
                        topic
                        not in found_channels[
                            channel_id
                        ]["topics"]
                    ):

                        found_channels[
                            channel_id
                        ]["topics"].append(
                            topic
                        )

                progress.progress(
                    int(
                        (
                            (index + 1)
                            / len(topics)
                        )
                        * 20
                    )
                )

            unique_ids = list(
                found_channels.keys()
            )

            if not unique_ids:

                progress.empty()
                status.empty()

                st.warning(
                    "YouTube не нашёл каналов "
                    "по указанным темам."
                )

                st.stop()

            # =================================================
            # CHANNEL STATS
            # =================================================

            status.write(
                f"Найдено уникальных каналов: "
                f"**{len(unique_ids)}**. "
                f"Проверяю статистику..."
            )

            channels = get_channel_details(
                unique_ids
            )

            candidate_channels = []

            hidden_subscribers = 0

            for channel in channels:

                statistics = channel.get(
                    "statistics",
                    {}
                )

                if statistics.get(
                    "hiddenSubscriberCount",
                    False
                ):

                    hidden_subscribers += 1
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

                if subscribers < min_subscribers:
                    continue

                if (
                    max_subscribers > 0
                    and subscribers > max_subscribers
                ):
                    continue

                if video_count < min_videos:
                    continue

                if (
                    max_videos > 0
                    and video_count > max_videos
                ):
                    continue

                candidate_channels.append(
                    channel
                )

            # =================================================
            # ANALYSIS
            # =================================================

            results = []

            total_candidates = max(
                len(candidate_channels),
                1
            )

            last_upload_cutoff = (
                get_last_upload_cutoff()
            )

            activity_rule = (
                activity_settings[
                    channel_activity
                ]
            )

            freshness_limit = (
                freshness_days[
                    channel_freshness
                ]
            )

            now = datetime.now(
                timezone.utc
            )

            for index, channel in enumerate(
                candidate_channels
            ):

                channel_id = channel.get(
                    "id"
                )

                snippet = channel.get(
                    "snippet",
                    {}
                )

                statistics = channel.get(
                    "statistics",
                    {}
                )

                content_details = channel.get(
                    "contentDetails",
                    {}
                )

                channel_title = snippet.get(
                    "title",
                    "Канал"
                )

                status.write(
                    f"📊 Проверяю: "
                    f"**{channel_title}**"
                )

                uploads_playlist_id = (
                    content_details.get(
                        "relatedPlaylists",
                        {}
                    ).get(
                        "uploads"
                    )
                )

                if not uploads_playlist_id:
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

                # ---------------------------------------------
                # Recent videos for view analysis
                # ---------------------------------------------

                recent_uploads = (
                    get_recent_uploads(
                        uploads_playlist_id,
                        recent_videos
                    )
                )

                if not recent_uploads:
                    continue

                latest_date = (
                    parse_youtube_date(
                        recent_uploads[0].get(
                            "published_at"
                        )
                    )
                )

                if (
                    last_upload_cutoff
                    and (
                        not latest_date
                        or latest_date
                        < last_upload_cutoff
                    )
                ):
                    continue

                # ---------------------------------------------
                # Activity
                # ---------------------------------------------

                activity_count_30 = 0

                dates_for_activity = []

                if activity_rule:

                    required_count, activity_days = (
                        activity_rule
                    )

                    amount_needed = min(
                        max(
                            required_count + 10,
                            50
                        ),
                        100
                    )

                    dates_for_activity = (
                        get_all_upload_dates(
                            uploads_playlist_id,
                            amount_needed
                        )
                    )

                    activity_cutoff = (
                        now
                        - timedelta(
                            days=activity_days
                        )
                    )

                    activity_count = sum(
                        1
                        for date in dates_for_activity
                        if date >= activity_cutoff
                    )

                    if (
                        activity_count
                        < required_count
                    ):
                        continue

                else:

                    dates_for_activity = (
                        get_all_upload_dates(
                            uploads_playlist_id,
                            50
                        )
                    )

                cutoff_30 = (
                    now
                    - timedelta(days=30)
                )

                activity_count_30 = sum(
                    1
                    for date in dates_for_activity
                    if date >= cutoff_30
                )

                # ---------------------------------------------
                # First available video
                # ---------------------------------------------

                oldest_date = (
                    get_oldest_upload_date(
                        uploads_playlist_id,
                        video_count
                    )
                )

                if freshness_limit is not None:

                    if not oldest_date:
                        continue

                    freshness_cutoff = (
                        now
                        - timedelta(
                            days=freshness_limit
                        )
                    )

                    if oldest_date < freshness_cutoff:
                        continue

                # ---------------------------------------------
                # Video statistics
                # ---------------------------------------------

                video_ids = [
                    item["video_id"]
                    for item in recent_uploads
                ]

                videos = get_video_details(
                    video_ids
                )

                videos = [
                    video
                    for video in videos
                    if video_matches_content_type(
                        video
                    )
                ]

                if not videos:
                    continue

                view_counts = []

                for video in videos:

                    views = int(
                        video.get(
                            "statistics",
                            {}
                        ).get(
                            "viewCount",
                            0
                        )
                    )

                    view_counts.append(
                        views
                    )

                if not view_counts:
                    continue

                highest_views = max(
                    view_counts
                )

                if highest_views < min_views:
                    continue

                average_views = int(
                    sum(view_counts)
                    / len(view_counts)
                )

                total_channel_views = int(
                    statistics.get(
                        "viewCount",
                        0
                    )
                )

                ratio = (
                    round(
                        highest_views
                        / subscribers,
                        1
                    )
                    if subscribers > 0
                    else 0
                )

                matched_topics = (
                    found_channels.get(
                        channel_id,
                        {}
                    ).get(
                        "topics",
                        []
                    )
                )

                channel_age_days = (
                    (now - oldest_date).days
                    if oldest_date
                    else None
                )

                results.append(
                    {
                        "Канал":
                            channel_title,

                        "Ссылка":
                            (
                                "https://www.youtube.com/"
                                f"channel/{channel_id}"
                            ),

                        "Подписчики":
                            subscribers,

                        "Видео на канале":
                            video_count,

                        "Лучший результат":
                            highest_views,

                        "Средние просмотры":
                            average_views,

                        "Лучшее видео / подписчики":
                            ratio,

                        "Видео за 30 дней":
                            activity_count_30,

                        "Первое доступное видео":
                            (
                                oldest_date.strftime(
                                    "%d.%m.%Y"
                                )
                                if oldest_date
                                else "—"
                            ),

                        "Последнее видео":
                            (
                                latest_date.strftime(
                                    "%d.%m.%Y"
                                )
                                if latest_date
                                else "—"
                            ),

                        "Возраст контента (дни)":
                            (
                                channel_age_days
                                if channel_age_days
                                is not None
                                else 999999
                            ),

                        "Всего просмотров":
                            total_channel_views,

                        "Проверено видео":
                            len(videos),

                        "Найден по темам":
                            ", ".join(
                                matched_topics
                            )
                    }
                )

                progress.progress(
                    min(
                        100,
                        20
                        + int(
                            (
                                (index + 1)
                                / total_candidates
                            )
                            * 80
                        )
                    )
                )

            progress.progress(100)
            status.empty()

            # =================================================
            # SORTING
            # =================================================

            if sort_by == "Лучший результат":

                results.sort(
                    key=lambda row:
                        row["Лучший результат"],
                    reverse=True
                )

            elif sort_by == "Самые новые каналы":

                results.sort(
                    key=lambda row:
                        row[
                            "Возраст контента (дни)"
                        ]
                )

            elif sort_by == "Самые активные":

                results.sort(
                    key=lambda row:
                        row["Видео за 30 дней"],
                    reverse=True
                )

            elif sort_by == "Меньше всего подписчиков":

                results.sort(
                    key=lambda row:
                        row["Подписчики"]
                )

            elif sort_by == "Больше всего подписчиков":

                results.sort(
                    key=lambda row:
                        row["Подписчики"],
                    reverse=True
                )

            # =================================================
            # RESULTS
            # =================================================

            st.subheader(
                "📊 Результаты"
            )

            if results:

                st.success(
                    f"Подходящих каналов: "
                    f"{len(results)}"
                )

                display_results = []

                for row in results:

                    display_row = dict(row)

                    display_row.pop(
                        "Возраст контента (дни)",
                        None
                    )

                    display_results.append(
                        display_row
                    )

                st.dataframe(
                    display_results,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Ссылка":
                            st.column_config.LinkColumn(
                                "Ссылка"
                            )
                    }
                )

                csv_columns = list(
                    display_results[0].keys()
                )

                csv_lines = [
                    ",".join(csv_columns)
                ]

                for row in display_results:

                    values = []

                    for column in csv_columns:

                        value = str(
                            row[column]
                        )

                        value = (
                            '"'
                            + value.replace(
                                '"',
                                '""'
                            )
                            + '"'
                        )

                        values.append(value)

                    csv_lines.append(
                        ",".join(values)
                    )

                csv_data = (
                    "\n".join(csv_lines)
                ).encode(
                    "utf-8-sig"
                )

                st.download_button(
                    "⬇️ Скачать результаты CSV",
                    data=csv_data,
                    file_name="youtube_channels.csv",
                    mime="text/csv"
                )

            else:

                st.warning(
                    "По заданным фильтрам "
                    "подходящих каналов не найдено. "
                    "Попробуйте немного ослабить "
                    "один или несколько фильтров."
                )

            if hidden_subscribers > 0:

                st.caption(
                    f"Каналов со скрытым количеством "
                    f"подписчиков пропущено: "
                    f"{hidden_subscribers}."
                )

        except Exception as error:

            st.error(
                "Произошла ошибка при обращении "
                "к YouTube API."
            )

            with st.expander(
                "Показать техническую ошибку"
            ):

                st.code(
                    str(error)
                )

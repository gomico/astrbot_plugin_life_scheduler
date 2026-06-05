import asyncio
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from astrbot.api import logger

_OPEN_METEO_CURRENT_PARAMS = (
    "temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m"
)

_WEATHER_CODE_LABELS = {
    0: "晴朗",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴天",
    45: "有雾",
    48: "雾凇",
    51: "小毛毛雨",
    53: "中等毛毛雨",
    55: "大毛毛雨",
    56: "轻度冻毛毛雨",
    57: "重度冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "轻度冻雨",
    67: "重度冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "中阵雨",
    82: "大阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "带冰雹雷暴",
    99: "强烈带冰雹雷暴",
}


def parse_weather_coordinates(latitude: str, longitude: str) -> tuple[float, float]:
    lat = float(str(latitude).strip())
    lon = float(str(longitude).strip())
    if not (-90 <= lat <= 90):
        raise ValueError("纬度必须在 -90 到 90 之间")
    if not (-180 <= lon <= 180):
        raise ValueError("经度必须在 -180 到 180 之间")
    return lat, lon


def format_weather_context(current: dict) -> str:
    temperature = _format_number(current.get("temperature_2m"))
    feels_like = _format_number(current.get("apparent_temperature"))
    precipitation = _format_number(current.get("precipitation"))
    wind_speed = _format_number(current.get("wind_speed_10m"))
    weather_code = current.get("weather_code")
    weather_desc = _describe_weather_code(weather_code)
    return (
        f"天气：{weather_desc}，"
        f"气温 {temperature}°C，"
        f"体感 {feels_like}°C，"
        f"降水 {precipitation} mm，"
        f"风速 {wind_speed} km/h"
    )


async def fetch_weather_context(latitude: str, longitude: str) -> str:
    try:
        lat, lon = parse_weather_coordinates(latitude, longitude)
    except Exception as exc:
        logger.error(f"天气坐标配置错误: {exc}")
        return "天气信息获取失败"

    try:
        payload = await asyncio.to_thread(_fetch_open_meteo_current, lat, lon)
        return format_weather_context(payload)
    except Exception as exc:
        logger.error(f"Open-Meteo 天气获取失败: {exc}")
        return "天气信息获取失败"


def _fetch_open_meteo_current(latitude: float, longitude: float) -> dict:
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": _OPEN_METEO_CURRENT_PARAMS,
            "timezone": "auto",
        }
    )
    url = f"https://api.open-meteo.com/v1/forecast?{query}"
    request = Request(url, headers={"User-Agent": "AstrBot-Life-Scheduler/1.0"})
    with urlopen(request, timeout=10) as response:
        body = response.read().decode("utf-8")
    payload = json.loads(body)
    current = payload.get("current")
    if not isinstance(current, dict):
        raise ValueError("Open-Meteo 返回缺少 current 字段")
    return current


def _describe_weather_code(code: object) -> str:
    try:
        int_code = int(code)
    except Exception:
        return f"天气代码 {code}" if code is not None else "未知天气"
    return _WEATHER_CODE_LABELS.get(int_code, f"天气代码 {int_code}")


def _format_number(value: object) -> str:
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "未知"

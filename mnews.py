# encoding:utf-8

import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *
import requests
import json
import os

@plugins.register(
    name="mnews",
    desire_priority=998,
    desc="A simple plugin that says morning news",
    version="0.1",
    author="chjs",
)
class Mnews(Plugin):
    CONFIG_FILE = "config.json"
    API_URL = "https://v2.alapi.cn/api/zaobao"
    HELP_TEXT = "早报功能\nyour_bot keywords: 获取早报。eg: bot 早报"

    def __init__(self):
        super().__init__()
        try:
            curdir = os.path.dirname(__file__)
            config_path = os.path.join(curdir, self.CONFIG_FILE)
            logger.debug("[mnews] 进入加载配置文件方法")

            if not os.path.exists(config_path):
                raise ValueError(f"[mnews] 请创建并配置 {config_path}")

            with open(config_path, "r", encoding="utf-8") as f:
                conf = json.load(f)

            self.mnews_api_key = conf.get("mnews_api_key")
            if self.mnews_api_key == "your api key" or not self.mnews_api_key:
                raise ValueError("[mnews] 请检查 'mnews_api_key' 的值")

            self.mnews_type = conf.get("mnews_type", "image")
            self.keywords = conf.get("keywords", ["早报", "mnews"])

            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            logger.info("[mnews] 初始化完成")
        except Exception as e:
            logger.error("[mnews] 初始化失败，请忽略或查看 https://github.com/CJSen/mnews")
            raise e

    def get_help_text(self, verbose=False, **kwargs):
        return self.HELP_TEXT

    def on_handle_context(self, e_context: EventContext):
        content = e_context["context"].content
        logger.debug(f"[mnews] 处理上下文内容: {content}")

        if e_context["context"].type != ContextType.TEXT:
            return

        if content in self.keywords:
            reply = Reply()
            try:
                response_json = self._get_news()
            except Exception as e:
                logger.error(f"[mnews] 获取新闻失败: {e}")
                reply.type = ReplyType.TEXT
                reply.content = "获取早报失败，请稍后再试。"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

            if self.mnews_type == "image":
                reply.type = ReplyType.IMAGE_URL
                images_url = response_json["data"].get("image")
                reply.content = images_url
                logger.debug(f"[mnews] 图片URL: {images_url}")
            elif self.mnews_type == "text":
                reply.type = ReplyType.TEXT
                data = response_json["data"]
                news = "\n".join([data["date"]] + data["news"] + [data["weiyu"]])
                reply.content = news
                logger.debug(f"[mnews] 新闻内容: {news}")
            else:
                logger.error("[mnews] 消息类型配置错误，请检查")

            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

    def _get_news(self):
        url = self.API_URL
        payload = f"token={self.mnews_api_key}&format=json"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        retries = 3  # 重试次数
        timeout = 5  # 每次请求的超时时间（秒）

        for attempt in range(retries):
            try:
                response = requests.post(url, data=payload, headers=headers, timeout=timeout)
                response.raise_for_status()  # 如果响应有问题，则抛出HTTP错误
                return response.json()
            except requests.RequestException as e:
                logger.warning(f"[mnews] 请求失败，正在重试 {attempt + 1}/{retries} 次: {e}")
                if attempt == retries - 1:  # 如果已经是最后一次尝试了，抛出异常
                    logger.error(f"[mnews] 请求新闻接口失败: {e}")
                    raise
                else:
                    continue  # 继续下一次重试

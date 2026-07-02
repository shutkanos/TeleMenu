from . import scenes
from .data import Data
import datetime

@scenes.SceneManager.decorator_register(name="ban_notification")
class BanNotificationScene(scenes.Scene):
    def build(self):
        ban_info = self.context.get('ban_info', {})
        ban_text = ban_info.get('text', Data.get_text('violation'))
        ban_start = ban_info.get('start', 0)
        ban_end = ban_info.get('end', 0)

        start_time = datetime.datetime.fromtimestamp(ban_start).strftime('%Y-%m-%d %H:%M:%S') if ban_start else Data.get_text('unknown')
        end_time = datetime.datetime.fromtimestamp(ban_end).strftime('%Y-%m-%d %H:%M:%S') if ban_end else Data.get_text('unknown')

        if ban_end and ban_start:
            duration_seconds = ban_end - ban_start
            duration_minutes = duration_seconds // 60
            duration_hours = duration_minutes // 60
            duration_days = duration_hours // 24

            if duration_days > 0:
                duration_str = f"{duration_days} {Data.get_text('days')}"
            elif duration_hours > 0:
                duration_str = f"{duration_hours} {Data.get_text('hours')}"
            else:
                duration_str = f"{duration_minutes} {Data.get_text('minutes')}"
        else:
            duration_str = Data.get_text('unknown')

        content = (f"{Data.get_text('ban_title')}\n\n"
                   f"{Data.get_text('ban_reason')}: {ban_text}\n"
                   f"{Data.get_text('ban_start')}: {start_time}\n"
                   f"{Data.get_text('ban_end')}: {end_time}\n"
                   f"{Data.get_text('ban_duration')}: {duration_str}\n\n"
                   f"{Data.get_text('ban_footer')}")

        self.add_message(scenes.TextMessage(content=content, buttons=[]))

@scenes.SceneManager.decorator_register(name="unban_notification")
class UnbanNotificationScene(scenes.Scene):
    def build(self):
        ban_info = self.context.get('ban_info', {})
        ban_text = ban_info.get('text', Data.get_text('violation'))
        ban_start = ban_info.get('start', 0)
        ban_end = ban_info.get('end', 0)

        start_time = datetime.datetime.fromtimestamp(ban_start).strftime('%Y-%m-%d %H:%M:%S') if ban_start else Data.get_text('unknown')
        end_time = datetime.datetime.fromtimestamp(ban_end).strftime('%Y-%m-%d %H:%M:%S') if ban_end else Data.get_text('unknown')

        content = (f"{Data.get_text('unban_title')}\n\n"
                   f"{Data.get_text('unban_header')}\n\n"
                   f"{Data.get_text('unban_info')}\n"
                   f"{Data.get_text('ban_reason')}: {ban_text}\n"
                   f"{Data.get_text('ban_start')}: {start_time}\n"
                   f"{Data.get_text('ban_end')}: {end_time}\n\n"
                   f"{Data.get_text('unban_footer')}")

        self.add_message(scenes.TextMessage(content=content, buttons=[]))
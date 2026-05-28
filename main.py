import asyncio
import os

from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.platform.astr_message_event import AstrMessageEvent

# 脚本路径：优先用环境变量，否则用插件目录旁的 restart.sh
_DEFAULT_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "restart.sh")
SCRIPT_PATH = os.environ.get("NAPCAT_RESTART_SCRIPT", _DEFAULT_SCRIPT)


class NapcatRestartPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    @filter.command("napcat restart")
    async def napcat_restart(self, event: AstrMessageEvent):
        """运行 restart.sh 重启并重新登录 Napcat"""
        sender = str(event.get_sender_id())
        admin_list = [str(q) for q in (self.config.get("admin_qq") or [])]
        # 配置了名单时按名单校验，否则回退到 AstrBot 全局管理员判断
        if admin_list:
            if sender not in admin_list:
                yield event.plain_result("❌ 你没有执行此命令的权限")
                return
        else:
            if event.get_permission_type() < filter.PermissionType.ADMIN:
                yield event.plain_result("❌ 你没有执行此命令的权限")
                return

        script = os.path.abspath(SCRIPT_PATH)
        if not os.path.isfile(script):
            yield event.plain_result(f"❌ 找不到脚本：{script}")
            return

        yield event.plain_result("⏳ 正在重启 Napcat，请稍候（约 30 秒）…")
        logger.info(f"[napcat_restart] 执行脚本: {script}")

        try:
            proc = await asyncio.create_subprocess_exec(
                "bash", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
            output = stdout.decode("utf-8", errors="replace").strip()
            logger.info(f"[napcat_restart] 脚本输出:\n{output}")

            if proc.returncode == 0:
                await asyncio.sleep(10)
                yield event.plain_result("✅ Napcat 重启成功")
            else:
                yield event.plain_result("❌ Napcat 重启失败")

        except asyncio.TimeoutError:
            yield event.plain_result("❌ 脚本执行超时（>120s），请检查服务器状态")
        except Exception as e:
            logger.error(f"[napcat_restart] 执行异常: {e}")
            yield event.plain_result(f"❌ 执行出错：{e}")

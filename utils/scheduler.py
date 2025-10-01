#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务调度器
Scheduled Task Manager
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MaintenanceScheduler:
    """自动维护任务调度器"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')
        self._is_running = False

    def _execute_maintenance_task(self):
        """执行维护任务的包装函数"""
        try:
            from database.operations import MaintenanceOperations
            from database.operations import SystemSettingsOperations

            logger.info("⏰ 开始执行自动维护任务...")

            # 执行维护任务
            released_count, expired_count, subscription_expired_count, converted_count = \
                MaintenanceOperations.run_daily_maintenance()

            logger.info(f"✅ 自动维护完成 - 释放:{released_count}, 过期:{expired_count}, "
                       f"套餐过期:{subscription_expired_count}, 转换:{converted_count}")

        except Exception as e:
            logger.error(f"❌ 自动维护任务执行失败: {e}", exc_info=True)

    def start(self):
        """启动定时任务"""
        if self._is_running:
            logger.warning("调度器已经在运行")
            return

        try:
            # 每天执行3次：早上8点、下午2点、晚上8点
            # Cron 表达式：分 时 日 月 周
            self.scheduler.add_job(
                self._execute_maintenance_task,
                CronTrigger(hour='8,14,20', minute='0'),
                id='daily_maintenance',
                name='每日自动维护任务',
                replace_existing=True
            )

            self.scheduler.start()
            self._is_running = True
            logger.info("🚀 定时任务调度器已启动 - 每日 8:00, 14:00, 20:00 执行维护任务")

        except Exception as e:
            logger.error(f"❌ 启动调度器失败: {e}", exc_info=True)

    def stop(self):
        """停止定时任务"""
        if not self._is_running:
            return

        try:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("🛑 定时任务调度器已停止")
        except Exception as e:
            logger.error(f"❌ 停止调度器失败: {e}", exc_info=True)

    def get_next_run_time(self):
        """获取下次执行时间"""
        if not self._is_running:
            return None

        try:
            job = self.scheduler.get_job('daily_maintenance')
            if job:
                return job.next_run_time
        except:
            pass
        return None

    def is_running(self):
        """检查调度器是否在运行"""
        return self._is_running


# 全局调度器实例
_global_scheduler = None


def get_scheduler() -> MaintenanceScheduler:
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = MaintenanceScheduler()
    return _global_scheduler


def start_scheduler():
    """启动全局调度器"""
    scheduler = get_scheduler()
    scheduler.start()


def stop_scheduler():
    """停止全局调度器"""
    global _global_scheduler
    if _global_scheduler:
        _global_scheduler.stop()


if __name__ == "__main__":
    # 测试调度器
    print("测试定时任务调度器...")
    scheduler = MaintenanceScheduler()
    scheduler.start()

    next_run = scheduler.get_next_run_time()
    if next_run:
        print(f"下次执行时间: {next_run}")

    print("调度器正在运行，按 Ctrl+C 停止...")

    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n停止调度器...")
        scheduler.stop()
        print("调度器已停止")

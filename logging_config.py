#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置 - 抑制无害的框架错误
"""

import logging
import sys


class WebSocketErrorFilter(logging.Filter):
    """过滤 WebSocket 相关的无害错误"""
    
    def filter(self, record):
        # 过滤 WebSocket 关闭错误
        if 'WebSocketClosedError' in str(record.getMessage()):
            return False
        if 'Stream is closed' in str(record.getMessage()):
            return False
        if 'Task exception was never retrieved' in str(record.getMessage()):
            return False
        return True


def setup_logging():
    """配置日志系统"""
    
    # 获取 root logger
    root_logger = logging.getLogger()
    
    # 为 tornado 和 asyncio 添加过滤器
    tornado_logger = logging.getLogger('tornado')
    asyncio_logger = logging.getLogger('asyncio')
    
    websocket_filter = WebSocketErrorFilter()
    
    # 添加过滤器到所有处理器
    for logger in [root_logger, tornado_logger, asyncio_logger]:
        logger.addFilter(websocket_filter)
        for handler in logger.handlers:
            handler.addFilter(websocket_filter)
    
    # 设置日志级别
    tornado_logger.setLevel(logging.ERROR)
    asyncio_logger.setLevel(logging.ERROR)
    
    # 配置应用日志
    app_logger = logging.getLogger(__name__)
    app_logger.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 设置格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    console_handler.addFilter(websocket_filter)
    
    # 添加处理器
    if not app_logger.handlers:
        app_logger.addHandler(console_handler)
    
    return app_logger


if __name__ == '__main__':
    logger = setup_logging()
    logger.info("日志系统配置完成")

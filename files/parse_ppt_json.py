#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PPT JSON 解析工具
"""
import json
import sys


def parse_ppt_json(json_file):
    """解析 PPT JSON 结构文件"""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"文件名：{data.get('file_name', 'Unknown')}")
    print(f"幻灯片数量：{data.get('slide_count', 0)}")
    print()

    for slide in data.get("slides", []):
        print(f"--- 第 {slide.get('slide_num', '?')} 页 ---")
        if slide.get("title"):
            print(f"标题：{slide['title']}")
        for shape in slide.get("shapes", []):
            if shape.get("text"):
                print(f"  - {shape['text'][:50]}...")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python parse_ppt_json.py <json 文件路径>")
        sys.exit(1)

    parse_ppt_json(sys.argv[1])

# -*- coding: utf-8 -*-
"""用 playwright 抓取官方答题器渲染后的题目数据。"""
import ast
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from playwright.sync_api import sync_playwright

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "banks", "keju", "dtk_questions.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://w.163.com/h5/xyq/dtk/index.html#/keju", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(5000)  # 等 Vue 渲染

    # 1) 拦截所有网络请求
    # (已完成加载，直接获取页面内容)

    # 2) 获取渲染后的全文
    text = page.inner_text("body")
    print("页面文本前500字:")
    print(text[:500])

    # 3) 获取所有选项元素
    options = page.query_selector_all('[class*="option"], [class*="answer"], [class*="item"]')
    print(f"\n选项元素: {len(options)}")

    # 4) 获取完整 HTML
    html = page.content()
    with open(os.path.join(ROOT, "banks", "keju", "dtk_rendered.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML长度: {len(html)}")

    # 5) 尝试从 Vue 实例获取数据
    vue_data = page.evaluate("""() => {
        const app = document.querySelector('#app').__vue_app__;
        if (app) {
            const state = app._instance?.proxy?.$store?.state;
            if (state) return JSON.stringify(state).substring(0, 5000);
        }
        return null;
    }""")
    if vue_data:
        print("Vue state:", vue_data[:500])
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(vue_data)

    # 6) 全局变量搜索
    globals_data = page.evaluate("""() => {
        const results = {};
        for (const key of Object.keys(window)) {
            try {
                const val = window[key];
                if (val && typeof val === 'object' && !Array.isArray(val)) continue;
                if (Array.isArray(val) && val.length > 50) {
                    results[key] = `Array(${val.length})`;
                }
            } catch(e) {}
        }
        return results;
    }""")
    print("全局数组:", globals_data)

    browser.close()
    print("done")

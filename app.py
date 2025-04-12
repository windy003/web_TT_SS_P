import time
import os
from flask import Flask, request, render_template
import re
import html
import time
import os
import json
import traceback
from playwright.sync_api import sync_playwright
import gunicorn


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():


    url_old = ""
    content_old = ""
    # 读取 backup.json 文件
    if os.path.exists("./backup/backup.json"):
        with open("./backup/backup.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            url_old = data.get("url", "").strip()
            print(f"url_old: {url_old}")
            content_old = data.get("content", "")

    if request.method == 'POST':
        if 'url' in request.form:
            url = request.form['url'].strip().split("%")[0]
            print(f"url: {url}")
            if url_old:
                if url == url_old:
                    print("url 相同,使用content_old")
                    return render_template('index.html',content=content_old)
                else:
                    save_url(url)
                    print(f"url: {url}")
                    print(f"old_url: {url_old}")
                    return load_from_url(url)
            else:
                save_url(url)
                return load_from_url(url)
    
    return render_template('index.html')



def load_from_url(url):
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False)  # 设置 headless=True 可以隐藏浏览器窗口
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"
        )
        page = context.new_page()
        
        try:
            # 访问文章链接
            print(f"正在访问: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            
            # 等待文章内容加载
            page.wait_for_selector("article", state="visible", timeout=10000)
            
            

            # 点击展开按钮
            try:
                expand_button = page.locator("button", has_text="点击展开剩余")
                if expand_button.count() > 0:  # 检查按钮是否存在
                    expand_button.click()
                print("点击了展开按钮")
            except Exception as e:
                print("点击展开按钮时出错:", e)


            # 向下滚动以加载更多内容
            for _ in range(10):  # 根据需要调整滚动次数
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1)

            
            # 获取元素对象
            article_content = page.query_selector(".article-content")

            # 检查元素是否存在
            if article_content is not None:
                # 获取元素的内容
                content = article_content.inner_html()  # 获取内部 HTML
                # 或者
                # content = article_content.outer_html()  # 获取完整 HTML
                print(content)
            else:
                print("article-content 元素未找到")
            
            save_content(content)
            return render_template('index.html',content=content)
            
        except Exception as e:
            print(f"爬取文章时出错: {e}")
            
        finally:
            browser.close()


def save_url(url):
    try:
        # 如果 backup.json 文件存在，读取现有数据
        if os.path.exists("./backup/backup.json"):
            with open("./backup/backup.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        # 更新 url 的值
        data["url"] = url

        # 写入 backup.json 文件
        with open("./backup/backup.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"写入 backup.json 文件失败: {e}")
        traceback.print_exc()

def save_content(content):
    try:
        # 如果 backup.json 文件存在，读取现有数据
        if os.path.exists("./backup/backup.json"):
            with open("./backup/backup.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        # 更新 content 的值
        data["content"] = content

        # 写入 backup.json 文件
        with open("./backup/backup.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"写入 backup.json 文件失败: {e}")
        traceback.print_exc()






if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5008) 
    # app.run(host='0.0.0.0', port=5008)
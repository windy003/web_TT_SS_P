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
    """
    使用 Playwright 爬取指定头条文章链接的内容
    
    参数:
        url: 头条文章的URL
    返回:
        包含文章内容的字典
    """
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
            
            
            # page.wait_for_timeout(5000)


            content = ""

            # 获取文章标题
            title = page.query_selector("h1").inner_text() if page.query_selector("h1") else "无标题"
        

            


            try:
                expand_button = page.locator("button", has_text="点击展开剩余")
                if expand_button.count() > 0:  # 检查按钮是否存在
                    expand_button.click()
                print("点击了展开按钮")
            except Exception as e:
                print("点击展开按钮时出错:", e)


            # 向下滚动以加载更多内容
            for _ in range(15):  # 根据需要调整滚动次数
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(1)

            content += title + "<br><br>"
            # 获取文章发布时间
            publish_time = ""
            time_selectors = ["span.pubtime", "div.publication-time", "div.article-meta span"]
            for selector in time_selectors:
                element = page.query_selector(selector)
                if element:
                    publish_time = element.inner_text().strip()
                    break
                    

            content += publish_time + "<br><br>"
            # 获取文章作者
            author = ""
            author_selectors = ["div.article-meta a", "div.author", "span.name"]
            for selector in author_selectors:
                element = page.query_selector(selector)
                if element:
                    author = element.inner_text().strip()
                    break
            
            content += author + "<br><br>"
            # 获取文章正文内容
            article_element = page.query_selector("article")
            
            if article_element:
                # 遍历 article_element 内的所有标签
                for element in article_element.query_selector_all("*"):  # 获取所有子元素
                    tag_name = element.evaluate("el => el.tagName").strip().lower()  # 获取标签名并转换为小写
                    if tag_name == "p":
                        # 处理 p 标签
                        paragraph_text = element.inner_text().strip()
                        print(f"段落内容: {paragraph_text}")
                        content += paragraph_text # 将段落内容添加到正文中
                        
                    elif tag_name == "img":
                        content += element.evaluate("el => el.outerHTML")  # 获取元素的完整 HTML
                    elif tag_name == "section":
                        # 处理 section 标签
                        section_content = element.inner_text().strip()
                        print(f"段落内容: {section_content}")
                        content += section_content   # 将段落内容添加到正文中
                    elif tag_name == "h1":
                        content += element.inner_text().strip()
                    elif tag_name == "div":
                        has_specific_class = element.evaluate("el => el.classList.contains('weitoutiao-html')")
                        if has_specific_class:
                            content += element.inner_text().strip()
            
            
            
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
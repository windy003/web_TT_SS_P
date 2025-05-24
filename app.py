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
import traceback
from flask import send_file


app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'url' in request.form:
            url = request.form['url'].strip()
            return  load_wenzhang_from_url(url)


    return render_template('index.html')


def load_wenzhang_from_url(url):
    print("使用的是load_wenzhang_from_url函数")
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




            # 等待页面加载
            page.goto(url, wait_until="networkidle", timeout=60000)


            # 设置页面缩放比例到最小（10%）
            page.evaluate("document.body.style.zoom = '0.1'")
            
            # 等待文章内容加载
            page.wait_for_selector("article", state="visible", timeout=10000)
            

            content = []

            # 获取文章标题
            title = page.query_selector("h1").inner_text() if page.query_selector("h1") else "无标题"
        

            
            

            # 点击展开按钮
            try:
                expand_button = page.locator("button", has_text="点击展开剩余")
                if expand_button.count() > 0:  # 检查按钮是否存在
                    expand_button.click()
                print("点击了展开按钮")
            except Exception as e:
                print("点击展开按钮时出错:", e)




            # # 向下滚动以加载更多内容
            # for _ in range(10):  # 根据需要调整滚动次数
            #     page.evaluate("window.scrollBy(0, window.innerHeight)")
            #     time.sleep(1)

            content.append(title)
            # 获取文章发布时间
            publish_time = ""
            time_selectors = ["span.pubtime", "div.publication-time", "div.article-meta span"]
            for selector in time_selectors:
                element = page.query_selector(selector)
                if element:
                    publish_time = element.inner_text().strip()
                    break
                    

            content.append(publish_time)
            # 获取文章作者
            author = ""
            author_selectors = ["div.article-meta a", "div.author", "span.name"]
            for selector in author_selectors:
                element = page.query_selector(selector)
                if element:
                    author = element.inner_text().strip()
                    break
            
            content.append(author)


            # 自动识别评论并向下滚动
            try:
                comment_selector = ".ttp-comment-wrapper, .ttp-comment-block,.comment-folded"
                
                
                # 最大滚动次数，防止无限循环
                max_scroll_attempts = 30
                scroll_count = 0
                comment_visible = False
                
                while scroll_count < max_scroll_attempts and not comment_visible:
                    # 检查评论区是否在视口中
                    comment_elements = page.query_selector_all(comment_selector)
                    for comment_element in comment_elements:
                        # 使用 JavaScript 判断元素是否在视口中
                        is_in_viewport = comment_element.evaluate("""
                            el => {
                                const rect = el.getBoundingClientRect();
                                return (
                                    rect.top < (window.innerHeight || document.documentElement.clientHeight) &&
                                    rect.bottom > 0 &&
                                    rect.left < (window.innerWidth || document.documentElement.clientWidth) &&
                                    rect.right > 0
                                );
                            }
                        """)
                        if is_in_viewport:
                            print("评论区域已出现在屏幕上")
                            comment_visible = True
                            break
                    
                    if comment_visible:
                        break
                    
                    # 向下滚动一个窗口高度
                    page.evaluate("window.scrollBy(0, window.innerHeight)")
                    scroll_count += 1
                    print(f"滚动次数: {scroll_count}")
                    
                    # 等待一小段时间让内容加载
                    time.sleep(2)
                
                        
            except Exception as e:
                print(f"自动识别评论并向下滚动时出错: {e}")
                traceback.print_exc()



            # 获取文章正文内容
            article_element = page.query_selector("article")
                
            if article_element:
                content_final = "<br>".join(scan_element(article_element, content))
                

                generate_static_html(content_final)

                with open("./tmp/tmp.txt", "w", encoding="utf-8") as f:
                    f.write(content_final)

                return render_template('index.html',content=content_final)
                
        except Exception as e:
            print(f"出错: {e}")
            traceback.print_exc()
            
        # finally:
        #     browser.close()


def search_text_in_merged_content_str(content,text):
    merged_content = "".join(content)
    if text in merged_content:
        return True
    else:
        return False



def scan_element(element,content):

    try:
        for ele in element.query_selector_all(":scope > *"):
            tag_name = ele.evaluate("el => el.tagName").strip().lower()
            if tag_name == "p":
                p_text = ele.evaluate("el => el.textContent").strip()
                if p_text and p_text not in content and not search_text_in_merged_content_str(content,p_text):
                    content.append(p_text)
                scan_element(ele,content)
            elif tag_name == "img":
                content.append(ele.evaluate("el => el.outerHTML"))  # 获取元素的完整 HTML
            elif tag_name == "section":
                # 处理 section 标签
                section_content = ele.evaluate("el => el.textContent").strip()
                # print(f"段落内容: {section_content}")
                if section_content and section_content not in content and not search_text_in_merged_content_str(content,section_content):
                    content.append(section_content)   # 将段落内容添加到正文中
                scan_element(ele,content)
            elif tag_name == "h1":
                content.append(ele.evaluate("el => el.textContent").strip())
            elif tag_name == "div":
                if ele.evaluate("el => el.classList.contains('weitoutiao-html')"):
                    weitoutiao_html = ele.evaluate("el => el.outerHTML").strip()
                    if weitoutiao_html and weitoutiao_html not in content:
                        content.append(weitoutiao_html)
                scan_element(ele,content)
            elif tag_name == "ol":
                content.append("<br>")
                li_elements = ele.query_selector_all("li")  # 获取所有 li 元素
                for index, li in enumerate(li_elements, start=1):  # 遍历 li 元素并添加序号
                    li_text = li.inner_text().strip()  # 获取 li 元素的文本内容
                    content.append(f"{index}. {li_text}<br>")  # 添加序号和文本到 content
            elif tag_name == "ul":
                content.append("<br><br>")
                li_elements = ele.query_selector_all("li")  # 获取所有 li 元素
                for index, li in enumerate(li_elements, start=1):  # 遍历 li 元素并添加序号
                    li_text = li.inner_text().strip()  # 获取 li 元素的文本内容
                    content.append(f"{index}. {li_text}<br>")  # 添加序号和文本到 content
                content.append("<br>")
            elif tag_name == "li":
                content.append("<br>")
                content.append(ele.inner_text().strip())
                content.append("<br>")
            elif tag_name == "span":
                scan_element(ele,content)
            elif tag_name == "blockquote":
                scan_element(ele,content)

        return content
    
        
    
    except Exception as e:
        print(f"扫描元素时出错: {e}")
        traceback.print_exc()

    




def generate_static_html(content):
    """生成静态HTML文件"""
    try:
        
        # 读取模板文件
        with open("./templates/index.html", "r", encoding="utf-8") as f:
            template_content = f.read()
        
        # 替换模板中的内容
        # 移除Flask模板语法，替换为静态内容
        static_html = template_content.replace(
            "{{ url_for('static', filename='180x180.png') }}", 
            "../static/180x180.png"
        )
        
        # 添加内容到页面中
        if content:
            content_section = f'''
                <div id="div_tag">
                {content}
                </div>
            '''
        else:
            content_section = '''
            <div id="div_tag">
                暂无内容
            </div>
            '''

        # 正则表达式（贪婪模式）
        pattern = re.compile(r'<div id="div_tag">.*?</div>', re.DOTALL)

        # 查找匹配
        match = pattern.search(static_html)

        # 如果有匹配项，替换匹配的内容
        if match:
            # 从匹配对象中提取匹配的字符串
            matched_text = match.group()
            # 替换匹配的内容
            static_html = static_html.replace(matched_text, content_section)
        # 写入静态HTML文件
        with open("./backup/latest.html", "w", encoding="utf-8") as f:
            f.write(static_html)
        
       
        print(f"静态HTML文件生成成功")
        
    except Exception as e:
        print(f"生成静态HTML文件失败: {e}")
        traceback.print_exc()




@app.route('/latest')
def serve_latest():
    if os.path.exists("./backup/latest.html"):
        return send_file("./backup/latest.html")




if __name__ == '__main__':
    from waitress import serve
    serve(app, host='0.0.0.0', port=5008) 
    # app.run(host='0.0.0.0', port=5008)